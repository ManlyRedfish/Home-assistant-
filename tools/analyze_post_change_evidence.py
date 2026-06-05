#!/usr/bin/env python3
"""Read-only Moose House V5.5 telemetry analyzer.

Operator intent is classified only from direct evidence: Supervisor_Enabled,
Manual_Override_State, legacy Section14_WAF_Active fallback, or an overlapping
supervisor_state_log annotation. Temperatures, setpoints, modes, actions, and
runtime patterns are observations only and never prove operator intent.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Sequence

COOL_SHOVE_F = 61.0
HEAT_SHOVE_F = 79.0
BOOST_SETPOINT_F = 77.0
MIN_OBSERVATION_DAYS = 14
TS_GAP_MINUTES = 30
POSTURE_NO_DATA = "NO_DATA"
POSTURE_MISSING_COLUMNS = "MISSING_CORE_COLUMNS"
POSTURE_CONTAMINATED = "CONTAMINATED_WINDOW"
POSTURE_CONTEXT_INCOMPLETE = "CONTEXT_INCOMPLETE"
POSTURE_INSUFFICIENT_WINDOW = "INSUFFICIENT_WINDOW"
POSTURE_CLEAN_CANDIDATE = "CLEAN_OBSERVATION_CANDIDATE"

TIMESTAMP_NAMES = ("Timestamp", "timestamp", "Time", "time", "Datetime", "DateTime", "Date_Time")
TIMESTAMP_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M")
CONTAMINATING_KINDS = {"supervisor_disabled", "manual_setpoint_nudge", "waf_observed", "away_window", "truth_unavailable", "stale_setpoint_artifact", "hardware_maintenance", "sensor_relocation", "comfort_complaint"}

TRUTH = {
    "Living Room": (3, "LR_Temp_Truth", "LR_Truth_Count", ("LR_Temp_RoomProbe_BT_Primary", "LR_Temp_RoomProbe_ST", "LR_Temp_HVAC_Samsung")),
    "Master": (4, "Master_Temp_Truth", None, ("Master_Temp_RoomProbe_BT", "Master_Temp_RoomProbe_ST", "Master_Temp_RoomProbe_Matter", "Master_Temp_HVAC_Samsung")),
    "Lincoln": (4, "Lincoln_Temp_Truth", "Lincoln_Truth_Count", ("Lincoln_Temp_RoomProbe_BT", "Lincoln_Temp_RoomProbe_ST", "Lincoln_Temp_RoomProbe_Matter", "Lincoln_Temp_HVAC_Samsung")),
    "Lilly": (4, "Lilly_Temp_Truth", None, ("Lilly_Temp_RoomProbe_BT", "Lilly_Temp_RoomProbe_ST", "Lilly_Temp_RoomProbe_Matter", "Lilly_Temp_HVAC_Samsung")),
}
HVAC = {
    "Living Room": ("LR_Air_Mode", "LR_Air_Action", "LR_Air_Setpoint"),
    "Master": ("Master_Air_Mode", "Master_Air_Action", "Master_Air_Setpoint"),
    "Lincoln": ("Lincoln_Air_Mode", "Lincoln_Air_Action", "Lincoln_Air_Setpoint"),
    "Lilly": ("Lilly_Air_Mode", "Lilly_Air_Action", "Lilly_Air_Setpoint"),
}
REQUIRED = ("Timestamp", "LR_Temp_Truth", "Master_Temp_Truth", "Lincoln_Temp_Truth", "Lilly_Temp_Truth", "LR_Air_Setpoint", "Master_Air_Setpoint", "Lincoln_Air_Setpoint", "Lilly_Air_Setpoint")


@dataclass
class Loaded:
    header: List[str]
    rows: List[dict]
    timestamps: List[Optional[datetime]]
    span_days: Optional[float]
    gaps: int


@dataclass
class Annotation:
    start: datetime
    end: Optional[datetime]
    kind: str
    note: str


@dataclass
class Context:
    supervisor_disabled_rows: int = 0
    manual_override_rows: int = 0
    legacy_waf_rows: int = 0
    annotation_rows: int = 0
    annotation_kinds: Counter = field(default_factory=Counter)
    contaminated: set[int] = field(default_factory=set)
    supervisor_present: bool = False
    override_present: bool = False
    legacy_waf_present: bool = False
    annotation_file_present: bool = False

    @property
    def direct_context_present(self) -> bool:
        return self.supervisor_present or self.override_present or self.annotation_file_present


def parse_timestamp(value: object) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def parse_float(value: object) -> Optional[float]:
    try:
        text = str(value or "").strip()
        return None if not text else float(text)
    except ValueError:
        return None


def parse_bool(value: object) -> Optional[bool]:
    text = str(value or "").strip().lower()
    if text in {"on", "true", "yes", "1", "active"}:
        return True
    if text in {"off", "false", "no", "0", "idle"}:
        return False
    return None


def load_csv(path: Path) -> Loaded:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        header, rows = list(reader.fieldnames or []), [dict(row) for row in reader]
    ts_col = next((h for h in header if h.strip() in TIMESTAMP_NAMES), None)
    timestamps = [parse_timestamp(row.get(ts_col, "")) for row in rows] if ts_col else [None] * len(rows)
    parsed = sorted(ts for ts in timestamps if ts is not None)
    span = (parsed[-1] - parsed[0]).total_seconds() / 86400 if len(parsed) >= 2 else None
    gaps = sum(1 for left, right in zip(parsed, parsed[1:]) if right - left > timedelta(minutes=TS_GAP_MINUTES))
    return Loaded(header, rows, timestamps, span, gaps)


def load_annotations(path: Optional[Path]) -> List[Annotation]:
    if path is None:
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"start_local", "end_local", "kind", "note"}
        fields = set(reader.fieldnames or [])
        if not required.issubset(fields):
            raise ValueError(f"annotation CSV missing columns: {sorted(required - fields)}")
        result = []
        for row in reader:
            start = parse_timestamp(row.get("start_local"))
            if start:
                result.append(Annotation(start, parse_timestamp(row.get("end_local")), str(row.get("kind", "")).strip().lower(), str(row.get("note", "")).strip()))
        return result


def column_index(header: Sequence[str]) -> Dict[str, Optional[str]]:
    actual = {h.strip(): h for h in header}
    names = set(REQUIRED) | {"Supervisor_Enabled", "Manual_Override_State", "Manual_Override_Remaining_Sec", "Section14_WAF_Active"}
    for expected, truth_col, count_col, contributors in TRUTH.values():
        names.add(truth_col)
        names.update(contributors)
        if count_col:
            names.add(count_col)
    for mode, action, setpoint in HVAC.values():
        names.update((mode, action, setpoint))
    return {name: (next((actual[x] for x in TIMESTAMP_NAMES if x in actual), None) if name == "Timestamp" else actual.get(name)) for name in names}


def annotation_applies(annotation: Annotation, timestamp: datetime) -> bool:
    return annotation.start <= timestamp <= annotation.end if annotation.end else abs((timestamp - annotation.start).total_seconds()) <= 900


def assess_context(loaded: Loaded, cols: Dict[str, Optional[str]], annotations: Sequence[Annotation], annotation_file_present: bool) -> Context:
    context = Context(
        supervisor_present=cols.get("Supervisor_Enabled") is not None,
        override_present=cols.get("Manual_Override_State") is not None,
        legacy_waf_present=cols.get("Section14_WAF_Active") is not None,
        annotation_file_present=annotation_file_present,
    )
    for index, (row, timestamp) in enumerate(zip(loaded.rows, loaded.timestamps)):
        contaminated = False
        supervisor = cols.get("Supervisor_Enabled")
        if supervisor and parse_bool(row.get(supervisor)) is False:
            context.supervisor_disabled_rows += 1
            contaminated = True
        override = cols.get("Manual_Override_State")
        if override:
            if str(row.get(override, "")).strip().lower() == "active":
                context.manual_override_rows += 1
                contaminated = True
        else:
            waf = cols.get("Section14_WAF_Active")
            if waf and parse_bool(row.get(waf)) is True:
                context.legacy_waf_rows += 1
                contaminated = True
        if timestamp:
            matches = [a for a in annotations if a.kind in CONTAMINATING_KINDS and annotation_applies(a, timestamp)]
            if matches:
                context.annotation_rows += 1
                for match in matches:
                    context.annotation_kinds[match.kind] += 1
                contaminated = True
        if contaminated:
            context.contaminated.add(index)
    return context


def summarize_topology(rows: Sequence[dict], cols: Dict[str, Optional[str]]) -> List[dict]:
    output = []
    for room, (expected, truth_col, count_col, contributors) in TRUTH.items():
        truth_blank = degraded = 0
        counts = Counter()
        for row in rows:
            if not str(row.get(cols.get(truth_col), "") or "").strip():
                truth_blank += 1
            available = sum(parse_float(row.get(cols.get(name))) is not None for name in contributors if cols.get(name))
            degraded += available < expected
            if count_col and cols.get(count_col):
                value = parse_float(row.get(cols[count_col]))
                if value is not None:
                    counts[int(value)] += 1
        output.append({"room": room, "expected": expected, "truth_blank": truth_blank, "degraded": degraded, "counts": counts})
    return output


def summarize_hvac(rows: Sequence[dict], cols: Dict[str, Optional[str]]) -> List[dict]:
    output = []
    for room, (mode_name, action_name, setpoint_name) in HVAC.items():
        setpoints, modes, actions = Counter(), Counter(), Counter()
        for row in rows:
            value = parse_float(row.get(cols.get(setpoint_name))) if cols.get(setpoint_name) else None
            if value is not None:
                setpoints[value] += 1
            for name, counter in ((mode_name, modes), (action_name, actions)):
                if cols.get(name):
                    text = str(row.get(cols[name], "") or "").strip().lower()
                    if text:
                        counter[text] += 1
        output.append({"room": room, "setpoints": setpoints, "modes": modes, "actions": actions})
    return output


def posture(loaded: Loaded, cols: Dict[str, Optional[str]], context: Context) -> tuple[str, str]:
    if not loaded.rows:
        return POSTURE_NO_DATA, "No data rows are present."
    missing = [name for name in REQUIRED if cols.get(name) is None]
    if missing:
        return POSTURE_MISSING_COLUMNS, f"Missing required columns: {sorted(missing)}"
    if context.contaminated:
        return POSTURE_CONTAMINATED, f"{len(context.contaminated)} of {len(loaded.rows)} rows have direct operator/context evidence."
    if not context.direct_context_present:
        return POSTURE_CONTEXT_INCOMPLETE, "No direct supervisor/override fields or annotation file were available; the analyzer will not infer operator intent from temperatures, setpoints, modes, actions, or runtime patterns."
    if loaded.span_days is None or loaded.span_days < MIN_OBSERVATION_DAYS:
        span = "unknown" if loaded.span_days is None else f"{loaded.span_days:.2f}"
        return POSTURE_INSUFFICIENT_WINDOW, f"Telemetry span is {span} days; at least {MIN_OBSERVATION_DAYS} days are required."
    return POSTURE_CLEAN_CANDIDATE, "Direct context shows no contamination and the observation window is long enough."


def counter_text(counter: Counter) -> str:
    return ", ".join(f"{key}×{value}" for key, value in sorted(counter.items(), key=lambda item: str(item[0]))) or "none"


def analyze(telemetry_path: Path, annotation_path: Optional[Path] = None) -> str:
    loaded = load_csv(telemetry_path)
    cols = column_index(loaded.header)
    context = assess_context(loaded, cols, load_annotations(annotation_path), annotation_path is not None)
    label, reason = posture(loaded, cols, context)
    lines = [
        "# Post-Change Evidence Review (V5.5)", "",
        "_Read-only local analysis; no Home Assistant or Google Sheets write path._", "",
        "## Posture", "", f"- **{label}**", f"  - {reason}", "",
        "## Direct Operator/Control Context", "",
        f"- `Supervisor_Enabled` present: {context.supervisor_present}",
        f"- `Manual_Override_State` present: {context.override_present}",
        f"- legacy `Section14_WAF_Active` present: {context.legacy_waf_present}",
        f"- annotation file supplied: {context.annotation_file_present}",
        f"- supervisor-disabled rows: {context.supervisor_disabled_rows}",
        f"- manual-override-active rows: {context.manual_override_rows}",
        f"- legacy-WAF rows used as fallback: {context.legacy_waf_rows}",
        f"- annotation-overlap rows: {context.annotation_rows}",
        f"- annotation kinds: {counter_text(context.annotation_kinds)}", "",
        "> Temperatures, setpoints, modes, actions, and zero-runtime patterns are observations only; they do not prove operator intent.", "",
        "## Truth Topology", "", "| Room | Expected | Truth blank rows | Degraded rows | Exported counts |", "|---|---:|---:|---:|---|",
    ]
    for item in summarize_topology(loaded.rows, cols):
        lines.append(f"| {item['room']} | {item['expected']} | {item['truth_blank']} | {item['degraded']} | {counter_text(item['counts'])} |")
    lines += ["", "## Observed HVAC Commands", "", "A 61°F or 79°F setpoint does not establish who issued it.", "", "| Room | Setpoints | Modes | Actions |", "|---|---|---|---|"]
    for item in summarize_hvac(loaded.rows, cols):
        lines.append(f"| {item['room']} | {counter_text(item['setpoints'])} | {counter_text(item['modes'])} | {counter_text(item['actions'])} |")
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("telemetry_csv", type=Path)
    parser.add_argument("--annotations", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/post_change_evidence_review.md"))
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    report = analyze(args.telemetry_csv, args.annotations)
    if args.no_write:
        print(report, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
