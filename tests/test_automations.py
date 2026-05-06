import yaml
import pytest
import os


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

def test_google_sheets_actions_use_secrets(automations_data):
    """Ensure any google_sheets.append_sheet action uses !secret for config_entry"""
    for automation in automations_data:
        actions = automation.get('action', [])
        if not isinstance(actions, list):
            actions = [actions]

        def check_action(action_item):
            if isinstance(action_item, dict):
                # Check direct action
                if action_item.get('action') == 'google_sheets.append_sheet' or action_item.get('service') == 'google_sheets.append_sheet':
                    data = action_item.get('data', {})
                    config_entry = data.get('config_entry')
                    assert config_entry and config_entry.startswith('SECRET_'), \
                        f"Automation '{automation.get('alias')}' uses google_sheets without !secret for config_entry"

                # Recursively check nested actions (choose, if, repeat, parallel)
                for key in ['choose', 'if', 'repeat', 'parallel', 'default', 'then', 'else', 'sequence']:
                    if key in action_item:
                        nested = action_item[key]
                        if isinstance(nested, list):
                            for n in nested:
                                check_action(n)
                        elif isinstance(nested, dict):
                            # For choose blocks
                            if key == 'choose':
                                for choice in action_item[key]:
                                    if 'sequence' in choice:
                                        for n in choice['sequence']:
                                            check_action(n)
                            else:
                                check_action(nested)

        for action in actions:
            check_action(action)

def test_slugified_entities_check():
    """
    Ensure entities correctly handle apostrophes by checking common 'lilly_s_room'
    pattern instead of 'lillys_room' as per memory instructions.
    """
    file_path = os.path.join(os.path.dirname(__file__), '..', 'automations.yaml')
    with open(file_path, 'r') as f:
        content = f.read()

    # Check that lillys_room doesn't exist, it should be lilly_s_room
    assert "lillys_room" not in content.lower(), "Found non-slugified 'lillys_room', should be 'lilly_s_room' per conventions"

def test_all_automations_have_mode(automations_data):
    for a in automations_data:
        assert 'mode' in a, f"Automation '{a.get('id')}' is missing 'mode'"
