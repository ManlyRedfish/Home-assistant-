import yaml
import pytest
import os
from pathlib import Path


class MooseAutomationLoader(yaml.SafeLoader):
    pass


# Home Assistant specific constructors
def secret_constructor(loader, node):
    return f"SECRET_{node.value}"

def include_constructor(loader, node):
    return f"INCLUDE_{node.value}"

def input_constructor(loader, node):
    return f"INPUT_{node.value}"

def include_dir_merge_list_constructor(loader, node):
    return []

MooseAutomationLoader.add_constructor('!secret', secret_constructor)
MooseAutomationLoader.add_constructor('!include', include_constructor)
MooseAutomationLoader.add_constructor('!input', input_constructor)
MooseAutomationLoader.add_constructor('!include_dir_merge_list', include_dir_merge_list_constructor)
MooseAutomationLoader.add_constructor('!include_dir_named', include_dir_merge_list_constructor)

@pytest.fixture(scope="module")
def automations_data():
    file_path = os.path.join(os.path.dirname(__file__), '..', 'automations.yaml')
    with open(file_path, 'r') as f:
        data = yaml.load(f, Loader=MooseAutomationLoader)
    return data


def test_automations_is_list(automations_data):
    assert isinstance(automations_data, list), "automations.yaml must contain a list of automations"

def test_automations_have_required_fields(automations_data):
    for i, automation in enumerate(automations_data):
        assert isinstance(automation, dict), f"Automation at index {i} is not a dictionary"

        # Check required fields
        for field in ['id', 'alias', 'trigger', 'action']:
            assert field in automation, f"Automation '{automation.get('alias', f'index {i}')}' is missing '{field}'"


def test_automation_ids_are_unique(automations_data):
    ids = []
    for automation in automations_data:
        if 'id' in automation:
            ids.append(automation['id'])

    seen = set()
    duplicates = [x for x in ids if x in seen or seen.add(x)]
    assert len(duplicates) == 0, f"Duplicate automation IDs found: {duplicates}"

NESTED_ACTION_KEYS = {
    "choose",
    "if",
    "repeat",
    "parallel",
    "default",
    "then",
    "else",
    "sequence",
}

def test_google_sheets_actions_use_secrets(automations_data):
    """Ensure any google_sheets.append_sheet action uses !secret for config_entry"""
    for automation in automations_data:
        actions = automation.get('action', [])
        if not isinstance(actions, list):
            actions = [actions]

        def check_action(action_item):
            if not isinstance(action_item, dict):
                return

            # Check direct action
            if action_item.get('action') == 'google_sheets.append_sheet' or action_item.get('service') == 'google_sheets.append_sheet':
                data = action_item.get('data', {})
                config_entry = data.get('config_entry')
                assert config_entry and config_entry.startswith('SECRET_'), \
                    f"Automation '{automation.get('alias')}' uses google_sheets without !secret for config_entry"

            # Recursively check nested actions
            for key, nested in action_item.items():
                if key not in NESTED_ACTION_KEYS:
                    continue

                if isinstance(nested, list):
                    for item in nested:
                        check_action(item)
                elif isinstance(nested, dict):
                    check_action(nested)

        for action in actions:
            check_action(action)

def test_apostrophe_room_entities_use_slugified_names():
    """
    Ensure entities correctly handle apostrophes by checking common 'lilly_s_room' and 'lincoln_s_room'
    patterns instead of 'lillys_room' and 'lincolns_room' as per memory instructions.
    """
    active_yaml_files = [
        Path("automations.yaml"),
        Path("configuration.yaml"),
    ]

    forbidden_tokens = {
        "lillys_room": "lilly_s_room",
        "lincolns_room": "lincoln_s_room",
    }

    for path in active_yaml_files:
        content = path.read_text(encoding="utf-8").lower()
        for bad, good in forbidden_tokens.items():
            assert bad not in content, (
                f"{path} contains non-slugified '{bad}', expected '{good}'"
            )

def test_all_automations_have_mode(automations_data):
    for a in automations_data:
        assert 'mode' in a, f"Automation '{a.get('id')}' is missing 'mode'"


def test_ghost_assassin_suppresses_lincoln_phantom_heat(automations_data):
    ghost = next(
        (a for a in automations_data if a.get("id") == "v7_5_ghost_assassin"),
        None,
    )

    assert ghost is not None, "Ghost Assassin automation must remain present"
    assert ghost.get("mode") == "single"

    triggers = ghost.get("trigger", [])
    assert any(
        trigger.get("platform") == "time" and trigger.get("at") == "01:20:00"
        for trigger in triggers
    ), "Ghost Assassin must run at the known 01:20 Samsung/SmartThings ghost window"

    conditions = ghost.get("condition", [])
    assert any(
        condition.get("condition") == "state"
        and condition.get("entity_id") == "climate.lincoln_air"
        and condition.get("state") == "heat"
        for condition in conditions
    ), "Ghost Assassin must only suppress Lincoln when it is in phantom heat"

    assert any(
        condition.get("condition") == "template"
        and "input_select.hvac_season_mode" in condition.get("value_template", "")
        and "!= 'heating'" in condition.get("value_template", "")
        for condition in conditions
    ), "Ghost Assassin must not block intentional heating-season heat"

    actions = ghost.get("action", [])
    assert any(
        (action.get("action") or action.get("service")) == "climate.set_hvac_mode"
        and action.get("target", {}).get("entity_id") == "climate.lincoln_air"
        and action.get("data", {}).get("hvac_mode") == "off"
        for action in actions
    ), "Ghost Assassin must force Lincoln head unit off"

    assert any(
        (action.get("action") or action.get("service")) == "notify.notify"
        for action in actions
    ), "Ghost Assassin should notify when it blocks phantom heat"
