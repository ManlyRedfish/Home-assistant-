from __future__ import annotations

import csv
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "analyze_post_change_evidence.py"

spec = importlib.util.spec_from_file_location("analyzer", TOOL)
analyzer = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = analyzer
spec.loader.exec_module(analyzer)

BASE_HEADER = [
    "Timestamp",
    "LR_Temp_Truth", "Master_Temp_Truth", "Lincoln_Temp_Truth", "Lilly_Temp_Truth",
    "LR_Air_Setpoint", "Master_Air_Setpoint", "Lincoln_Air_Setpoint", "Lilly_Air_Setpoint",
    "LR_Air_Mode", "Master_Air_Mode", "Lincoln_Air_Mode", "Lilly_Air_Mode",
    "LR_Air_Action", "Master_Air_Action", "Lincoln_Air_Action", "Lilly_Air_Action",
]


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def row(timestamp: str, **extra: str) -> dict:
    data = {name: "" for name in BASE_HEADER}
    data.update({
        "Timestamp": timestamp,
        "LR_Temp_Truth": "66", "Master_Temp_Truth": "64",
        "Lincoln_Temp_Truth": "69", "Lilly_Temp_Truth": "70",
        "LR_Air_Setpoint": "61", "Master_Air_Setpoint": "61",
        "Lincoln_Air_Setpoint": "61", "Lilly_Air_Setpoint": "61",
        "LR_Air_Mode": "cool", "Master_Air_Mode": "cool",
        "Lincoln_Air_Mode": "cool", "Lilly_Air_Mode": "cool",
    })
    data.update(extra)
    return data


def test_constants_and_read_only_contract() -> None:
    assert analyzer.COOL_SHOVE_F == 61.0
    assert analyzer.HEAT_SHOVE_F == 79.0
    assert analyzer.BOOST_SETPOINT_F == 77.0
    text = TOOL.read_text(encoding="utf-8")
    for forbidden in ("requests", "urllib", "homeassistant", "googleapiclient"):
        assert f"import {forbidden}" not in text


def test_supervisor_disabled_is_direct_contamination(tmp_path: Path) -> None:
    path = tmp_path / "telemetry.csv"
    header = BASE_HEADER + ["Supervisor_Enabled", "Manual_Override_State"]
    write_csv(path, header, [row("2026-06-05 12:00:00", Supervisor_Enabled="false", Manual_Override_State="idle")])
    report = analyzer.analyze(path)
    assert "CONTAMINATED_WINDOW" in report
    assert "supervisor-disabled rows: 1" in report


def test_manual_override_active_is_direct_contamination(tmp_path: Path) -> None:
    path = tmp_path / "telemetry.csv"
    header = BASE_HEADER + ["Supervisor_Enabled", "Manual_Override_State"]
    write_csv(path, header, [row("2026-06-05 12:00:00", Supervisor_Enabled="true", Manual_Override_State="active")])
    report = analyzer.analyze(path)
    assert "CONTAMINATED_WINDOW" in report
    assert "manual-override-active rows: 1" in report


def test_legacy_waf_is_fallback_only(tmp_path: Path) -> None:
    path = tmp_path / "telemetry.csv"
    header = BASE_HEADER + ["Supervisor_Enabled", "Section14_WAF_Active"]
    write_csv(path, header, [row("2026-06-05 12:00:00", Supervisor_Enabled="true", Section14_WAF_Active="true")])
    report = analyzer.analyze(path)
    assert "CONTAMINATED_WINDOW" in report
    assert "legacy-WAF rows used as fallback: 1" in report


def test_new_override_column_takes_precedence_over_legacy_waf(tmp_path: Path) -> None:
    path = tmp_path / "telemetry.csv"
    header = BASE_HEADER + ["Supervisor_Enabled", "Manual_Override_State", "Section14_WAF_Active"]
    write_csv(path, header, [row(
        "2026-06-05 12:00:00",
        Supervisor_Enabled="true",
        Manual_Override_State="idle",
        Section14_WAF_Active="true",
    )])
    report = analyzer.analyze(path)
    assert "legacy-WAF rows used as fallback: 0" in report
    assert "CONTAMINATED_WINDOW" not in report


def test_annotation_interval_marks_historical_rows(tmp_path: Path) -> None:
    telemetry = tmp_path / "telemetry.csv"
    annotations = tmp_path / "annotations.csv"
    write_csv(telemetry, BASE_HEADER, [row("2026-06-04 12:00:00")])
    write_csv(annotations, ["start_local", "end_local", "kind", "note", "created_at"], [{
        "start_local": "2026-06-03 00:00:00",
        "end_local": "2026-06-05 15:00:00",
        "kind": "supervisor_disabled",
        "note": "operator-directed cold experiment",
        "created_at": "2026-06-05",
    }])
    report = analyzer.analyze(telemetry, annotations)
    assert "CONTAMINATED_WINDOW" in report
    assert "annotation-overlap rows: 1" in report
    assert "supervisor_disabled" in report


def test_no_context_does_not_infer_from_cold_setpoints(tmp_path: Path) -> None:
    path = tmp_path / "telemetry.csv"
    write_csv(path, BASE_HEADER, [row("2026-06-05 12:00:00")])
    report = analyzer.analyze(path)
    assert "CONTEXT_INCOMPLETE" in report
    assert "will not infer operator intent" in report


def test_unusual_temperature_or_setpoint_is_observation_not_contamination(tmp_path: Path) -> None:
    path = tmp_path / "telemetry.csv"
    header = BASE_HEADER + ["Supervisor_Enabled", "Manual_Override_State"]
    cold = row(
        "2026-06-05 12:00:00",
        Supervisor_Enabled="true",
        Manual_Override_State="idle",
        LR_Temp_Truth="59.5",
        LR_Air_Setpoint="55",
    )
    write_csv(path, header, [cold])
    report = analyzer.analyze(path)
    assert "CONTAMINATED_WINDOW" not in report
    assert "55.0×1" in report


def test_annotation_schema_validation(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    write_csv(path, ["start_local", "kind"], [{"start_local": "2026-06-05", "kind": "other"}])
    with pytest.raises(ValueError):
        analyzer.load_annotations(path)


@pytest.mark.parametrize(
    "text, expected",
    [
        # One case per format declared in TIMESTAMP_FORMATS, in declaration order.
        ("2026-06-05 12:00:00", datetime(2026, 6, 5, 12, 0, 0)),
        ("2026-06-05T12:00:00", datetime(2026, 6, 5, 12, 0, 0)),
        ("2026-06-05 12:00", datetime(2026, 6, 5, 12, 0, 0)),
        ("06/05/2026 12:00:00", datetime(2026, 6, 5, 12, 0, 0)),
        ("06/05/2026 12:00", datetime(2026, 6, 5, 12, 0, 0)),
    ],
)
def test_parse_timestamp_accepts_each_declared_format(text: str, expected: datetime) -> None:
    assert analyzer.parse_timestamp(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        # Forms that no strptime format matches but datetime.fromisoformat handles.
        ("2026-06-05", datetime(2026, 6, 5, 0, 0, 0)),  # date-only -> midnight
        ("2026-06-05T12:00:00.123456", datetime(2026, 6, 5, 12, 0, 0, 123456)),  # microseconds
    ],
)
def test_parse_timestamp_falls_back_to_isoformat(text: str, expected: datetime) -> None:
    assert analyzer.parse_timestamp(text) == expected


def test_parse_timestamp_isoformat_preserves_timezone() -> None:
    result = analyzer.parse_timestamp("2026-06-05T12:00:00+00:00")
    assert result == datetime(2026, 6, 5, 12, 0, 0, tzinfo=timezone.utc)
    assert result is not None and result.tzinfo == timezone.utc


def test_parse_timestamp_strips_surrounding_whitespace() -> None:
    assert analyzer.parse_timestamp("  2026-06-05 12:00:00  ") == datetime(2026, 6, 5, 12, 0, 0)


@pytest.mark.parametrize(
    "text",
    [
        "",  # empty string
        "   ",  # whitespace only collapses to empty after strip
        "not a date",  # gibberish
        "2026-13-45 99:99:99",  # well-shaped but out-of-range components
        "06/05/2026",  # US date with no time matches no format
        "12:00:00",  # time with no date
        "2026-06-05 12:00:00 extra",  # trailing junk defeats full-string match
    ],
)
def test_parse_timestamp_returns_none_for_unparseable_text(text: str) -> None:
    assert analyzer.parse_timestamp(text) is None


@pytest.mark.parametrize("value", [None, 0, 0.0, False])
def test_parse_timestamp_returns_none_for_falsy_values(value: object) -> None:
    # `str(value or "")` treats every falsy value as an empty string, so numeric
    # zero and False are deliberately unparseable rather than epoch timestamps.
    assert analyzer.parse_timestamp(value) is None
