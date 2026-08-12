"""Structural contract for the bounded H safety-ceiling ordering repair."""

from pathlib import Path

import yaml


class AutomationLoader(yaml.SafeLoader):
    pass


AutomationLoader.add_constructor("!secret", lambda loader, node: node.value)

AUTOMATIONS = yaml.load(
    Path("automations.yaml").read_text(encoding="utf-8"),
    Loader=AutomationLoader,
)


def _automation(automation_id):
    return next(item for item in AUTOMATIONS if item.get("id") == automation_id)


def _service(action):
    return action.get("action") or action.get("service")


def test_cooling_safety_off_precedes_fallible_setup_and_preserves_timing():
    ceiling = _automation("v7_5_safety_ceiling_gates")
    cooling = ceiling["action"][1]["choose"][0]["sequence"]

    assert _service(cooling[0]) == "climate.set_hvac_mode"
    assert cooling[0]["target"]["entity_id"] == "{{ trigger.id }}"
    assert cooling[0]["data"] == {"hvac_mode": "off"}

    # Native Core stops a sequence when an action raises. Because OFF is first,
    # failure of this later setup cannot suppress or undo that protective OFF.
    assert _service(cooling[1]) == "climate.set_temperature"
    assert cooling[1]["target"]["entity_id"] == "{{ trigger.id }}"
    assert cooling[1]["data"] == {"hvac_mode": "cool", "temperature": 68}
    assert cooling[2] == {"delay": "00:45:00"}
    assert _service(cooling[3]) == "climate.set_hvac_mode"
    assert cooling[3]["data"] == {"hvac_mode": "off"}


def test_non_cooling_safety_off_precedes_fan_only_and_preserves_timing():
    ceiling = _automation("v7_5_safety_ceiling_gates")
    assert ceiling["action"][1]["default"] == [
        {
            "action": "climate.set_hvac_mode",
            "target": {"entity_id": "{{ trigger.id }}"},
            "data": {"hvac_mode": "off"},
        },
        {
            "action": "climate.set_hvac_mode",
            "target": {"entity_id": "{{ trigger.id }}"},
            "data": {"hvac_mode": "fan_only"},
        },
        {"delay": "00:45:00"},
        {
            "action": "climate.set_hvac_mode",
            "target": {"entity_id": "{{ trigger.id }}"},
            "data": {"hvac_mode": "off"},
        },
    ]


def test_ceiling_has_no_blind_climate_continue_on_error():
    ceiling = _automation("v7_5_safety_ceiling_gates")

    def walk(value):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)

    climate_calls = [
        node for node in walk(ceiling)
        if str(_service(node) or "").startswith("climate.")
    ]
    assert climate_calls
    assert all("continue_on_error" not in call for call in climate_calls)


def test_adjacent_watchdogs_keep_their_ids_and_protective_thresholds():
    lr_floor = _automation("v8_2_lr_runaway_cooling_cutoff")
    master_floor = _automation("v8_2_master_emergency_floor")
    truth_failsafe = _automation("v8_6_truth_unavailable_cooling_failsafe")
    reconciliation = _automation("v8_6b_truth_unavailable_cooling_reconciliation")

    assert lr_floor["trigger"][0]["below"] == 60
    assert master_floor["trigger"][0]["below"] == 58
    assert len(truth_failsafe["trigger"]) == 4
    assert {trigger["for"] for trigger in truth_failsafe["trigger"]} == {"00:02:00"}
    assert {trigger["platform"] for trigger in reconciliation["trigger"]} == {
        "homeassistant",
        "time_pattern",
    }
