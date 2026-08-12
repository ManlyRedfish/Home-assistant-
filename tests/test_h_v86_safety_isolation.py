"""Structural contract for the bounded H V8.6B per-zone isolation repair."""

from pathlib import Path

import yaml


class AutomationLoader(yaml.SafeLoader):
    pass


AutomationLoader.add_constructor("!secret", lambda loader, node: node.value)

AUTOMATIONS = yaml.load(
    Path("automations.yaml").read_text(encoding="utf-8"),
    Loader=AutomationLoader,
)

EXPECTED_PAIRS = [
    {
        "truth": "sensor.living_room_temperature_truth",
        "climate": "climate.living_room_air",
    },
    {
        "truth": "sensor.master_bedroom_temperature_truth",
        "climate": "climate.master_bedroom_air",
    },
    {
        "truth": "sensor.lincoln_s_room_temperature_truth",
        "climate": "climate.lincoln_air",
    },
    {
        "truth": "sensor.lilly_s_room_temperature_truth",
        "climate": "climate.lilly_air",
    },
]


def _automation(automation_id):
    return next(item for item in AUTOMATIONS if item.get("id") == automation_id)


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_reconciliation_preserves_schedule_mode_and_four_exact_pairs():
    reconciliation = _automation("v8_6b_truth_unavailable_cooling_reconciliation")

    assert reconciliation["mode"] == "single"
    assert reconciliation["trigger"] == [
        {"platform": "homeassistant", "event": "start"},
        {"platform": "time_pattern", "minutes": "/5"},
    ]
    assert reconciliation["action"][0]["choose"][0]["sequence"] == [
        {"delay": "00:03:00"}
    ]
    assert reconciliation["action"][1]["repeat"]["for_each"] == EXPECTED_PAIRS


def test_each_repeat_iteration_is_a_complete_isolated_zone_boundary():
    reconciliation = _automation("v8_6b_truth_unavailable_cooling_reconciliation")
    sequence = reconciliation["action"][1]["repeat"]["sequence"]

    assert len(sequence) == 1
    boundary = sequence[0]
    assert boundary["alias"] == "Zone boundary: truth-unavailable cooling reconciliation"
    assert boundary["continue_on_error"] is True
    assert set(boundary) == {"alias", "continue_on_error", "if", "then"}
    assert len(boundary["if"]) == 1
    assert boundary["if"][0]["condition"] == "template"
    assert boundary["then"] == [
        {
            "action": "climate.set_hvac_mode",
            "target": {"entity_id": "{{ repeat.item.climate }}"},
            "data": {"hvac_mode": "off"},
        }
    ]


def test_boundary_retains_invalid_truth_age_and_cooling_guards():
    reconciliation = _automation("v8_6b_truth_unavailable_cooling_reconciliation")
    boundary = reconciliation["action"][1]["repeat"]["sequence"][0]
    guard = boundary["if"][0]["value_template"]

    assert "repeat.item.truth" in guard
    assert "repeat.item.climate" in guard
    assert "x is none or x != x or x < -90 or x > 200" in guard
    assert "states[truth_entity] if truth_entity in states else none" in guard
    assert "states(climate_entity) == 'cool'" in guard
    assert ">= 120" in guard


def test_reconciliation_climate_actions_are_off_only_and_not_blindly_contained():
    reconciliation = _automation("v8_6b_truth_unavailable_cooling_reconciliation")
    climate_calls = [
        node
        for node in _walk(reconciliation)
        if str(node.get("action") or node.get("service") or "").startswith("climate.")
    ]

    assert len(climate_calls) == 1
    assert climate_calls[0]["action"] == "climate.set_hvac_mode"
    assert climate_calls[0]["data"] == {"hvac_mode": "off"}
    assert "continue_on_error" not in climate_calls[0]
    assert all(node.get("action") != "climate.set_temperature" for node in _walk(reconciliation))
    assert all(node.get("data", {}).get("hvac_mode") != "cool" for node in _walk(reconciliation))
