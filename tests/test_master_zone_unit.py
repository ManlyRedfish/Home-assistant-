"""Focused contract tests for the unwired Master supervisor extraction."""

from pathlib import Path

import yaml

from supervisor_fixture import load_supervisor, zone_action_groups


ROOT = Path(__file__).parents[1]
AUTOMATIONS = ROOT / "automations.yaml"
MASTER_UNIT = ROOT / "supervisor_zones" / "master.yaml"


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_master_unit_is_an_exact_unwired_extraction():
    supervisor = load_supervisor(AUTOMATIONS)
    source_groups = zone_action_groups(supervisor)["climate.master_bedroom_air"]
    unit = yaml.safe_load(MASTER_UNIT.read_text(encoding="utf-8"))

    assert len(unit) == len(source_groups) == 2
    assert [tuple(item["source_path"]) for item in unit] == [
        group.path for group in source_groups
    ]
    assert [item["action"] for item in unit] == [group.action for group in source_groups]
    assert "supervisor_zones/master.yaml" not in AUTOMATIONS.read_text(encoding="utf-8")


def test_master_unit_declares_parent_dependencies_and_live_authority():
    text = MASTER_UNIT.read_text(encoding="utf-8")

    for dependency in (
        "master_truth_ok",
        "master_temp",
        "m_on_at",
        "m_off_at",
        "m_current",
        "m_setpoint",
        "climate.master_bedroom_air",
    ):
        assert dependency in text

    assert "sleep, daytime, and away" in text
    assert "currently loaded automations.yaml source semantics" in text
    assert "live source remains authoritative" in text
    assert "pre-cool, timing" in text
    assert "policy conflict" in text
    assert "MUST NOT be silently resolved" in text


def test_master_unit_is_single_zone_and_preserves_off_actions():
    unit = yaml.safe_load(MASTER_UNIT.read_text(encoding="utf-8"))
    steps = list(_walk(unit))
    climate_targets = {
        (step.get("target") or {}).get("entity_id")
        for step in steps
        if isinstance(step.get("action"), str)
        and step["action"].startswith("climate.")
    }

    assert climate_targets == {"climate.master_bedroom_air"}
    assert sum(
        step.get("action") == "climate.set_hvac_mode"
        and (step.get("data") or {}).get("hvac_mode") == "off"
        for step in steps
    ) == 2


def test_set_temperature_failure_stops_later_fan_setup_and_remains_observable():
    unit = yaml.safe_load(MASTER_UNIT.read_text(encoding="utf-8"))

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
