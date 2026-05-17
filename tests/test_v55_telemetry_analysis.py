"""V5.5 Telemetry Analysis Tests
================================

Coverage for ``tools/analyze_v55_telemetry.py``:

- Empty CSV / missing file are handled cleanly without crashing.
- Required Section 14 columns are detected; missing required columns gate
  the verdict to ``NOT_VALIDATED_MISSING_COLUMNS``.
- Boost cycles are detected from ``Section14_Boost_Active`` transitions.
- Cycle classifications follow the doctrine in
  ``docs/v8_4_heating_recovery_boost_plan.md`` and
  ``docs/telemetry_confounders.md``.
- A short (<14 day) clean dataset cannot produce ``VALIDATED_CANDIDATE``.
- A WAF-released cycle is contaminated and gates the verdict to
  ``NOT_VALIDATED_CONTAMINATED``.
- Report rendering succeeds for typical and degenerate inputs.
- The analyzer module never imports network or Home Assistant client code,
  and never writes anywhere except the explicitly-passed report path.
"""

from __future__ import annotations

import csv
import importlib.util
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Module loader. Avoids requiring ``tools/`` to be a package.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
_MODULE_PATH = _REPO_ROOT / "tools" / "analyze_v55_telemetry.py"


def _load_module():
    # Register before exec_module so @dataclass introspection of forward
    # references resolves through sys.modules (cpython dataclasses.py
    # requires the module to be findable by cls.__module__ at decoration
    # time).
    sys.modules.pop("analyze_v55_telemetry", None)
    spec = importlib.util.spec_from_file_location(
        "analyze_v55_telemetry", str(_MODULE_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["analyze_v55_telemetry"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def analyzer():
    return _load_module()


# ---------------------------------------------------------------------------
# CSV fixture builders.
# ---------------------------------------------------------------------------
ALL_REQUIRED_HEADERS = [
    "Timestamp",
    "Season_Mode",
    "Away_Mode",
    "LR_Temp_Truth",
    "Section14_Boost_Active",
    "Section14_Timer_State",
    "Section14_Timer_Remaining",
    "Section14_Last_Engage_Reason",
    "Section14_Last_Release_Reason",
    "Section14_Last_Engage_At",
    "Section14_Last_Release_At",
    "Section14_Engage_Eligible",
    "Section14_WAF_Active",
    "Section14_Truth_Available",
]


def _write_csv(path: Path, headers, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(headers))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _row(ts, **overrides):
    base = {h: "" for h in ALL_REQUIRED_HEADERS}
    base["Timestamp"] = ts
    base["Season_Mode"] = "heating"
    base["Away_Mode"] = "off"
    base["Section14_Engage_Eligible"] = "true"
    base["Section14_WAF_Active"] = "false"
    base["Section14_Truth_Available"] = "true"
    base["Section14_Timer_State"] = "idle"
    base["Section14_Boost_Active"] = "off"
    base.update(overrides)
    return base


def _ticks(start: datetime, count: int, step_minutes: int = 15):
    cur = start
    for _ in range(count):
        yield cur
        cur += timedelta(minutes=step_minutes)


def _build_clean_long_dataset(span_days: int = 21, cycles_per_window: int = 3):
    """Build a 14+ day dataset with clean truth_cap-released cycles.

    A "clean" cycle here looks like: one tick at LR_Truth ~63°F with boost
    on engaging, two ticks at ~65°F with boost on, one tick at ~68°F with
    boost off and Section14_Last_Release_Reason=truth_cap. Gaps between
    cycles are filled with steady idle rows.
    """
    start = datetime(2026, 4, 1, 0, 0, 0)
    rows = []
    timestamps = list(
        _ticks(start, span_days * 24 * 4)
    )  # 15-min ticks for ``span_days`` days

    cycle_anchor_indices = [50 + 4 * i * 24 * 7 // 1 for i in range(cycles_per_window)]
    cycle_anchor_indices = [
        idx for idx in [50, 600, 1200] if idx + 4 < len(timestamps)
    ][:cycles_per_window]

    cycle_starts = set(cycle_anchor_indices)
    cycle_engage_at = {}

    cycle_pattern = [
        # (offset, lr_truth, boost_active, last_engage_reason, last_release_reason)
        (0, "63.20", "on", "truth_below_64", ""),
        (1, "64.50", "on", "truth_below_64", ""),
        (2, "66.10", "on", "truth_below_64", ""),
        (3, "67.05", "off", "truth_below_64", "truth_cap"),
    ]

    for idx, ts in enumerate(timestamps):
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        cycle_offset = None
        cycle_index = None
        for ci in cycle_starts:
            if ci <= idx <= ci + 3:
                cycle_offset = idx - ci
                cycle_index = ci
                break
        if cycle_offset is not None:
            offset, lr, active, eng, rel = cycle_pattern[cycle_offset]
            timer_state = "active" if active == "on" else "idle"
            engage_at = cycle_engage_at.setdefault(
                cycle_index,
                timestamps[cycle_index].strftime("%Y-%m-%d %H:%M:%S"),
            )
            release_at = ts_str if rel else ""
            rows.append(
                _row(
                    ts_str,
                    LR_Temp_Truth=lr,
                    Section14_Boost_Active=active,
                    Section14_Timer_State=timer_state,
                    Section14_Last_Engage_Reason=eng,
                    Section14_Last_Release_Reason=rel,
                    Section14_Last_Engage_At=engage_at,
                    Section14_Last_Release_At=release_at,
                )
            )
        else:
            rows.append(_row(ts_str, LR_Temp_Truth="68.00"))
    return rows


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------
def test_module_loads(analyzer):
    """Sanity guard: the module loads without syntax errors and exposes the
    public verdict labels expected by docs and tests."""
    expected = {
        "NOT_VALIDATED_NO_DATA",
        "NOT_VALIDATED_MISSING_COLUMNS",
        "NOT_VALIDATED_CONTAMINATED",
        "NOT_VALIDATED_TOO_FEW_DAYS",
        "PARTIAL_EVIDENCE_NEEDS_REVIEW",
        "VALIDATED_CANDIDATE",
    }
    actual = {
        analyzer.VERDICT_NO_DATA,
        analyzer.VERDICT_MISSING_COLUMNS,
        analyzer.VERDICT_CONTAMINATED,
        analyzer.VERDICT_TOO_FEW_DAYS,
        analyzer.VERDICT_PARTIAL,
        analyzer.VERDICT_VALIDATED,
    }
    assert actual == expected


def test_missing_file_returns_error_exit(analyzer, tmp_path, capsys):
    missing = tmp_path / "no_such_file.csv"
    rc = analyzer.main([str(missing), "--no-write"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "error" in captured.err.lower() or "not found" in captured.err.lower()


def test_empty_csv_yields_no_data(analyzer, tmp_path):
    csv_path = tmp_path / "empty.csv"
    _write_csv(csv_path, ALL_REQUIRED_HEADERS, rows=[])
    result = analyzer.analyze(csv_path)
    assert result.verdict.label == analyzer.VERDICT_NO_DATA
    assert result.cycles == []
    assert result.loaded.rows == []


def test_columns_detected_when_present(analyzer, tmp_path):
    csv_path = tmp_path / "cols.csv"
    _write_csv(
        csv_path,
        ALL_REQUIRED_HEADERS + ["Lincoln_Temp_Diag_MSR", "Lincoln_Presence_MSR"],
        rows=[
            _row(
                "2026-04-01 00:00:00",
                LR_Temp_Truth="68.00",
                **{"Lincoln_Temp_Diag_MSR": "67.20", "Lincoln_Presence_MSR": "off"},
            )
        ],
    )
    result = analyzer.analyze(csv_path)
    for canonical in (
        "Timestamp",
        "LR_Temp_Truth",
        "Section14_Boost_Active",
        "Section14_Last_Release_Reason",
        "Lincoln_Temp_Diag_MSR",
        "Lincoln_Presence_MSR",
    ):
        assert result.normalized.get(canonical) is not None, canonical


def test_lr_truth_synonym_is_accepted(analyzer, tmp_path):
    """The LR truth column should accept the documented synonym header."""
    headers = [h if h != "LR_Temp_Truth" else "Living_Room_Temp_Truth"
               for h in ALL_REQUIRED_HEADERS]
    csv_path = tmp_path / "synonym.csv"
    row = _row("2026-04-01 00:00:00")
    row["Living_Room_Temp_Truth"] = "68.00"
    row.pop("LR_Temp_Truth", None)
    _write_csv(csv_path, headers, rows=[row])
    result = analyzer.analyze(csv_path)
    assert result.normalized["LR_Temp_Truth"] == "Living_Room_Temp_Truth"


def test_missing_section14_columns_gate_verdict(analyzer, tmp_path):
    minimal_headers = ["Timestamp", "Season_Mode", "Away_Mode", "LR_Temp_Truth"]
    csv_path = tmp_path / "missing.csv"
    _write_csv(
        csv_path,
        minimal_headers,
        rows=[
            {"Timestamp": "2026-04-01 00:00:00", "Season_Mode": "heating",
             "Away_Mode": "off", "LR_Temp_Truth": "65.00"}
        ],
    )
    result = analyzer.analyze(csv_path)
    assert result.verdict.label == analyzer.VERDICT_MISSING_COLUMNS
    assert any("Section14" in r for r in result.verdict.reasons)


def test_boost_cycle_detected_from_active_transitions(analyzer, tmp_path):
    rows = [
        _row("2026-04-01 10:00:00", LR_Temp_Truth="63.50"),
        _row("2026-04-01 10:15:00", LR_Temp_Truth="63.20",
             Section14_Boost_Active="on", Section14_Timer_State="active",
             Section14_Last_Engage_Reason="truth_below_64",
             Section14_Last_Engage_At="2026-04-01 10:14:00"),
        _row("2026-04-01 10:30:00", LR_Temp_Truth="65.40",
             Section14_Boost_Active="on", Section14_Timer_State="active",
             Section14_Last_Engage_Reason="truth_below_64",
             Section14_Last_Engage_At="2026-04-01 10:14:00"),
        _row("2026-04-01 10:45:00", LR_Temp_Truth="67.10",
             Section14_Boost_Active="off",
             Section14_Last_Engage_Reason="truth_below_64",
             Section14_Last_Release_Reason="truth_cap",
             Section14_Last_Engage_At="2026-04-01 10:14:00",
             Section14_Last_Release_At="2026-04-01 10:44:00"),
    ]
    csv_path = tmp_path / "cycle.csv"
    _write_csv(csv_path, ALL_REQUIRED_HEADERS, rows)
    result = analyzer.analyze(csv_path)
    assert len(result.cycles) == 1
    cycle = result.cycles[0]
    assert cycle.engage_reason == "truth_below_64"
    assert cycle.release_reason == "truth_cap"
    assert cycle.lr_min == pytest.approx(63.20)
    assert cycle.lr_max == pytest.approx(65.40)
    assert cycle.lr_start == pytest.approx(63.20)
    assert cycle.lr_end == pytest.approx(65.40)
    assert cycle.classification() == "clean"


def test_waf_release_cycle_is_contaminated(analyzer, tmp_path):
    rows = [
        _row("2026-04-01 10:00:00", LR_Temp_Truth="63.50"),
        _row("2026-04-01 10:15:00", LR_Temp_Truth="63.20",
             Section14_Boost_Active="on",
             Section14_Last_Engage_Reason="truth_below_64"),
        _row("2026-04-01 10:30:00", LR_Temp_Truth="63.80",
             Section14_Boost_Active="off",
             Section14_Last_Release_Reason="waf",
             Section14_WAF_Active="true"),
    ]
    csv_path = tmp_path / "waf.csv"
    _write_csv(csv_path, ALL_REQUIRED_HEADERS, rows)
    result = analyzer.analyze(csv_path)
    assert len(result.cycles) == 1
    assert result.cycles[0].classification() == "contaminated"
    assert result.verdict.label == analyzer.VERDICT_CONTAMINATED


def test_short_clean_dataset_cannot_validate(analyzer, tmp_path):
    """A clean cycle on a single day must yield NOT_VALIDATED_TOO_FEW_DAYS,
    not VALIDATED_CANDIDATE — the 14-day floor is non-negotiable."""
    rows = [
        _row("2026-04-01 10:00:00", LR_Temp_Truth="63.50"),
        _row("2026-04-01 10:15:00", LR_Temp_Truth="63.20",
             Section14_Boost_Active="on",
             Section14_Timer_State="active",
             Section14_Last_Engage_Reason="truth_below_64"),
        _row("2026-04-01 10:30:00", LR_Temp_Truth="65.40",
             Section14_Boost_Active="on",
             Section14_Timer_State="active",
             Section14_Last_Engage_Reason="truth_below_64"),
        _row("2026-04-01 10:45:00", LR_Temp_Truth="67.10",
             Section14_Boost_Active="off",
             Section14_Last_Release_Reason="truth_cap"),
    ]
    csv_path = tmp_path / "short.csv"
    _write_csv(csv_path, ALL_REQUIRED_HEADERS, rows)
    result = analyzer.analyze(csv_path)
    assert result.verdict.label == analyzer.VERDICT_TOO_FEW_DAYS


def test_long_clean_dataset_does_not_validate_at_67_band(analyzer, tmp_path):
    """A 14+ day dataset of truth_cap-released cycles must NOT auto-validate.

    Doctrine sets truth_cap = 67°F, which is below the 68–72°F comfort band
    enforced by the verdict gate. The verdict should land on
    PARTIAL_EVIDENCE_NEEDS_REVIEW so that operator review is required before
    any effectiveness claim.
    """
    rows = _build_clean_long_dataset(span_days=21, cycles_per_window=3)
    csv_path = tmp_path / "long.csv"
    _write_csv(csv_path, ALL_REQUIRED_HEADERS, rows)
    result = analyzer.analyze(csv_path)
    assert result.loaded.span_days is not None
    assert result.loaded.span_days >= 14
    assert len(result.cycles) >= 1
    assert all(c.classification() == "clean" for c in result.cycles)
    assert result.verdict.label == analyzer.VERDICT_PARTIAL


def test_truncated_cycle_at_end_is_indeterminate(analyzer, tmp_path):
    """If boost is still active in the final row, the cycle is truncated and
    must be classified indeterminate (not clean)."""
    rows = [
        _row("2026-04-01 10:00:00", LR_Temp_Truth="63.50"),
        _row("2026-04-01 10:15:00", LR_Temp_Truth="63.20",
             Section14_Boost_Active="on",
             Section14_Last_Engage_Reason="truth_below_64"),
        _row("2026-04-01 10:30:00", LR_Temp_Truth="64.10",
             Section14_Boost_Active="on",
             Section14_Last_Engage_Reason="truth_below_64"),
    ]
    csv_path = tmp_path / "trunc.csv"
    _write_csv(csv_path, ALL_REQUIRED_HEADERS, rows)
    result = analyzer.analyze(csv_path)
    assert len(result.cycles) == 1
    assert result.cycles[0].truncated_at_end is True
    assert result.cycles[0].classification() == "indeterminate"


def test_lincoln_msr_summary_is_observation_only(analyzer, tmp_path):
    """When MSR columns are present, the summary reports min/max and
    blank-row counts, but the report text must not contain control or
    promotion language."""
    extended = ALL_REQUIRED_HEADERS + [
        "Lincoln_Temp_Diag_MSR",
        "Lincoln_Pressure_Diag_MSR",
        "Lincoln_ESPTemp_Diag_MSR",
        "Lincoln_Presence_MSR",
    ]
    rows = []
    for i in range(5):
        ts = (datetime(2026, 4, 1, 0, 0, 0) + timedelta(minutes=15 * i)
              ).strftime("%Y-%m-%d %H:%M:%S")
        row = _row(ts, LR_Temp_Truth="68.00")
        row["Lincoln_Temp_Diag_MSR"] = f"{67.0 + i * 0.1:.2f}"
        row["Lincoln_Pressure_Diag_MSR"] = "1013.20"
        row["Lincoln_ESPTemp_Diag_MSR"] = "32.5"
        row["Lincoln_Presence_MSR"] = "off" if i % 2 == 0 else "on"
        rows.append(row)
    csv_path = tmp_path / "lincoln.csv"
    _write_csv(csv_path, extended, rows)
    result = analyzer.analyze(csv_path)
    summary = result.lincoln_summary
    assert summary["Lincoln_Temp_Diag_MSR"]["present"] is True
    assert summary["Lincoln_Temp_Diag_MSR"]["min"] == pytest.approx(67.0)
    assert summary["Lincoln_Temp_Diag_MSR"]["max"] == pytest.approx(67.4)
    assert summary["Lincoln_Presence_MSR"]["on_count"] == 2
    assert summary["Lincoln_Presence_MSR"]["off_count"] == 3
    assert "observability-only" in result.report_text.lower()


def test_report_writes_file_and_creates_directory(analyzer, tmp_path):
    csv_path = tmp_path / "in.csv"
    _write_csv(
        csv_path,
        ALL_REQUIRED_HEADERS,
        rows=[_row("2026-04-01 00:00:00", LR_Temp_Truth="68.00")],
    )
    out_path = tmp_path / "nested" / "subdir" / "report.md"
    rc = analyzer.main([str(csv_path), "--output", str(out_path)])
    assert rc == 0
    assert out_path.exists()
    text = out_path.read_text(encoding="utf-8")
    assert "# V5.5 Telemetry Evidence Review" in text
    assert "## V8.4 Boost Effectiveness Verdict" in text
    assert "## Section 14 Boost Cycles" in text


def test_no_write_mode_does_not_create_default_report(analyzer, tmp_path, capsys, monkeypatch):
    """``--no-write`` must not touch the filesystem outside reading the input."""
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "in.csv"
    _write_csv(
        csv_path,
        ALL_REQUIRED_HEADERS,
        rows=[_row("2026-04-01 00:00:00", LR_Temp_Truth="68.00")],
    )
    rc = analyzer.main([str(csv_path), "--no-write"])
    assert rc == 0
    assert not (tmp_path / "reports").exists()
    captured = capsys.readouterr()
    assert "# V5.5 Telemetry Evidence Review" in captured.out


def test_module_imports_no_network_clients():
    """The analyzer must not silently pull in HA clients, Google API SDKs,
    requests, urllib3, or any other network library at import time."""
    sys.modules.pop("analyze_v55_telemetry", None)
    _load_module()
    forbidden_prefixes = (
        "requests",
        "urllib3",
        "httpx",
        "aiohttp",
        "google.api_core",
        "googleapiclient",
        "google.auth",
        "homeassistant",
        "hass_client",
        "gspread",
    )
    leaked = sorted(
        m for m in sys.modules
        if any(m == p or m.startswith(p + ".") for p in forbidden_prefixes)
    )
    assert leaked == [], (
        "analyze_v55_telemetry pulled in forbidden network/HA modules: "
        f"{leaked}. The script must remain stdlib-only."
    )
