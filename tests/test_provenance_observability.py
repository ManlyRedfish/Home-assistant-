"""
Tests for the V8.5 HVAC Provenance Logger (issue #66).

The provenance logger is a narrow, observability-only automation that
appends rows to the Google Sheets worksheet `hvac_provenance_log` so
operators / analysts can classify whether each tracked HVAC change looks
manual, automation-driven, integration-driven, restore-driven, or unknown.

These tests guard the design contract:
  1. The automation exists with the documented id / mode / max.
  2. It writes via google_sheets.append_sheet using the existing
     `!secret google_sheets_config_entry`, targeting `hvac_provenance_log`.
  3. The action body never mutates control surfaces (no climate.set_*,
     no timer.*, no input_*.*, no notify.*, no shell_command.*,
     no script.log_event).
  4. No automation reads from `hvac_provenance_log`. The tab is
     HA-write-only; only the provenance logger's append_sheet target may
     reference its name.

See docs/hvac_provenance_logger_design.md §10 for the full acceptance
criteria.
"""

import os
import re

import yaml
import pytest


class MooseProvenanceLoader(yaml.SafeLoader):
    pass


def _secret(loader, node):
    return f"SECRET_{node.value}"


def _include(loader, node):
    return f"INCLUDE_{node.value}"


def _input(loader, node):
    return f"INPUT_{node.value}"


def _include_dir_merge_list(loader, node):
    return []


MooseProvenanceLoader.add_constructor("!secret", _secret)
MooseProvenanceLoader.add_constructor("!include", _include)
MooseProvenanceLoader.add_constructor("!input", _input)
MooseProvenanceLoader.add_constructor(
    "!include_dir_merge_list", _include_dir_merge_list
)
MooseProvenanceLoader.add_constructor("!include_dir_named", _include_dir_merge_list)


PROVENANCE_ID = "v8_5_hvac_provenance_logger"
PROVENANCE_WORKSHEET = "hvac_provenance_log"

# Service calls forbidden in the provenance logger's action body. These map
# 1:1 to docs/hvac_provenance_logger_design.md §10 acceptance criterion 4.
FORBIDDEN_SERVICES = {
    "climate.set_temperature",
    "climate.set_hvac_mode",
    "timer.start",
    "timer.cancel",
    "timer.finish",
    "input_boolean.turn_on",
    "input_boolean.turn_off",
    "input_text.set_value",
    "input_datetime.set_datetime",
    "script.log_event",
}

# Domain-prefix forbids: any service in these domains is rejected.
FORBIDDEN_DOMAINS = ("notify.", "shell_command.")


@pytest.fixture(scope="module")
def automations_data():
    file_path = os.path.join(os.path.dirname(__file__), "..", "automations.yaml")
    with open(file_path, "r") as f:
        return yaml.load(f, Loader=MooseProvenanceLoader)


@pytest.fixture(scope="module")
def provenance_logger(automations_data):
    for auto in automations_data:
        if auto.get("id") == PROVENANCE_ID:
            return auto
    pytest.fail(f"Provenance logger automation with id '{PROVENANCE_ID}' not found")


@pytest.fixture(scope="module")
def automations_yaml_text():
    file_path = os.path.join(os.path.dirname(__file__), "..", "automations.yaml")
    with open(file_path, "r") as f:
        return f.read()


def _iter_action_items(action):
    """Yield every action dict in a possibly-nested action sequence."""
    if action is None:
        return
    if isinstance(action, dict):
        action = [action]
    for item in action:
        if not isinstance(item, dict):
            continue
        yield item
        for nested_key in (
            "choose",
            "if",
            "repeat",
            "parallel",
            "default",
            "then",
            "else",
            "sequence",
        ):
            nested = item.get(nested_key)
            if nested is None:
                continue
            if nested_key == "choose" and isinstance(nested, list):
                for choice in nested:
                    if isinstance(choice, dict):
                        for sub in _iter_action_items(choice.get("sequence")):
                            yield sub
                continue
            if isinstance(nested, list):
                for sub in _iter_action_items(nested):
                    yield sub
            elif isinstance(nested, dict):
                for sub in _iter_action_items([nested]):
                    yield sub


def _service_of(item):
    """Return the service identifier of an action item, or None."""
    if not isinstance(item, dict):
        return None
    return item.get("action") or item.get("service")


def test_provenance_logger_exists(provenance_logger):
    """Automation `v8_5_hvac_provenance_logger` exists with mode=parallel, max=20."""
    assert provenance_logger.get("id") == PROVENANCE_ID
    assert (
        provenance_logger.get("mode") == "parallel"
    ), "Provenance logger must declare mode: parallel"
    assert provenance_logger.get("max") == 20, "Provenance logger must declare max: 20"


def test_provenance_logger_uses_google_sheets_secret(provenance_logger):
    """Logger uses google_sheets.append_sheet with !secret config_entry and the
    `hvac_provenance_log` worksheet."""
    sheet_calls = []
    for item in _iter_action_items(provenance_logger.get("action")):
        if _service_of(item) == "google_sheets.append_sheet":
            sheet_calls.append(item)

    assert len(sheet_calls) == 1, (
        "Provenance logger must contain exactly one google_sheets.append_sheet "
        f"call (found {len(sheet_calls)})"
    )

    data = sheet_calls[0].get("data", {}) or {}
    config_entry = data.get("config_entry")
    assert config_entry == "SECRET_google_sheets_config_entry", (
        "Provenance logger must reuse !secret google_sheets_config_entry "
        f"(found: {config_entry!r})"
    )
    assert data.get("worksheet") == PROVENANCE_WORKSHEET, (
        "Provenance logger must target worksheet 'hvac_provenance_log' "
        f"(found: {data.get('worksheet')!r})"
    )


def test_provenance_logger_does_not_mutate_control(provenance_logger):
    """Action block must not call any control-surface service. The logger is
    observability-only — it may not change climate state, helpers, timers,
    notify users, run shell commands, or revive script.log_event."""
    offenders = []
    for item in _iter_action_items(provenance_logger.get("action")):
        svc = _service_of(item)
        if svc is None:
            continue
        if svc in FORBIDDEN_SERVICES:
            offenders.append(svc)
        elif any(svc.startswith(prefix) for prefix in FORBIDDEN_DOMAINS):
            offenders.append(svc)

    assert not offenders, (
        "Provenance logger action body contains forbidden control-surface "
        f"service calls: {sorted(set(offenders))}. The logger must remain "
        "observability-only (see docs/hvac_provenance_logger_design.md §10)."
    )


def _contains_string_reference(value, needle):
    if isinstance(value, dict):
        return any(
            _contains_string_reference(key, needle)
            or _contains_string_reference(item, needle)
            for key, item in value.items()
        )

    if isinstance(value, list):
        return any(_contains_string_reference(item, needle) for item in value)

    if isinstance(value, str):
        return needle in value

    return False


def test_contains_string_reference_helper():
    """Verify that _contains_string_reference correctly finds strings in nested structures."""
    needle = "find_me"

    # Should find in string values
    assert _contains_string_reference("find_me_here", needle) is True

    # Should find in dict values
    assert _contains_string_reference({"key": "yes_find_me"}, needle) is True

    # Should find in dict keys
    assert _contains_string_reference({"find_me_key": "value"}, needle) is True

    # Should find in nested lists
    assert _contains_string_reference(["a", ["b", "c_find_me_d"]], needle) is True

    # Should ignore non-strings correctly
    assert _contains_string_reference(123, needle) is False
    assert _contains_string_reference({"key": 456}, needle) is False
    assert _contains_string_reference(True, needle) is False


def test_no_automation_reads_hvac_provenance_log(
    automations_data, automations_yaml_text
):
    """No automation may reference `hvac_provenance_log` except the provenance
    logger's google_sheets.append_sheet write target. Anything else implies
    HA is reading from (or otherwise consuming) the forensic tab."""
    # Coarse text guard: the worksheet name should appear only in the logger
    # automation block — once as the worksheet target, optionally repeated
    # in section header comments. Any reference outside that block is
    # disallowed.
    occurrences = [
        m.start()
        for m in re.finditer(re.escape(PROVENANCE_WORKSHEET), automations_yaml_text)
    ]
    assert occurrences, (
        f"Expected at least one mention of '{PROVENANCE_WORKSHEET}' in "
        "automations.yaml (the logger's worksheet target)."
    )

    # Structural guard: walk every other automation and assert nothing in its
    # triggers, conditions, or actions references the worksheet name.
    for auto in automations_data:
        if auto.get("id") == PROVENANCE_ID:
            continue
        assert not _contains_string_reference(auto, PROVENANCE_WORKSHEET), (
            f"Automation '{auto.get('id')}' references "
            f"'{PROVENANCE_WORKSHEET}'. The provenance tab must remain "
            "HA-write-only — no other automation may read or mention it."
        )
