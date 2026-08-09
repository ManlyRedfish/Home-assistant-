"""
Truth-Confidence Model Contract (pure model — no runtime dependency)
====================================================================

First guardrail PR after PR #122. This test pins the *planned* graded
truth-confidence model from
``docs/comfort_band_and_truth_confidence_plan.md`` and
``docs/5_runtime_layer.md`` §7.9 as a pure, self-contained contract.

IMPORTANT: this test does NOT touch runtime YAML. It does not add live template
sensors, does not change ``configuration.yaml`` truth logic, and does not
migrate freshness from ``last_changed`` to ``last_reported``. It encodes the
future contract so a later runtime implementation has a fixed target.

The four planned truth states:
  - healthy  : 2+ valid PRIMARY sources (Matter / Bluetooth / SmartThings).
  - degraded : exactly one valid primary source, or primary + fallback only.
  - fallback : only Samsung / mini-split internal (or held-last-good) remains;
               NEVER healthy.
  - failed   : no usable source.

Source classes:
  - primary       : human-space Matter / BT / SmartThings sensors.
  - fallback      : Samsung / mini-split internal thermistor (biased, low weight).
  - experimental  : Apollo / MSR / ESP. Observability-only. Never feeds the
                    value and never raises confidence to healthy.

Freshness contract (proposed): a source is "report-fresh" if it has REPORTED
recently, regardless of whether its VALUE changed. A stable sensor whose value
has not changed for a long time but is still reporting is NOT stale.
"""

import os

import pytest


# --------------------------------------------------------------------------- #
# Reference model (the proposed contract). Pure functions, no HA, no YAML.
# These mirror the doctrine in docs/comfort_band_and_truth_confidence_plan.md
# and docs/5_runtime_layer.md §7.9. They are intentionally self-contained: this
# is a contract test, not a runtime implementation.
# --------------------------------------------------------------------------- #

PRIMARY = "primary"
FALLBACK = "fallback"
EXPERIMENTAL = "experimental"

VALID_STATUSES = {"healthy", "degraded", "fallback", "failed"}


def classify_truth_status(sources):
    """Classify a room's truth status from its candidate sources.

    ``sources`` is an iterable of dicts: {"class": <PRIMARY|FALLBACK|EXPERIMENTAL>,
    "valid": <bool>}.  "valid" means the source is present, fresh, and (for
    primaries) not outlier-rejected.

    Experimental sources never elevate status — they are observability-only.
    """
    valid_primary = sum(
        1 for s in sources if s.get("class") == PRIMARY and s.get("valid")
    )
    valid_fallback = sum(
        1 for s in sources if s.get("class") == FALLBACK and s.get("valid")
    )

    if valid_primary >= 2:
        return "healthy"
    if valid_primary == 1:
        return "degraded"
    # Zero valid primary sources below here.
    if valid_fallback >= 1:
        return "fallback"
    return "failed"


def is_report_fresh(last_changed_age_s, last_reported_age_s, max_age_s=7200):
    """Proposed freshness rule: freshness follows REPORT time, not value-change
    time. A stable but still-reporting sensor is fresh."""
    return last_reported_age_s < max_age_s


def is_value_change_fresh(last_changed_age_s, max_age_s=7200):
    """The OLD freshness rule (value-change time), modelled here only to
    document the bug the report-time model fixes. Not a target; the live
    config now uses report-time freshness (see the report-time tests below)."""
    return last_changed_age_s < max_age_s


# --------------------------------------------------------------------------- #
# Status ladder contract
# --------------------------------------------------------------------------- #

def test_two_primary_sources_is_healthy():
    sources = [
        {"class": PRIMARY, "valid": True},   # e.g. Matter
        {"class": PRIMARY, "valid": True},   # e.g. Bluetooth
        {"class": FALLBACK, "valid": True},  # Samsung internal present too
    ]
    assert classify_truth_status(sources) == "healthy"


def test_one_primary_source_is_degraded():
    sources = [
        {"class": PRIMARY, "valid": True},
        {"class": PRIMARY, "valid": False},  # second primary stale/rejected
    ]
    assert classify_truth_status(sources) == "degraded"


def test_primary_plus_fallback_only_is_degraded():
    sources = [
        {"class": PRIMARY, "valid": True},
        {"class": FALLBACK, "valid": True},
    ]
    assert classify_truth_status(sources) == "degraded"


def test_samsung_only_is_fallback_never_healthy():
    sources = [
        {"class": FALLBACK, "valid": True},   # Samsung / mini-split internal only
        {"class": PRIMARY, "valid": False},   # all primaries unavailable
    ]
    status = classify_truth_status(sources)
    assert status == "fallback"
    assert status != "healthy", "Samsung/mini-split-only truth must never be healthy."


def test_no_usable_source_is_failed():
    sources = [
        {"class": PRIMARY, "valid": False},
        {"class": FALLBACK, "valid": False},
        {"class": EXPERIMENTAL, "valid": True},  # ESP/Apollo cannot rescue
    ]
    assert classify_truth_status(sources) == "failed"


def test_empty_source_set_is_failed():
    assert classify_truth_status([]) == "failed"


# --------------------------------------------------------------------------- #
# Partial degradation must not collapse into total failure
# --------------------------------------------------------------------------- #

def test_unavailable_esp_with_other_primaries_is_not_failed():
    """An unavailable ESP/Apollo source must not equal total truth failure when
    Matter / Bluetooth / SmartThings remain available."""
    sources = [
        {"class": EXPERIMENTAL, "valid": False},  # ESP/Apollo down
        {"class": PRIMARY, "valid": True},        # Matter up
        {"class": PRIMARY, "valid": True},        # SmartThings up
    ]
    status = classify_truth_status(sources)
    assert status != "failed"
    assert status == "healthy"


def test_experimental_sources_never_make_healthy():
    """Apollo/MSR/ESP are observability-only; they must not raise confidence."""
    sources = [
        {"class": EXPERIMENTAL, "valid": True},
        {"class": EXPERIMENTAL, "valid": True},
        {"class": EXPERIMENTAL, "valid": True},
    ]
    assert classify_truth_status(sources) == "failed"


# --------------------------------------------------------------------------- #
# Freshness contract: stable value != stale
# --------------------------------------------------------------------------- #

def test_stable_sensor_with_recent_report_is_report_fresh():
    """Old last_changed (value unchanged for ~3h) but recent last_reported
    (reported 60s ago) must be considered fresh under the proposed model."""
    assert is_report_fresh(last_changed_age_s=10800, last_reported_age_s=60) is True


def test_proposed_model_diverges_from_current_last_changed_rule():
    """Documents the bug: the SAME stable-but-reporting sensor is wrongly
    treated as stale by the current last_changed-only rule."""
    last_changed_age_s = 10800  # value hasn't changed in 3h
    last_reported_age_s = 60     # but it's still reporting
    assert is_report_fresh(last_changed_age_s, last_reported_age_s) is True
    assert is_value_change_fresh(last_changed_age_s) is False


# --------------------------------------------------------------------------- #
# Doc consistency: the contract states above match the doctrine docs
# --------------------------------------------------------------------------- #

def _read_doc(rel_path):
    path = os.path.join(os.path.dirname(__file__), "..", "docs", rel_path)
    assert os.path.exists(path), f"Expected doctrine doc missing: docs/{rel_path}"
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def test_status_ladder_is_documented_in_runtime_layer():
    runtime = _read_doc("5_runtime_layer.md")
    for status in VALID_STATUSES:
        assert status in runtime, f"Runtime layer §7.9 must document the '{status}' status."


def test_plan_doc_documents_status_ladder():
    plan = _read_doc("comfort_band_and_truth_confidence_plan.md")
    for status in VALID_STATUSES:
        assert status in plan, f"Plan doc must document the '{status}' status."


# --------------------------------------------------------------------------- #
# Runtime expectation — the freshness migration has landed (see
# claude/truth-freshness-last-reported). These were xfail in PR #123 and are
# now hard assertions: truth freshness is measured by report time.
# --------------------------------------------------------------------------- #

def _read_config_text():
    path = os.path.join(os.path.dirname(__file__), "..", "configuration.yaml")
    if not os.path.exists(path):
        pytest.skip("configuration.yaml not found.")
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def test_live_truth_templates_use_report_time_freshness():
    """The live truth templates use report-time freshness (last_reported /
    last_updated) so a stable-but-reporting sensor is not false-staled."""
    config_text = _read_config_text()
    assert "last_reported" in config_text or "last_updated" in config_text, (
        "Truth templates must use report-time freshness (last_reported / "
        "last_updated)."
    )


def test_live_truth_freshness_clock_is_not_last_changed():
    """Regression guard: last_changed must not be used as the freshness clock
    for truth templates. The freshness-check shape is
    `(now() - <state>.<clock>).total_seconds() < max_age`; that clock must be
    report-time, never value-change time.

    Note: this asserts on configuration.yaml only. automations.yaml legitimately
    uses climate.*.last_changed for state-duration logic (how long a unit has
    been in a mode), which is a value-transition measurement, not freshness."""
    config_text = _read_config_text()
    assert ".last_changed).total_seconds()" not in config_text, (
        "configuration.yaml truth freshness must not use last_changed as its "
        "max_age clock; use last_reported (report-time freshness)."
    )
    # And the report-time clock must actually be the one wired into the
    # freshness comparison.
    assert ".last_reported).total_seconds()" in config_text, (
        "configuration.yaml truth freshness must compare against last_reported."
    )
