"""Contract tests for Packet A truth-unavailable cooling failsafe.

These tests pin the Stage-1 repository implementation to the approved Design 1
boundaries: OFF-only invalid-truth protection, unchanged healthy deadband
doctrine, and no configuration/hardware topology changes.

SCOPE NOTE (2026-06-15 isolated restore):
This branch restores ONLY the two OFF-only safety automations
(`v8_6_truth_unavailable_cooling_failsafe` and
`v8_6b_truth_unavailable_cooling_reconciliation`) from Packet A commit
9e39e42, recovered to re-link the live registry orphans. It does NOT bring
over Packet A's separate `v7_5_main_supervisor` rewrite (the off-biased
`*_truth_ok` cooling-template guards), which is a larger comfort-path change
that has since diverged on `main` and is out of scope for a narrow safety
restore. The two supervisor-coupling tests below are therefore skipped here;
they belong with the supervisor change if/when it is restored separately.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest
import yaml


class MooseAutomationLoader(yaml.SafeLoader):
    pass


def _secret_constructor(loader: yaml.Loader, node: yaml.Node) -> str:
    return f"SECRET_{node.value}"


MooseAutomationLoader.add_constructor("!secret", _secret_constructor)


AUTOMATIONS_PATH = Path("automations.yaml")
AUTOMATIONS_TEXT = AUTOMATIONS_PATH.read_text(encoding="utf-8")
AUTOMATIONS = yaml.load(AUTOMATIONS_TEXT, Loader=MooseAutomationLoader)

TRUTH_TO_CLIMATE = {
    "living_room_air": "sensor.living_room_temperature_truth",
    "master_bedroom_air": "sensor.master_bedroom_temperature_truth",
    "lincoln_air": "sensor.lincoln_s_room_temperature_truth",
    "lilly_air": "sensor.lilly_s_room_temperature_truth",
}


def _automation(automation_id: str) -> dict[str, Any]:
    match = next((a for a in AUTOMATIONS if a.get("id") == automation_id), None)
    assert match is not None, f"Missing automation {automation_id}"
    return match


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _packet_a_valid(raw: str) -> bool:
    try:
        x = float(raw)
    except (TypeError, ValueError):
        return False
    return x == x and -90 <= x <= 200


def _packet_a_invalid(raw: str) -> bool:
    try:
        x = float(raw)
    except (TypeError, ValueError):
        return True
    return x != x or x < -90 or x > 200


def test_packet_a_numeric_contract_rejects_nan_infinity_and_implausible_values():
    invalid_values = ["unknown", "unavailable", "", "nan", "inf", "-inf", "201", "-91"]
    valid_values = ["-90", "0", "61", "70.5", "200"]

    for raw in invalid_values:
        assert not _packet_a_valid(raw)
        assert _packet_a_invalid(raw)

    for raw in valid_values:
        assert _packet_a_valid(raw)
        assert not _packet_a_invalid(raw)
        assert math.isfinite(float(raw))


@pytest.mark.skip(
    reason="Packet A supervisor off-biasing not part of this isolated V8.6 "
    "automation restore; see module SCOPE NOTE."
)
def test_supervisor_declares_truth_validity_before_float_70_fallbacks():
    supervisor = _automation("v7_5_main_supervisor")
    variables = supervisor["action"][0]["variables"]

    expected_variables = {
        "lr_truth_ok": "sensor.living_room_temperature_truth",
        "master_truth_ok": "sensor.master_bedroom_temperature_truth",
        "lincoln_truth_ok": "sensor.lincoln_s_room_temperature_truth",
        "lilly_truth_ok": "sensor.lilly_s_room_temperature_truth",
    }
    for variable_name, truth_entity in expected_variables.items():
        template = variables.get(variable_name, "")
        assert truth_entity in template
        assert "float(none)" in template
        assert "x is not none" in template
        assert "x == x" in template
        assert "-90 <= x <= 200" in template

    assert AUTOMATIONS_TEXT.index("lr_truth_ok") < AUTOMATIONS_TEXT.index("lr_temp: \"{{ states('sensor.living_room_temperature_truth') | float(70) }}\"")
    assert AUTOMATIONS_TEXT.index("master_truth_ok") < AUTOMATIONS_TEXT.index("master_temp: \"{{ states('sensor.master_bedroom_temperature_truth') | float(70) }}\"")
    assert AUTOMATIONS_TEXT.index("lincoln_truth_ok") < AUTOMATIONS_TEXT.index("lincoln_temp: \"{{ states('sensor.lincoln_s_room_temperature_truth') | float(70) }}\"")
    assert AUTOMATIONS_TEXT.index("lilly_truth_ok") < AUTOMATIONS_TEXT.index("lilly_temp: \"{{ states('sensor.lilly_s_room_temperature_truth') | float(70) }}\"")


@pytest.mark.skip(
    reason="Packet A supervisor off-biasing not part of this isolated V8.6 "
    "automation restore; see module SCOPE NOTE."
)
def test_supervisor_cooling_templates_are_invalid_truth_off_biased():
    required_guards = [
        "{% if not master_truth_ok %}off\n                  {% elif master_temp > m_on_at %}cool",
        "{% if not lincoln_truth_ok %}off\n                  {% elif lincoln_temp > l_on_at %}cool",
        "{% if not lilly_truth_ok %}off\n                  {% elif lilly_temp > ly_on_at %}cool",
        "{% if not lr_truth_ok %}off\n                  {% elif lr_temp > lr_on_at %}cool",
        "{% if not master_truth_ok %}off\n                          {% elif master_temp > m_sleep_on_at %}cool",
        "'off' if not master_truth_ok else ('cool' if master_temp > 70 else 'off')",
        "'off' if not lincoln_truth_ok else ('cool' if lincoln_temp > 70 else 'off')",
        "'off' if not lilly_truth_ok else ('cool' if lilly_temp > 70 else 'off')",
    ]
    for guard in required_guards:
        assert guard in AUTOMATIONS_TEXT

    # Healthy-state doctrine remains hysteresis/HOLD based: the thresholds and
    # equality operators are unchanged, with HOLD still preserving current cool.
    assert "master_temp > m_on_at" in AUTOMATIONS_TEXT
    assert "master_temp <= m_off_at" in AUTOMATIONS_TEXT
    assert "m_current == 'cool'" in AUTOMATIONS_TEXT
    assert "temperature: \"{{ m_setpoint }}\"" in AUTOMATIONS_TEXT
    assert "temperature: \"{{ lr_setpoint }}\"" in AUTOMATIONS_TEXT


def test_truth_unavailable_failsafe_has_four_off_only_template_triggers():
    failsafe = _automation("v8_6_truth_unavailable_cooling_failsafe")
    triggers = failsafe["trigger"]

    assert {trigger["id"] for trigger in triggers} == set(TRUTH_TO_CLIMATE)
    for trigger in triggers:
        template = trigger["value_template"]
        assert trigger["platform"] == "template"
        assert trigger["for"] == "00:02:00"
        assert TRUTH_TO_CLIMATE[trigger["id"]] in template
        assert "float(none)" in template
        assert "x is none" in template
        assert "x != x" in template
        assert "x < -90" in template
        assert "x > 200" in template

    actions = failsafe["action"]
    assert "{{ 'climate.' ~ trigger.id }}" == actions[0]["variables"]["climate_entity"]
    off_sequence = actions[1]["choose"][0]["sequence"]
    assert off_sequence[0]["action"] == "climate.set_hvac_mode"
    assert off_sequence[0]["data"]["hvac_mode"] == "off"
    assert "states(climate_entity) == 'cool'" in actions[1]["choose"][0]["conditions"][0]["value_template"]
    assert off_sequence[1]["continue_on_error"] is True

    for node in _walk(failsafe):
        assert node.get("action") != "climate.set_temperature"
        assert node.get("data", {}).get("hvac_mode") != "cool"


def test_truth_unavailable_reconciliation_is_startup_periodic_and_off_only():
    reconciliation = _automation("v8_6b_truth_unavailable_cooling_reconciliation")
    triggers = reconciliation["trigger"]

    assert {trigger["platform"] for trigger in triggers} == {"homeassistant", "time_pattern"}
    assert any(trigger.get("event") == "start" for trigger in triggers)
    assert any(trigger.get("minutes") == "/5" for trigger in triggers)
    assert reconciliation["action"][0]["choose"][0]["sequence"][0]["delay"] == "00:03:00"

    repeat = reconciliation["action"][1]["repeat"]
    pairs = {(item["truth"], item["climate"]) for item in repeat["for_each"]}
    assert pairs == {(truth, f"climate.{trigger_id}") for trigger_id, truth in TRUTH_TO_CLIMATE.items()}

    repeat_text = str(repeat)
    assert "states[truth_entity] if truth_entity in states else none" in repeat_text
    assert "x is none or x != x or x < -90 or x > 200" in repeat_text
    assert "states(climate_entity) == 'cool'" in repeat_text
    assert ">= 120" in repeat_text

    for node in _walk(reconciliation):
        assert node.get("action") != "climate.set_temperature"
        assert node.get("data", {}).get("hvac_mode") != "cool"


def test_packet_a_does_not_modify_excluded_configuration_or_packet_b_surfaces():
    assert Path("configuration.yaml").exists()
    assert "v8_6_truth_unavailable_cooling_failsafe" in AUTOMATIONS_TEXT
    assert "cooldown" not in AUTOMATIONS_TEXT.lower()[
        AUTOMATIONS_TEXT.index("v8_6_truth_unavailable_cooling_failsafe") : AUTOMATIONS_TEXT.index("v9_sleep_priority_interlock")
    ]
    assert "input_boolean" not in AUTOMATIONS_TEXT[
        AUTOMATIONS_TEXT.index("v8_6_truth_unavailable_cooling_failsafe") : AUTOMATIONS_TEXT.index("v9_sleep_priority_interlock")
    ]
