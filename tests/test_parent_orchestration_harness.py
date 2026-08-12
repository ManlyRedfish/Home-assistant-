"""Executable F0 contract for future parent zone orchestration."""

import pytest

from parent_orchestration_harness import ZONE_ORDER, run_parent


@pytest.mark.parametrize(
    ("failed_zone", "later_zones"),
    (
        ("Master", ("Lincoln", "Lilly", "Living Room")),
        ("Lincoln", ("Lilly", "Living Room")),
        ("Lilly", ("Living Room",)),
    ),
)
def test_failure_does_not_stop_later_zones(failed_zone, later_zones):
    report = run_parent({failed_zone: RuntimeError(f"{failed_zone} failed")})

    failed_index = ZONE_ORDER.index(failed_zone)
    assert report.invoked == ZONE_ORDER
    assert report.invoked[failed_index + 1 :] == later_zones


def test_no_failure_invokes_all_zones_successfully_in_order():
    report = run_parent()

    assert report.invoked == ZONE_ORDER
    assert report.successful == ZONE_ORDER
    assert report.failures == ()


def test_failed_zone_is_not_successful_and_failure_remains_observable():
    error = RuntimeError("Lincoln unavailable")

    report = run_parent({"Lincoln": error})

    assert report.successful == ("Master", "Lilly", "Living Room")
    assert "Lincoln" not in report.successful
    assert len(report.failures) == 1
    assert report.failures[0].zone == "Lincoln"
    assert report.failures[0].exception is error
