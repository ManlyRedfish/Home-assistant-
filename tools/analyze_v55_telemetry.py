#!/usr/bin/env python3
"""Read-only analysis of an exported VTherm_Launch_Data_v5_5 CSV.

Hard contract enforced by this script:

- Reads only the local CSV path passed on the command line.
- Never connects to Home Assistant, ESPHome, or any device.
- Never connects to Google Sheets and never writes back to any sheet.
- Requires no secrets, credentials, or network access.
- Writes only the local markdown report file (default
  ``reports/v55_telemetry_evidence_review.md``) and stdout.
- Does not declare V8.4 boost effective unless strict criteria are met.
- Default verdict bias is conservative: prefer ``NOT_VALIDATED_*`` /
  ``PARTIAL_EVIDENCE_NEEDS_REVIEW`` over optimistic claims.

Usage:

    python tools/analyze_v55_telemetry.py path/to/Home_Assistant_5_5.csv

Doctrine references:

- docs/v55_sheet_evidence_review.md (operator doc; companion to this script)
- docs/v8_4_heating_recovery_boost_plan.md (Section 14 thresholds)
- docs/analysis/v8_4_lr_boost_v5_evidence_review.md (prior evidence review)
- docs/telemetry_confounders.md (operator-suppressed-window classifier)
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Optional, Sequence


# ---------------------------------------------------------------------------
# Doctrine constants. These mirror the live thresholds, not analyzer policy:
# changes here are documentation drift, not control changes.
# ---------------------------------------------------------------------------
COMFORT_LOW_F = 68.0
COMFORT_HIGH_F = 72.0
LR_RUNAWAY_FLOOR_F = 60.0          # Section 3 LR runaway cooling cutoff
LR_CEILING_F = 76.0                # Section 3 all-season ceiling
TRUTH_CAP_F = 67.0                 # Section 14 truth cap
COLD_ENGAGE_F = 64.0               # Section 14 cold engage threshold
MIN_VALIDATION_DAYS = 14


# Verdict labels - these strings are part of the public contract; tests and
# the report rely on them. Do not rename.
VERDICT_NO_DATA = "NOT_VALIDATED_NO_DATA"
VERDICT_MISSING_COLUMNS = "NOT_VALIDATED_MISSING_COLUMNS"
VERDICT_CONTAMINATED = "NOT_VALIDATED_CONTAMINATED"
VERDICT_TOO_FEW_DAYS = "NOT_VALIDATED_TOO_FEW_DAYS"
VERDICT_PARTIAL = "PARTIAL_EVIDENCE_NEEDS_REVIEW"
VERDICT_VALIDATED = "VALIDATED_CANDIDATE"


# Required columns gate. Missing any of these forces NOT_VALIDATED_MISSING_COLUMNS.
REQUIRED_SECTION14_COLS = (
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
)

EXPECTED_LR_TRUTH_COLS = (
    "LR_Temp_Truth",
    "Living_Room_Temp_Truth",
    "Living_Room_Temperature_Truth",
)

EXPECTED_MSR_OBSERVABILITY_COLS = (
    "LR_CO2_Diag_MSR",
    "Lincoln_Temp_Diag_MSR",
    "Lincoln_Pressure_Diag_MSR",
    "Lincoln_ESPTemp_Diag_MSR",
    "LR_Presence_MSR",
    "Lincoln_Presence_MSR",
)


# Synonym map: canonical name -> tuple of acceptable header strings.
# Tolerant lookup so minor header drift between exports does not crash the run.
CANONICAL_SYNONYMS = {
    "Timestamp": ("Timestamp", "timestamp", "Time", "time", "Datetime", "DateTime", "Date_Time"),
    "Season_Mode": ("Season_Mode",),
    "Away_Mode": ("Away_Mode",),
    "LR_Temp_Truth": (
        "LR_Temp_Truth",
        "Living_Room_Temp_Truth",
        "Living_Room_Temperature_Truth",
        "LR_Temperature_Truth",
    ),
    "LR_Air_Setpoint": ("LR_Air_Setpoint",),
    "LR_Air_Mode": ("LR_Air_Mode",),
    "LR_Air_Action": ("LR_Air_Action",),
    "LR_HP_Runtime_Today_Hrs": ("LR_HP_Runtime_Today_Hrs",),
    "Section14_Boost_Active": ("Section14_Boost_Active",),
    "Section14_Timer_State": ("Section14_Timer_State",),
    "Section14_Timer_Remaining": ("Section14_Timer_Remaining",),
    "Section14_Last_Engage_Reason": ("Section14_Last_Engage_Reason",),
    "Section14_Last_Release_Reason": ("Section14_Last_Release_Reason",),
    "Section14_Last_Engage_At": ("Section14_Last_Engage_At",),
    "Section14_Last_Release_At": ("Section14_Last_Release_At",),
    "Section14_Engage_Eligible": ("Section14_Engage_Eligible",),
    "Section14_WAF_Active": ("Section14_WAF_Active",),
    "Section14_Truth_Available": ("Section14_Truth_Available",),
    "LR_CO2_Diag_MSR": ("LR_CO2_Diag_MSR",),
    "Lincoln_Temp_Diag_MSR": ("Lincoln_Temp_Diag_MSR",),
    "Lincoln_Pressure_Diag_MSR": ("Lincoln_Pressure_Diag_MSR",),
    "Lincoln_ESPTemp_Diag_MSR": ("Lincoln_ESPTemp_Diag_MSR",),
    "LR_Presence_MSR": ("LR_Presence_MSR",),
    "Lincoln_Presence_MSR": ("Lincoln_Presence_MSR",),
}


# ---------------------------------------------------------------------------
# Parsers and column normalization.
# ---------------------------------------------------------------------------
def normalize_columns(header: Sequence[str]) -> dict:
    """Return ``{canonical_name: actual_header_name_or_None}``."""
    actual = {h.strip(): h for h in header if isinstance(h, str)}
    out = {}
    for canonical, candidates in CANONICAL_SYNONYMS.items():
        out[canonical] = next((actual[c] for c in candidates if c in actual), None)
    return out


_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
)


def parse_timestamp(value: object) -> Optional[datetime]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    for fmt in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def parse_float(value: object) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_bool(value: object) -> Optional[bool]:
    if value is None:
        return None
    s = str(value).strip().lower()
    if not s:
        return None
    if s in ("on", "true", "yes", "1", "active"):
        return True
    if s in ("off", "false", "no", "0", "idle"):
        return False
    return None


# ---------------------------------------------------------------------------
# Boost cycle model.
# ---------------------------------------------------------------------------
@dataclass
class BoostCycle:
    start_ts: Optional[datetime] = None
    end_ts: Optional[datetime] = None
    start_row: int = -1
    end_row: int = -1
    engage_reason: str = ""
    release_reason: str = ""
    timer_state_at_release: str = ""
    timer_remaining_at_engage_seconds: Optional[int] = None
    waf_active_during: bool = False
    truth_unavailable_during: bool = False
    lr_min: Optional[float] = None
    lr_max: Optional[float] = None
    lr_start: Optional[float] = None
    lr_end: Optional[float] = None
    truncated_at_start: bool = False
    truncated_at_end: bool = False

    @property
    def duration(self) -> Optional[timedelta]:
        if self.start_ts and self.end_ts:
            return self.end_ts - self.start_ts
        return None

    @property
    def timer_expired(self) -> bool:
        return self.release_reason == "timeout"

    def in_comfort_band_at_release(self) -> Optional[bool]:
        if self.lr_end is None:
            return None
        return COMFORT_LOW_F <= self.lr_end <= COMFORT_HIGH_F

    def in_comfort_band_throughout(self) -> Optional[bool]:
        if self.lr_min is None or self.lr_max is None:
            return None
        return self.lr_min >= COMFORT_LOW_F and self.lr_max <= COMFORT_HIGH_F

    def classification(self) -> str:
        if self.release_reason in ("waf", "truth_unavailable"):
            return "contaminated"
        if self.waf_active_during or self.truth_unavailable_during:
            return "contaminated"
        if self.lr_min is not None and self.lr_min < LR_RUNAWAY_FLOOR_F:
            return "contaminated"
        if self.lr_max is not None and self.lr_max > LR_CEILING_F:
            return "contaminated"
        if self.truncated_at_start or self.truncated_at_end:
            return "indeterminate"
        if self.start_ts is None or self.end_ts is None:
            return "indeterminate"
        if self.release_reason == "truth_cap":
            return "clean"
        # timeout, season_change, unknown_release_reason, blank, unmapped
        return "indeterminate"


def detect_boost_cycles(rows: Sequence[dict], normalized: dict) -> List[BoostCycle]:
    boost_col = normalized.get("Section14_Boost_Active")
    if boost_col is None:
        return []
    ts_col = normalized.get("Timestamp")
    lr_col = normalized.get("LR_Temp_Truth")
    waf_col = normalized.get("Section14_WAF_Active")
    truth_avail_col = normalized.get("Section14_Truth_Available")
    timer_state_col = normalized.get("Section14_Timer_State")
    timer_rem_col = normalized.get("Section14_Timer_Remaining")
    engage_reason_col = normalized.get("Section14_Last_Engage_Reason")
    release_reason_col = normalized.get("Section14_Last_Release_Reason")

    cycles: List[BoostCycle] = []
    current: Optional[BoostCycle] = None
    seen_off_first = False

    for idx, row in enumerate(rows):
        active = parse_bool(row.get(boost_col, "")) if boost_col else None
        ts = parse_timestamp(row.get(ts_col, "")) if ts_col else None
        lr = parse_float(row.get(lr_col, "")) if lr_col else None

        if active is True:
            if current is None:
                current = BoostCycle(
                    start_ts=ts,
                    start_row=idx,
                    end_row=idx,
                    truncated_at_start=(not seen_off_first),
                )
                if engage_reason_col:
                    current.engage_reason = (row.get(engage_reason_col, "") or "").strip()
                if timer_rem_col:
                    rem = parse_float(row.get(timer_rem_col, ""))
                    current.timer_remaining_at_engage_seconds = (
                        int(rem) if rem is not None else None
                    )
            if lr is not None:
                if current.lr_start is None:
                    current.lr_start = lr
                current.lr_end = lr
                current.lr_min = lr if current.lr_min is None else min(current.lr_min, lr)
                current.lr_max = lr if current.lr_max is None else max(current.lr_max, lr)
            if waf_col and parse_bool(row.get(waf_col, "")) is True:
                current.waf_active_during = True
            if truth_avail_col and parse_bool(row.get(truth_avail_col, "")) is False:
                current.truth_unavailable_during = True
            current.end_row = idx
        elif active is False:
            seen_off_first = True
            if current is not None:
                current.end_ts = ts
                current.end_row = idx
                if release_reason_col:
                    current.release_reason = (row.get(release_reason_col, "") or "").strip()
                if timer_state_col:
                    current.timer_state_at_release = (
                        row.get(timer_state_col, "") or ""
                    ).strip()
                cycles.append(current)
                current = None

    if current is not None:
        current.truncated_at_end = True
        cycles.append(current)

    return cycles


# ---------------------------------------------------------------------------
# Lincoln MSR observability summary (read-only — no control implications).
# ---------------------------------------------------------------------------
def lincoln_msr_summary(rows: Sequence[dict], normalized: dict) -> dict:
    out: dict = {}

    presence_col = normalized.get("Lincoln_Presence_MSR")
    if presence_col is not None:
        non_blank = [(row.get(presence_col, "") or "").strip() for row in rows]
        non_blank = [v for v in non_blank if v != ""]
        on_count = sum(1 for v in non_blank if v.lower() in ("on", "true", "1"))
        off_count = sum(1 for v in non_blank if v.lower() in ("off", "false", "0"))
        out["Lincoln_Presence_MSR"] = {
            "present": True,
            "rows_total": len(rows),
            "rows_blank": len(rows) - len(non_blank),
            "on_count": on_count,
            "off_count": off_count,
            "other_count": len(non_blank) - on_count - off_count,
        }
    else:
        out["Lincoln_Presence_MSR"] = {"present": False}

    for canonical in (
        "Lincoln_Temp_Diag_MSR",
        "Lincoln_Pressure_Diag_MSR",
        "Lincoln_ESPTemp_Diag_MSR",
    ):
        col = normalized.get(canonical)
        if col is None:
            out[canonical] = {"present": False}
            continue
        nums = [parse_float(row.get(col, "")) for row in rows]
        nums_clean = [n for n in nums if n is not None]
        out[canonical] = {
            "present": True,
            "rows_total": len(rows),
            "rows_blank": len(rows) - len(nums_clean),
            "min": min(nums_clean) if nums_clean else None,
            "max": max(nums_clean) if nums_clean else None,
        }
    return out


# ---------------------------------------------------------------------------
# Verdict gate.
# ---------------------------------------------------------------------------
@dataclass
class Verdict:
    label: str
    reasons: List[str] = field(default_factory=list)


def assess_verdict(
    rows: Sequence[dict],
    normalized: dict,
    cycles: Sequence[BoostCycle],
    span_days: Optional[float],
    timestamp_gaps_count: int = 0,
) -> Verdict:
    if not rows:
        return Verdict(VERDICT_NO_DATA, ["No data rows present in CSV."])
    missing_required = [c for c in REQUIRED_SECTION14_COLS if normalized.get(c) is None]
    if missing_required:
        return Verdict(
            VERDICT_MISSING_COLUMNS,
            [f"Missing required Section 14 columns: {sorted(missing_required)}"],
        )

    classifications = [c.classification() for c in cycles]
    contaminated = "contaminated" in classifications
    has_indeterminate = "indeterminate" in classifications

    reasons: List[str] = []

    if contaminated:
        reasons.append(
            "At least one boost cycle is contaminated "
            "(WAF, truth_unavailable, runaway floor breach, or ceiling breach)."
        )
        return Verdict(VERDICT_CONTAMINATED, reasons)

    if span_days is None or span_days < MIN_VALIDATION_DAYS:
        span_text = "unknown" if span_days is None else f"{span_days:.2f}"
        reasons.append(
            f"Telemetry span is {span_text} day(s); "
            f"requires ≥ {MIN_VALIDATION_DAYS} contiguous days."
        )
        return Verdict(VERDICT_TOO_FEW_DAYS, reasons)

    if timestamp_gaps_count > 0:
        reasons.append(
            f"Telemetry span is {span_days:.2f} day(s) but has "
            f"{timestamp_gaps_count} gap(s) > 30 min; contiguity broken. "
            f"Requires ≥ {MIN_VALIDATION_DAYS} contiguous days without "
            f"missing capture windows."
        )
        return Verdict(VERDICT_TOO_FEW_DAYS, reasons)

    if not cycles:
        reasons.append("No Section 14 boost cycles detected in this dataset.")
        return Verdict(VERDICT_PARTIAL, reasons)

    if has_indeterminate:
        reasons.append(
            "At least one cycle is indeterminate "
            "(truncated capture, timeout, season_change, or unmapped release reason)."
        )
        return Verdict(VERDICT_PARTIAL, reasons)

    band_results = [c.in_comfort_band_throughout() for c in cycles]
    if not all(b is True for b in band_results):
        reasons.append(
            "At least one cycle did not stay within the 68–72°F comfort band "
            "throughout the boost window. With truth_cap = 67°F by doctrine, "
            "this criterion is currently expected to fail; treat as needs review."
        )
        return Verdict(VERDICT_PARTIAL, reasons)

    reasons.append(
        f"All cycles classified clean, span ≥ {MIN_VALIDATION_DAYS} days, "
        "and 68–72°F comfort band held throughout each boost window."
    )
    return Verdict(VERDICT_VALIDATED, reasons)


# ---------------------------------------------------------------------------
# CSV loader.
# ---------------------------------------------------------------------------
@dataclass
class LoadedCsv:
    header: List[str]
    rows: List[dict]
    timestamps: List[Optional[datetime]]
    span_days: Optional[float]
    timestamp_gaps_count: int


def load_csv(path: Path) -> LoadedCsv:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = list(reader.fieldnames or [])
        rows = [dict(r) for r in reader]

    ts_actual = next(
        (h for h in header if h.strip() in CANONICAL_SYNONYMS["Timestamp"]),
        None,
    )
    timestamps: List[Optional[datetime]] = []
    if ts_actual is not None:
        timestamps = [parse_timestamp(r.get(ts_actual, "")) for r in rows]
    parsed = [t for t in timestamps if t is not None]
    span_days: Optional[float] = None
    if len(parsed) >= 2:
        span_days = (max(parsed) - min(parsed)).total_seconds() / 86400.0

    gaps = 0
    if len(parsed) >= 2:
        sorted_ts = sorted(parsed)
        for prev, nxt in zip(sorted_ts, sorted_ts[1:]):
            if (nxt - prev) > timedelta(minutes=30):
                gaps += 1

    return LoadedCsv(
        header=header,
        rows=rows,
        timestamps=timestamps,
        span_days=span_days,
        timestamp_gaps_count=gaps,
    )


# ---------------------------------------------------------------------------
# Report rendering.
# ---------------------------------------------------------------------------
def _fmt_ts(dt: Optional[datetime]) -> str:
    return dt.isoformat(sep=" ") if dt else ""


def _fmt_float(v: Optional[float], digits: int = 2) -> str:
    return f"{v:.{digits}f}" if v is not None else ""


def _fmt_bool(v: Optional[bool]) -> str:
    if v is None:
        return ""
    return "yes" if v else "no"


def _fmt_duration(d: Optional[timedelta]) -> str:
    if d is None:
        return ""
    total_seconds = int(d.total_seconds())
    if total_seconds < 0:
        return f"-{abs(total_seconds)}s"
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}h{minutes:02d}m{seconds:02d}s"
    if minutes:
        return f"{minutes}m{seconds:02d}s"
    return f"{seconds}s"


def render_report(
    input_path: Path,
    loaded: LoadedCsv,
    normalized: dict,
    cycles: Sequence[BoostCycle],
    verdict: Verdict,
    lincoln: dict,
) -> str:
    lines: List[str] = []
    lines.append("# V5.5 Telemetry Evidence Review")
    lines.append("")
    lines.append(
        "_Generated by `tools/analyze_v55_telemetry.py`. Read-only analysis "
        "of an exported CSV. No Home Assistant runtime behavior is changed by "
        "running this script._"
    )
    lines.append("")

    lines.append("## Scope Boundary")
    lines.append("")
    lines.append(
        "- Source: a local CSV export of the Google Sheet `Home Assistant` → "
        "tab `5.5` (`VTherm_Launch_Data_v5_5`)."
    )
    lines.append("- This script only **reads** the CSV. It does not connect to "
                 "Home Assistant, ESPHome, Google Sheets, or any device.")
    lines.append("- It does not write back to Google Sheets and requires no "
                 "credentials.")
    lines.append("- It cannot change automations, helpers, thermostat behavior, "
                 "Section 2 / Section 3 / Section 14 logic, or safety gates.")
    lines.append("- This report supersedes nothing. It is forensic evidence; "
                 "doctrine still lives in `docs/`.")
    lines.append("")

    lines.append("## Input File")
    lines.append("")
    lines.append(f"- Path: `{input_path}`")
    lines.append(f"- Header column count: {len(loaded.header)}")
    lines.append(f"- Data row count: {len(loaded.rows)}")
    parsed_ts = [t for t in loaded.timestamps if t is not None]
    if parsed_ts:
        lines.append(f"- First timestamp: {_fmt_ts(min(parsed_ts))}")
        lines.append(f"- Last timestamp:  {_fmt_ts(max(parsed_ts))}")
        if loaded.span_days is not None:
            lines.append(f"- Span: {loaded.span_days:.2f} day(s)")
    else:
        lines.append("- Timestamps could not be parsed from this export.")
    lines.append("")

    lines.append("## Column Coverage")
    lines.append("")
    found = [k for k, v in normalized.items() if v is not None]
    missing = [k for k, v in normalized.items() if v is None]
    lines.append(f"- Found canonical columns ({len(found)}): "
                 + (", ".join(f"`{c}`" for c in found) or "_none_"))
    lines.append(f"- Missing canonical columns ({len(missing)}): "
                 + (", ".join(f"`{c}`" for c in missing) or "_none_"))
    missing_required = [c for c in REQUIRED_SECTION14_COLS if normalized.get(c) is None]
    if missing_required:
        lines.append("")
        lines.append("**Required Section 14 columns missing — verdict gated.**")
        for c in missing_required:
            lines.append(f"  - `{c}`")
    lines.append("")

    lines.append("## Section 14 Boost Cycles")
    lines.append("")
    if not cycles:
        lines.append("_No boost cycles detected in this dataset._")
    else:
        lines.append(
            "| # | Start | End | Duration | Engage reason | Release reason | "
            "Timer expired | WAF active | Truth unavailable | "
            "LR start °F | LR end °F | LR min °F | LR max °F | "
            "Comfort band (release / throughout) | Classification |"
        )
        lines.append(
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"
        )
        for idx, c in enumerate(cycles, 1):
            lines.append(
                "| {n} | {s} | {e} | {dur} | {er} | {rr} | {to} | {waf} | {tu} | "
                "{lrs} | {lre} | {lrmn} | {lrmx} | {bandr} / {bandt} | {cls} |"
                .format(
                    n=idx,
                    s=_fmt_ts(c.start_ts),
                    e=_fmt_ts(c.end_ts),
                    dur=_fmt_duration(c.duration),
                    er=c.engage_reason or "_blank_",
                    rr=c.release_reason or "_blank_",
                    to=_fmt_bool(c.timer_expired),
                    waf=_fmt_bool(c.waf_active_during),
                    tu=_fmt_bool(c.truth_unavailable_during),
                    lrs=_fmt_float(c.lr_start),
                    lre=_fmt_float(c.lr_end),
                    lrmn=_fmt_float(c.lr_min),
                    lrmx=_fmt_float(c.lr_max),
                    bandr=_fmt_bool(c.in_comfort_band_at_release()),
                    bandt=_fmt_bool(c.in_comfort_band_throughout()),
                    cls=c.classification(),
                )
            )
    lines.append("")

    lines.append("## V8.4 Boost Effectiveness Verdict")
    lines.append("")
    lines.append(f"- **Verdict:** `{verdict.label}`")
    for reason in verdict.reasons:
        lines.append(f"  - {reason}")
    lines.append("")
    lines.append(
        "Verdict labels are: `NOT_VALIDATED_NO_DATA`, "
        "`NOT_VALIDATED_MISSING_COLUMNS`, `NOT_VALIDATED_CONTAMINATED`, "
        "`NOT_VALIDATED_TOO_FEW_DAYS`, `PARTIAL_EVIDENCE_NEEDS_REVIEW`, "
        "`VALIDATED_CANDIDATE`."
    )
    lines.append("")

    lines.append("## Lincoln MSR Fan-Only Exception Observability")
    lines.append("")
    lines.append(
        "Apollo / MSR data remains observability-only by doctrine. The Lincoln "
        "fan-only destratification path is the single documented exception "
        "(setpoint-neutral, `fan_only` / `off` only). The data below is a "
        "row-summary of the MSR-derived columns; no control claim is made."
    )
    lines.append("")
    presence = lincoln.get("Lincoln_Presence_MSR", {"present": False})
    if presence.get("present"):
        lines.append(
            f"- `Lincoln_Presence_MSR` distribution: "
            f"on={presence['on_count']}, off={presence['off_count']}, "
            f"other={presence['other_count']}, "
            f"blank/unavailable={presence['rows_blank']} "
            f"(of {presence['rows_total']} rows)."
        )
    else:
        lines.append("- `Lincoln_Presence_MSR` column not present in export.")
    for canonical, label in (
        ("Lincoln_Temp_Diag_MSR", "Lincoln MSR DPS310 temperature"),
        ("Lincoln_Pressure_Diag_MSR", "Lincoln MSR DPS310 pressure"),
        ("Lincoln_ESPTemp_Diag_MSR", "Lincoln MSR ESP32 internal temperature"),
    ):
        info = lincoln.get(canonical, {"present": False})
        if info.get("present"):
            lines.append(
                f"- `{canonical}` ({label}): min={_fmt_float(info['min'])}, "
                f"max={_fmt_float(info['max'])}, "
                f"blank/unavailable={info['rows_blank']} of {info['rows_total']} rows."
            )
        else:
            lines.append(f"- `{canonical}` ({label}): column not present in export.")
    lines.append("")
    lines.append(
        "_This summary is read-only. It does not propose extending the Lincoln "
        "exception, promoting any MSR signal into VTherm truth, or feeding any "
        "control surface. See `docs/apollo_msr_observability_checklist.md`._"
    )
    lines.append("")

    lines.append("## Data Quality Notes")
    lines.append("")
    lines.append(f"- Timestamp gaps (> 30 min): {loaded.timestamp_gaps_count}")
    if loaded.timestamps and not all(t is not None for t in loaded.timestamps):
        unparseable = sum(1 for t in loaded.timestamps if t is None)
        lines.append(f"- Unparseable timestamp rows: {unparseable}")
    if missing_required:
        lines.append(f"- Required Section 14 columns missing: {sorted(missing_required)}")
    lr_col = normalized.get("LR_Temp_Truth")
    if lr_col is None:
        lines.append("- `LR_Temp_Truth` (or synonym) not present.")
    else:
        lr_blank = sum(
            1 for r in loaded.rows
            if not str(r.get(lr_col, "") or "").strip()
        )
        lines.append(
            f"- `LR_Temp_Truth` blank/unavailable rows: {lr_blank} of {len(loaded.rows)}"
        )
    lines.append("")

    lines.append("## Follow-up Needed")
    lines.append("")
    lines.append(
        "Before issue #49 can close or any V8.4 effectiveness claim can be "
        "made, the following evidence is required and is **not** supplied "
        "by this report on its own:"
    )
    lines.append("")
    lines.append(
        "- ≥ 14 contiguous days of clean V5.5 telemetry without "
        "`supervisor_disabled`, `manual_setpoint_nudge`, or "
        "`truth_unavailable` annotations overlapping any candidate cycle."
    )
    lines.append(
        "- ≥ 3 boost cycles released by `truth_cap` (not `timeout`, `waf`, "
        "`season_change`, or `truth_unavailable`)."
    )
    lines.append(
        "- A pair-matched baseline window (matched time-of-day, starting "
        "LR_Truth, Season_Mode, Away_Mode) for each candidate cycle."
    )
    lines.append(
        "- Confirmation from `supervisor_state_log` and `hvac_provenance_log` "
        "that no operator override or non-automation provenance overlaps any "
        "candidate cycle."
    )
    lines.append(
        "- For the Lincoln fan-only exception observability section: this "
        "remains read-only. Extending the exception requires a separate "
        "doctrine update and a matching test allow-list change "
        "(`tests/test_msr_observability_boundary.py`)."
    )
    lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Top-level analysis runner.
# ---------------------------------------------------------------------------
@dataclass
class AnalysisResult:
    loaded: LoadedCsv
    normalized: dict
    cycles: List[BoostCycle]
    verdict: Verdict
    lincoln_summary: dict
    report_text: str


def analyze(input_path: Path) -> AnalysisResult:
    loaded = load_csv(input_path)
    normalized = normalize_columns(loaded.header)
    cycles = detect_boost_cycles(loaded.rows, normalized)
    verdict = assess_verdict(
        loaded.rows,
        normalized,
        cycles,
        loaded.span_days,
        loaded.timestamp_gaps_count,
    )
    lincoln = lincoln_msr_summary(loaded.rows, normalized)
    report = render_report(input_path, loaded, normalized, cycles, verdict, lincoln)
    return AnalysisResult(
        loaded=loaded,
        normalized=normalized,
        cycles=cycles,
        verdict=verdict,
        lincoln_summary=lincoln,
        report_text=report,
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only forensic analysis of an exported VTherm_Launch_Data_v5_5 "
            "CSV. No network access; no Home Assistant or Google Sheets writes."
        )
    )
    parser.add_argument(
        "csv_path",
        type=Path,
        help="Path to the local CSV export of Google Sheet tab `5.5`.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("reports/v55_telemetry_evidence_review.md"),
        help="Markdown report output path "
             "(default: reports/v55_telemetry_evidence_review.md)",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Print the report to stdout only; do not write the markdown file.",
    )
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        result = analyze(args.csv_path)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.no_write:
        sys.stdout.write(result.report_text)
    else:
        out_path: Path = args.output
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result.report_text, encoding="utf-8")
        print(f"wrote {out_path}")
        print(f"verdict: {result.verdict.label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
