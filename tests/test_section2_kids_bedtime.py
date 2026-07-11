"""
Section 2 kids' bedtime cooling block — locks the 2026-06-07 operator decision.

Contract (see docs/kids-bedroom-overnight-cooling-plan.md v6 and AGENTS.md
"Current Operator Decisions"):
- Lincoln + Lilly, independent per room, during 18:00-07:00 in cooling and
  shoulder seasons.
- Engage cooling at room truth >= 70; release to off at <= 66; hold state
  between 66-70 (continue cool while pulling down, stay off while resting).
- Actuator during pull-down: cool @ 61 + fan_mode turbo (both intentional).
- fan_mode turbo issued ONLY on the cool path.

The bedtime block lives inline in `automation.v7_5_main_supervisor` between
the V9-E pre-cool state writes and the season `choose`. No new automation,
no new helpers.
"""

import os

import pytest
import yaml


class MooseSupervisorLoader(yaml.SafeLoader):
    pass


def _yaml_include(loader, node):
    return f"INCLUDE_{node.value}"


def _yaml_secret(loader, node):
    return f"SECRET_{node.value}"


def _yaml_input(loader, node):
    return f"INPUT_{node.value}"


def _yaml_include_list(loader, node):
    return []


MooseSupervisorLoader.add_constructor("!include", _yaml_include)
MooseSupervisorLoader.add_constructor("!secret", _yaml_secret)
MooseSupervisorLoader.add_constructor("!input", _yaml_input)
MooseSupervisorLoader.add_constructor("!include_dir_merge_list", _yaml_include_list)
MooseSupervisorLoader.add_constructor("!include_dir_named", _yaml_include_list)


SUPERVISOR_ID = "v7_5_main_supervisor"


@pytest.fixture(scope="module")
def supervisor():
    path = os.path.join(os.path.dirname(__file__), "..", "automations.yaml")
    with open(path, "r") as fh:
        data = yaml.load(fh, Loader=MooseSupervisorLoader)
    auto = next((a for a in data if a.get("id") == SUPERVISOR_ID), None)
    assert auto is not None, f"{SUPERVISOR_ID} automation must exist"
    return auto


def _walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk(value)


def _bedtime_if_step(supervisor):
    """Locate the top-level `- if:` step whose value_template gates on
    `kids_bedtime and season in ['cooling', 'shoulder']`."""
    for step in supervisor.get("action", []):
        if not isinstance(step, dict) or "if" not in step:
            continue
        conditions = step.get("if") or []
        for cond in conditions:
            if not isinstance(cond, dict):
                continue
            template = cond.get("value_template", "")
            if "kids_bedtime" in template and "season in ['cooling', 'shoulder']" in template:
                return step
    pytest.fail(
        "Could not find the kids' bedtime `- if:` step in v7_5_main_supervisor.action"
    )


def test_kids_bedtime_variable_present(supervisor):
    for node in _walk(supervisor):
        variables = node.get("variables") if isinstance(node, dict) else None
        if isinstance(variables, dict) and "kids_bedtime" in variables:
            assert (
                variables["kids_bedtime"]
                == "{{ now().hour >= 18 or now().hour < 7 }}"
            ), f"kids_bedtime template unexpected: {variables['kids_bedtime']!r}"
            return
    pytest.fail("kids_bedtime variable missing from supervisor variables block")


def test_bedtime_block_gates_on_kids_bedtime_and_cooling_or_shoulder(supervisor):
    step = _bedtime_if_step(supervisor)
    # Ensure the gate is a single condition (no extra silent conditions).
    conditions = step.get("if") or []
    assert len(conditions) == 1, (
        "Bedtime block should gate on exactly one condition; got: "
        f"{conditions!r}"
    )
    template = conditions[0].get("value_template", "")
    assert "kids_bedtime" in template
    assert "season in ['cooling', 'shoulder']" in template


def _bedtime_room_if(step, entity):
    """Return the inner `- if:` step that owns one room's cool/off decision."""
    inner_steps = step.get("then") or []
    for inner in inner_steps:
        if not isinstance(inner, dict) or "if" not in inner:
            continue
        # Discover the actions in either the then or else branch and match
        # the room by entity id.
        for branch_key in ("then", "else"):
            for act in inner.get(branch_key) or []:
                if not isinstance(act, dict):
                    continue
                target = act.get("target", {}).get("entity_id")
                if target == entity:
                    return inner
    pytest.fail(f"Bedtime block has no inner `- if:` block for {entity}")


@pytest.mark.parametrize(
    "entity, temp_var",
    [
        ("climate.lincoln_air", "kb_lincoln_cool"),
        ("climate.lilly_air", "kb_lilly_cool"),
    ],
)
def test_bedtime_room_has_cool_and_off_branches(supervisor, entity, temp_var):
    """Each room has an inner `- if:` that gates on kb_<room>_cool. The then
    branch commands cool + fan turbo; the else branch commands off. fan_mode
    turbo is issued ONLY on the cool path — not on off."""
    outer = _bedtime_if_step(supervisor)
    inner = _bedtime_room_if(outer, entity)

    inner_conditions = inner.get("if") or []
    inner_template = "".join(c.get("value_template", "") for c in inner_conditions)
    assert temp_var in inner_template, (
        f"Bedtime {entity} inner if must gate on {temp_var}; got: "
        f"{inner_template!r}"
    )

    then_steps = inner.get("then") or []
    else_steps = inner.get("else") or []
    assert then_steps, f"Bedtime {entity} then branch must not be empty"
    assert else_steps, f"Bedtime {entity} else branch must not be empty"

    # Then: exactly one set_temperature (cool@61) and one set_fan_mode (turbo).
    set_temperature_hits = [
        s for s in then_steps
        if (s.get("action") or s.get("service")) == "climate.set_temperature"
        and s.get("target", {}).get("entity_id") == entity
    ]
    set_fan_mode_hits = [
        s for s in then_steps
        if (s.get("action") or s.get("service")) == "climate.set_fan_mode"
        and s.get("target", {}).get("entity_id") == entity
    ]
    assert len(set_temperature_hits) == 1, (
        f"Bedtime {entity} cool path must issue exactly one set_temperature; "
        f"got {len(set_temperature_hits)}"
    )
    assert len(set_fan_mode_hits) == 1, (
        f"Bedtime {entity} cool path must issue exactly one set_fan_mode; "
        f"got {len(set_fan_mode_hits)}"
    )
    assert set_temperature_hits[0].get("data", {}).get("hvac_mode") == "cool"
    assert set_temperature_hits[0].get("data", {}).get("temperature") == 61
    assert set_fan_mode_hits[0].get("data", {}).get("fan_mode") == "turbo"

    # Else: exactly one set_hvac_mode off. No turbo written on the off path.
    set_hvac_off = [
        s for s in else_steps
        if (s.get("action") or s.get("service")) == "climate.set_hvac_mode"
        and s.get("target", {}).get("entity_id") == entity
        and s.get("data", {}).get("hvac_mode") == "off"
    ]
    assert len(set_hvac_off) == 1, (
        f"Bedtime {entity} off path must issue exactly one set_hvac_mode off; "
        f"got {len(set_hvac_off)}"
    )
    turbo_on_off_path = [
        s for s in else_steps
        if (s.get("action") or s.get("service")) == "climate.set_fan_mode"
    ]
    assert not turbo_on_off_path, (
        f"Bedtime {entity} off path must not issue set_fan_mode: "
        f"{turbo_on_off_path!r}"
    )


def test_bedtime_hysteresis_variables_encode_66_70_deadband(supervisor):
    """Lincoln: engage at truth >= 70, continue while > 66 (66/70 deadband).
    Lilly: engage at truth >= 72, continue while > 68 (68/72 deadband per
    2026-07-09 operator decision)."""
    outer = _bedtime_if_step(supervisor)
    variables_step = next(
        (s for s in outer.get("then") or [] if isinstance(s, dict) and "variables" in s),
        None,
    )
    assert variables_step, "Bedtime block must define kb_lincoln_cool / kb_lilly_cool variables"
    variables = variables_step["variables"]

    # Lincoln — 66/70 deadband (unchanged)
    ln_template = variables["kb_lincoln_cool"]
    assert "lincoln_temp >= 70" in ln_template, (
        "Lincoln must engage at lincoln_temp >= 70"
    )
    assert "lincoln_temp > 66" in ln_template, (
        "Lincoln must continue only while lincoln_temp > 66"
    )
    assert "== 'cool'" in ln_template, (
        "Lincoln continue-branch must consult current head state"
    )

    # Lilly — 68/72 deadband (permanent, per 2026-07-09 operator decision)
    ly_template = variables["kb_lilly_cool"]
    assert "lilly_temp >= 72" in ly_template, (
        "Lilly must engage at lilly_temp >= 72"
    )
    assert "lilly_temp > 68" in ly_template, (
        "Lilly must continue only while lilly_temp > 68"
    )
    assert "== 'cool'" in ly_template, (
        "Lilly continue-branch must consult current head state"
    )


def test_bedtime_lincoln_and_lilly_are_independent(supervisor):
    """Lincoln and Lilly must run in separate `- if:` steps so one room's
    state never gates the other."""
    outer = _bedtime_if_step(supervisor)
    inner_ifs = [
        s for s in outer.get("then") or []
        if isinstance(s, dict) and "if" in s
    ]
    # We expect exactly two per-room `- if:` steps (Lincoln, Lilly).
    assert len(inner_ifs) == 2, (
        f"Bedtime block must have exactly two per-room inner `- if:` steps; "
        f"got {len(inner_ifs)}"
    )
    entities_seen = set()
    for inner in inner_ifs:
        for branch_key in ("then", "else"):
            for act in inner.get(branch_key) or []:
                target = act.get("target", {}).get("entity_id") if isinstance(act, dict) else None
                if target in ("climate.lincoln_air", "climate.lilly_air"):
                    entities_seen.add(target)
    assert entities_seen == {"climate.lincoln_air", "climate.lilly_air"}, (
        f"Bedtime block must own both Lincoln and Lilly independently; "
        f"saw: {entities_seen!r}"
    )
