"""
Truth-Sensor Report-Time Freshness Regression Guards
====================================================

Locks the freshness-clock migration delivered in
``claude/truth-freshness-last-reported`` (the follow-up to PR #123).

Doctrine: freshness means "is this sensor still REPORTING?" — measured by
report time (``last_reported``), not value-change time (``last_changed``). A
thermally stable room can report the same temperature for hours; that is not
staleness. See:
  docs/comfort_band_and_truth_confidence_plan.md
  docs/5_runtime_layer.md §7.9
  truth_sensor_architecture.md (Sensor Freshness)

These tests inspect the live YAML source text. They assert nothing about, and
change nothing in, comfort thresholds, weights, source lists, safety gates, or
supervisor behavior.
"""

import os
import re

import pytest


REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")

CONFIG = os.path.join(REPO_ROOT, "configuration.yaml")
AUTOMATIONS = os.path.join(REPO_ROOT, "automations.yaml")

# The freshness-check shape used throughout the truth templates:
#   (now() - states.<entity>.<clock>).total_seconds() < <max_age>
FRESHNESS_CALL = ".total_seconds()"
LAST_CHANGED_CLOCK = ".last_changed).total_seconds()"
LAST_REPORTED_CLOCK = ".last_reported).total_seconds()"


def _read(path):
    if not os.path.exists(path):
        pytest.skip(f"{os.path.basename(path)} not found.")
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------------------- #
# configuration.yaml: freshness clock migrated to report time
# --------------------------------------------------------------------------- #

def test_config_truth_freshness_uses_report_time_clock():
    text = _read(CONFIG)
    assert LAST_REPORTED_CLOCK in text, (
        "Truth freshness checks must compare against last_reported."
    )


def test_config_truth_freshness_does_not_use_last_changed_clock():
    text = _read(CONFIG)
    assert LAST_CHANGED_CLOCK not in text, (
        "configuration.yaml must not use last_changed as a freshness clock; "
        "a stable-but-reporting sensor would be false-staled."
    )
    # Note: the word "last_changed" may still appear in an explanatory comment;
    # what matters is that it is never wired into a .total_seconds() freshness
    # comparison (asserted above).


def test_config_every_freshness_call_uses_report_time():
    """Every (... ).total_seconds() freshness comparison resolves to a
    last_reported clock — none slipped through as last_changed."""
    text = _read(CONFIG)
    total_calls = text.count(FRESHNESS_CALL)
    reported_calls = text.count(LAST_REPORTED_CLOCK)
    changed_calls = text.count(LAST_CHANGED_CLOCK)
    assert changed_calls == 0
    assert reported_calls == total_calls, (
        f"{total_calls} freshness calls found but only {reported_calls} use "
        "last_reported; some freshness check is on a different clock."
    )


# --------------------------------------------------------------------------- #
# CO2 cadence preserved (distinct 3h window, only the clock changed)
# --------------------------------------------------------------------------- #

def test_config_co2_three_hour_window_preserved():
    """CO2 truth keeps its distinct 10800s (3h) window — this PR changes the
    freshness CLOCK only, not any max_age / cadence value."""
    text = _read(CONFIG)
    assert "< 10800" in text, "CO2 truth 3-hour (10800s) window must be preserved."
    # The 2-hour temperature/humidity window is also untouched.
    assert "max_age = 7200" in text, "2-hour (7200s) staleness window must be preserved."


# --------------------------------------------------------------------------- #
# Migration did not bleed into automations.yaml
# --------------------------------------------------------------------------- #

def test_automations_freshness_clock_untouched():
    """automations.yaml must not be touched by this migration: it legitimately
    uses climate.*.last_changed to measure how long a unit has been in a mode
    (state-duration / value-transition), which is NOT a reporting-freshness
    check and must stay last_changed."""
    text = _read(AUTOMATIONS)
    assert ".last_reported)" not in text, (
        "automations.yaml should not have been migrated to last_reported."
    )
    # Every last_changed in automations.yaml must be on a climate.* entity
    # (state-duration), never a sensor.* freshness check.
    domains = re.findall(r"states\.(\w+)\.\w+\.last_changed", text)
    assert domains, "Expected the existing climate.* state-duration checks to remain."
    non_climate = [d for d in domains if d != "climate"]
    assert not non_climate, (
        f"automations.yaml last_changed used on non-climate domains {non_climate}; "
        "those would be freshness checks that should use report-time instead."
    )


# --------------------------------------------------------------------------- #
# Safety + comfort invariants untouched by a freshness PR
# --------------------------------------------------------------------------- #

def test_section3_safety_floor_thresholds_unchanged():
    """A freshness PR must not alter Section 3 safety floors."""
    text = _read(AUTOMATIONS)
    assert "below: 60" in text, "LR runaway 60°F floor must remain."
    assert "below: 58" in text, "Master emergency 58°F floor must remain."


def test_truth_sensor_weights_unchanged_spot_check():
    """Spot-check that representative truth weights are untouched (this PR
    changes only the freshness clock, never weights)."""
    text = _read(CONFIG)
    # Samsung internal stays low-weight; primaries keep their weights.
    assert "(hp * 0.20)" in text, "Samsung internal temperature weight 0.20 must remain."
    assert "(hp * 0.25)" in text, "Samsung internal humidity weight 0.25 must remain."
    assert "outlier_limit = 3.0" in text, "Lincoln 3°F outlier limit must remain."
