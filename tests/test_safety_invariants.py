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


def _action_calls_climate_set_hvac_mode_off(auto, expected_entity_id):
    actions = auto.get("action", [])
    if isinstance(actions, dict):
        actions = [actions]

    return any(
        isinstance(action, dict)
        and (action.get("action") or action.get("service")) == "climate.set_hvac_mode"
        and action.get("target", {}).get("entity_id") == expected_entity_id
        and action.get("data", {}).get("hvac_mode") == "off"
        for action in actions
    )

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

            assert _action_calls_climate_set_hvac_mode_off(auto, 'climate.living_room_air'), (
                "LR runaway cutoff automation must force climate.living_room_air to hvac_mode off."
            )
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

            assert _action_calls_climate_set_hvac_mode_off(auto, 'climate.master_bedroom_air'), (
                "Master emergency floor automation must force climate.master_bedroom_air to hvac_mode off."
            )
            break

    assert found, "Master emergency cooling floor automation (v8_2_master_emergency_floor) not found in automations.yaml"


def test_required_safety_automations_are_present_by_unique_id(automations_data):
    """
    Validates required Section 3 safety automations are present by unique ID.
    This avoids false passes from raw match counts when duplicate IDs appear.
    """
    required_automations = {
        "v8_2_lr_runaway_cooling_cutoff",
        "v8_2_master_emergency_floor",
    }
    seen_automation_ids = set()

    for auto in automations_data:
        auto_id = auto.get("id")
        if auto_id in required_automations:
            seen_automation_ids.add(auto_id)

    missing_automation_ids = required_automations - seen_automation_ids
    assert not missing_automation_ids, (
        "Missing required safety automations: "
        f"{sorted(missing_automation_ids)}"
    )
