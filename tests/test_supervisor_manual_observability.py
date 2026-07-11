"""
Regression tests for the observability-only supervisor/manual-override
telemetry enhancement.

The added fields are forensic outputs. They must not become inputs to the
comfort supervisor, safety gates, Section 14 boost, truth math, setpoints, or
thresholds.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml


class MooseLoader(yaml.SafeLoader):
    pass


def _secret(loader, node):
    return f"SECRET_{node.value}"


def _include(loader, node):
    return f"INCLUDE_{node.value}"


def _input(loader, node):
    return f"INPUT_{node.value}"


def _include_dir_merge_list(loader, node):
    return []


MooseLoader.add_constructor("!secret", _secret)
MooseLoader.add_constructor("!include", _include)
MooseLoader.add_constructor("!input", _input)
MooseLoader.add_constructor("!include_dir_merge_list", _include_dir_merge_list)
MooseLoader.add_constructor("!include_dir_named", _include_dir_merge_list)


ROOT = Path(__file__).resolve().parents[1]
AUTOMATIONS = ROOT / "automations.yaml"
CONFIGURATION = ROOT / "configuration.yaml"

TELEMETRY_ID = "vtherm_mega_tracker_v5"
PROVENANCE_ID = "v8_5_hvac_provenance_logger"
SUPERVISOR_ENTITY = "automation.v7_5_main_supervisor"
MANUAL_TIMER = "timer.manual_hvac_override"
NEW_FIELDS = {
    "Supervisor_Enabled",
}

# These hashes intentionally lock the control surfaces. If this test fails,
# the PR includes control-behavior changes and needs explicit review before
# the pinned hashes are updated.
#
# Re-pin history:
#   - section2 + configuration re-pinned for the V9-E evidence-gated Master
#     pre-cool exception (docs/v9_v10_goals.md §2.6): Section 2 gained the
#     pre-cool variables/guards and two Master hvac_mode template consults;
#     configuration.yaml gained the Section 16 helpers and forecast cache.
#     Section 3 (safety gates) and Section 14 hashes were NOT re-pinned —
#     those surfaces remain byte-for-byte unchanged.
#   - section2 + configuration re-pinned for V9-E revision
#     (impl/v9e-precool-revision): window gate changed to forecast-conditioned
#     release (02:00-13:00/11:00/06:00 with hard 14:00 backstop), slope guard
#     and runtime guard removed, config-invariant guard added, precool_max_runtime
#     retired, runtime counter cap raised to 720 min. See
#     docs/analysis/v9e_precool_revision_spec.md and
#     docs/analysis/v9e_precool_release_trigger.md.
#   - configuration re-pinned to repair a duplicate-key regression from the
#     V9-E revision: the precool_max_runtime/precool_drop_rate_limit deletion
#     left a stray, valueless `precool_previous_master_temp:` key at EOF, a
#     duplicate of the real helper. Home Assistant rejects the input_number:
#     mapping on the duplicate, so the integration never sets up and
#     input_number.set_value de-registers — surfacing as "V9-E: Master Pre-Cool
#     Nightly Reset has an unknown action: input_number.set_value". Removing the
#     stray key (no behavior change; helper set unchanged) restores the action.
#   - section3 re-pinned for the V8.6 truth-unavailable cooling failsafe restore:
#     re-introduced the two OFF-only safety automations
#     (v8_6_truth_unavailable_cooling_failsafe + ...reconciliation) recovered
#     verbatim from Packet A commit 9e39e42 to re-link the live registry orphans.
#     Section 3 only; sections 2/14 and configuration.yaml unchanged. These gates
#     force a head OFF when its room-truth sensor is invalid while cooling; they
#     never authorize cooling. See the Section 3 V8.6 comment block and
#     tests/test_packetA_truth_unavailable_failsafe.py.
#   - section2 + configuration re-pinned for the Heat Wave Override — 96h
#     (automations.yaml Section 19). Section 2's main supervisor gained a single
#     comfort gate condition (`input_boolean.heat_wave_override == off`) so the
#     supervisor stands down while the operator override owns the actuators; the
#     pre-existing `timer.manual_hvac_override == idle` gate is unchanged.
#     configuration.yaml gained the override helpers (timer.heat_wave_override_96h
#     @96h restore:true, input_boolean.heat_wave_override,
#     input_datetime.heat_wave_override_deadline) and the actuator
#     script.heat_wave_override_apply plus a one-shot
#     script.heat_wave_override_season_reconcile (called only by the Section 19
#     release paths to re-derive input_select.hvac_season_mode from deck truth
#     using Section 5's thresholds, so supervision does not resume in a stale
#     season after a long override). Section 3 (safety gates) and Section 14
#     hashes were deliberately NOT re-pinned — those surfaces remain byte-for-byte
#     unchanged, proving the override gates only comfort logic and leaves the
#     LR 60°F / Master 58°F floors and truth-unavailable failsafes untouched.
#   - configuration re-pinned for the Heat Wave Override Samsung command
#     reliability patch: script.heat_wave_override_apply now issues a split,
#     serialized Samsung-safe sequence per head — set_hvac_mode cool, ~2s delay,
#     set_temperature 61 (temperature ONLY, no bundled hvac_mode), ~1s delay,
#     set_fan_mode turbo. This replaces the single bundled set_temperature that
#     the Samsung/SmartThings integration could silently ignore the temperature
#     on (observed live on climate.living_room_air retaining a stale 79°F
#     target). Same per-room truth guards (LR>60 / Master>58 / valid). Only the
#     actuator script body changed — automations.yaml (Section 2/3/14 and the
#     Section 19 lifecycle), helpers, and season reconcile are untouched.
#   - section2 re-pinned for the Lilly Heatwave Sleep Guard: a toggle-armed,
#     Lilly-only exception in the cooling-season block. Two new local
#     variables (is_lilly_sleep — 19:00-07:00; lilly_heatwave_sleep_guard —
#     reads input_boolean.lilly_heatwave_sleep_guard) gate ly_off_at/ly_on_at
#     down to 66/70 ONLY when the helper is on AND the clock is in the sleep
#     window; helper off, or daytime with the helper on, falls through to the
#     unchanged 68/72. Away (74/76) still takes priority over the guard.
#     Master, Lincoln, Living Room, heating, and away logic are untouched.
#   - section2 re-pinned for Packet B Rev 4 CHANGE-3: LR night conservation
#     profile (P4) wired into the cooling branch. Adds one local variable
#     (`lr_conservation: away or lr_night_primary`) and switches the LR
#     lr_off_at / lr_on_at ternaries from `74/76 if away else 68/72` to
#     `74/76 if lr_conservation else 68/72`. When
#     input_boolean.night_mode_lr_primary is on and not away, LR cools to
#     the 74/76 conservation band instead of the daytime 68/72; away (P1)
#     precedence is preserved because the disjunction still activates
#     conservation via `away` alone. LR cooling command remains
#     cool@61 (CHANGE-2 turbo on every cooling call is deferred). Master,
#     Lincoln, Lilly, shoulder, and heating logic are byte-for-byte
#     unchanged. Section 14 hash deliberately NOT re-pinned — that surface
#     remains unchanged, proving CHANGE-3 is scoped to the comfort branch.
#     Evidence gate satisfied by
#     docs/analysis/lr-night-cooling-capacity-discovery.md (9 Master
#     starvation events with 100% LR co-fire, 90°F outdoor crossover) per
#     docs/3_regression_appendix.md §4.5 reopen condition.
#   - section3 re-pinned for the V7.5 + V8 shade watcher template bug fix
#     (PR #156, same commit as CHANGE-3): `trigger.context.parent_id`
#     corrected to `trigger.to_state.context.parent_id` on the Section 3
#     shade watcher's manual-only guard (the state-trigger dict on HA
#     2024+ carries `context` on `to_state`, not on `trigger` itself; the
#     bad accessor raised 1,029+ UndefinedError entries in the log). One
#     accessor path corrected; no threshold, gate, or safety behavior
#     changed. Section 3 remains OFF-only safety.
#   - configuration re-pinned for the Section 10 control-wrapper
#     graceful-degradation fix (deadband-supervisor-sensor-chain-layih9):
#     each of the seven `*_temperature_control` template wrappers now
#     falls back to its underlying `*_temperature_truth` sensor when the
#     Section 12 `*_temperature_smoothed` lowpass filter is
#     unknown/unavailable, and its `availability` follows the OR of the
#     two. Preserves the smoothed value in every normal condition;
#     prevents the sensor chain from stranding `_control` unavailable
#     after a recorder DB migration leaves the `filter` platform unable
#     to initialize (2026-07-09 PostgreSQL/TrueNAS incident — LR + Office
#     reproduced live). Only Section 10 changed; Section 12 filters,
#     truth definitions, Section 16 helpers, and all Section 2/3/14
#     surfaces are byte-for-byte unchanged. Section 2/3/14 hashes were
#     deliberately NOT re-pinned — proving this is a sensor-chain-only
#     fix with no comfort-doctrine or safety-gate change.
#   - section2, section3, section14 re-pinned for timer removal + smoothed truth:
#     timer.manual_hvac_override removed (11 locations), all supervisor/Section 6/
#     Section 14 _temperature_truth → _temperature_control, > → >= on cooling
#     engage thresholds, transition logger defensive attrs.get() fix.
#     configuration.yaml is byte-for-byte unchanged.
EXPECTED_SECTION_HASHES = {
    "section2_main_supervisor": (
        "# SECTION 2: MAIN SUPERVISOR",
        "# SECTION 3:",
        # Re-pinned for timer removal + smoothed truth: timer gate removed,
        # _temperature_truth → _temperature_control, > → >= on cooling engage.
        "2adef484f783c2625a235137849b8afdaf9acce35ada7eebf1ecc1dfb1ece5ce",
    ),
    "section3_safety_gates": (
        "# SECTION 3: SAFETY GATES",
        "# SECTION 4:",
        # Re-pinned: manually_hvac_override references removed from Section 3
        # comment. Section 3 safety floors and thresholds are unchanged.
        "b4081f516033ceea1c888b91a89e0f83f7b96d5f8556317672707350310269f2",
    ),
    "section14_lr_boost": (
        "# SECTION 14: V8.4 LR HEATING RECOVERY BOOST PILOT",
        "# SECTION 15:",
        # Re-pinned: WAF_Active hardcoded false, Engage_Eligible override var
        # removed, timer.gating removed from boost_release, observability
        # fields removed.
        "184ea751ed94859366df953f09b85a0d32f66d1369adfd74fa2e3d76231db081",
    ),
}
EXPECTED_CONFIGURATION_HASH = "62b4d8f94dd3d0291b69d12438fbf60135c7e1f278b32c91c872aadf55026ac1"


@pytest.fixture(scope="module")
def automations_text() -> str:
    return AUTOMATIONS.read_text()


@pytest.fixture(scope="module")
def automations_data():
    return yaml.load(AUTOMATIONS.read_text(), Loader=MooseLoader)


def _find_automation(automations_data, automation_id: str):
    for automation in automations_data:
        if automation.get("id") == automation_id:
            return automation
    pytest.fail(f"Automation {automation_id!r} not found")


def _iter_action_items(action):
    if action is None:
        return
    if isinstance(action, dict):
        action = [action]
    for item in action:
        if not isinstance(item, dict):
            continue
        yield item
        for nested_key in ("choose", "if", "repeat", "parallel", "default", "then", "else", "sequence"):
            nested = item.get(nested_key)
            if nested is None:
                continue
            if nested_key == "choose" and isinstance(nested, list):
                for choice in nested:
                    if isinstance(choice, dict):
                        yield from _iter_action_items(choice.get("sequence"))
                continue
            if isinstance(nested, list):
                yield from _iter_action_items(nested)
            elif isinstance(nested, dict):
                yield from _iter_action_items([nested])


def _append_sheet_payload(automation: dict, worksheet: str) -> dict:
    for item in _iter_action_items(automation.get("action")):
        if (item.get("action") or item.get("service")) != "google_sheets.append_sheet":
            continue
        data = item.get("data") or {}
        if data.get("worksheet") == worksheet:
            payload = data.get("data")
            assert isinstance(payload, dict)
            return payload
    pytest.fail(f"No google_sheets.append_sheet action targeting {worksheet!r}")


def _section(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start + 1)
    return text[start:end]


def test_v55_wide_row_contains_supervisor_field(automations_data):
    tracker = _find_automation(automations_data, TELEMETRY_ID)
    payload = _append_sheet_payload(tracker, "VTherm_Launch_Data_v5_5")

    assert NEW_FIELDS <= set(payload), "V5.5 wide-row telemetry fields are missing"
    assert SUPERVISOR_ENTITY in payload["Supervisor_Enabled"]


def test_provenance_logger_observes_supervisor_enabled_disabled_transitions(automations_data):
    logger = _find_automation(automations_data, PROVENANCE_ID)
    triggers = logger.get("trigger") or []

    assert any(
        trigger.get("platform") == "state"
        and trigger.get("entity_id") == SUPERVISOR_ENTITY
        and trigger.get("id") == "supervisor_enabled_state"
        for trigger in triggers
    ), "Section 15 must observe main-supervisor enable/disable transitions"

    variables = next(
        item.get("variables")
        for item in _iter_action_items(logger.get("action"))
        if isinstance(item.get("variables"), dict)
    )
    candidate_template = variables["automation_candidate_v"]
    assert SUPERVISOR_ENTITY in candidate_template
    assert "v7_5_main_supervisor" in candidate_template


def test_no_control_automation_consumes_new_telemetry_fields(automations_text):
    section1 = _section(automations_text, "# SECTION 1:", "# SECTION 2:")
    rest = automations_text.replace(section1, "")

    for field in NEW_FIELDS:
        assert field not in rest, f"{field} leaked outside the write-only telemetry exporter"

    for section_start, section_end in [
        ("# SECTION 2:", "# SECTION 3:"),
        ("# SECTION 3:", "# SECTION 4:"),
        ("# SECTION 14:", "# SECTION 15:"),
    ]:
        control_section = _section(automations_text, section_start, section_end)
        assert SUPERVISOR_ENTITY not in control_section
        for field in NEW_FIELDS:
            assert field not in control_section


def test_no_automation_reads_google_sheets_tabs(automations_data):
    for automation in automations_data:
        for item in _iter_action_items(automation.get("action")):
            service = item.get("action") or item.get("service")
            if service:
                assert not service.startswith("google_sheets.get"), (
                    "Google Sheets must remain a write-only forensic sink"
                )


def test_control_surfaces_and_truth_configuration_are_byte_for_byte_unchanged(automations_text):
    for name, (start, end, expected_hash) in EXPECTED_SECTION_HASHES.items():
        digest = hashlib.sha256(_section(automations_text, start, end).encode()).hexdigest()
        assert digest == expected_hash, f"{name} changed in an observability-only PR"

    configuration_digest = hashlib.sha256(CONFIGURATION.read_bytes()).hexdigest()
    assert configuration_digest == EXPECTED_CONFIGURATION_HASH, (
        "configuration.yaml changed; truth weights/helpers are outside this PR's scope"
    )


def test_verified_supervisor_entity_id_is_documented(automations_text):
    assert "Verified live main-supervisor entity_id: automation.v7_5_main_supervisor" in automations_text
    assert "Do not derive this from the YAML id alone" in automations_text
