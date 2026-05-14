import pytest
import yaml
import os

class MooseSafetyLoader(yaml.SafeLoader):
    pass

def yaml_include(loader, node):
    return f"INCLUDE_{node.value}"

def yaml_secret(loader, node):
    return f"SECRET_{node.value}"

def yaml_input(loader, node):
    return f"INPUT_{node.value}"

def include_dir_merge_list_constructor(loader, node):
    return []

MooseSafetyLoader.add_constructor('!include', yaml_include)
MooseSafetyLoader.add_constructor('!secret', yaml_secret)
MooseSafetyLoader.add_constructor('!input', yaml_input)
MooseSafetyLoader.add_constructor('!include_dir_merge_list', include_dir_merge_list_constructor)
MooseSafetyLoader.add_constructor('!include_dir_named', include_dir_merge_list_constructor)

@pytest.fixture(scope="module")
def automations_data():
    filepath = os.path.join(os.path.dirname(__file__), '..', 'automations.yaml')
    if not os.path.exists(filepath):
        pytest.skip("automations.yaml not found.")
        return []

    with open(filepath, 'r') as file:
        try:
            return yaml.load(file, Loader=MooseSafetyLoader)
        except Exception as e:
            pytest.fail(f"Could not parse automations.yaml: {e}")

def test_lr_runaway_cooling_cutoff_exists(automations_data):
    """
    Validates Section 3 Safety Invariant: Living Room runaway cooling cutoff at 60F.
    References: docs/1_startup_canon.md (Section 5.2 Safety Doctrine)
    """
    found = False
    for auto in automations_data:
        if auto.get('id') == 'v8_2_lr_runaway_cooling_cutoff':
            found = True

            # Very conservative assertion: verify the 60F threshold is defined in the trigger
            triggers = auto.get('trigger', [])
            threshold_found = False
            for trigger in triggers:
                if trigger.get('platform') == 'numeric_state' and trigger.get('entity_id') == 'sensor.living_room_temperature_truth':
                    if trigger.get('below') == 60:
                        threshold_found = True
                        break

            assert threshold_found, "LR runaway cutoff automation exists, but 60F threshold trigger is missing or modified."
            break

    assert found, "Living Room runaway cooling cutoff automation (v8_2_lr_runaway_cooling_cutoff) not found in automations.yaml"

def test_master_emergency_cooling_floor_exists(automations_data):
    """
    Validates Section 3 Safety Invariant: Master emergency cooling floor at 58F.
    References: docs/1_startup_canon.md (Section 5.2 Safety Doctrine)
    """
    found = False
    for auto in automations_data:
        if auto.get('id') == 'v8_2_master_emergency_floor':
            found = True

            # Mirror the LR runaway test: pin the 58F threshold statically.
            # This static check does not require full HA runtime simulation —
            # the trigger shape is identical to the LR runaway cutoff.
            triggers = auto.get('trigger', [])
            threshold_found = False
            for trigger in triggers:
                if trigger.get('platform') == 'numeric_state' and trigger.get('entity_id') == 'sensor.master_bedroom_temperature_truth':
                    if trigger.get('below') == 58:
                        threshold_found = True
                        break

            assert threshold_found, "Master emergency floor automation exists, but 58F threshold trigger is missing or modified."
            break

    assert found, "Master emergency cooling floor automation (v8_2_master_emergency_floor) not found in automations.yaml"


def _find_automation(automations_data, automation_id):
    for auto in automations_data:
        if auto.get('id') == automation_id:
            return auto
    return None

def _has_numeric_state_below_trigger(auto, entity_id, below):
    triggers = auto.get('trigger', [])
    for trigger in triggers:
        if trigger.get('platform') == 'numeric_state' and trigger.get('entity_id') == entity_id:
            if trigger.get('below') == below:
                return True
    return False

def _iter_action_items(action):
    if action is None:
        return
    if isinstance(action, dict):
        action = [action]
    for item in action:
        if not isinstance(item, dict):
            continue
        yield item
        # Recursively yield nested actions
        for nested_key in ("choose", "if", "repeat", "parallel", "default", "then", "else", "sequence"):
            if nested_key in item:
                nested = item[nested_key]
                if nested_key == "choose" and isinstance(nested, list):
                    for choice in nested:
                        if "sequence" in choice:
                            for sub in _iter_action_items(choice.get("sequence")):
                                yield sub
                elif isinstance(nested, list):
                    for sub in _iter_action_items(nested):
                        yield sub
                elif isinstance(nested, dict):
                    for sub in _iter_action_items([nested]):
                        yield sub

def _turns_climate_entity_off(auto, entity_id):
    for item in _iter_action_items(auto.get('action', [])):
        action_key = item.get('action') or item.get('service')
        if action_key == 'climate.set_hvac_mode':
            # Check target or data for entity_id
            target = item.get('target', {})
            data = item.get('data', {})

            target_entity = target.get('entity_id')
            data_entity = data.get('entity_id')

            # Check for hvac_mode: off
            hvac_mode = data.get('hvac_mode')

            if (target_entity == entity_id or data_entity == entity_id) and hvac_mode == 'off':
                return True
    return False


def test_cooling_safety_floors_force_climate_off(automations_data):
    """
    Validates Section 3 Safety Invariant: LR and Master runaway cooling cutoffs
    both force the respective climate entity 'off'.
    """
    # Living Room Check
    lr_auto = _find_automation(automations_data, 'v8_2_lr_runaway_cooling_cutoff')
    assert lr_auto is not None, "Living Room runaway cooling cutoff automation (v8_2_lr_runaway_cooling_cutoff) not found"

    assert _has_numeric_state_below_trigger(lr_auto, 'sensor.living_room_temperature_truth', 60), \
        "LR runaway cutoff automation exists, but 60F threshold trigger is missing or modified."

    assert _turns_climate_entity_off(lr_auto, 'climate.living_room_air'), \
        "LR runaway cutoff automation does not force climate.living_room_air 'off'"

    # Master Check
    master_auto = _find_automation(automations_data, 'v8_2_master_emergency_floor')
    assert master_auto is not None, "Master emergency cooling floor automation (v8_2_master_emergency_floor) not found"

    assert _has_numeric_state_below_trigger(master_auto, 'sensor.master_bedroom_temperature_truth', 58), \
        "Master emergency floor automation exists, but 58F threshold trigger is missing or modified."

    assert _turns_climate_entity_off(master_auto, 'climate.master_bedroom_air'), \
        "Master emergency floor automation does not force climate.master_bedroom_air 'off'"
