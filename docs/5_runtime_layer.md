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
On occasion the operator has manually disabled `automation.v7_5_main_supervisor` (Section 2) during disrupted-sleep nights/days. The verified live Home Assistant entity id is `automation.v7_5_main_supervisor`; this is documented explicitly because HA automation `entity_id`s are runtime entities and must not be inferred solely from the YAML `id:`. Section 1 telemetry continues to write rows in those windows, but the rows reflect operator-managed state, not Section 2 doctrine. Apr 28–May 1 (2026) is the canonical contaminated window: three consecutive days of `LR_HP_Runtime_Today_Hrs = 0.00` with LR truth dropping to 60.3°F while LR was pinned `off@68`. Cold-drift, zero-runtime, or `Section 2 did/did not do X` claims drawn from operator-suppressed windows are category errors. The classification rules and the canonical contaminated window are documented in `docs/telemetry_confounders.md`.

V5.5 rows now carry three forensic-only fields for this classification problem: `Supervisor_Enabled` (`true` when `automation.v7_5_main_supervisor` is `on`, `false` when it is `off`, blank when unknown/unavailable), `Manual_Override_State` (the full state of `timer.manual_hvac_override`), and `Manual_Override_Remaining_Sec` (seconds until the timer's `finishes_at`, blank unless active and never negative). These fields are evidence outputs only. They are not read by Section 2, Section 3, Section 14, truth calculations, setpoints, thresholds, or any control branch.

### 7.7 Apollo / MSR Observability Boundary
Apollo / MSR data (mmWave presence, CO2, DPS310 temperature/pressure, ESP temperature) is observability-only. MSR entities are exported through Section 1 (`vtherm_mega_tracker_v5` → `VTherm_Launch_Data_v5_5`) for forensic analysis but do not feed VTherm room truth, setpoints, the Section 2 supervisor, Section 3 safety gates, Section 7.5 ceiling gates, Section 14 LR boost, or any Samsung guardrail.

There is one documented narrow exception: `binary_sensor.lincoln_msr_radar_zone_3_occupancy` is wrapped by `binary_sensor.lincoln_presence_debounced_v3` (configuration.yaml Section 2) and consumed by Section 6 (`v8_comfort_fan_destratification`) as the variable `lincoln_fan_allowed`. The exception only gates `climate.set_hvac_mode` for `climate.lincoln_air` between `fan_only` and `off`. It is setpoint-neutral and does not touch any safety surface. The full constraints are listed in `docs/apollo_msr_observability_checklist.md` §"Explicit Exception: Lincoln Fan-Only Destratification" and locked by `tests/test_msr_observability_boundary.py`. The exception is not a precedent and does not extend to other rooms or other control surfaces.

### 7.8 Manual Override Contract

`timer.manual_hvac_override` is the household's immediate comfort intent surface. The WAF watcher (`v7_5_waf_manual_override`) is the single legitimate immediate ingest: a parent-less context state change on any of the four climate entities starts the timer.

The contract:

- Comfort-policy automations **should** respect `timer.manual_hvac_override == idle`. Writing climate state while the timer is `active` is a contract violation per `docs/3_regression_appendix.md` §4.15.
- True safety gates (equipment protection, not occupant comfort) **may** override manual intent.
- Ambiguous interlocks require doctrine clarification before they are allowed to override manual intent. See `docs/v9_v10_goals.md` §2.3.

The table below classifies every automation in `automations.yaml` that can write HVAC mode or setpoint (or that is otherwise relevant to override evaluation). Classifications are doctrine, not runtime changes — V9 simplification may move "ambiguous interlock" rows into a definitive class once telemetry evidence and doctrine clarification land, but no row changes runtime behavior in this PR.

| Automation `id` | Section | Writes | Gates on `timer.manual_hvac_override`? | Classification |
|---|---|---|---|---|
| `v7_5_main_supervisor` | 2 | All four climate entities + Nest | Yes (top-level `idle` condition) | Comfort policy |
| `v7_5_safety_ceiling_gates` | 3 | Triggering room (cool 68°F / fan_only) | Yes (`idle` condition) | Comfort policy (76°F is comfort ceiling, not equipment protection) |
| `v8_2_lr_runaway_cooling_cutoff` | 3 | LR off | No | True safety gate (60°F LR equipment protection) |
| `v8_2_master_emergency_floor` | 3 | Master off | No | True safety gate (58°F Master equipment protection) |
| `v9_sleep_priority_interlock` | 3 | LR off when Master cool | No | Canonical ambiguous interlock. Current runtime shape: state triggers (`master→cool`, `LR→heat`), conditions (`master==cool`, `LR==heat`, `LR truth > 60°F`), action (`climate.living_room_air -> off`). No `timer.manual_hvac_override` gate. SPI fire provenance is now observed via Section 15 `spi_last_triggered` (PR #98): each fire produces a row in `hvac_provenance_log` with `automation_candidate = v9_sleep_priority_interlock`. No dedicated logbook tag yet. Doctrine question remains open: comfort policy, compressor-protection gate, or observability-only candidate. |
| `v7_5_waf_manual_override` | 3 | Starts `timer.manual_hvac_override` | N/A (it *is* the contract source) | Manual-intent ingest |
| `v7_5_ghost_assassin` | 4 | Lincoln off at 01:20 (non-heating season) | No | Integration-anomaly gate (Samsung phantom heat suppression). Classification consistency with Section 8 is pending. |
| `v7_5_auto_season_mode` | 5 | `input_select.hvac_season_mode` only | No (downstream supervisor does) | Mode change (indirect). Override respect is via the supervisor's gate. |
| `v8_comfort_fan_destratification` | 6 | fan_only / off on Master, Lincoln, Lilly | Yes | Comfort policy |
| `v8_shade_night_privacy` | 7 | Shade tilt | Parallel `timer.shade_manual_override` | Comfort policy (separate shade contract) |
| `v8_shade_morning_open` | 7 | Shade tilt | Parallel `timer.shade_manual_override` | Comfort policy (separate shade contract) |
| `v8_shade_manual_override` | 7 | Starts `timer.shade_manual_override` | N/A (shade contract source) | Manual-intent ingest (shade) |
| `v8_shade_afternoon_solar_rejection` | 7 | Shade tilt | Parallel `timer.shade_manual_override` | Comfort policy (separate shade contract) |
| `v8_shade_solar_harvest` | 7B | Shade tilt | Parallel `timer.shade_manual_override` | Comfort policy (separate shade contract) |
| `v8_samsung_auto_guardrail` | 8 | Forced off when Samsung auto is rogue | Yes | Integration-anomaly gate (respects manual intent). Classification consistency with Section 4 ghost assassin is pending. |
| `v8_truth_count_alert` | 9 | None (notify only) | N/A | Observability only |
| `v8_3_hvac_transition_log` | 11 | None (logbook only) | N/A | Observability only |
| `v8_4_lr_heating_recovery_boost_engage` | 14 | LR heat@77 | Yes | Comfort policy |
| `v8_4_lr_heating_recovery_boost_release` | 14 | LR off (skipped if override is concurrently active) | Triggers on override active; release action skips climate-off when override is active | Comfort policy (releases gracefully to manual intent) |
| `v8_5_hvac_provenance_logger` | 15 | None (Google Sheets only) | N/A | Observability only |

**Ambiguity status.** `v9_sleep_priority_interlock` (Section 3) and `v7_5_ghost_assassin` (Section 4) are the two paths whose authority over manual intent is currently unproven under the new doctrine. They are recorded here as **ambiguous interlocks** pending forensic recurrence evidence and explicit doctrine clarification per `docs/v9_v10_goals.md` §2.3 and §8. This table records the classification only; no runtime change is proposed in this PR.


#### SPI doctrine note (canonical ambiguous interlock)

`v9_sleep_priority_interlock` is the canonical worked example of an ambiguous interlock and remains classification-only in doctrine.

- **Current trigger shape:** state transitions on `climate.master_bedroom_air -> cool` and `climate.living_room_air -> heat`.
- **Current conditions:** Master must be `cool`, LR must be `heat`, and `sensor.living_room_temperature_truth > 60°F`.
- **Current action:** force `climate.living_room_air -> off`.
- **Current omissions:** no `timer.manual_hvac_override` gate. SPI fire provenance is now observed via Section 15 `spi_last_triggered` (PR #98, closing #88): each fire writes a row to `hvac_provenance_log` with `automation_candidate = v9_sleep_priority_interlock`. A dedicated logbook tag for SPI fires does not exist yet.
- **Doctrine classification question (open):** is SPI (α) comfort policy, (β) compressor/cross-mode protection, or (γ) an observability-only candidate after measurement?

**Candidate positions (no selection yet):**

- **Position α:** SPI is comfort policy and should eventually respect `timer.manual_hvac_override`.
- **Position β:** SPI is compressor/cross-mode protection and may remain authoritative over manual intent.
- **Position γ:** SPI should become observability-only if telemetry shows intervention is rare or low-value.

**Evidence required before choosing α/β/γ:**

1. SPI fire frequency.
2. Whether LR heat at fire time was manual or supervisor-driven.
3. Whether Master cool at fire time was manual or supervisor-driven.
4. Whether SPI correlates with measurable equipment or comfort benefit.
5. At least 3 logged SPI fire events from the Section 15 `spi_last_triggered` observer (PR #98, closing #88).

No runtime classification change is selected in this document, and no runtime PR is recommended until the accumulated `hvac_provenance_log` rows from the Section 15 `spi_last_triggered` observer (PR #98) provide enough evidence to answer the α/β/γ question above.

**Doctrine notes.**

- The 76°F ceiling gate is comfort, not equipment protection. It correctly gates on override.
- Samsung Auto Guardrail (Section 8) and Ghost Assassin (Section 4) are both integration-anomaly gates protecting against known device misbehavior, but they disagree on whether to gate on override. Picking a consistent rule is V9 doctrine work, not a runtime change.
- Section 14 boost release is the canonical example of a comfort-policy automation that *yields* to manual intent rather than fighting it: when the override timer goes `active`, release fires and the release path skips the climate-off command if override is still active.

### 7.9 Planned Comfort-Profile and Truth-Confidence Model (NOT YET LIVE)

This subsection records *planned* doctrine from
[`comfort_band_and_truth_confidence_plan.md`](comfort_band_and_truth_confidence_plan.md)
(accepted in PR #122). **None of it is live runtime.** It is documented here so
the runtime boundary is explicit and future agents do not mistake the plan for
implementation. The live control layer remains V8.3 and the live truth layer
remains V3.1, exactly as described in §5 and §6 above.

**Comfort bands, not thermostat targets.** Moose House controls with comfort
bands / deadbands. The system holds while room truth is inside the active band
and acts only on band exit. The commanded Samsung / mini-split setpoint is an
actuator demand, not comfort truth — it already is in the live supervisor
(`automations.yaml` Section 2 comments), and the planned model keeps it that
way. Samsung's preferred 72–75°F is not comfort truth for this house.

**Runtime shove command scope.** Section 2 now uses Samsung saturation command
setpoints on existing mini-split command paths only: cooling commands shove to
61°F and heating commands shove to 79°F. The room is not intended to reach those
values; the existing Moose House room-truth start/stop thresholds still decide
when to run and when to shut down. Runtime house-wide arbitration,
destratification changes, comfort profiles, watchdog changes, and live truth
confidence/status sensors remain deferred.

**Comfort bands are preferences; safety gates are physical protection.** Comfort
bands are tunable household preference. Section 3 safety gates (LR runaway
60°F, Master emergency floor 58°F) are absolute equipment protection and stay
separate. A comfort band may never be defined as a safety gate, and a comfort
threshold may never alias a safety floor. The 76°F ceiling is a comfort ceiling
(see §7.8 doctrine notes), not a safety invariant.

**Planned comfort profiles (single global selector first; per-room deferred):**

| Profile | Intent |
|---|---|
| `eric_cold` | Meat-locker; coldest comfort profile; Eric's default preference. |
| `family_normal` | Normal household comfort. Closest to the current live bands. |
| `sleep_cold` | Sleep-window cold profile; room-specific (Master) application deferred. |
| `away_relaxed` | House protection / energy savings, not comfort optimization. |
| `safety_only` | Comfort bands disabled; only Section 3 emergency cutoffs and structural protection remain. |

Draft band numbers in the plan doc are non-binding. A band-number change is a
separate, evidence-gated runtime PR per [`v9_v10_goals.md`](v9_v10_goals.md) §10.

**Planned truth-confidence outputs (per room, not yet built):**
`sensor.<room>_temperature_truth_confidence` (numeric) and
`sensor.<room>_temperature_truth_status` with the four-state ladder:

| Status | Rule |
|---|---|
| `healthy` | 2+ valid **primary** sources (Matter / Bluetooth / SmartThings) fresh and within tolerance. |
| `degraded` | exactly one valid primary source, or primary + fallback only. |
| `fallback` | only Samsung/mini-split internal or held-last-good remains. **Never `healthy`.** |
| `failed` | no usable source. |

Source classes: **primary** = human-space Matter / BT / SmartThings (current
weight 0.9–1.0); **fallback** = Samsung internal thermistor (weight 0.20,
always biased); **experimental / observability-only** = Apollo / MSR / ESP
temperature, DPS310, CO2, radar, pressure — these never feed the weighted value
and never raise confidence to `healthy`, preserving the §7.7 observability
boundary.

**Three invariants that are doctrine now (runtime deferred):**

1. Samsung/mini-split-only truth must never be `healthy` (today's
   `availability` cliff counts the Samsung internal as a valid source, which is
   the gap this model closes).
2. An unavailable ESP/Apollo source must not equal total truth failure when
   Matter / Bluetooth / SmartThings remain available — partial degradation must
   not collapse into `failed` (consistent with Startup Canon §4 and §6).
3. A stable temperature sensor must not be treated as stale merely because its
   value did not change. **LANDED:** the live truth templates now measure
   freshness by report time (`last_reported`) instead of value-change time
   (`last_changed`), so an unchanging-but-reporting sensor is no longer
   false-staled. The 2-hour (`max_age = 7200`) temperature/humidity window and
   the 3-hour (`10800`) CO2 window are unchanged; only the freshness clock
   moved. `last_updated` was rejected as the clock because it also fails to
   advance when a stable sensor reports an unchanged value with unchanged
   attributes. `automations.yaml` still uses `climate.*.last_changed` for
   state-duration (how long a unit has held a mode) — that is value-transition
   measurement, not reporting freshness, and is correctly left unchanged.

**Regression guardrails:**
`tests/test_comfort_band_safety_separation.py` locks the comfort-vs-safety
separation and the 60°F/58°F floors; `tests/test_truth_confidence_model_contract.py`
locks the four-state ladder as a pure model contract and asserts the live
config uses report-time freshness; `tests/test_truth_freshness_report_time.py`
locks the freshness clock (config uses `last_reported`, never `last_changed`;
`automations.yaml` untouched; CO2/temperature windows and weights preserved).

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
