"""
Contract tests for the Master Bedroom fan <-> AC sync (Section 17) and its
self-healing reconcile safety net (Section 18).

Background: the SwitchBot fan (fan.master_bedroom_switch_fan) reaches HA through
the SmartThings cloud, which can drop or stale a single command. Section 17 is
edge-driven (mode: single, triggers only on climate.master_bedroom_air mode
transitions), so a dropped command leaves the fan out of sync until the next AC
mode change — observed as the fan stuck `on @ 66%` while the AC read `off`.
Section 18 re-asserts the same contract on the fan's own state changes and a
5-minute time pattern so a dropped command self-heals.

These checks are conservative structural assertions against the parsed YAML; they
do not require an HA runtime. References: automations.yaml Sections 17 & 18.
"""

import os

import pytest
import yaml


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


MooseSafetyLoader.add_constructor("!include", yaml_include)
MooseSafetyLoader.add_constructor("!secret", yaml_secret)
MooseSafetyLoader.add_constructor("!input", yaml_input)
MooseSafetyLoader.add_constructor("!include_dir_merge_list", include_dir_merge_list_constructor)
MooseSafetyLoader.add_constructor("!include_dir_named", include_dir_merge_list_constructor)


FAN_ENTITY = "fan.master_bedroom_switch_fan"
CLIMATE_ENTITY = "climate.master_bedroom_air"


@pytest.fixture(scope="module")
def automations_data():
    filepath = os.path.join(os.path.dirname(__file__), "..", "automations.yaml")
    if not os.path.exists(filepath):
        pytest.skip("automations.yaml not found.")
        return []

    with open(filepath, "r") as file:
        try:
            return yaml.load(file, Loader=MooseSafetyLoader)
        except Exception as e:  # pragma: no cover - parse failure is a hard fail
            pytest.fail(f"Could not parse automations.yaml: {e}")


def _by_id(automations_data, auto_id):
    for auto in automations_data:
        if auto.get("id") == auto_id:
            return auto
    return None


def _triggers(auto):
    triggers = auto.get("trigger", [])
    if isinstance(triggers, dict):
        triggers = [triggers]
    return triggers


def _flatten_actions(node):
    """Yield every dict action under a (possibly nested choose/sequence) action block."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _flatten_actions(value)
    elif isinstance(node, list):
        for item in node:
            yield from _flatten_actions(item)


def _fan_calls(auto):
    actions = auto.get("action", [])
    calls = []
    for action in _flatten_actions(actions):
        service = action.get("action") or action.get("service")
        if service not in ("fan.turn_on", "fan.turn_off"):
            continue
        target = action.get("target", {}) or {}
        data = action.get("data", {}) or {}
        entity = target.get("entity_id") or data.get("entity_id")
        calls.append((service, entity, data))
    return calls


# ---------------------------------------------------------------------------
# Section 17 — edge-driven sync
# ---------------------------------------------------------------------------

def test_section17_fan_sync_present(automations_data):
    auto = _by_id(automations_data, "master_bedroom_fan_sync")
    assert auto is not None, "Section 17 master_bedroom_fan_sync automation is missing."
    assert auto.get("mode") == "single"

    # Triggers must watch the AC mode transitions, not the fan.
    watched = {t.get("entity_id") for t in _triggers(auto) if t.get("platform") == "state"}
    assert watched == {CLIMATE_ENTITY}, (
        "Section 17 should trigger only on climate.master_bedroom_air mode transitions."
    )


def test_section17_on_state_is_full_speed(automations_data):
    """The defined on-state is 100% — never 33/66. A stuck 66% is therefore stale,
    confirming the failure mode Section 18 heals."""
    auto = _by_id(automations_data, "master_bedroom_fan_sync")
    on_calls = [c for c in _fan_calls(auto) if c[0] == "fan.turn_on"]
    assert on_calls, "Section 17 must turn the fan on when the AC runs."
    for _service, entity, data in on_calls:
        assert entity == FAN_ENTITY
        assert data.get("percentage") == 100, "Section 17 must command 100%, the only on-state."


# ---------------------------------------------------------------------------
# Section 18 — self-healing reconcile
# ---------------------------------------------------------------------------

def test_section18_reconcile_present(automations_data):
    auto = _by_id(automations_data, "master_bedroom_fan_reconcile")
    assert auto is not None, (
        "Section 18 master_bedroom_fan_reconcile self-heal automation is missing."
    )
    assert auto.get("mode") == "single"


def test_section18_reconcile_triggers_on_fan_and_time_pattern(automations_data):
    """The whole point of the safety net: it must re-evaluate independent of AC
    mode transitions, otherwise a dropped command stays dropped."""
    auto = _by_id(automations_data, "master_bedroom_fan_reconcile")
    triggers = _triggers(auto)

    has_fan_state = any(
        t.get("platform") == "state" and t.get("entity_id") == FAN_ENTITY for t in triggers
    )
    has_time_pattern = any(t.get("platform") == "time_pattern" for t in triggers)

    assert has_fan_state, "Reconcile must trigger on the fan's own state changes."
    assert has_time_pattern, "Reconcile must trigger on a time pattern to catch stuck state."


def test_section18_reconcile_reasserts_both_directions(automations_data):
    """Reconcile must be able to push the fan off (AC off) and on@100% (AC running)."""
    auto = _by_id(automations_data, "master_bedroom_fan_reconcile")
    calls = _fan_calls(auto)
    services = {c[0] for c in calls}

    assert "fan.turn_off" in services, "Reconcile must re-issue turn_off when the AC is off."
    on_calls = [c for c in calls if c[0] == "fan.turn_on"]
    assert on_calls, "Reconcile must re-issue turn_on when the AC is running."
    for _service, entity, data in on_calls:
        assert entity == FAN_ENTITY
        assert data.get("percentage") == 100, "Reconcile on-state must match Section 17 (100%)."


def test_section18_reconcile_only_touches_the_fan(automations_data):
    """Safety boundary: the reconcile loop must never command the climate entity.
    It reconciles the fan to the AC, not the other way around."""
    auto = _by_id(automations_data, "master_bedroom_fan_reconcile")
    for action in _flatten_actions(auto.get("action", [])):
        service = action.get("action") or action.get("service")
        if service and service.startswith("climate."):
            pytest.fail(
                f"Reconcile must not command climate state; found '{service}'."
            )
