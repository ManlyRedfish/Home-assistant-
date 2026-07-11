"""
Section 20 contract test — LR night mode schedule.

Locks the daily time-based toggle of input_boolean.night_mode_lr_primary:
  - ON  at 19:00 (activates P4 LR conservation, 74/76 deadband)
  - OFF at 07:00 (returns to P5 daytime fallthrough, 68/72 deadband)
"""

from __future__ import annotations

import os

import pytest
import yaml


class MooseAutomationLoader(yaml.SafeLoader):
    pass


def _secret(loader, node):
    return f"SECRET_{node.value}"


def _include(loader, node):
    return f"INCLUDE_{node.value}"


def _input(loader, node):
    return f"INPUT_{node.value}"


def _include_dir_merge_list(loader, node):
    return []


MooseAutomationLoader.add_constructor("!secret", _secret)
MooseAutomationLoader.add_constructor("!include", _include)
MooseAutomationLoader.add_constructor("!input", _input)
MooseAutomationLoader.add_constructor("!include_dir_merge_list", _include_dir_merge_list)
MooseAutomationLoader.add_constructor("!include_dir_named", _include_dir_merge_list)

AUTOMATION_ID = "lr_night_mode_schedule"
NIGHT_HELPER = "input_boolean.night_mode_lr_primary"


@pytest.fixture(scope="module")
def schedule_automation():
    file_path = os.path.join(os.path.dirname(__file__), "..", "automations.yaml")
    with open(file_path, "r") as f:
        data = yaml.load(f, Loader=MooseAutomationLoader)
    auto = next((a for a in data if a.get("id") == AUTOMATION_ID), None)
    assert auto is not None, f"Automation '{AUTOMATION_ID}' not found in automations.yaml"
    return auto


def test_automation_exists_and_is_single(schedule_automation):
    assert schedule_automation.get("mode") == "single"


def test_trigger_times(schedule_automation):
    triggers = schedule_automation["trigger"]
    by_id = {t["id"]: t["at"] for t in triggers}
    assert by_id.get("night_mode_on") == "19:00:00", "19:00 ON trigger missing or wrong time"
    assert by_id.get("night_mode_off") == "07:00:00", "07:00 OFF trigger missing or wrong time"


def test_choose_actions(schedule_automation):
    choose_blocks = schedule_automation["action"][0]["choose"]

    on_branch = next(
        (b for b in choose_blocks if b["conditions"][0]["id"] == "night_mode_on"), None
    )
    off_branch = next(
        (b for b in choose_blocks if b["conditions"][0]["id"] == "night_mode_off"), None
    )

    assert on_branch is not None, "night_mode_on choose branch missing"
    assert off_branch is not None, "night_mode_off choose branch missing"

    assert on_branch["sequence"][0]["action"] == "input_boolean.turn_on"
    assert on_branch["sequence"][0]["target"]["entity_id"] == NIGHT_HELPER

    assert off_branch["sequence"][0]["action"] == "input_boolean.turn_off"
    assert off_branch["sequence"][0]["target"]["entity_id"] == NIGHT_HELPER
