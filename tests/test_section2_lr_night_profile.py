"""
Packet B Rev 4 CHANGE-3 contract test — LR night conservation profile (P4).

Locks the Section 2 cooling-branch behavior for the Living Room when
`input_boolean.night_mode_lr_primary` is on:

    engage  = truth > 76 °F
    release = truth ≤ 74 °F
    hold between thresholds (preserve prior call)
    command = cool / 61 °F  (fan mode untouched — CHANGE-2 is deferred)

Reference docs:
- docs/analysis/lr-night-cooling-capacity-discovery.md (July 3 evidence)
- docs/analysis/packet_b_revision_4_control_contract.md §1.3 (profile matrix)
- docs/analysis/packet_b_revision_4_control_contract.md §5 CHANGE-3
- docs/analysis/packet_b_revision_4_control_contract.md §5.2 test 3

Precedence invariants asserted here (§1.2):
- P1 (away) and P4 (LR night) share the 76 / 74 numbers but are distinct
  profiles. The away path must not depend on `night_mode_lr_primary` and
  must not activate it.
- Section 2 remains the sole comfort writer. It must never write
  `input_boolean.night_mode_lr_primary` (operator-managed) or
  `input_boolean.away_mode`.
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


SUPERVISOR_ID = "v7_5_main_supervisor"

LR_CLIMATE = "climate.living_room_air"
NIGHT_HELPER = "input_boolean.night_mode_lr_primary"
AWAY_HELPER = "input_boolean.away_mode"

WRITE_SERVICES = {
    "input_boolean.turn_on",
    "input_boolean.turn_off",
    "input_boolean.toggle",
    "homeassistant.turn_on",
    "homeassistant.turn_off",
    "homeassistant.toggle",
}


@pytest.fixture(scope="module")
def supervisor_actions():
    file_path = os.path.join(os.path.dirname(__file__), "..", "automations.yaml")
    with open(file_path, "r") as f:
        data = yaml.load(f, Loader=MooseAutomationLoader)

    supervisor = next(
        (a for a in data if isinstance(a, dict) and a.get("id") == SUPERVISOR_ID),
        None,
    )
    assert supervisor is not None, f"Main supervisor automation {SUPERVISOR_ID} not found"

    actions = supervisor.get("action", [])
    assert isinstance(actions, list), "Main supervisor actions must be a list"
    return actions


def _iter_nodes(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _iter_nodes(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_nodes(item)


def _cooling_branch_sequence(actions):
    for item in actions:
        if not isinstance(item, dict) or "choose" not in item:
            continue
        for choice in item["choose"]:
            if not isinstance(choice, dict):
                continue
            conditions = choice.get("conditions", [])
            for cond in conditions:
                if (
                    isinstance(cond, dict)
                    and cond.get("condition") == "template"
                    and "season == 'cooling'" in (cond.get("value_template") or "")
                ):
                    return choice.get("sequence", [])
    pytest.fail("Cooling branch not found in main supervisor `choose`")


def _lr_command_step(cooling_sequence):
    """Return the climate.set_temperature action targeting the LR head."""
    for node in _iter_nodes(cooling_sequence):
        if not isinstance(node, dict):
            continue
        service = node.get("action") or node.get("service")
        if service != "climate.set_temperature":
            continue
        target = node.get("target") or {}
        entity = target.get("entity_id")
        entities = entity if isinstance(entity, list) else [entity]
        if LR_CLIMATE in entities:
            return node
    pytest.fail(f"climate.set_temperature step for {LR_CLIMATE} not found in cooling branch")


def _lr_threshold_variables(cooling_sequence):
    """Return the variables dict that defines lr_off_at / lr_on_at / lr_conservation."""
    for node in _iter_nodes(cooling_sequence):
        if not isinstance(node, dict):
            continue
        variables = node.get("variables")
        if isinstance(variables, dict) and {"lr_off_at", "lr_on_at"} <= variables.keys():
            return variables
    pytest.fail("LR threshold variables block (lr_off_at / lr_on_at) not found in cooling branch")


def _entities_targeted(step: dict):
    target = step.get("target") or {}
    entity = target.get("entity_id")
    if isinstance(entity, list):
        return set(entity)
    if isinstance(entity, str):
        return {entity}
    return set()


# ---------------------------------------------------------------------------
# Assertion 1: LR night profile is engage > 76 / release ≤ 74 / hold-through,
# command cool / 61 °F (fan untouched — CHANGE-2 deferred).
# ---------------------------------------------------------------------------


def test_lr_night_profile_thresholds_and_command(supervisor_actions):
    cooling_sequence = _cooling_branch_sequence(supervisor_actions)
    variables = _lr_threshold_variables(cooling_sequence)

    # The Jinja that consolidates P1 (away) and P4 (LR night) — both profiles
    # share the 76/74 numbers per §1.3 but the disjunction keeps them
    # independent: either input alone must activate conservation.
    assert variables["lr_conservation"] == "{{ away or lr_night_primary }}", (
        "lr_conservation must be `away or lr_night_primary` so P1 and P4 can "
        "each activate conservation on its own. See Packet B §1.2/§1.3."
    )
    assert variables["lr_off_at"] == "{{ 74 if lr_conservation else 68 }}", (
        "LR release threshold must be 74 °F under conservation (P1/P4), else 68 °F (P5)."
    )
    assert variables["lr_on_at"] == "{{ 76 if lr_conservation else 72 }}", (
        "LR engage threshold must be 76 °F under conservation (P1/P4), else 72 °F (P5)."
    )
    assert variables["lr_setpoint"] == "{{ 61 }}", (
        "LR cooling command setpoint is the 61 °F shove (PR #126 doctrine, unchanged)."
    )

    lr_step = _lr_command_step(cooling_sequence)
    data = lr_step.get("data") or {}

    # Hold-through: engage checked first (temp > lr_on_at → cool), then release
    # (temp ≤ lr_off_at → off), then preserve the prior call.
    hvac_template = data.get("hvac_mode") or ""
    for fragment in (
        "lr_temp > lr_on_at",
        "lr_temp <= lr_off_at",
        "lr_current == 'cool'",
    ):
        assert fragment in hvac_template, (
            f"LR hvac_mode template missing `{fragment}` — hysteresis contract "
            "requires engage/release/hold, in that order."
        )
    assert data.get("temperature") == "{{ lr_setpoint }}", (
        "LR cooling command temperature must be templated from lr_setpoint (61 °F shove)."
    )
    # CHANGE-2 (turbo on every cooling call) is explicitly deferred; the LR
    # cooling call must not silently ship a fan mode ahead of that CHANGE.
    assert "fan_mode" not in data, (
        "CHANGE-2 (turbo on every cooling call) is deferred; no fan_mode may be "
        "attached to the LR cooling command in this PR."
    )


# ---------------------------------------------------------------------------
# Assertion 2: Daytime P5 fallback — with night_mode_lr_primary off (and not
# away), LR uses 68 release / 72 engage. Guaranteed by the `else` branch of
# the lr_off_at / lr_on_at templates.
# ---------------------------------------------------------------------------


def test_lr_daytime_p5_fallback(supervisor_actions):
    cooling_sequence = _cooling_branch_sequence(supervisor_actions)
    variables = _lr_threshold_variables(cooling_sequence)

    # `lr_conservation = away or lr_night_primary` is false iff both are off,
    # so the `else` branch of these ternaries defines the daytime P5 numbers.
    assert variables["lr_off_at"].endswith("else 68 }}"), (
        "Daytime P5 release must be ≤ 68 °F (fallback branch of lr_off_at)."
    )
    assert variables["lr_on_at"].endswith("else 72 }}"), (
        "Daytime P5 engage must be > 72 °F (fallback branch of lr_on_at)."
    )


# ---------------------------------------------------------------------------
# Assertion 3: Away (P1) precedence — with away on, LR still resolves to
# 76 / 74 even when night_mode_lr_primary is off. P1 must NOT depend on the
# night-mode helper, and (per assertions 4/5) must not activate it either.
# ---------------------------------------------------------------------------


def test_away_activates_conservation_independently_of_night_helper(supervisor_actions):
    cooling_sequence = _cooling_branch_sequence(supervisor_actions)
    variables = _lr_threshold_variables(cooling_sequence)

    # `away or lr_night_primary` — an OR — means `away` alone (P1) yields the
    # conservation branch regardless of the helper. Both terms must be present
    # as independent operands of a disjunction.
    conservation = variables["lr_conservation"]
    assert "away" in conservation and "lr_night_primary" in conservation, (
        "lr_conservation must reference both `away` and `lr_night_primary`."
    )
    assert " or " in conservation, (
        "lr_conservation must be a disjunction so P1 (away) can activate "
        "conservation without needing `night_mode_lr_primary`."
    )
    assert " and " not in conservation, (
        "lr_conservation must not require BOTH `away` and `lr_night_primary` — "
        "that would make P1 depend on the LR-night helper (contract violation)."
    )


# ---------------------------------------------------------------------------
# Assertion 4: Section 2 must never write `input_boolean.night_mode_lr_primary`
# (it is operator-managed — §5 CHANGE-3, §10.3 prohibition list).
# ---------------------------------------------------------------------------


def test_section2_does_not_write_night_mode_helper(supervisor_actions):
    for node in _iter_nodes(supervisor_actions):
        if not isinstance(node, dict):
            continue
        service = node.get("action") or node.get("service")
        if service in WRITE_SERVICES and NIGHT_HELPER in _entities_targeted(node):
            pytest.fail(
                f"Section 2 must never write {NIGHT_HELPER}; found `{service}` "
                "in the main supervisor. See Packet B Rev 4 §5 CHANGE-3."
            )
        # Guard against alternate write shapes (data.entity_id, service_data).
        for key in ("data", "service_data", "data_template"):
            payload = node.get(key)
            if isinstance(payload, dict):
                payload_entity = payload.get("entity_id")
                entities = (
                    payload_entity
                    if isinstance(payload_entity, list)
                    else [payload_entity] if isinstance(payload_entity, str) else []
                )
                if NIGHT_HELPER in entities and service in WRITE_SERVICES:
                    pytest.fail(
                        f"Section 2 must never write {NIGHT_HELPER} (found via "
                        f"data.entity_id under `{service}`)."
                    )


# ---------------------------------------------------------------------------
# Assertion 5: Section 2 must never write `input_boolean.away_mode`
# (away is a separate ingest surface — §1.2 P1, §10.3 prohibition list).
# ---------------------------------------------------------------------------


def test_section2_does_not_write_away_mode(supervisor_actions):
    for node in _iter_nodes(supervisor_actions):
        if not isinstance(node, dict):
            continue
        service = node.get("action") or node.get("service")
        if service in WRITE_SERVICES and AWAY_HELPER in _entities_targeted(node):
            pytest.fail(
                f"Section 2 must never write {AWAY_HELPER}; found `{service}` "
                "in the main supervisor. See Packet B Rev 4 §1.2 (P1 precedence)."
            )
        for key in ("data", "service_data", "data_template"):
            payload = node.get(key)
            if isinstance(payload, dict):
                payload_entity = payload.get("entity_id")
                entities = (
                    payload_entity
                    if isinstance(payload_entity, list)
                    else [payload_entity] if isinstance(payload_entity, str) else []
                )
                if AWAY_HELPER in entities and service in WRITE_SERVICES:
                    pytest.fail(
                        f"Section 2 must never write {AWAY_HELPER} (found via "
                        f"data.entity_id under `{service}`)."
                    )
