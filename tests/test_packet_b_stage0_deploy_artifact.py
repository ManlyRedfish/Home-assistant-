"""Contract checks for the copy-ready Packet B Stage 0 Section 2 artifact."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "deploy" / "packet_b_stage0_section2_replacement.yaml"


def _text() -> str:
    return ARTIFACT.read_text(encoding="utf-8")


def _doc():
    return yaml.safe_load(_text())


def test_artifact_is_one_valid_supervisor_automation():
    doc = _doc()
    assert isinstance(doc, list)
    assert len(doc) == 1
    assert doc[0]["id"] == "v7_5_main_supervisor"


def test_packet_a_truth_guards_are_preserved():
    text = _text()
    for name in (
        "lr_truth_ok",
        "master_truth_ok",
        "lincoln_truth_ok",
        "lilly_truth_ok",
    ):
        assert name in text
    assert text.count("not lr_truth_ok") >= 1
    assert text.count("not master_truth_ok") >= 1
    assert text.count("not lincoln_truth_ok") >= 1
    assert text.count("not lilly_truth_ok") >= 1


def test_profile_windows_and_thresholds_are_locked():
    text = _text()
    assert 'is_master_sleep: "{{ now().hour >= 18 or now().hour < 6 }}"' in text
    assert 'kids_bedtime: "{{ now().hour >= 18 or now().hour < 7 }}"' in text
    assert "lincoln_temp >= 70" in text
    assert "lincoln_temp <= 66" in text
    assert "lilly_temp >= 70" in text
    assert "lilly_temp <= 66" in text
    assert 'm_off_at: "{{ 74 if away else (62 if is_master_sleep else 68) }}"' in text
    assert 'm_on_at: "{{ 76 if away else (66 if is_master_sleep else 72) }}"' in text
    assert 'lr_conservation: "{{ away or lr_night_primary }}"' in text


def test_turbo_token_and_actuator_shove_are_single_source_constants():
    text = _text()
    assert "cooling_setpoint: 61" in text
    assert "cooling_fan_mode: turbo" in text
    assert "climate.set_fan_mode" in text
    assert 'fan_mode: "{{ cooling_fan_mode }}"' in text
    assert 'temperature: "{{ cooling_setpoint }}"' in text
    assert "fan_mode: high" not in text


def test_kids_bedtime_uses_top_level_call_resolutions():
    text = _text()
    assert "lincoln_bedtime_call:" in text
    assert "lilly_bedtime_call:" in text
    assert "{{ lincoln_bedtime_call == 'cool' }}" in text
    assert "{{ lilly_bedtime_call == 'cool' }}" in text
    assert "kids_bedtime and not away and season in ['cooling', 'shoulder']" in text


def test_bedroom_cooling_priority_suppresses_every_shoulder_lr_heat_path():
    text = _text()
    assert "bedroom_cool_priority:" in text
    assert "master_shoulder_call == 'cool'" in text
    assert "lincoln_bedtime_call == 'cool'" in text
    assert "lilly_bedtime_call == 'cool'" in text
    assert "lr_temp > 60" in text
    # Night and cold-day LR heat templates must both test suppression first.
    assert text.count("{% if bedroom_cool_priority %}off") == 2


def test_stage0_artifact_does_not_add_helpers_or_touch_recorder():
    text = _text()
    assert "recorder:" not in text
    assert "input_boolean:" not in text
    assert "input_select:" not in text
    assert "timer:" not in text
    assert "v9_sleep_priority_interlock" not in text
