import os

import pytest
import yaml


class MooseManualOverrideLoader(yaml.SafeLoader):
    pass


def _secret(loader, node):
    return f"SECRET_{node.value}"


def _include(loader, node):
    return f"INCLUDE_{node.value}"


def _input(loader, node):
    return f"INPUT_{node.value}"


def _include_dir_merge_list(loader, node):
    return []


MooseManualOverrideLoader.add_constructor("!secret", _secret)
MooseManualOverrideLoader.add_constructor("!include", _include)
MooseManualOverrideLoader.add_constructor("!input", _input)
MooseManualOverrideLoader.add_constructor(
    "!include_dir_merge_list", _include_dir_merge_list
)
MooseManualOverrideLoader.add_constructor(
    "!include_dir_named", _include_dir_merge_list
)


@pytest.fixture(scope="module")
def automations_data():
    file_path = os.path.join(os.path.dirname(__file__), "..", "automations.yaml")
    with open(file_path, "r") as f:
        return yaml.load(f, Loader=MooseManualOverrideLoader)


def _get_automation(automations_data, automation_id):
    for auto in automations_data:
        if auto.get("id") == automation_id:
            return auto
    pytest.fail(f"Automation with id '{automation_id}' not found")


def _iter_nodes(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _iter_nodes(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_nodes(item)


def _has_manual_override_idle_condition(auto):
    return _condition_tree_requires_manual_override_idle(auto.get("condition", []))


def _is_manual_override_idle_leaf(node):
    return (
        isinstance(node, dict)
        and node.get("condition") == "state"
        and node.get("entity_id") == "timer.manual_hvac_override"
        and node.get("state") == "idle"
    )


def _condition_tree_requires_manual_override_idle(node):
    """Conservative structural check.

    Returns True only when every satisfiable condition path requires
    `timer.manual_hvac_override == idle`.
    """
    if isinstance(node, list):
        # Home Assistant condition lists are conjunctions.
        return any(_condition_tree_requires_manual_override_idle(item) for item in node)

    if not isinstance(node, dict):
        return False

    if _is_manual_override_idle_leaf(node):
        return True

    condition_type = node.get("condition")
    children = node.get("conditions", [])

    if condition_type == "and":
        # An AND implies idle if at least one conjunct implies idle.
        return any(_condition_tree_requires_manual_override_idle(item) for item in children)

    if condition_type == "or":
        # An OR implies idle only if all branches imply idle.
        return bool(children) and all(
            _condition_tree_requires_manual_override_idle(item) for item in children
        )

    if condition_type == "not":
        # Conservative: treat NOT forms as not proving idle.
        return False

    return False


def _has_any_manual_override_condition(auto):
    for node in _iter_nodes(auto):
        if node.get("entity_id") == "timer.manual_hvac_override":
            return True
    return False


def _assert_respects_manual_override_idle(automations_data, automation_id):
    auto = _get_automation(automations_data, automation_id)
    assert _has_manual_override_idle_condition(auto), (
        f"Manual Override Contract violation for '{automation_id}': expected "
        "a condition requiring timer.manual_hvac_override == idle. "
        "See docs/5_runtime_layer.md §7.8 and docs/3_regression_appendix.md §4.15."
    )


def test_supervisor_respects_manual_override(automations_data):
    _assert_respects_manual_override_idle(automations_data, "v7_5_main_supervisor")


def test_ceiling_gates_respect_manual_override(automations_data):
    _assert_respects_manual_override_idle(automations_data, "v7_5_safety_ceiling_gates")


def test_destratification_respects_manual_override(automations_data):
    _assert_respects_manual_override_idle(
        automations_data, "v8_comfort_fan_destratification"
    )


def test_samsung_guardrail_respects_manual_override(automations_data):
    _assert_respects_manual_override_idle(automations_data, "v8_samsung_auto_guardrail")


def test_boost_engage_respects_manual_override(automations_data):
    _assert_respects_manual_override_idle(
        automations_data, "v8_4_lr_heating_recovery_boost_engage"
    )


def test_boost_release_yields_to_manual_override(automations_data):
    auto = _get_automation(automations_data, "v8_4_lr_heating_recovery_boost_release")

    waf_trigger_found = any(
        trigger.get("platform") == "state"
        and trigger.get("entity_id") == "timer.manual_hvac_override"
        and trigger.get("to") == "active"
        and trigger.get("id") == "waf"
        for trigger in auto.get("trigger", [])
    )
    assert waf_trigger_found, (
        "Manual Override Contract violation: v8_4_lr_heating_recovery_boost_release "
        "must include WAF trigger (platform: state, entity_id: "
        "timer.manual_hvac_override, to: active, id: waf). "
        "See docs/5_runtime_layer.md §7.8 and docs/3_regression_appendix.md §4.16."
    )

    choose_guard_with_lr_off = False
    for action_item in auto.get("action", []):
        if not isinstance(action_item, dict) or "choose" not in action_item:
            continue

        for branch in action_item.get("choose", []):
            if not isinstance(branch, dict):
                continue

            conditions = branch.get("conditions", [])
            has_contract_guard = any(
                isinstance(cond, dict)
                and cond.get("condition") == "not"
                and isinstance(cond.get("conditions"), list)
                and any(
                    isinstance(inner, dict)
                    and inner.get("condition") == "state"
                    and inner.get("entity_id") == "timer.manual_hvac_override"
                    and inner.get("state") == "active"
                    for inner in cond.get("conditions", [])
                )
                for cond in conditions
            )
            if not has_contract_guard:
                continue

            sequence = branch.get("sequence", [])
            has_lr_off = any(
                isinstance(step, dict)
                and (step.get("action") or step.get("service"))
                == "climate.set_hvac_mode"
                and (step.get("target") or {}).get("entity_id")
                == "climate.living_room_air"
                and (step.get("data") or {}).get("hvac_mode") == "off"
                for step in sequence
            )
            if has_lr_off:
                choose_guard_with_lr_off = True
                break

        if choose_guard_with_lr_off:
            break

    assert choose_guard_with_lr_off, (
        "Manual Override Contract violation: boost release climate-off path must be in "
        "a choose branch guarded by `not(state(timer.manual_hvac_override == active))`, "
        "so manual override (WAF) does not force LR HVAC off. "
        "See docs/5_runtime_layer.md §7.8 and docs/3_regression_appendix.md §4.15/§4.16."
    )


def test_lr_runaway_does_not_gate_on_override(automations_data):
    auto = _get_automation(automations_data, "v8_2_lr_runaway_cooling_cutoff")
    assert not _has_any_manual_override_condition(auto), (
        "True safety gate v8_2_lr_runaway_cooling_cutoff must not gate on "
        "timer.manual_hvac_override. See docs/5_runtime_layer.md §7.8."
    )


def test_master_floor_does_not_gate_on_override(automations_data):
    auto = _get_automation(automations_data, "v8_2_master_emergency_floor")
    assert not _has_any_manual_override_condition(auto), (
        "True safety gate v8_2_master_emergency_floor must not gate on "
        "timer.manual_hvac_override. See docs/5_runtime_layer.md §7.8."
    )


def test_regression_or_branch_can_not_bypass_manual_override():
    auto = {
        "condition": {
            "condition": "or",
            "conditions": [
                {
                    "condition": "state",
                    "entity_id": "timer.manual_hvac_override",
                    "state": "idle",
                },
                {
                    "condition": "state",
                    "entity_id": "binary_sensor.some_other_gate",
                    "state": "on",
                },
            ],
        }
    }
    assert not _has_manual_override_idle_condition(auto)


def test_regression_safety_automation_nested_choose_must_not_reference_override():
    auto = {
        "id": "fake_safety",
        "condition": [],
        "action": [
            {
                "choose": [
                    {
                        "conditions": [
                            {
                                "condition": "state",
                                "entity_id": "timer.manual_hvac_override",
                                "state": "idle",
                            }
                        ],
                        "sequence": [{"action": "climate.turn_off"}],
                    }
                ]
            }
        ],
    }
    assert _has_any_manual_override_condition(auto)


def test_regression_valid_and_or_structure_still_passes():
    auto = {
        "condition": {
            "condition": "and",
            "conditions": [
                {
                    "condition": "state",
                    "entity_id": "sensor.occupancy",
                    "state": "on",
                },
                {
                    "condition": "or",
                    "conditions": [
                        {
                            "condition": "state",
                            "entity_id": "timer.manual_hvac_override",
                            "state": "idle",
                        },
                        {
                            "condition": "and",
                            "conditions": [
                                {
                                    "condition": "state",
                                    "entity_id": "timer.manual_hvac_override",
                                    "state": "idle",
                                },
                                {
                                    "condition": "state",
                                    "entity_id": "sensor.window",
                                    "state": "closed",
                                },
                            ],
                        },
                    ],
                },
            ],
        }
    }
    assert _has_manual_override_idle_condition(auto)
