"""Structural contract for the accepted-live kids low-temperature watchdogs."""

from pathlib import Path

import yaml


class AutomationLoader(yaml.SafeLoader):
    pass


AutomationLoader.add_constructor("!secret", lambda loader, node: node.value)

AUTOMATIONS = yaml.load(
    Path("automations.yaml").read_text(encoding="utf-8"),
    Loader=AutomationLoader,
)

WATCHDOGS = {
    "repair_lilly_low_temperature_off_watchdog": (
        "sensor.lilly_s_room_temperature_truth",
        "climate.lilly_air",
    ),
    "repair_lincoln_low_temperature_off_watchdog": (
        "sensor.lincoln_s_room_temperature_truth",
        "climate.lincoln_air",
    ),
}


def _automation(automation_id):
    matches = [item for item in AUTOMATIONS if item.get("id") == automation_id]
    assert len(matches) == 1
    return matches[0]


def _service(action):
    return action.get("action") or action.get("service")


def test_live_watchdog_ids_and_exact_trigger_contract():
    for automation_id, (truth_entity, climate_entity) in WATCHDOGS.items():
        watchdog = _automation(automation_id)
        assert watchdog["mode"] == "single"
        assert watchdog["trigger"] == [
            {
                "platform": "numeric_state",
                "entity_id": truth_entity,
                "below": 64,
                "for": "00:02:00",
            }
        ]
        assert watchdog["condition"][0] == {
            "condition": "state",
            "entity_id": climate_entity,
            "state": "cool",
        }
        finite_guard = watchdog["condition"][1]["value_template"]
        assert truth_entity in finite_guard
        assert "float(none)" in finite_guard
        assert "x is not none" in finite_guard and "x == x" in finite_guard


def test_live_watchdogs_are_off_first_and_never_set_temperature_or_fan():
    for automation_id, (_, climate_entity) in WATCHDOGS.items():
        actions = _automation(automation_id)["action"]
        assert actions[0] == {
            "action": "climate.set_hvac_mode",
            "target": {"entity_id": climate_entity},
            "data": {"hvac_mode": "off"},
        }
        services = [_service(action) for action in actions]
        assert "climate.set_temperature" not in services
        assert "climate.set_fan_mode" not in services


def test_continuation_is_only_on_logbook_and_notification_actions():
    for automation_id in WATCHDOGS:
        actions = _automation(automation_id)["action"]
        continued = [action for action in actions if "continue_on_error" in action]
        assert [_service(action) for action in continued] == [
            "logbook.log",
            "notify.notify",
        ]
        assert all(action["continue_on_error"] is True for action in continued)
        assert "continue_on_error" not in actions[0]
