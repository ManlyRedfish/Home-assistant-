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

def test_cooling_not_permitted_below_safety_floor_static(automations_data):
    """
    Static guardrail ensuring that cooling is not permitted below the safety floor.
    Full HA runtime simulation (mocking the climate entity state and observing it
    is forced 'off') is intentionally out of scope for now to avoid complex dependencies.
    Instead, we statically verify the 'off' action is present in the safety automations.
    """
    required_automations = {
        'v8_2_runaway_cooling_cutoff_lr': 'climate.living_room_air',
        'v8_2_master_emergency_floor': 'climate.master_bedroom_air'
    }

    found_automations = 0

    for auto in automations_data:
        auto_id = auto.get('id')
        if auto_id in required_automations:
            found_automations += 1
            target_climate = required_automations[auto_id]
            actions = auto.get('action', [])

            # Look for the climate.set_hvac_mode action that turns it off
            action_found = False
            for action in actions:
                if action.get('action') == 'climate.set_hvac_mode':
                    target = action.get('target', {})
                    data = action.get('data', {})
                    if target.get('entity_id') == target_climate and data.get('hvac_mode') == 'off':
                        action_found = True
                        break

            assert action_found, f"Automation {auto_id} exists but is missing the action to turn off {target_climate}."

    assert found_automations == len(required_automations), "Not all required safety floor automations were found."
