"""Execution tests for the reviewed-zone parent adapter seam."""

import pytest

from parent_orchestration_adapter import ZONE_ARTIFACTS, load_zone_calls, run_parent
from parent_orchestration_harness import ZONE_ORDER


EXPECTED_CALL_COUNTS = {
    "Master": 6,
    "Lincoln": 9,
    "Lilly": 9,
    "Living Room": 6,
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
