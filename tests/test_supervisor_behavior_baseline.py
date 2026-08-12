"""Behavior-preservation baselines for the current Section 2 zone policies."""

from pathlib import Path

import pytest

from supervisor_fixture import load_supervisor, zone_action_groups


AUTOMATIONS = Path(__file__).parents[1] / "automations.yaml"


@pytest.fixture(scope="module")
def supervisor():
    return load_supervisor(AUTOMATIONS)


@pytest.fixture(scope="module")
def zone_groups(supervisor):
    return zone_action_groups(supervisor)


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _variables(value, required):
    for node in _walk(value):
        variables = node.get("variables") if isinstance(node, dict) else None
        if isinstance(variables, dict) and required <= variables.keys():
            return variables
    pytest.fail(f"Supervisor variables not found: {sorted(required)}")


def _zone_group(zone_groups, entity_id, marker, path_prefix=None):
    matches = [
        group
        for group in zone_groups[entity_id]
        if marker in str(group.action)
        and (path_prefix is None or group.path[: len(path_prefix)] == path_prefix)
    ]
    assert len(matches) == 1, f"Expected one {marker!r} group for {entity_id}"
    return matches[0].action


def _assert_cool_61_turbo(group, entity_id):
    actions = list(_walk(group))
    assert any(
        (step.get("action") or step.get("service")) == "climate.set_temperature"
        and (step.get("target") or {}).get("entity_id") == entity_id
        and (step.get("data") or {}).get("hvac_mode") == "cool"
        and (step.get("data") or {}).get("temperature") == 61
        for step in actions
    )
    assert any(
        (step.get("action") or step.get("service")) == "climate.set_fan_mode"
        and (step.get("target") or {}).get("entity_id") == entity_id
        and (step.get("data") or {}).get("fan_mode") == "turbo"
        for step in actions
    )


@pytest.mark.parametrize(
    ("entity_id", "decision", "engage", "release"),
    (
        ("climate.lilly_air", "kb_lilly_cool", "lilly_temp >= 72", "lilly_temp > 68"),
        ("climate.lincoln_air", "kb_lincoln_cool", "lincoln_temp >= 70", "lincoln_temp > 66"),
    ),
)
def test_kids_bedtime_engage_release_and_action_intent(
    supervisor, zone_groups, entity_id, decision, engage, release
):
    variables = _variables(supervisor, {decision})
    template = variables[decision]
    assert engage in template
    assert release in template
    assert "== 'cool'" in template

    group = _zone_group(zone_groups, entity_id, decision)
    _assert_cool_61_turbo(group, entity_id)
    assert any(
        (step.get("action") or step.get("service")) == "climate.set_hvac_mode"
        and (step.get("data") or {}).get("hvac_mode") == "off"
        for step in _walk(group)
    )


def test_master_current_night_policy(supervisor, zone_groups):
    variables = _variables(supervisor, {"is_master_sleep", "m_off_at", "m_on_at", "m_setpoint"})
    assert variables["is_master_sleep"] == "{{ now().hour >= 18 or now().hour < 6 }}"
    assert variables["m_off_at"] == "{{ 74 if away else (62 if is_master_sleep else 68) }}"
    assert variables["m_on_at"] == "{{ 76 if away else (66 if is_master_sleep else 72) }}"
    assert variables["m_setpoint"] == "{{ 61 }}"

    group = _zone_group(zone_groups, "climate.master_bedroom_air", "master_temp >= m_on_at")
    template = str(group)
    assert "master_temp >= m_on_at" in template
    assert "master_temp <= m_off_at" in template
    assert "m_current == 'cool'" in template
    assert "fan_mode': 'turbo'" in template


def test_living_room_current_cooling_policy(supervisor, zone_groups):
    variables = _variables(
        supervisor, {"lr_conservation", "lr_off_at", "lr_on_at", "lr_setpoint"}
    )
    assert variables["lr_conservation"] == "{{ away or lr_night_primary }}"
    assert variables["lr_off_at"] == "{{ 74 if lr_conservation else 68 }}"
    assert variables["lr_on_at"] == "{{ 76 if lr_conservation else 72 }}"
    assert variables["lr_setpoint"] == "{{ 61 }}"

    group = _zone_group(
        zone_groups,
        "climate.living_room_air",
        "lr_temp > lr_on_at",
        ("action", 2, "choose", 0),
    )
    template = str(group)
    assert "lr_temp > lr_on_at" in template
    assert "lr_temp <= lr_off_at" in template
    assert "lr_current == 'cool'" in template
    assert "fan_mode': 'turbo'" in template
