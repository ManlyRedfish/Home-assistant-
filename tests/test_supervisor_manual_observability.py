"""
Regression tests for the observability-only supervisor/manual-override
telemetry enhancement.

The added fields are forensic outputs. They must not become inputs to the
comfort supervisor, safety gates, Section 14 boost, truth math, setpoints, or
thresholds.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml


class MooseLoader(yaml.SafeLoader):
    pass


def _secret(loader, node):
    return f"SECRET_{node.value}"


def _include(loader, node):
    return f"INCLUDE_{node.value}"


def _input(loader, node):
    return f"INPUT_{node.value}"


def _include_dir_merge_list(loader, node):
    return []


MooseLoader.add_constructor("!secret", _secret)
MooseLoader.add_constructor("!include", _include)
MooseLoader.add_constructor("!input", _input)
MooseLoader.add_constructor("!include_dir_merge_list", _include_dir_merge_list)
MooseLoader.add_constructor("!include_dir_named", _include_dir_merge_list)


ROOT = Path(__file__).resolve().parents[1]
AUTOMATIONS = ROOT / "automations.yaml"
CONFIGURATION = ROOT / "configuration.yaml"

TELEMETRY_ID = "vtherm_mega_tracker_v5"
PROVENANCE_ID = "v8_5_hvac_provenance_logger"
SUPERVISOR_ENTITY = "automation.v7_5_main_supervisor"
MANUAL_TIMER = "timer.manual_hvac_override"
NEW_FIELDS = {
    "Supervisor_Enabled",
    "Manual_Override_State",
    "Manual_Override_Remaining_Sec",
}

# These hashes intentionally lock the untouched control surfaces for this
# observability-only change. If this test fails, the PR is no longer limited to
# telemetry/provenance/docs and needs explicit control-behavior review.
EXPECTED_SECTION_HASHES = {
    "section2_main_supervisor": (
        "# SECTION 2: MAIN SUPERVISOR",
        "# SECTION 3:",
        "6d409d3c584cbd5eafa76fd9c9ac9c36e2c616a90c7c271bfd59ad512e0925e5",
    ),
    "section3_safety_gates": (
        "# SECTION 3: SAFETY GATES",
        "# SECTION 4:",
        "bc762a54c7c33b739a15c4a0d85e40c6141d82f209373f5e0a7cd32591944a75",
    ),
    "section14_lr_boost": (
        "# SECTION 14: V8.4 LR HEATING RECOVERY BOOST PILOT",
        "# SECTION 15:",
        "fcb18b5953a9bfb9f1d1e9f10ba8217cc46c7db63cb268bfab5daa6ffd2b71c3",
    ),
}
EXPECTED_CONFIGURATION_HASH = "74f482be8cd06fe8bbc1515854aa452f3fb64d992a1820681d3fd978ae55bc92"


@pytest.fixture(scope="module")
def automations_text() -> str:
    return AUTOMATIONS.read_text()


@pytest.fixture(scope="module")
def automations_data():
    return yaml.load(AUTOMATIONS.read_text(), Loader=MooseLoader)


def _find_automation(automations_data, automation_id: str):
    for automation in automations_data:
        if automation.get("id") == automation_id:
            return automation
    pytest.fail(f"Automation {automation_id!r} not found")


def _iter_action_items(action):
    if action is None:
        return
    if isinstance(action, dict):
        action = [action]
    for item in action:
        if not isinstance(item, dict):
            continue
        yield item
        for nested_key in ("choose", "if", "repeat", "parallel", "default", "then", "else", "sequence"):
            nested = item.get(nested_key)
            if nested is None:
                continue
            if nested_key == "choose" and isinstance(nested, list):
                for choice in nested:
                    if isinstance(choice, dict):
                        yield from _iter_action_items(choice.get("sequence"))
                continue
            if isinstance(nested, list):
                yield from _iter_action_items(nested)
            elif isinstance(nested, dict):
                yield from _iter_action_items([nested])


def _append_sheet_payload(automation: dict, worksheet: str) -> dict:
    for item in _iter_action_items(automation.get("action")):
        if (item.get("action") or item.get("service")) != "google_sheets.append_sheet":
            continue
        data = item.get("data") or {}
        if data.get("worksheet") == worksheet:
            payload = data.get("data")
            assert isinstance(payload, dict)
            return payload
    pytest.fail(f"No google_sheets.append_sheet action targeting {worksheet!r}")


def _section(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start + 1)
    return text[start:end]


def test_v55_wide_row_contains_supervisor_and_manual_override_fields(automations_data):
    tracker = _find_automation(automations_data, TELEMETRY_ID)
    payload = _append_sheet_payload(tracker, "VTherm_Launch_Data_v5_5")

    assert NEW_FIELDS <= set(payload), "V5.5 wide-row telemetry fields are missing"
    assert SUPERVISOR_ENTITY in payload["Supervisor_Enabled"]
    assert MANUAL_TIMER in payload["Manual_Override_State"]
    assert MANUAL_TIMER in payload["Manual_Override_Remaining_Sec"]


def test_manual_override_state_exports_full_timer_state_not_boolean(automations_data):
    tracker = _find_automation(automations_data, TELEMETRY_ID)
    template = _append_sheet_payload(tracker, "VTherm_Launch_Data_v5_5")[
        "Manual_Override_State"
    ]

    assert "states('timer.manual_hvac_override')" in template
    assert "unknown" in template and "unavailable" in template
    assert "active" not in template, "state export must not collapse timer to active/inactive"
    assert "true" not in template.lower() and "false" not in template.lower()


def test_manual_override_remaining_seconds_template_is_active_only_and_non_negative(automations_data):
    tracker = _find_automation(automations_data, TELEMETRY_ID)
    template = _append_sheet_payload(tracker, "VTherm_Launch_Data_v5_5")[
        "Manual_Override_Remaining_Sec"
    ]

    assert "states('timer.manual_hvac_override')" in template
    assert "state_attr('timer.manual_hvac_override', 'finishes_at')" in template
    assert "t == 'active'" in template
    assert "as_datetime(finishes) - now()" in template
    assert "| max" in template and ", 0]" in template, (
        "remaining seconds must be clamped at zero and never go negative"
    )
    assert "{% else %}{% endif %}" in template, (
        "remaining seconds must stay blank when inactive/unknown/unavailable"
    )


def test_provenance_logger_observes_supervisor_enabled_disabled_transitions(automations_data):
    logger = _find_automation(automations_data, PROVENANCE_ID)
    triggers = logger.get("trigger") or []

    assert any(
        trigger.get("platform") == "state"
        and trigger.get("entity_id") == SUPERVISOR_ENTITY
        and trigger.get("id") == "supervisor_enabled_state"
        for trigger in triggers
    ), "Section 15 must observe main-supervisor enable/disable transitions"

    variables = next(
        item.get("variables")
        for item in _iter_action_items(logger.get("action"))
        if isinstance(item.get("variables"), dict)
    )
    candidate_template = variables["automation_candidate_v"]
    assert SUPERVISOR_ENTITY in candidate_template
    assert "v7_5_main_supervisor" in candidate_template


def test_no_control_automation_consumes_new_telemetry_fields(automations_text):
    section1 = _section(automations_text, "# SECTION 1:", "# SECTION 2:")
    rest = automations_text.replace(section1, "")

    for field in NEW_FIELDS:
        assert field not in rest, f"{field} leaked outside the write-only telemetry exporter"

    for section_start, section_end in [
        ("# SECTION 2:", "# SECTION 3:"),
        ("# SECTION 3:", "# SECTION 4:"),
        ("# SECTION 14:", "# SECTION 15:"),
    ]:
        control_section = _section(automations_text, section_start, section_end)
        assert SUPERVISOR_ENTITY not in control_section
        for field in NEW_FIELDS:
            assert field not in control_section


def test_no_automation_reads_google_sheets_tabs(automations_data):
    for automation in automations_data:
        for item in _iter_action_items(automation.get("action")):
            service = item.get("action") or item.get("service")
            if service:
                assert not service.startswith("google_sheets.get"), (
                    "Google Sheets must remain a write-only forensic sink"
                )


def test_control_surfaces_and_truth_configuration_are_byte_for_byte_unchanged(automations_text):
    for name, (start, end, expected_hash) in EXPECTED_SECTION_HASHES.items():
        digest = hashlib.sha256(_section(automations_text, start, end).encode()).hexdigest()
        assert digest == expected_hash, f"{name} changed in an observability-only PR"

    configuration_digest = hashlib.sha256(CONFIGURATION.read_bytes()).hexdigest()
    assert configuration_digest == EXPECTED_CONFIGURATION_HASH, (
        "configuration.yaml changed; truth weights/helpers are outside this PR's scope"
    )


def test_verified_supervisor_entity_id_is_documented(automations_text):
    assert "Verified live main-supervisor entity_id: automation.v7_5_main_supervisor" in automations_text
    assert "Do not derive this from the YAML id alone" in automations_text
