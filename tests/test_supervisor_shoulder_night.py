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


def _outer_choose(supervisor):
    for step in supervisor.get("action", []):
        if isinstance(step, dict) and "choose" in step:
            return step["choose"]
    pytest.fail("Could not find the season choose block in v7_5_main_supervisor")


def _shoulder_branch(supervisor):
    for branch in _outer_choose(supervisor):
        for cond in branch.get("conditions", []):
            template = cond.get("value_template", "")
            if "season == 'shoulder'" in template:
                return branch
    pytest.fail("Could not find the shoulder-season branch")


def _shoulder_night_sequence(supervisor):
    shoulder = _shoulder_branch(supervisor)
    for step in shoulder.get("sequence", []):
        if isinstance(step, dict) and "choose" in step:
            for sub in step["choose"]:
                for cond in sub.get("conditions", []):
                    if "is_night" in cond.get("value_template", ""):
                        return sub.get("sequence", [])
    pytest.fail("Could not find the shoulder-night sub-branch")


def _bulk_off_targets(sequence):
    for step in sequence:
        if (
            isinstance(step, dict)
            and (step.get("action") or step.get("service")) == "climate.set_hvac_mode"
            and step.get("data", {}).get("hvac_mode") in ("off", False)
        ):
            entity_id = step.get("target", {}).get("entity_id")
            if isinstance(entity_id, str):
                return [entity_id]
            return list(entity_id or [])
    pytest.fail("Shoulder-night sub-branch has no bulk set_hvac_mode off step")


def _master_cooling_step(sequence):
    for step in sequence:
        if not isinstance(step, dict):
            continue
        if (step.get("action") or step.get("service")) != "climate.set_temperature":
            continue
        target = step.get("target", {}).get("entity_id")
        targets = [target] if isinstance(target, str) else list(target or [])
        if "climate.master_bedroom_air" in targets:
            return step
    return None


def test_shoulder_night_master_cooling_escape_step_exists(supervisor):
    sequence = _shoulder_night_sequence(supervisor)
    step = _master_cooling_step(sequence)
    assert step is not None, (
        "Shoulder-night sub-branch must contain a climate.set_temperature step "
        "targeting climate.master_bedroom_air (sleep-comfort escape)."
    )

    hvac_template = step.get("data", {}).get("hvac_mode", "")
    for token in ("cool", "off", "master_temp"):
        assert token in hvac_template, (
            f"Master cooling escape hvac_mode template must reference '{token}' "
            f"in the same step (single-action-dict invariant). Template was: "
            f"{hvac_template!r}"
        )


def test_shoulder_night_bulk_off_excludes_master(supervisor):
    targets = _bulk_off_targets(_shoulder_night_sequence(supervisor))
    assert "climate.master_bedroom_air" not in targets, (
        "Shoulder-night bulk-off list must not include climate.master_bedroom_air; "
        "master cooling escape owns that entity in this sub-branch."
    )


def test_shoulder_night_bulk_off_covers_dining_only(supervisor):
    # 2026-06-07 operator decision: Lincoln + Lilly are owned by the KIDS BEDTIME
    # COOLING block above the season choose during 18:00-07:00 in cooling +
    # shoulder. Since is_night (22:00-06:00) is a strict subset of kids_bedtime
    # (18:00-07:00), the shoulder-night bulk-off must exclude both kids' heads
    # and cover Dining only. Master is owned by the cooling escape step.
    targets = _bulk_off_targets(_shoulder_night_sequence(supervisor))
    assert "climate.dining_room" in targets, (
        "Shoulder-night bulk-off must still cover climate.dining_room."
    )
    for kid_entity in ("climate.lincoln_air", "climate.lilly_air"):
        assert kid_entity not in targets, (
            f"Shoulder-night bulk-off must not include {kid_entity}; the kids' "
            f"bedtime block owns Lincoln + Lilly here."
        )


def test_shoulder_night_lr_heating_preserved(supervisor):
    sequence = _shoulder_night_sequence(supervisor)
    lr_step = next(
        (
            s
            for s in sequence
            if isinstance(s, dict)
            and (s.get("action") or s.get("service")) == "climate.set_temperature"
            and s.get("target", {}).get("entity_id") == "climate.living_room_air"
        ),
        None,
    )
    assert lr_step is not None, "Shoulder-night LR set_temperature step must exist"

    data = lr_step.get("data", {})
    assert "lr_temp < (58 if away else 65)" in data.get("hvac_mode", ""), (
        "Shoulder-night LR heat/off decision must still gate on "
        "lr_temp < (58 if away else 65)."
    )
    assert data.get("temperature") == 79, (
        "Shoulder-night LR heat command must shove to 79 while the 58/65 "
        "truth threshold remains in hvac_mode."
    )


def test_shoulder_night_master_setpoint_below_off_threshold(supervisor):
    sequence = _shoulder_night_sequence(supervisor)
    step = _master_cooling_step(sequence)
    assert step is not None

    variable_steps = [
        s
        for s in sequence
        if isinstance(s, dict) and isinstance(s.get("variables"), dict)
    ]
    merged = {}
    for vs in variable_steps:
        merged.update(vs["variables"])

    on_at = merged.get("m_sleep_on_at", "")
    off_at = merged.get("m_sleep_off_at", "")
    setpoint = merged.get("m_sleep_setpoint", "")

    assert "if away else 66" in on_at, f"m_sleep_on_at template unexpected: {on_at!r}"
    assert (
        "if away else 62" in off_at
    ), f"m_sleep_off_at template unexpected: {off_at!r}"
    assert setpoint == "{{ 61 }}", (
        "Shoulder-night Master cooling command must shove to 61 while the "
        "sleep on/off thresholds remain unchanged."
    )
