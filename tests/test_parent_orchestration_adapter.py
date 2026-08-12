"""Execution tests for the reviewed-zone parent adapter seam."""

from pathlib import Path

import pytest

from parent_orchestration_adapter import ZONE_ARTIFACTS, load_zone_calls, run_parent
from parent_orchestration_harness import ZONE_ORDER
from supervisor_fixture import load_supervisor, zone_action_groups


EXPECTED_CALL_COUNTS = {
    "Master": 6,
    "Lincoln": 9,
    "Lilly": 9,
    "Living Room": 6,
}

AUTOMATIONS = Path(__file__).parents[1] / "automations.yaml"
EXPECTED_BOUNDARY_COUNTS = {
    "climate.master_bedroom_air": 2,
    "climate.lincoln_air": 3,
    "climate.lilly_air": 3,
    "climate.living_room_air": 2,
}


def test_no_failure_invokes_all_zone_units_and_calls_in_order():
    calls = []

    report = run_parent(calls.append)

    assert report.invoked == ZONE_ORDER
    assert report.successful == ZONE_ORDER
    assert report.failures == ()
    assert calls == [call for zone in ZONE_ORDER for call in load_zone_calls(zone)]
    assert {zone: len(load_zone_calls(zone)) for zone in ZONE_ORDER} == EXPECTED_CALL_COUNTS


@pytest.mark.parametrize("failed_zone", ("Master", "Lincoln", "Lilly"))
def test_failure_stops_failed_zone_calls_and_continues_later_zones(failed_zone):
    attempted = []
    error = RuntimeError(f"{failed_zone} call failed")
    failure_index = 1

    def executor(call):
        attempted.append(call)
        zone_attempts = [item for item in attempted if item.zone == call.zone]
        if call.zone == failed_zone and len(zone_attempts) - 1 == failure_index:
            raise error

    report = run_parent(executor)

    assert report.invoked == ZONE_ORDER
    assert failed_zone not in report.successful
    assert report.successful == tuple(zone for zone in ZONE_ORDER if zone != failed_zone)
    assert [(failure.zone, failure.exception) for failure in report.failures] == [
        (failed_zone, error)
    ]
    assert len([call for call in attempted if call.zone == failed_zone]) == failure_index + 1
    for later_zone in ZONE_ORDER[ZONE_ORDER.index(failed_zone) + 1 :]:
        assert [call for call in attempted if call.zone == later_zone] == list(
            load_zone_calls(later_zone)
        )


def test_adapter_does_not_modify_zone_artifacts():
    before = {path: path.read_bytes() for path in ZONE_ARTIFACTS.values()}

    run_parent(lambda call: None)

    assert {path: path.read_bytes() for path in ZONE_ARTIFACTS.values()} == before


def test_actual_parent_contains_each_complete_zone_at_the_action_boundary():
    groups = zone_action_groups(load_supervisor(AUTOMATIONS))

    assert {entity: len(found) for entity, found in groups.items()} == (
        EXPECTED_BOUNDARY_COUNTS
    )
    for entity, found in groups.items():
        assert all(group.continue_on_error for group in found), entity
        assert all(group.alias and group.alias.startswith("Zone boundary:") for group in found)


def test_parent_never_moves_continue_on_error_onto_a_climate_service_call():
    supervisor = load_supervisor(AUTOMATIONS)

    def walk(value):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)

    climate_calls = [
        node
        for node in walk(supervisor)
        if isinstance(node.get("action"), str)
        and node["action"].startswith("climate.")
    ]
    assert climate_calls
    assert all("continue_on_error" not in call for call in climate_calls)


@pytest.mark.parametrize("season_index", (0, 1))
def test_parent_cooling_paths_preserve_zone_evaluation_order(season_index):
    supervisor = load_supervisor(AUTOMATIONS)
    season_choose = supervisor["action"][2]["choose"]
    sequence = season_choose[season_index]["sequence"]

    if season_index == 1:
        sequence = sequence[0]["default"][0]["default"]

    aliases = [
        step["alias"]
        for step in sequence
        if isinstance(step, dict) and step.get("alias", "").startswith("Zone boundary:")
    ]
    assert aliases == [
        "Zone boundary: Master cooling" if season_index == 0 else "Zone boundary: Master shoulder cooling",
        "Zone boundary: Lincoln cooling" if season_index == 0 else "Zone boundary: Lincoln shoulder cooling",
        "Zone boundary: Lilly cooling" if season_index == 0 else "Zone boundary: Lilly shoulder cooling",
        "Zone boundary: Living Room cooling" if season_index == 0 else "Zone boundary: Living Room shoulder cooling",
    ]
