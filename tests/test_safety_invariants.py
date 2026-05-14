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
        if auto.get('id') == 'v8_2_runaway_cooling_cutoff_lr':
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

    assert found, "Living Room runaway cooling cutoff automation (v8_2_runaway_cooling_cutoff_lr) not found in automations.yaml"

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

def _has_numeric_state_below_trigger(auto, entity_id, below):
    triggers = auto.get('trigger', [])
    if not isinstance(triggers, list):
        triggers = [triggers]
    for trigger in triggers:
        if trigger.get('platform') == 'numeric_state' and trigger.get('entity_id') == entity_id:
            if trigger.get('below') == below:
                return True
    return False

def _turns_climate_entity_off(auto, entity_id):
    actions = auto.get('action', [])
    if not isinstance(actions, list):
        actions = [actions]

    for action in actions:
        action_name = action.get('action') or action.get('service')
        if action_name == 'climate.set_hvac_mode':
            target_entity = action.get('target', {}).get('entity_id') or action.get('data', {}).get('entity_id')
            if target_entity == entity_id:
                if action.get('data', {}).get('hvac_mode') == 'off':
                    return True
    return False

def test_safety_floor_automations_force_climate_off(automations_data):
    """
    Verifies that the safety floor automations exist and actually force the climate entity off.
    """
    lr_found = False
    master_found = False

    for auto in automations_data:
        # Check LR runaway cutoff
        if auto.get('id') == 'v8_2_runaway_cooling_cutoff_lr':
            lr_found = True
            assert _has_numeric_state_below_trigger(auto, 'sensor.living_room_temperature_truth', 60), \
                "LR runaway cutoff missing 60F threshold trigger."
            assert _turns_climate_entity_off(auto, 'climate.living_room_air'), \
                "LR runaway cutoff does not force climate.living_room_air off."

        # Check Master emergency floor
        if auto.get('id') == 'v8_2_master_emergency_floor':
            master_found = True
            assert _has_numeric_state_below_trigger(auto, 'sensor.master_bedroom_temperature_truth', 58), \
                "Master emergency floor missing 58F threshold trigger."
            assert _turns_climate_entity_off(auto, 'climate.master_bedroom_air'), \
                "Master emergency floor does not force climate.master_bedroom_air off."

    assert lr_found, "LR runaway cutoff automation not found"
    assert master_found, "Master emergency floor automation not found"
