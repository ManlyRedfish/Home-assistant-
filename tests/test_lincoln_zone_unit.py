"""Focused contract tests for the unwired Lincoln supervisor extraction."""

from pathlib import Path

import yaml

from supervisor_fixture import load_supervisor, zone_action_groups


ROOT = Path(__file__).parents[1]
AUTOMATIONS = ROOT / "automations.yaml"
LINCOLN_UNIT = ROOT / "supervisor_zones" / "lincoln.yaml"


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_lincoln_unit_is_an_exact_unwired_extraction():
    supervisor = load_supervisor(AUTOMATIONS)
    source_groups = zone_action_groups(supervisor)["climate.lincoln_air"]
    unit = yaml.safe_load(LINCOLN_UNIT.read_text(encoding="utf-8"))

    assert len(unit) == len(source_groups) == 3
    assert [tuple(item["source_path"]) for item in unit] == [
        group.path for group in source_groups
    ]
    assert [item["action"] for item in unit] == [group.action for group in source_groups]
    assert "supervisor_zones/lincoln.yaml" not in AUTOMATIONS.read_text(encoding="utf-8")


def test_lincoln_unit_declares_parent_dependencies_and_live_authority():
    text = LINCOLN_UNIT.read_text(encoding="utf-8")

    for dependency in (
        "kb_lincoln_cool",
        "lincoln_truth_ok",
        "kids_bedtime",
        "lincoln_temp",
        "l_on_at",
        "l_off_at",
        "l_current",
        "l_setpoint",
        "climate.lincoln_air",
    ):
        assert dependency in text

    assert "currently loaded automations.yaml source semantics" in text
    assert "live source remains authoritative" in text
    assert "timing or policy conflict" in text
    assert "MUST NOT be silently resolved" in text


def test_lincoln_unit_is_single_zone_and_preserves_off_actions():
    unit = yaml.safe_load(LINCOLN_UNIT.read_text(encoding="utf-8"))
    steps = list(_walk(unit))
    climate_targets = {
        (step.get("target") or {}).get("entity_id")
        for step in steps
        if isinstance(step.get("action"), str)
        and step["action"].startswith("climate.")
    }

    assert climate_targets == {"climate.lincoln_air"}
    assert sum(
        step.get("action") == "climate.set_hvac_mode"
        and (step.get("data") or {}).get("hvac_mode") == "off"
        for step in steps
    ) == 3


def test_set_temperature_failure_stops_later_fan_setup_and_remains_observable():
    unit = yaml.safe_load(LINCOLN_UNIT.read_text(encoding="utf-8"))

    for item in unit:
        sequences = [
            value
            for node in _walk(item["action"])
            for value in node.values()
            if isinstance(value, list)
            and any(
                isinstance(step, dict)
                and step.get("action") == "climate.set_temperature"
                for step in value
            )
        ]
        assert len(sequences) == 1
        sequence = sequences[0]
        setpoint_index = next(
            index
            for index, step in enumerate(sequence)
            if step.get("action") == "climate.set_temperature"
        )
        fan_index = next(
            index
            for index, step in enumerate(sequence)
            if step.get("action") == "climate.set_fan_mode"
        )

        assert setpoint_index < fan_index
        assert "continue_on_error" not in sequence[setpoint_index]
