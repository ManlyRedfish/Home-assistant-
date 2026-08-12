"""Structural contract for the bounded H-boost release ordering repair."""

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


def test_release_off_precedes_contained_helper_and_timer_cleanup():
    release = _automation("v8_4_lr_heating_recovery_boost_release")
    actions = release["action"]

    assert actions[0] == {
        "action": "climate.set_hvac_mode",
        "target": {"entity_id": "climate.living_room_air"},
        "data": {"hvac_mode": "off"},
    }
    assert _service(actions[1]) == "input_boolean.turn_off"
    assert actions[1]["continue_on_error"] is True

    timer_cancel = actions[2]["choose"][0]["sequence"][0]
    assert _service(timer_cancel) == "timer.cancel"
    assert timer_cancel["continue_on_error"] is True

    climate_calls = [
        action for action in actions
        if str(_service(action) or "").startswith("climate.")
    ]
    assert climate_calls == [actions[0]]
    assert "continue_on_error" not in actions[0]


def test_release_triggers_and_thresholds_are_unchanged():
    release = _automation("v8_4_lr_heating_recovery_boost_release")

    assert release["trigger"] == [
        {
            "platform": "numeric_state",
            "entity_id": "sensor.living_room_temperature_truth",
            "above": 66.99,
            "id": "truth_cap",
        },
        {
            "platform": "event",
            "event_type": "timer.finished",
            "event_data": {
                "entity_id": "timer.lr_heating_recovery_boost_max_runtime"
            },
            "id": "timeout",
        },
        {
            "platform": "template",
            "value_template": "{{ states('input_select.hvac_season_mode') not in ['heating', 'shoulder'] }}",
            "id": "season_change",
        },
        {
            "platform": "template",
            "value_template": "{{ states('sensor.living_room_temperature_truth') in ['unknown', 'unavailable'] or states('sensor.living_room_temperature_truth') | float(none) is none }}",
            "id": "truth_unavailable",
        },
    ]


def test_boost_policy_values_observability_and_watchdogs_are_unchanged():
    engage = _automation("v8_4_lr_heating_recovery_boost_engage")
    release = _automation("v8_4_lr_heating_recovery_boost_release")

    assert engage["trigger"][0]["below"] == 64
    assert engage["action"][1]["data"]["duration"] == "01:30:00"
    assert engage["action"][2]["data"] == {"temperature": 77, "hvac_mode": "heat"}

    release_text = repr(release["action"])
    for value in (
        "truth_cap",
        "timeout",
        "season_change",
        "truth_unavailable",
        "unknown_release_reason",
        "input_datetime.lr_heating_recovery_boost_last_release_at",
    ):
        assert value in release_text

    assert _automation("v8_2_lr_runaway_cooling_cutoff")["trigger"][0]["below"] == 60
    assert _automation("v8_2_master_emergency_floor")["trigger"][0]["below"] == 58
    truth_failsafe = _automation("v8_6_truth_unavailable_cooling_failsafe")
    assert len(truth_failsafe["trigger"]) == 4
    assert {trigger["for"] for trigger in truth_failsafe["trigger"]} == {"00:02:00"}
