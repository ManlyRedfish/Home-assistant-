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

def _action_calls_climate_set_hvac_mode_off(auto, expected_entity_id):
    """
    Helper function to verify if an automation's action block contains
    a service call to set the given climate entity's hvac_mode to 'off'.
    Supports 'action:' and 'service:' syntaxes.
    """
    actions = auto.get('action', auto.get('sequence', []))
    for action in actions:
        service_call = action.get('action') or action.get('service')
        if service_call == 'climate.set_hvac_mode':
            # Check target or data for the entity_id
            target = action.get('target', {})
            data = action.get('data', {})

            entities = target.get('entity_id') or data.get('entity_id')
            if isinstance(entities, str):
                entities = [entities]
            elif not entities:
                entities = []

            if expected_entity_id in entities:
                if data.get('hvac_mode') == 'off':
                    return True
    return False

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

            action_found = _action_calls_climate_set_hvac_mode_off(auto, 'climate.living_room_air')
            assert action_found, "LR runaway cutoff automation exists, but action to turn off climate.living_room_air is missing or modified."
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

            action_found = _action_calls_climate_set_hvac_mode_off(auto, 'climate.master_bedroom_air')
            assert action_found, "Master emergency floor automation exists, but action to turn off climate.master_bedroom_air is missing or modified."
            break

    assert found, "Master emergency cooling floor automation (v8_2_master_emergency_floor) not found in automations.yaml"

def test_cooling_not_permitted_below_safety_floor():
    """
    Placeholder for future HA simulation test: Cooling should not be permitted below safety floor.
    Currently, we only statically analyze YAML.
    Full simulation would require mocking the climate entity state and observing it is forced 'off'.
    """
    # TODO: Implement full HA runtime simulation to verify that the climate entity
    # changes to 'off' when truth temp < 60F for LR and < 58F for Master.
    pass
