"""Structural contract for bounded per-room fan destratification isolation."""

from pathlib import Path

import yaml


class AutomationLoader(yaml.SafeLoader):
    pass


AutomationLoader.add_constructor("!secret", lambda loader, node: node.value)

AUTOMATIONS = yaml.load(
    Path("automations.yaml").read_text(encoding="utf-8"), Loader=AutomationLoader
)

EXPECTED_ROOMS = [
    {
        "name": "Master",
        "entity": "climate.master_bedroom_air",
        "delta": "master_delta",
        "allowed": "master_fan_allowed",
        "temperature": "master_temp",
    },
    {
        "name": "Lincoln",
        "entity": "climate.lincoln_air",
        "delta": "lincoln_delta",
        "allowed": "lincoln_fan_allowed",
        "temperature": "lincoln_temp",
    },
    {
        "name": "Lilly",
        "entity": "climate.lilly_air",
        "delta": "lilly_delta",
        "allowed": "lilly_fan_allowed",
        "temperature": "lilly_temp",
    },
]


def _automation():
    return next(
        item
        for item in AUTOMATIONS
        if item.get("id") == "v8_comfort_fan_destratification"
    )


def _boundaries():
    return _automation()["action"][1:]


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_automation_remains_mode_single_with_three_complete_room_boundaries():
    assert _automation()["mode"] == "single"
    assert len(_boundaries()) == 3

    for boundary, room in zip(_boundaries(), EXPECTED_ROOMS):
        assert boundary["alias"] == f"Room boundary: {room['name']} fan destratification"
        assert boundary["continue_on_error"] is True
        assert set(boundary) == {"alias", "continue_on_error", "choose"}
        assert len(boundary["choose"]) == 2


def test_each_room_preserves_exact_conditions_and_action_order():
    for boundary, room in zip(_boundaries(), EXPECTED_ROOMS):
        start, stop = boundary["choose"]
        entity = room["entity"]

        assert start["conditions"] == [
            {
                "condition": "template",
                "value_template": start["conditions"][0]["value_template"],
            }
        ]
        start_guard = start["conditions"][0]["value_template"]
        assert f"is_state('{entity}', 'off')" in start_guard
        assert f"{room['delta']} >= 3.0" in start_guard
        assert f"and {room['allowed']}" in start_guard
        assert start["sequence"] == [
            {
                "action": "climate.set_hvac_mode",
                "target": {"entity_id": entity},
                "data": {"hvac_mode": "fan_only"},
            },
            {
                "action": "climate.set_fan_mode",
                "target": {"entity_id": entity},
                "data": {"fan_mode": "auto"},
            },
        ]

        assert stop["conditions"] == [
            {
                "condition": "template",
                "value_template": stop["conditions"][0]["value_template"],
            }
        ]
        stop_guard = stop["conditions"][0]["value_template"]
        assert f"states.climate.{entity.removeprefix('climate.')}.last_changed" in stop_guard
        assert f"is_state('{entity}', 'fan_only')" in stop_guard
        assert f"{room['delta']} <= 1.0 and runtime >= 2700" in stop_guard
        assert f"not {room['allowed']} and {room['temperature']} < 76" in stop_guard
        assert stop["sequence"] == [
            {
                "action": "climate.set_hvac_mode",
                "target": {"entity_id": entity},
                "data": {"hvac_mode": "off"},
            }
        ]


def test_continuation_exists_only_at_complete_room_boundaries():
    automation = _automation()
    continued = [node for node in _walk(automation) if "continue_on_error" in node]
    climate_calls = [
        node
        for node in _walk(automation)
        if str(node.get("action", "")).startswith("climate.")
    ]

    assert continued == _boundaries()
    assert all(node["continue_on_error"] is True for node in continued)
    assert len(climate_calls) == 9
    assert all("continue_on_error" not in call for call in climate_calls)
    assert {call["target"]["entity_id"] for call in climate_calls} == {
        room["entity"] for room in EXPECTED_ROOMS
    }
