# Doc 5 / Runtime Layer V2

**Runtime Date:** April 25, 2026
**Document Role:** Runtime Layer
**Status:** Live implementation boundary for the Moose House climate system. Update when active control logic, truth-sensor logic, helper structure, safety behavior, or telemetry schema materially changes.

## 1. Purpose of This Layer

This layer defines the live operational truth of the Moose House climate system. Its purpose is to identify the sources that describe what the system is actually doing now, acting as the boundary between the narrative canon and the live system.

## 2. What Counts as Runtime Truth

The Moose House runtime layer consists of the following active sources:

### 2.1 Active Control Source
**Source:** `automations.yaml`
**Current control architecture:** V8.3 — Comfort-First Hotfix with Stack-Effect Mitigation
This file contains the live supervisory climate behavior, safety gates, telemetry export automation, seasonal branches, and supporting operational logic. V8.3 introduces a top-anchored heating deadband, a passive 18:00-22:00 LR setpoint reduction to mitigate stack-effect, and an expanded Section 11 HVAC Transition Logger to audit hysteresis behavior.

### 2.2 Active Truth Source
**Source:** `configuration.yaml`
**Current truth architecture:** V3.1 — Audited Truth / Smoothed / Control
This file contains per-room truth sensors, staleness rejection, outlier handling, smoothed sensors, runtime tracking, and control wrappers. It explicitly states the design principles of weighted per-room truth, 2-hour staleness rejection, Lincoln outlier rejection, low-weight internal Samsung sensing, and removal of failed MSR-2 DPS310 sensors.

### 2.3 Active Evidence Source
**Source:** VTherm_Launch_Data_v5_5
**Current telemetry/export schema:** V5.5 — Semantic Heritage Schema + Section 14 boost-state observability
The live telemetry pipeline is defined in `automations.yaml` as a 15-minute export to Google Sheets under the worksheet `VTherm_Launch_Data_v5_5`, with room/metric/role/transport-aware naming. V5.5 is a wide-table interim schema that extends V5 with Section 14 boost-state observability columns (issue #62); it preserves the V5 row model and column conventions. V5 (`VTherm_Launch_Data_v5`) remains historical and is no longer written to. V6 (event-oriented) remains future work — see `docs/v6_telemetry_schema_proposal.md` and `docs/v6_observability_roadmap.md`.

### 2.4 Active Surface-State Sources
- Live Home Assistant state
- Helper states
- Template sensor states
- Logbook / history
- Runtime counters derived from history stats and equipment-firing binary sensors
*(These sources do not replace the YAML, but they expose runtime reality in motion.)*

## 3. Authority Rule

The Runtime Layer is the implementation boundary for current behavior.
- If Doc 1 (Startup Canon) and runtime disagree, runtime wins for implementation truth.
- If Doc 2 (Reference Map) and runtime disagree, verify whether the Reference Map is stale.
- If Doc 4 (Operations Sheet) describes behavior that runtime does not actually implement, runtime still wins for what is happening now.
- Telemetry reflects observed outcomes, not necessarily intended behavior.
- Historical doctrine never overrides active runtime files.

## 4. Scope of This Layer

This layer should preserve, at a high level:
- Which control architecture is currently live
- Which truth architecture is currently live
- Which telemetry schema is currently live
- Which helper/template structures materially affect control
- Which safety separations are active
- Which known runtime compromises are intentionally tolerated

This layer should not become a full YAML dump. It is a runtime map, not a code mirror.

## 5. Current Active Runtime Snapshot

### 5.1 Active Control Layer
**Current active control version:** V8.3
**Current control file:** `automations.yaml`
**Current posture:** Comfort-first deadband hotfix with explicit safety backstops, plus LR heating deadband and stack-effect mitigation.

### 5.2 Active Truth Layer
**Current active truth version:** V3.1
**Current truth file:** `configuration.yaml`
**Current posture:** Audited, trimmed, smoothed truth architecture.

### 5.3 Active Telemetry Layer (V5.5 Semantic Heritage Schema + Section 14 boost obs)
**Current telemetry version:** V5.5
**Current export destination:** Google Sheets
**Current worksheet:** `VTherm_Launch_Data_v5_5`
**Current schema style:** Semantic Heritage naming, mapping room + metric + role + transport into export headers, plus Section 14 boost-state observability columns.

**V5 vs V5.5 vs V6 boundary:**
- V5 (`VTherm_Launch_Data_v5`) — historical and unchanged. No longer written to. Referenced by `docs/analysis/v8_4_lr_boost_v5_evidence_review.md`.
- V5.5 (`VTherm_Launch_Data_v5_5`) — begins the Section 14 observability era. Wide-table interim schema. Adds the §14 sub-block columns from `automations.yaml` Section 1: `Section14_Boost_Active`, `Section14_Timer_State`, `Section14_Timer_Remaining`, `Section14_Last_Engage_Reason`, `Section14_Last_Release_Reason`, `Section14_Last_Engage_At`, `Section14_Last_Release_At`, `Section14_Engage_Eligible`, `Section14_WAF_Active`, `Section14_Truth_Available`. No control or threshold change.
- V6 — future event-oriented telemetry work. Out of scope here.

**⚠️  Worksheet header row:** the live Google Sheets `VTherm_Launch_Data_v5_5` worksheet header must include the new sub-block-14 columns in the same order they appear in `automations.yaml` Section 1 before the first export tick after this change ships, otherwise rows will be misaligned. This is an out-of-band manual step.

## 6. Live Runtime Components

### 6.1 Control Components
The live control runtime includes:
- **Main Supervisor (V8.3):** Runs every 15 minutes and acts as the central climate brain for mini-split control. The live file explicitly identifies this section as the central climate supervisor.
- **Comfort-first cooling deadband logic:** The live cooling doctrine uses:
  - All rooms: setpoint 68, off ≤68, on >72
  - Master sleep window (6pm–6am): setpoint 63, off ≤62, on >66
  - Away: setpoint 74, off ≤74, on >76
- **Heating deadband logic (V8.3):** The live heating doctrine uses:
  - Heating/Shoulder daytime: top-anchored deadband (target 68, off ≥68, on <64) to prevent short-cycling.
  - Bedtime (18:00-22:00, non-away): LR target drops to 64, deadband 62-64°F, to passively reduce stack-effect upstairs heating.
- **Nest off during cooling branch:** During the cooling branch, the Nest-controlled dining/boiler climate is forced off while mini-splits govern cooling behavior.
- **Seasonal branching:** The supervisor branches by `input_select.hvac_season_mode`, supporting cooling and shoulder-season behavior in the live file.
- **Away mode relaxation:** Runtime behavior relaxes temperature targets when `input_boolean.away_mode` is active.

### 6.2 Safety Components
The runtime explicitly separates safety from comfort. The live automations file describes V8.3 as including:
- LR runaway cutoff at 60°F
- Master emergency cooling floor at 58°F
- Ceiling gates
- Separation of comfort logic from runaway protection as an active design direction
*(This separation is important: safety logic is not the same thing as comfort logic, and the runtime treats them as distinct systems.)*

### 6.3 Semantic Heritage Naming Disclaimer
**Important Note:** Transport labels in V5 column names are historical/positional, not literal. For example, Lilly `*_BT` is a WiFi Wyze cam, and multiple `*_Matter` columns are removed-from-truth SwitchBot paths. Do not assume the column suffix strictly dictates the current active transport protocol.

### 6.4 Truth Components
The live truth runtime includes:
- **Per-room weighted truth sensors:** `configuration.yaml` explicitly describes per-room weighted averages from multiple physical sensors.
- **2-hour staleness rejection:** The design principles explicitly state a 2-hour staleness rejection policy on all inputs.
- **Lincoln outlier rejection:** Lincoln is the pilot room for outlier rejection, with a 3°F limit against the base mean of primary sensors. Samsung internal sensing is excluded from the outlier calculation itself.
- **Low-weight internal HVAC sensing:** Samsung internal thermistors remain present but are intentionally low-weight because they are biased hardware. This is explicitly part of the V3.1 design principles.
- **Smoothed output → control wrappers:** `configuration.yaml` explicitly defines smoothed sensors and control wrappers as part of the architecture.

### 6.5 Helper / Memory Components
The runtime depends on several helpers. The live automations file explicitly lists helper dependencies including:
- `input_select.hvac_season_mode`
- `input_boolean.night_mode_lr_primary`
- `timer.manual_hvac_override`
- `timer.shade_manual_override`
- `input_boolean.away_mode`
- `input_boolean.lr_heating_recovery_boost_active` (Section 14 V8.4 LR boost latch)
- `timer.lr_heating_recovery_boost_max_runtime` (Section 14 V8.4 LR boost timeout, `restore: true`)
- `input_text.lr_heating_recovery_boost_last_engage_reason` (Section 14 v5.5 observability — last engage classifier; written by engage action block; observability-only, no control authority)
- `input_text.lr_heating_recovery_boost_last_release_reason` (Section 14 v5.5 observability — one of `truth_cap` / `timeout` / `waf` / `season_change` / `truth_unavailable` / `unknown_release_reason`; written by release action block; observability-only, no control authority)
- `input_datetime.lr_heating_recovery_boost_last_engage_at` (Section 14 v5.5 observability — engage timestamp; observability-only)
- `input_datetime.lr_heating_recovery_boost_last_release_at` (Section 14 v5.5 observability — release timestamp; observability-only)
*(These helpers are not just UI artifacts. They are part of the live control path and must exist for runtime behavior to function properly. The four v5.5 observability helpers are written from Section 14 action blocks AFTER the existing control actions complete; they do not gate, change, or interrupt any Section 14 trigger, condition, climate command, timer call, or latch flip.)*

### 6.6 Evidence / Runtime Observation Components
The runtime evidence layer includes:
- 15-minute Google Sheets export
- Logbook / history review
- Equipment firing binary sensors
- `history_stats` runtime tracking
- Truth contributor / active count diagnostics
*(`configuration.yaml` explicitly states that binary sensors feed runtime tracking and presence-driven automations, and that equipment-firing sensors are used for runtime counters.)*

## 7. Known Runtime Constraints

The current runtime includes deliberate compromises. These are known live realities, not archive trivia.

### 7.1 HVAC-Mode-as-Memory
The V8.3 supervisor uses HVAC mode as deadband memory. The live file explicitly describes this as a known-imperfect shortcut that degrades gracefully when device and controller intent diverge between 15-minute ticks.

### 7.2 Command-on-Every-Tick
Commands are issued every supervisor tick rather than only on state transitions. The live file calls this noisy but acceptable for now, and explicitly identifies it as deferred V9 cleanup.

### 7.3 No Explicit Capacity Arbitration
The live V8.3 runtime does not implement explicit multi-head capacity arbitration. The automations file explicitly states that this is deferred until there is measured evidence of real starvation under load.

### 7.4 Orphaned / Transitional Runtime Pieces
The live file explicitly identifies:
- **PRE-COOL LATCH (Section 3B):** (REMOVED in PR #28 — the orphaned Section 3B `v8_precool_latch` automation was deleted from `automations.yaml`. The `input_boolean.precool_active` helper is no longer toggled or read by any YAML; if it persists as a UI-defined helper it has no remaining writers or readers.)
- **MASTER PRE-COOL:** (DISABLED — superseded by V8.1/V8.2 cooling branch)
- **HVAC TRANSITION LOGGER:** (Expanded in V8.3 to capture heating hysteresis transitions)
- **EVENT JOURNAL (Section 13 + Section 12):** (REMOVED — The disabled Event Journal infrastructure, including Section 13 in `configuration.yaml`, the `script.log_event` no-op, and Section 12 EJ observers in `automations.yaml`, has been permanently removed. The `notify.event_journal` sink never registered on this HA build and multiple attempts to land a working sink failed. Future logging requirements should be addressed with a proven HA-compatible sink.)
- **V8.4 LR HEATING RECOVERY BOOST (Section 14):** (DEPLOYED, ENGAGED REPEATEDLY BUT EVERY CYCLE CONTAMINATED — engage and release automations are enabled and the helpers (`input_boolean.lr_heating_recovery_boost_active`, `timer.lr_heating_recovery_boost_max_runtime`) are live. As of 2026-05-04, the engage path has fired four times (2026-05-03 04:45, 2026-05-03 11:45, 2026-05-04 10:00, 2026-05-04 13:30) — each with `LR_Air_Setpoint=77` and a non-zero `LR_HP_Runtime_Today_Hrs` delta on the engage tick. Every observed cycle was terminated externally within minutes (presumed WAF or `truth_unavailable`), not by `truth_cap` at 67°F or the 90-minute timeout. **Boost effectiveness on recovery time is therefore still unmeasured.** Validation evidence pipeline is HA Logbook + `VTherm_Launch_Data_v5` + Section 14 traces, per the postmortem §9. See `docs/telemetry_confounders.md` for the operator-suppressed-window rules that govern interpretation of Section 14 cycles.)
*(These are part of the current runtime surface and should not be silently forgotten.)*

### 7.5 Sensor Exclusion Reality
`configuration.yaml` currently describes both MSR-2 DPS310 sensors as removed from truth because of hardware failure. That is the active runtime position in the config file, even if later operational notes may nuance the exact diagnosis. Runtime truth comes from what the live config currently excludes, not from retrospective reinterpretation.

### 7.6 Operator-Suppressed Telemetry Windows
On occasion the operator has manually disabled `automation.v7_5_main_supervisor` (Section 2) during disrupted-sleep nights/days. Section 1 telemetry continues to write rows in those windows, but the rows reflect operator-managed state, not Section 2 doctrine. Apr 28–May 1 (2026) is the canonical contaminated window: three consecutive days of `LR_HP_Runtime_Today_Hrs = 0.00` with LR truth dropping to 60.3°F while LR was pinned `off@68`. Cold-drift, zero-runtime, or `Section 2 did/did not do X` claims drawn from operator-suppressed windows are category errors. The classification rules and the canonical contaminated window are documented in `docs/telemetry_confounders.md`. No runtime change is required; this is a forward-analysis guardrail, addressed against Issue #31.

## 8. Runtime Change Rules

Update this layer only when live implementation changes.
This layer should be updated when:
- Active control version changes
- Active truth version changes
- Helper dependencies materially change
- Safety logic materially changes
- Telemetry schema or worksheet changes
- A source is added to or removed from truth calculations
- A runtime workaround is introduced, retired, or replaced
*(Do not update this layer merely to improve prose.)*

## 9. What This Layer Is Not

This document is not:
- Doc 1 / Startup Canon
- Doc 2 / Reference Map
- Appendix A / Historical Audit Appendix
- Doc 3 / Regression Appendix
- Doc 4 / Operations Sheet
- The full YAML dump
*(It exists to preserve runtime truth boundaries, not to duplicate every implementation detail.)*

## 10. Runtime Verification Workflow

When checking a runtime claim, use this order:
1. Check active `automations.yaml`
2. Check active `configuration.yaml`
3. Check helper and template states
4. Check telemetry/logbook/history for observed behavior
5. Check Doc 2 / Reference Map for routing or source precedence
6. Check Doc 1 / Startup Canon for intended doctrine
7. Check Audit / Regression docs only when historical explanation is needed

## 11. Minimum Runtime Inventory

The runtime layer should always preserve, at minimum:
- Active control version: V8.3
- Active truth version: V3.1
- Active telemetry version: V5.5
- Telemetry worksheet: VTherm_Launch_Data_v5_5
- Key helper dependencies
- Key climate entities
- Key room truth entities
- Active safety mechanisms
- Known excluded/degraded runtime pieces
- Known deferred architectural debts

## 12. Current Runtime Risks

The primary current runtime risks are:
- Helper-based memory shortcuts being mistaken for final architecture
- Command-every-tick behavior creating visible noise or churn
- Degraded transports being confused with total truth failure
- Stale prose docs drifting away from the live files
- Transitional instrumentation or orphaned helpers being forgotten and misinterpreted later
*(These are runtime-management risks, not necessarily current failure events.)*

## 13. Final Principle

This layer exists so Moose House always has a clear implementation boundary.
- Doc 1 (Startup Canon) tells new sessions what to believe.
- Doc 2 (Reference Map) tells them where to look.
- Doc 3 (Regression Appendix) tells them what not to reinvent.
- Doc 4 (Operations Sheet) tells them whether current doctrine is working.
- Doc 5 (Runtime Layer) tells them what is actually live now.
