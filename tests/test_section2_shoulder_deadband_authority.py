"""
Section 2 shoulder-season deadband authority.

Locks the 2026-07-12 operator decision: room deadbands are year-round
comfort contracts. Shoulder season may select equipment strategy, but it must
not replace room hysteresis with a one-threshold shortcut or bulk-force a
comfort-controlled room off.
"""

from __future__ import annotations

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


ROOT = os.path.join(os.path.dirname(__file__), "..")
AUTOMATIONS = os.path.join(ROOT, "automations.yaml")
SUPERVISOR_ID = "v7_5_main_supervisor"
COMFORT_HEADS = {
    "climate.living_room_air",
    "climate.master_bedroom_air",
    "climate.lincoln_air",
    "climate.lilly_air",
}


@pytest.fixture(scope="module")
def automations_text() -> str:
    with open(AUTOMATIONS, "r", encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def automations_data():
    with open(AUTOMATIONS, "r", encoding="utf-8") as fh:
        return yaml.load(fh, Loader=MooseSupervisorLoader)


@pytest.fixture(scope="module")
def supervisor(automations_data):
    auto = next((a for a in automations_data if a.get("id") == SUPERVISOR_ID), None)
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


def _section(text: str, start: str, end: str) -> str:
    assert start in text, f"Missing section start marker {start!r}"
    assert end in text, f"Missing section end marker {end!r}"
    return text.split(start, 1)[1].split(end, 1)[0]


def _outer_choose(supervisor):
    for step in supervisor.get("action", []):
        if isinstance(step, dict) and "choose" in step:
            return step["choose"]
    pytest.fail("Could not find the season choose block in v7_5_main_supervisor")


def _season_branch(supervisor, season: str):
    needle = f"season == '{season}'"
    for branch in _outer_choose(supervisor):
        for cond in branch.get("conditions", []):
            if needle in cond.get("value_template", ""):
                return branch
    pytest.fail(f"Could not find {season!r} branch")


def _shoulder_branch(supervisor):
    return _season_branch(supervisor, "shoulder")


def _shoulder_text(automations_text: str) -> str:
    section2 = _section(
        automations_text,
        "# SECTION 2: MAIN SUPERVISOR",
        "# SECTION 3: SAFETY GATES",
    )
    return section2.split("# BRANCH 2: SHOULDER SEASON", 1)[1].split(
        "# BRANCH 3: HEATING SEASON",
        1,
    )[0]


def _target_entities(step: dict) -> set[str]:
    entity_id = (step.get("target") or {}).get("entity_id")
    if isinstance(entity_id, str):
        return {entity_id}
    if isinstance(entity_id, list):
        return set(entity_id)
    return set()


def _hvac_mode(step: dict):
    return (step.get("data") or {}).get("hvac_mode")


def _set_hvac_mode_off_steps(sequence) -> list[dict]:
    return [
        step
        for step in _walk(sequence)
        if isinstance(step, dict)
        and (step.get("action") or step.get("service")) == "climate.set_hvac_mode"
        and _hvac_mode(step) in ("off", False)
    ]


def _variables(supervisor) -> dict[str, set]:
    found: dict[str, set] = {}
    for node in _walk(supervisor):
        variables = node.get("variables") if isinstance(node, dict) else None
        if isinstance(variables, dict):
            for key, value in variables.items():
                found.setdefault(key, set()).add(value)
    return found


def test_no_new_automation_ids_helpers_or_timers(automations_data, automations_text):
    ids = {a.get("id") for a in automations_data if isinstance(a, dict)}
    assert SUPERVISOR_ID in ids
    assert len(ids) == len([a for a in automations_data if isinstance(a, dict)])

    shoulder = _shoulder_text(automations_text)
    forbidden = ("input_boolean.", "input_number.", "input_select.", "timer.")
    for token in forbidden:
        assert token not in shoulder, (
            "Shoulder deadband repair must reuse existing Section 2 variables and "
            f"must not create or depend on helper/timer control paths: {token}"
        )


def test_section3_content_unchanged_from_base():
    import subprocess

    current = subprocess.check_output(
        ["git", "show", "HEAD:automations.yaml"],
        cwd=ROOT,
        text=True,
    )
    with open(AUTOMATIONS, "r", encoding="utf-8") as fh:
        working = fh.read()

    base_section3 = _section(current, "# SECTION 3: SAFETY GATES", "# SECTION 4:")
    work_section3 = _section(working, "# SECTION 3: SAFETY GATES", "# SECTION 4:")
    assert work_section3 == base_section3


def test_shoulder_branch_has_no_zero_width_cooling_shortcuts(automations_text):
    shoulder = _shoulder_text(automations_text)
    forbidden_fragments = (
        "'cool' if master_temp > 70 else 'off'",
        "'cool' if lincoln_temp > 70 else 'off'",
        "'cool' if lilly_temp > 70 else 'off'",
    )
    for fragment in forbidden_fragments:
        assert fragment not in shoulder, (
            "Shoulder cooling must use engage/release/hold hysteresis, not a "
            f"single threshold shortcut: {fragment}"
        )


def test_shoulder_bulk_off_never_targets_comfort_heads(supervisor):
    shoulder = _shoulder_branch(supervisor)
    offenders = []
    for step in _set_hvac_mode_off_steps(shoulder.get("sequence", [])):
        overlap = _target_entities(step) & COMFORT_HEADS
        if overlap:
            offenders.append((sorted(overlap), step))

    assert not offenders, (
        "Shoulder branch must not bulk-force comfort-controlled heads off. "
        f"Offending targets: {offenders!r}"
    )


def test_shoulder_daytime_lr_profile_resolves_to_68_72_when_not_away_or_night(supervisor):
    variables = _variables(supervisor)
    assert variables["lr_conservation"] == {"{{ away or lr_night_primary }}"}
    assert variables["lr_off_at"] == {"{{ 74 if lr_conservation else 68 }}"}
    assert variables["lr_on_at"] == {"{{ 76 if lr_conservation else 72 }}"}


def test_shoulder_lr_conservation_profile_resolves_to_74_76_with_hold(supervisor):
    variables = _variables(supervisor)
    assert variables["lr_off_at"] == {"{{ 74 if lr_conservation else 68 }}"}
    assert variables["lr_on_at"] == {"{{ 76 if lr_conservation else 72 }}"}

    lr_steps = [
        node
        for node in _walk(_shoulder_branch(supervisor))
        if isinstance(node, dict)
        and (node.get("action") or node.get("service")) == "climate.set_temperature"
        and _target_entities(node) == {"climate.living_room_air"}
        and "cool" in str(_hvac_mode(node))
    ]
    assert lr_steps, "Shoulder branch must include an LR cooling deadband command"
    assert any("lr_current == 'cool'" in str(_hvac_mode(step)) for step in lr_steps)


def test_shoulder_cooling_profiles_have_engage_release_and_hold(supervisor):
    expected_fragments = {
        "climate.living_room_air": (
            "lr_temp > lr_on_at",
            "lr_temp <= lr_off_at",
            "lr_current == 'cool'",
        ),
        "climate.master_bedroom_air": (
            "master_temp > m_on_at",
            "master_temp <= m_off_at",
            "m_current == 'cool'",
        ),
        "climate.lincoln_air": (
            "lincoln_temp >= l_on_at",
            "lincoln_temp <= l_off_at",
            "l_current == 'cool'",
        ),
        "climate.lilly_air": (
            "lilly_temp >= ly_on_at",
            "lilly_temp <= ly_off_at",
            "ly_current == 'cool'",
        ),
    }
    shoulder = _shoulder_branch(supervisor)
    for entity, fragments in expected_fragments.items():
        matching = [
            node
            for node in _walk(shoulder)
            if isinstance(node, dict)
            and (node.get("action") or node.get("service")) == "climate.set_temperature"
            and entity in _target_entities(node)
            and "cool" in str(_hvac_mode(node))
        ]
        assert matching, f"Shoulder branch must command {entity} through a cooling profile"
        rendered = "\n".join(str(_hvac_mode(node)) for node in matching)
        for fragment in fragments:
            assert fragment in rendered, f"{entity} shoulder cooling missing {fragment!r}"


def test_invalid_truth_off_is_zone_local_in_shoulder(supervisor):
    shoulder_text = str(_shoulder_branch(supervisor))
    for truth_flag, entity in (
        ("master_truth_ok", "climate.master_bedroom_air"),
        ("lincoln_truth_ok", "climate.lincoln_air"),
        ("lilly_truth_ok", "climate.lilly_air"),
        ("lr_truth_ok", "climate.living_room_air"),
    ):
        assert truth_flag in shoulder_text, (
            f"Shoulder branch must check {truth_flag} before controlling {entity}"
        )
        assert entity in shoulder_text


def test_lincoln_lilly_bedtime_ownership_remains_exclusive(supervisor):
    shoulder = _shoulder_branch(supervisor)
    bedtime_guarded_if_steps = [
        node
        for node in _walk(shoulder)
        if isinstance(node, dict)
        and "if" in node
        and "not kids_bedtime" in str(node.get("if"))
    ]
    assert bedtime_guarded_if_steps, (
        "Shoulder daytime kid fallback commands must remain gated by not kids_bedtime"
    )

    for node in _walk(shoulder):
        if not isinstance(node, dict):
            continue
        targets = _target_entities(node)
        if targets & {"climate.lincoln_air", "climate.lilly_air"}:
            assert "not kids_bedtime" in str(node) or "kids_bedtime" not in str(node), (
                "Shoulder branch must not add an ungated second writer for "
                f"bedtime kid heads: {node!r}"
            )


def test_dining_may_remain_shoulder_off_but_not_bundled_with_lr_or_bedrooms(supervisor):
    shoulder = _shoulder_branch(supervisor)
    dining_off_steps = [
        step
        for step in _set_hvac_mode_off_steps(shoulder.get("sequence", []))
        if "climate.dining_room" in _target_entities(step)
    ]
    assert dining_off_steps, "Dining/Nest may remain explicitly off in shoulder routing"
    for step in dining_off_steps:
        assert not (_target_entities(step) & COMFORT_HEADS), (
            "Dining shoulder off command must not bundle LR or bedroom heads "
            f"with it: {step!r}"
        )
