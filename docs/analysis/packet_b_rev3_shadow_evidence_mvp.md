# Packet B Revision 3 — Shadow Evidence MVP

```
═══════════════════════════════════════════════════════════════
PACKET B — ARCHITECTURE REVIEW (REVISION 3)
Moose House HVAC — Temperature Input Path: Shadow Evidence MVP
═══════════════════════════════════════════════════════════════

Author:    Fable (control-system architect)
Supersedes: Packet B Revision 2 (docs/analysis/packet_b_filter_model_revision.md)
Date:      2026-06-10
Status:    Design document. No runtime YAML changes proposed here.
           Codex implementation handoff provided in §13.
═══════════════════════════════════════════════════════════════
```

---

## 0. Supersession and Scope Narrowing

Revision 2 established two correct findings that survive unchanged:

1. The HA lowpass filter is event-driven — `y[n] = 0.9·y[n−1] + 0.1·x[n]` — not
   elapsed-time-based. Convergence depends on accepted-event rate, which is unmeasured.
2. The final raw-versus-filtered routing decision remains blocked on native replay evidence.

The Revision 2 blanket conclusion — "no implementation prompt until replay is complete" — was
correct for any *authoritative input-path migration* but was over-broad. It also blocked a
non-controlling MVP whose only purpose is to produce the missing evidence.

This revision narrows the block. The block remains in force for any change that:
- switches a live control consumer to filtered truth, OR
- repoints a live safety consumer away from raw truth.

The block does **not** apply to a non-controlling MVP that:
- preserves every existing raw-truth control path unchanged, AND
- adds read-only shadow instrumentation for evidence collection, AND
- corrects objectively false documentation.

This document designs that MVP at implementation-handoff detail. It does not implement it.

---

## 1. Purpose and Staged-Product Rationale

### 1.1 The evidence gap the MVP closes

The replay specification in Revision 2 §3 requires native-granularity event sequences for:

- `sensor.{lr,master,lincoln,lilly}_temperature_truth` (accepted-event stream, not 15-min snapshots)
- `sensor.*_temperature_smoothed` (cross-validation target)
- `sensor.*_temperature_control` (wrapper pass-through)
- Supervisor execution timestamps (`automation.v7_5_main_supervisor` logbook events)
- Decision gate inputs at each tick: season, away, night/sleep modes, override state

The existing 15-minute Google Drive export (`VTherm_Launch_Data_v5_5`) provides background
context and confirms the live routing picture but cannot reproduce the event-count filter
dynamics. The accepted-event sequence is what determines how quickly `y[n]` converges after a
temperature step — the core unknown — and it can only be measured from the native HA recorder.

### 1.2 The product decision

Packet B may ship as a safe MVP that:

1. Preserves all current raw-truth control behavior without change.
2. Preserves all raw-truth safety routes without change.
3. Corrects the three known documentation contradictions identified in §1 of Revision 2.
4. Adds a read-only shadow evaluator computing the supervisor decision that *would* have been
   made from filtered truth at each evaluation.
5. Ensures the shadow path cannot issue climate commands or alter any control state.
6. Records sufficient native-granularity evidence for the later replay and final routing decision.
7. Establishes an evidence checkpoint and later Fable review.

### 1.3 What this MVP is not

- It is not a final architecture decision.
- It is not evidence that Option A (raw truth permanently) has won.
- It is not a claim that filtered truth is better.
- It does not weaken, replace, or duplicate any Packet A behavior.
- It does not change any threshold, cadence, helper semantics, or override contract.

---

## 2. Current Behavior Preserved

### 2.1 Raw-truth supervisor route

The V8.3 supervisor (`automations.yaml`, automation id `v7_5_main_supervisor`, Section 2) reads:

```yaml
variables:
  outdoor:      "{{ states('sensor.deck_temperature_truth')          | float(50) }}"
  lr_temp:      "{{ states('sensor.living_room_temperature_truth')   | float(70) }}"
  master_temp:  "{{ states('sensor.master_bedroom_temperature_truth')| float(70) }}"
  lincoln_temp: "{{ states('sensor.lincoln_s_room_temperature_truth')| float(70) }}"
  lilly_temp:   "{{ states('sensor.lilly_s_room_temperature_truth')  | float(70) }}"
```

These are the four live controlled-zone raw truth entities. The supervisor does not reference
`sensor.*_temperature_smoothed` or `sensor.*_temperature_control` in any branch.

The MVP preserves this variables block exactly. No variable is added, renamed, or redirected.

This is documented as: **preserved MVP runtime behavior, not permanent architecture doctrine,
and not evidence that Option A has won.**

### 2.2 Raw-truth safety routes

The following safety automations read raw truth directly and are unchanged by the MVP:

| Automation id | Entity read | Threshold |
|---|---|---|
| `v8_2_lr_runaway_cooling_cutoff` | `sensor.living_room_temperature_truth` | < 60°F |
| `v8_2_master_emergency_floor` | `sensor.master_bedroom_temperature_truth` | < 58°F |
| `v7_5_safety_ceiling_gates` | Zone truth entities | > 76°F |
| `v7_5_ghost_assassin` | `sensor.lincoln_s_room_temperature_truth` | state trigger |
| `v9_sleep_priority_interlock` | `sensor.living_room_temperature_truth` | > 60°F condition |

The MVP adds no shadow routing to any of these paths. Their `numeric_state` and
`state` triggers remain pointed at raw truth. The event-driven filter introduces
unbounded wall-clock lag in frozen-lag mode; this makes raw truth more important for
safety, not less.

### 2.3 Preserved behavior is not a doctrine claim

Documenting the current raw-truth route as preserved behavior does not:
- Declare Option A the final winner.
- Prohibit a future migration to filtered truth after evidence supports it.
- Prohibit the final Fable review from selecting Option B or C.
- Establish raw truth as a permanent invariant beyond the MVP observation window.

The MVP is a staging platform for evidence collection. The final routing decision follows
the evidence. All existing architecture constraints from Revision 2 §4 survive.

---

## 3. MVP Architecture

### 3.1 Overview

```
Physical Sensors
  │
  ▼
Truth Sensors  ──── Safety Automations (read raw, unchanged)
  │               ──── Main Supervisor V8.3 (reads raw, unchanged)
  │               ──── 15-min V5.5 telemetry export (reads raw, unchanged)
  │
  ▼
Smoothed Sensors  ──── Shadow Template Sensors (§3.3, read-only)
  │                    │
  ▼                    ▼
Control Wrappers  ──── Shadow Observation Automation (§3.3, logbook only)
  │
  ▼
UI / Dashboard (unchanged)

Shadow layer:
  ─── reads smoothed/control entities and gate inputs (read-only)
  ─── writes nothing outside logbook events and its own template sensors
  ─── never issues climate.set_hvac_mode or climate.set_temperature
  ─── never modifies helpers, timers, overrides, or presets
```

### 3.2 Current control path (component A — unchanged)

All existing automations remain exactly as deployed:

| Component | File | Section | Read entities | Write entities | Status |
|---|---|---|---|---|---|
| Main supervisor | automations.yaml | 2 | raw truth (4 zones + deck) | climate.* | Unchanged |
| Safety gates | automations.yaml | 3 | raw truth | climate.* | Unchanged |
| Ghost Assassin | automations.yaml | 4 | raw truth | climate.lincoln_air | Unchanged |
| Section 14 boost | automations.yaml | 14 | raw truth, helpers | climate.living_room_air | Unchanged |
| Provenance logger | automations.yaml | 15 | climate.*, helpers | Google Sheets | Unchanged |
| Smoothed sensors | configuration.yaml | 12 | raw truth → lowpass | sensor.*_smoothed | Unchanged |
| Control wrappers | configuration.yaml | 10 | smoothed sensors | sensor.*_control | Unchanged |
| V5.5 telemetry export | automations.yaml | 1 | all truth/climate/helpers | Google Sheets | Unchanged |

### 3.3 Shadow evaluator layer (component B — new, read-only)

Two new constructs, both observational only:

**B1 — Shadow template sensors** (configuration.yaml, new Section 16)

For each controlled zone (LR, Master, Lincoln, Lilly): a set of read-only template sensors
that compute and expose the shadow filtered decision and divergence classification. These
sensors update reactively and are recorded by HA's native recorder. They do not issue any
service calls and cannot become supervisor inputs.

New entity IDs (per zone, LR shown; apply same pattern to master, lincoln, lilly):

| Entity | Role |
|---|---|
| `sensor.lr_shadow_filtered_decision` | cool/off/hold from filtered truth |
| `sensor.lr_shadow_raw_decision` | cool/off/hold from raw truth (computed in shadow, for cross-check) |
| `sensor.lr_shadow_divergence` | "same" or "different" |
| `sensor.lr_shadow_raw_threshold_distance` | (raw_truth − active_on_threshold), signed °F |
| `sensor.lr_shadow_filtered_threshold_distance` | (filtered_truth − active_on_threshold), signed °F |
| `sensor.lr_shadow_raw_value` | raw truth captured at evaluation instant |
| `sensor.lr_shadow_filtered_value` | control wrapper value captured at evaluation instant |

These seven sensors × four zones = 28 new observational entities. No existing entity is
modified. None is referenced by any existing automation.

**B2 — Shadow observation automation** (automations.yaml, new Section 17)

A single new automation (`id: v_shadow_evaluator`) that:
- Triggers on `time_pattern minutes: "/15"` (aligned with supervisor cadence) and `homeassistant: start`
- Uses a variables block that mirrors the supervisor's variables block exactly (same entity reads,
  same gate inputs — season, away, night/sleep modes, override state, boost active)
- Computes the shadow filtered decision for each zone using the same decision function as the
  supervisor but substituting `sensor.*_temperature_control` for `sensor.*_temperature_truth`
- Issues one `logbook.log` action per evaluation with a structured payload (§5.1)
- Issues zero `climate.*`, zero `input_boolean.*`, zero `timer.*`, zero `input_datetime.*` calls

The shadow automation never becomes an input to the live supervisor. It reads the same gate
inputs the supervisor reads but writes only to the logbook.

### 3.4 Evidence collection layer (component C — recorder + logbook)

The native HA recorder already captures state-change events for `sensor.*_temperature_truth`,
`sensor.*_temperature_smoothed`, and `sensor.*_temperature_control` at native event granularity.
What the MVP adds:

1. Explicit recorder `include` for all shadow template sensors (§5.5).
2. Recorder purge retention verification (minimum 14 days for the evidence window).
3. Supervisor execution timestamp preservation (logbook entries from `automation.v7_5_main_supervisor`).
4. Shadow observation automation logbook events (§5.1).
5. Event-level export specification (extension to `ha_nuisance_export.md` tooling — §5.6).

---

## 4. Shadow Decision Contract

### 4.1 Entity catalogue

**Inputs consumed by shadow automation (read-only):**

```
sensor.living_room_temperature_truth          # raw truth, same as supervisor
sensor.master_bedroom_temperature_truth
sensor.lincoln_s_room_temperature_truth
sensor.lilly_s_room_temperature_truth
sensor.deck_temperature_truth                 # outdoor, for shoulder branch

sensor.living_room_temperature_control        # filtered input (pass-through of smoothed)
sensor.master_bedroom_temperature_control
sensor.lincoln_s_room_temperature_control
sensor.lilly_s_room_temperature_control

input_select.hvac_season_mode                 # gate input
input_boolean.away_mode                       # gate input
input_boolean.night_mode_lr_primary           # gate input (LR)
timer.manual_hvac_override                    # gate input (override state)
input_boolean.lr_heating_recovery_boost_active # gate input (LR boost)

climate.living_room_air                       # current mode (read-only, for hold detection)
climate.master_bedroom_air
climate.lincoln_air
climate.lilly_air
```

**Outputs produced by shadow (write-only surfaces):**

```
logbook.log (structured events from Section 17 automation)
sensor.lr_shadow_*  (template sensors, configuration.yaml Section 16 — recorder only)
sensor.master_shadow_*
sensor.lincoln_shadow_*
sensor.lilly_shadow_*
```

**Explicitly never written by shadow:**

```
climate.living_room_air        # FORBIDDEN
climate.master_bedroom_air     # FORBIDDEN
climate.lincoln_air            # FORBIDDEN
climate.lilly_air              # FORBIDDEN
climate.dining_room            # FORBIDDEN
input_boolean.*                # FORBIDDEN (all helpers)
timer.*                        # FORBIDDEN (all timers)
input_datetime.*               # FORBIDDEN (all timestamps)
input_select.*                 # FORBIDDEN (all selects)
input_text.*                   # FORBIDDEN (all text helpers)
sensor.*_temperature_truth     # FORBIDDEN (not writable; belt-and-suspenders)
sensor.*_temperature_smoothed  # FORBIDDEN (not writable; belt-and-suspenders)
```

### 4.2 Per-evaluation record (captured in logbook event and template sensors)

At every shadow evaluation (every 15-minute tick), the following fields are captured
per controlled zone:

| Field | Type | Source entity |
|---|---|---|
| `eval_timestamp` | ISO8601 | `now()` in automation |
| `zone` | string (lr/master/lincoln/lilly) | literal |
| `raw_truth` | float \| null | `sensor.<zone>_temperature_truth` |
| `smoothed_value` | float \| null | `sensor.<zone>_temperature_smoothed` |
| `control_wrapper_value` | float \| null | `sensor.<zone>_temperature_control` |
| `active_on_threshold` | float | computed from gate inputs |
| `active_off_threshold` | float | computed from gate inputs |
| `season_mode` | string | `input_select.hvac_season_mode` |
| `away_state` | bool | `input_boolean.away_mode` |
| `night_mode_lr` | bool | `input_boolean.night_mode_lr_primary` (LR only, else null) |
| `sleep_window_active` | bool | time-based (18:00–06:00 for Master) |
| `manual_override_state` | string (idle/active/paused) | `timer.manual_hvac_override` |
| `lr_boost_active` | bool | `input_boolean.lr_heating_recovery_boost_active` (LR only) |
| `current_climate_mode` | string | `climate.<zone>_air` state |
| `raw_decision` | string (cool/off/hold) | computed from raw_truth + thresholds |
| `shadow_filtered_decision` | string (cool/off/hold) | computed from control_wrapper_value + same thresholds |
| `divergence` | string (same/different) | raw_decision vs shadow_filtered_decision |
| `divergence_direction` | string (none/raw_more_aggressive/filtered_more_aggressive) | derived |
| `raw_threshold_distance_on` | float \| null | raw_truth − active_on_threshold |
| `raw_threshold_distance_off` | float \| null | raw_truth − active_off_threshold |
| `filtered_threshold_distance_on` | float \| null | control_wrapper_value − active_on_threshold |
| `filtered_threshold_distance_off` | float \| null | control_wrapper_value − active_off_threshold |
| `raw_truth_available` | bool | raw_truth is not unknown/unavailable/non-numeric |
| `filtered_truth_available` | bool | control_wrapper_value is available |

### 4.3 Decision function specification

The shadow evaluator must implement the same decision function as the V8.3 supervisor for
the cooling and shoulder branches. Active thresholds are determined by gate inputs in this
priority order:

```
for each zone:
  1. If manual_override_state == "active": record hold; do not compute shadow decision.
     (The supervisor gates on override; the shadow gates identically.)

  2. Determine active thresholds:
     if away_mode:
       on_at = 76, off_at = 74    # all zones, all seasons
     elif zone == "master" and sleep_window_active (18:00–06:00):
       on_at = 66, off_at = 62    # master sleep window
     elif zone == "lr" and night_mode_lr:
       on_at = 72, off_at = 64    # LR stack-effect reduction period
     else:
       on_at = 72, off_at = 68    # standard day cooling (all zones)

  3. Compute raw_decision:
     if raw_truth > on_at:        cool
     elif raw_truth <= off_at:    off
     else:                        hold

  4. Compute shadow_filtered_decision:
     if control_wrapper_value is unavailable: mark filtered_unavailable, skip
     if control_wrapper_value > on_at:        cool
     elif control_wrapper_value <= off_at:    off
     else:                                    hold

  5. Divergence = "different" if raw_decision != shadow_filtered_decision else "same"

  6. divergence_direction:
     if divergence == "same": none
     if raw == "cool" and filtered == "hold/off": raw_more_aggressive
     if raw == "off"  and filtered == "hold/cool": filtered_more_aggressive
     if raw == "hold" and filtered == "cool":      filtered_more_aggressive
     if raw == "hold" and filtered == "off":       raw_more_aggressive
     (cool > hold > off in aggressiveness ordering)
```

**Note on heating branches:** The MVP targets evidence collection for the cooling
architecture decision. The shadow evaluator computes cooling-branch decisions only.
Heating and shoulder-heating branches do not produce divergence evidence useful for the
filtered-versus-raw cooling debate. If `season_mode` is `heating` and no cooling branch
applies, the shadow evaluator logs the gate inputs and records `decision = not_applicable`.

### 4.4 Forbidden operations (absolute list)

The shadow automation and shadow template sensors must not:

- Call `climate.set_hvac_mode` on any entity.
- Call `climate.set_temperature` on any entity.
- Write any `input_boolean`, `input_select`, `input_text`, or `input_datetime` entity.
- Start, cancel, or pause any `timer.*` entity.
- Write to `hvac_provenance_log` (Packet A + V9 provenance territory).
- Write to `VTherm_Launch_Data_v5_5` or any Google Sheets worksheet.
- Become an input to the live supervisor, any safety automation, or any comfort-policy automation.
- Gate, block, or delay the live supervisor evaluation.
- Set availability state of any existing entity.
- Run as a prerequisite or dependency for any existing automation.

If the shadow automation is disabled, deleted, or fails, none of the above behaviors change.

### 4.5 Failure mode behavior

The shadow evaluator must fail observationally:

- If `control_wrapper_value` is unavailable: log `filtered_unavailable = true`; skip
  shadow decision computation; do not fall back to raw truth; do not log a shadow decision.
- If raw truth is unavailable: log `raw_unavailable = true`; compute shadow from filtered
  if available; log raw decision as `unavailable`.
- If any gate input (season, away, override) is unavailable: log `gate_input_unavailable = true`
  and which input; skip shadow decision for that zone; do not skip supervisor evaluation.
- If the logbook call fails (HA service unavailable): log failure is lost silently. The shadow
  automation's own error does not propagate to the supervisor. The template sensors continue
  updating from their Jinja2 templates regardless of the automation's success.
- Template sensor `availability` is false only when the underlying entity referenced in the
  template is unavailable. Template sensors never reflect the supervisor's availability state.

---

## 5. Evidence Schema

### 5.1 Logbook event structure

The shadow observation automation (Section 17) emits one structured logbook event per
evaluation using `logbook.log` with:

```yaml
name: "shadow_evaluator"
message: >-
  {
    "ts": "{{ now().isoformat() }}",
    "zones": {
      "lr": {
        "raw": {{ lr_raw }},
        "smoothed": {{ lr_smoothed }},
        "control": {{ lr_control }},
        "on_at": {{ lr_on_at }},
        "off_at": {{ lr_off_at }},
        "raw_decision": "{{ lr_raw_decision }}",
        "shadow_decision": "{{ lr_shadow_decision }}",
        "divergence": "{{ lr_divergence }}",
        "divergence_dir": "{{ lr_divergence_dir }}",
        "raw_dist_on": {{ lr_raw_dist_on }},
        "filt_dist_on": {{ lr_filt_dist_on }}
      },
      "master": { ... same structure ... },
      "lincoln": { ... same structure ... },
      "lilly":   { ... same structure ... }
    },
    "gates": {
      "season": "{{ season }}",
      "away": {{ away }},
      "night_lr": {{ night_lr }},
      "override": "{{ override }}",
      "lr_boost": {{ lr_boost }},
      "sleep_window_master": {{ sleep_master }}
    },
    "raw_available": {{ raw_available }},
    "filtered_available": {{ filtered_available }}
  }
entity_id: sensor.living_room_temperature_truth
```

The `entity_id` field is set to `sensor.living_room_temperature_truth` so the logbook entry is
anchored to a real entity (required by `logbook.log`). The logbook entry does not modify the
entity's state.

### 5.2 Template sensor recorder values

The 28 shadow template sensors (§3.3 B1) are recorded automatically by HA's native recorder
whenever their state changes. These provide a time-series history queryable via the HA recorder
database (not only via logbook search). The recorder captures:

- `sensor.lr_shadow_filtered_decision` — cool/off/hold/unavailable
- `sensor.lr_shadow_raw_decision` — cool/off/hold/unavailable
- `sensor.lr_shadow_divergence` — same/different/unavailable
- `sensor.lr_shadow_raw_threshold_distance` — signed float
- `sensor.lr_shadow_filtered_threshold_distance` — signed float
- `sensor.lr_shadow_raw_value` — float snapshot
- `sensor.lr_shadow_filtered_value` — float snapshot

(× 4 zones = 28 entities)

### 5.3 What existing telemetry already provides

The `VTherm_Launch_Data_v5_5` Google Sheets export already captures at 15-minute intervals:

| Field | Column | Sufficient for replay? |
|---|---|---|
| Raw truth per zone | `LR_Temp_Truth`, `Master_Temp_Truth`, `Lincoln_Temp_Truth`, `Lilly_Temp_Truth` | No — 15-min snapshots miss inter-tick event counts |
| Climate mode per zone | `LR_Air_Mode`, `Master_Air_Mode`, etc. | Background only |
| Season mode | `Season_Mode` | Yes |
| Away mode | `Away_Mode` | Yes |
| Manual override state | `Manual_Override_State`, `Manual_Override_Remaining_Sec` | Background |
| Supervisor enabled | `Supervisor_Enabled` | Background |
| Section 14 boost state | `Section14_Boost_Active` etc. | Background |

What is **not sufficient** from V5.5:

- The inter-tick accepted-event sequence for truth entities (needed to simulate `y[n]`).
- The smoothed/control values at native event granularity (not just at 15-min ticks).
- Supervisor execution timestamps (not in V5.5; only in logbook).
- Shadow decision and divergence data (does not yet exist).
- `unknown`/`unavailable` transitions with timestamps (V5.5 blanks these, losing transition timing).

### 5.4 What the recorder provides and what needs verification

**Already in recorder (standard HA behavior):**

- State-change events for all `sensor.*_temperature_truth` entities at native granularity.
- State-change events for all `sensor.*_temperature_smoothed` and `sensor.*_temperature_control`
  entities at native granularity (these update whenever their computed values change).
- `unknown`/`unavailable` state transitions with `last_updated` timestamps.
- `automation.v7_5_main_supervisor` state changes (useful for execution timing).

**Requires verification before evidence window opens:**

1. **Recorder purge_keep_days**: Must be ≥ 14 days for the evidence window. Default HA is 10.
   If set to 10, the recorder must be configured to at least 14 for the evidence period.
   This is a one-line configuration change to `recorder:` in `configuration.yaml`.

2. **Entity include list**: Verify that `sensor.*_temperature_smoothed`, `sensor.*_temperature_control`,
   and the 28 new shadow entities are not excluded by a recorder `exclude` block.
   If an `exclude` block exists, add explicit includes.

3. **Supervisor logbook entries**: Verify that `automation.v7_5_main_supervisor` logbook entries
   survive the retention window. Logbook and recorder may have different retention settings.

4. **`last_reported` vs `last_updated` in recorder**: The replay procedure requires distinguishing
   value-change events from re-report events. `last_reported` is available in the recorder
   `states` table as the `last_reported` column (added in HA 2023.x+). Verify the recorder
   schema includes this column before relying on it for replay.

### 5.5 Recorder configuration requirements

Add to `configuration.yaml` recorder section (existing block, additive only):

```yaml
recorder:
  purge_keep_days: 14   # increase from default if currently lower
  include:
    entities:
      # Shadow evaluator entities (new Section 16)
      - sensor.lr_shadow_filtered_decision
      - sensor.lr_shadow_raw_decision
      - sensor.lr_shadow_divergence
      - sensor.lr_shadow_raw_threshold_distance
      - sensor.lr_shadow_filtered_threshold_distance
      - sensor.lr_shadow_raw_value
      - sensor.lr_shadow_filtered_value
      - sensor.master_shadow_filtered_decision
      - sensor.master_shadow_raw_decision
      - sensor.master_shadow_divergence
      - sensor.master_shadow_raw_threshold_distance
      - sensor.master_shadow_filtered_threshold_distance
      - sensor.master_shadow_raw_value
      - sensor.master_shadow_filtered_value
      - sensor.lincoln_shadow_filtered_decision
      - sensor.lincoln_shadow_raw_decision
      - sensor.lincoln_shadow_divergence
      - sensor.lincoln_shadow_raw_threshold_distance
      - sensor.lincoln_shadow_filtered_threshold_distance
      - sensor.lincoln_shadow_raw_value
      - sensor.lincoln_shadow_filtered_value
      - sensor.lilly_shadow_filtered_decision
      - sensor.lilly_shadow_raw_decision
      - sensor.lilly_shadow_divergence
      - sensor.lilly_shadow_raw_threshold_distance
      - sensor.lilly_shadow_filtered_threshold_distance
      - sensor.lilly_shadow_raw_value
      - sensor.lilly_shadow_filtered_value
      # Ensure these are not excluded (they should already be recorded)
      - sensor.living_room_temperature_smoothed
      - sensor.master_bedroom_temperature_smoothed
      - sensor.lincoln_s_room_temperature_smoothed
      - sensor.lilly_s_room_temperature_smoothed
      - sensor.living_room_temperature_control
      - sensor.master_bedroom_temperature_control
      - sensor.lincoln_s_room_temperature_control
      - sensor.lilly_s_room_temperature_control
```

If the current recorder config uses an `exclude` block rather than `include`, verify
that none of the entities above appear in the exclude list.

### 5.6 Export tooling

The existing `tools/export_ha_nuisance_evidence.ps1` and `docs/ha_nuisance_export.md` export
tooling produces wide-table 15-minute snapshots. For replay purposes, the tooling must be
extended to also export:

**New export: event-level recorder dump**

For each entity in §5.4 (truth, smoothed, control) plus the 28 shadow entities:

```sql
SELECT
  s.entity_id,
  s.state,
  s.last_updated,
  s.last_reported,
  s.last_changed,
  sm.entity_id AS entity_id_confirmed
FROM states s
JOIN states_meta sm ON s.metadata_id = sm.metadata_id
WHERE sm.entity_id IN (
  'sensor.living_room_temperature_truth',
  'sensor.master_bedroom_temperature_truth',
  'sensor.lincoln_s_room_temperature_truth',
  'sensor.lilly_s_room_temperature_truth',
  'sensor.living_room_temperature_smoothed',
  'sensor.master_bedroom_temperature_smoothed',
  'sensor.lincoln_s_room_temperature_smoothed',
  'sensor.lilly_s_room_temperature_smoothed',
  'sensor.living_room_temperature_control',
  'sensor.master_bedroom_temperature_control',
  'sensor.lincoln_s_room_temperature_control',
  'sensor.lilly_s_room_temperature_control',
  'sensor.lr_shadow_filtered_decision',
  'sensor.lr_shadow_raw_decision',
  'sensor.lr_shadow_divergence',
  -- ... (all 28 shadow entities)
  'automation.v7_5_main_supervisor'
)
AND s.last_updated >= [window_start]
AND s.last_updated <= [window_end]
ORDER BY s.last_updated ASC;
```

This produces the event sequence needed for `y[n] = round(0.9·y[n−1] + 0.1·x[n], 2)` replay
and cross-validation. The export must not resample to 15-minute intervals — the per-event
`last_updated` timestamps are the object of study.

The extension to the PS1 script should be a new `-EventLevel` flag that produces a separate
CSV file alongside the existing wide-table export, not a replacement.

---

## 6. Home Assistant Implementation Surfaces

### 6.1 Recommended approach: template sensors + observational automation

**Chosen:** Template sensors (configuration.yaml Section 16) + observational automation
(automations.yaml Section 17).

**Why template sensors for shadow decisions:**
- HA-native: computed reactively; no additional HA integration required.
- Recorder-compatible: state changes are automatically captured by the recorder.
- Inspectable: visible in the HA UI, accessible in history graphs.
- Failure-safe: if a referenced entity is unavailable, the template sensor becomes
  unavailable rather than returning a stale value.
- No service calls: template sensors in `sensor:` blocks cannot issue climate services.

**Why observational automation for tick-level evidence:**
- Matches supervisor cadence exactly (same `time_pattern minutes: "/15"` trigger).
- Captures all gate inputs at the exact evaluation instant, not continuously.
- Produces structured, timestamped logbook events correlated to supervisor ticks.
- The YAML `action:` block is auditable — a test can verify no `climate.*` calls exist.

**Alternatives considered and rejected:**

| Approach | Reason rejected |
|---|---|
| Event logging only (no template sensors) | Logbook events are not queryable via recorder; retention may be shorter |
| Google Sheets logging from shadow | Adds live runtime dependency on external service — explicitly prohibited |
| AppDaemon / custom component | Outside repository scope; requires additional infrastructure |
| Template sensors only (no automation) | Loses exact tick-level correlation; template updates are continuous, not tick-gated |
| Recorder entities via `recorder_stats` | No HA-native "push structured record per tick" mechanism without automation |

### 6.2 Section 16: Shadow template sensors (configuration.yaml)

Add a new labeled block after Section 15 (provenance logger) in the `template:` list:

```yaml
      # =========================================================
      # SECTION 16: SHADOW EVALUATOR — READ-ONLY EVIDENCE SENSORS
      # =========================================================
      # ⚠️  DO NOT DELETE without reading docs/analysis/packet_b_rev3_shadow_evidence_mvp.md
      # PURPOSE: Captures the supervisor decision that WOULD have been made from
      #          filtered truth at each evaluation, for post-hoc divergence analysis.
      #          These sensors are OBSERVATIONAL ONLY. They do not feed the
      #          supervisor, safety automations, or any control path.
      # READS:   sensor.*_temperature_truth, sensor.*_temperature_control,
      #          gate helpers (season, away, night_mode, override)
      # WRITES:  nothing (template sensors are read-only by definition)
      # RECORDED: yes — see recorder include block
      # =========================================================

      # LR Shadow Block
      - name: "LR Shadow Filtered Decision"
        unique_id: lr_shadow_filtered_decision_v1
        state: >
          {%- set ft = states('sensor.living_room_temperature_control') | float(none) -%}
          {%- set away = is_state('input_boolean.away_mode', 'on') -%}
          {%- set season = states('input_select.hvac_season_mode') -%}
          {%- set outdoor = states('sensor.deck_temperature_truth') | float(50) -%}
          {%- set cooling_active = season == 'cooling' or (season == 'shoulder' and outdoor > 70) -%}
          {%- if ft is none -%}unavailable
          {%- elif not cooling_active -%}not_applicable
          {%- elif away -%}
            {%- if ft > 76 -%}cool{%- elif ft <= 74 -%}off{%- else -%}hold{%- endif -%}
          {%- else -%}
            {%- if ft > 72 -%}cool{%- elif ft <= 68 -%}off{%- else -%}hold{%- endif -%}
          {%- endif -%}
        availability: >
          {{ states('sensor.living_room_temperature_control') not in ['unknown', 'unavailable'] }}

      - name: "LR Shadow Raw Decision"
        unique_id: lr_shadow_raw_decision_v1
        state: >
          {%- set rt = states('sensor.living_room_temperature_truth') | float(none) -%}
          {%- set away = is_state('input_boolean.away_mode', 'on') -%}
          {%- set season = states('input_select.hvac_season_mode') -%}
          {%- set outdoor = states('sensor.deck_temperature_truth') | float(50) -%}
          {%- set cooling_active = season == 'cooling' or (season == 'shoulder' and outdoor > 70) -%}
          {%- if rt is none -%}unavailable
          {%- elif not cooling_active -%}not_applicable
          {%- elif away -%}
            {%- if rt > 76 -%}cool{%- elif rt <= 74 -%}off{%- else -%}hold{%- endif -%}
          {%- else -%}
            {%- if rt > 72 -%}cool{%- elif rt <= 68 -%}off{%- else -%}hold{%- endif -%}
          {%- endif -%}
        availability: >
          {{ states('sensor.living_room_temperature_truth') not in ['unknown', 'unavailable'] }}

      - name: "LR Shadow Divergence"
        unique_id: lr_shadow_divergence_v1
        state: >
          {%- set rd = states('sensor.lr_shadow_raw_decision') -%}
          {%- set fd = states('sensor.lr_shadow_filtered_decision') -%}
          {%- if rd in ['unavailable','unknown'] or fd in ['unavailable','unknown'] -%}unavailable
          {%- elif rd == fd -%}same
          {%- else -%}different
          {%- endif -%}

      - name: "LR Shadow Raw Threshold Distance"
        unique_id: lr_shadow_raw_threshold_distance_v1
        unit_of_measurement: "°F"
        state: >
          {%- set rt = states('sensor.living_room_temperature_truth') | float(none) -%}
          {%- set away = is_state('input_boolean.away_mode', 'on') -%}
          {%- set on_at = 76 if away else 72 -%}
          {%- if rt is none -%}unknown{%- else -%}{{ (rt - on_at) | round(2) }}{%- endif -%}

      - name: "LR Shadow Filtered Threshold Distance"
        unique_id: lr_shadow_filtered_threshold_distance_v1
        unit_of_measurement: "°F"
        state: >
          {%- set ft = states('sensor.living_room_temperature_control') | float(none) -%}
          {%- set away = is_state('input_boolean.away_mode', 'on') -%}
          {%- set on_at = 76 if away else 72 -%}
          {%- if ft is none -%}unknown{%- else -%}{{ (ft - on_at) | round(2) }}{%- endif -%}

      - name: "LR Shadow Raw Value"
        unique_id: lr_shadow_raw_value_v1
        unit_of_measurement: "°F"
        device_class: temperature
        state_class: measurement
        state: >
          {{ states('sensor.living_room_temperature_truth') | float(none) }}
        availability: >
          {{ states('sensor.living_room_temperature_truth') not in ['unknown', 'unavailable'] }}

      - name: "LR Shadow Filtered Value"
        unique_id: lr_shadow_filtered_value_v1
        unit_of_measurement: "°F"
        device_class: temperature
        state_class: measurement
        state: >
          {{ states('sensor.living_room_temperature_control') | float(none) }}
        availability: >
          {{ states('sensor.living_room_temperature_control') not in ['unknown', 'unavailable'] }}

      # ─── Master, Lincoln, Lilly: identical pattern with zone-specific entity IDs ───
      # unique_id prefix: master_shadow_*, lincoln_shadow_*, lilly_shadow_*
      # Master adds sleep window branch: 18:00-06:00, on_at=66, off_at=62
      # Lincoln and Lilly: same thresholds as LR day mode (on_at=72, off_at=68)
```

**Note on Master sleep window:** The Master shadow template must include the sleep window
branch. The Jinja2 template for Master filtered decision adds:

```yaml
{%- set sleep_window = now().hour >= 18 or now().hour < 6 -%}
{%- if not away and sleep_window -%}
  {%- if ft > 66 -%}cool{%- elif ft <= 62 -%}off{%- else -%}hold{%- endif -%}
{%- else ... (standard logic) ... -%}
```

### 6.3 Section 17: Shadow observation automation (automations.yaml)

Add after Section 16 (or after Section 15, whichever is last) as a new automation block:

```yaml
# =========================================================
# SECTION 17: SHADOW EVALUATOR AUTOMATION
# =========================================================
# PURPOSE: Logs structured shadow evaluation evidence at supervisor cadence.
#          Read-only. No climate services. No helper writes.
# TRIGGER: Same time_pattern as supervisor (minutes: "/15") + HA start
# READS:   Raw truth, smoothed/control, gate helpers
# WRITES:  logbook.log ONLY — zero climate.*, zero input_*, zero timer.*
# =========================================================
- id: v_shadow_evaluator
  alias: "Shadow Evaluator — Evidence Collection (Observational Only)"
  description: >-
    Computes the supervisor decision that would result from filtered truth
    at each 15-minute tick. Writes to logbook only. Never issues climate commands.
    See docs/analysis/packet_b_rev3_shadow_evidence_mvp.md §6.3.
  trigger:
    - platform: time_pattern
      minutes: "/15"
    - platform: homeassistant
      event: start
  condition: []  # always runs; override-gating is noted in the variables block but not enforced
                 # (shadow runs even during override to capture override window evidence)
  action:
    - variables:
        # Gate inputs
        season:      "{{ states('input_select.hvac_season_mode') }}"
        away:        "{{ is_state('input_boolean.away_mode', 'on') }}"
        night_lr:    "{{ is_state('input_boolean.night_mode_lr_primary', 'on') }}"
        override:    "{{ states('timer.manual_hvac_override') }}"
        lr_boost:    "{{ is_state('input_boolean.lr_heating_recovery_boost_active', 'on') }}"
        outdoor:     "{{ states('sensor.deck_temperature_truth') | float(50) }}"
        sleep_master: "{{ now().hour >= 18 or now().hour < 6 }}"
        cooling_season: >
          {{ season == 'cooling' or (season == 'shoulder' and outdoor | float(50) > 70) }}
        # Raw truth
        lr_raw:      "{{ states('sensor.living_room_temperature_truth')    | float(none) }}"
        master_raw:  "{{ states('sensor.master_bedroom_temperature_truth') | float(none) }}"
        lincoln_raw: "{{ states('sensor.lincoln_s_room_temperature_truth') | float(none) }}"
        lilly_raw:   "{{ states('sensor.lilly_s_room_temperature_truth')   | float(none) }}"
        # Filtered (control wrapper)
        lr_filt:      "{{ states('sensor.living_room_temperature_control')    | float(none) }}"
        master_filt:  "{{ states('sensor.master_bedroom_temperature_control') | float(none) }}"
        lincoln_filt: "{{ states('sensor.lincoln_s_room_temperature_control') | float(none) }}"
        lilly_filt:   "{{ states('sensor.lilly_s_room_temperature_control')   | float(none) }}"
        # Smoothed (cross-validation only; supervisor does not read these)
        lr_smoothed:      "{{ states('sensor.living_room_temperature_smoothed')    | float(none) }}"
        master_smoothed:  "{{ states('sensor.master_bedroom_temperature_smoothed') | float(none) }}"
        lincoln_smoothed: "{{ states('sensor.lincoln_s_room_temperature_smoothed') | float(none) }}"
        lilly_smoothed:   "{{ states('sensor.lilly_s_room_temperature_smoothed')   | float(none) }}"
    - service: logbook.log
      data:
        name: "shadow_evaluator"
        entity_id: sensor.living_room_temperature_truth
        message: >-
          {"ts":"{{ now().isoformat() }}",
           "season":"{{ season }}","away":{{ away }},"night_lr":{{ night_lr }},
           "override":"{{ override }}","lr_boost":{{ lr_boost }},
           "cooling_season":{{ cooling_season }},
           "lr":{"raw":{{ lr_raw }},"smoothed":{{ lr_smoothed }},"filt":{{ lr_filt }},
                 "raw_dec":"{{ states('sensor.lr_shadow_raw_decision') }}",
                 "filt_dec":"{{ states('sensor.lr_shadow_filtered_decision') }}",
                 "diverge":"{{ states('sensor.lr_shadow_divergence') }}",
                 "raw_dist":{{ states('sensor.lr_shadow_raw_threshold_distance')|float(none) }},
                 "filt_dist":{{ states('sensor.lr_shadow_filtered_threshold_distance')|float(none) }}},
           "master":{"raw":{{ master_raw }},"smoothed":{{ master_smoothed }},"filt":{{ master_filt }},
                     "raw_dec":"{{ states('sensor.master_shadow_raw_decision') }}",
                     "filt_dec":"{{ states('sensor.master_shadow_filtered_decision') }}",
                     "diverge":"{{ states('sensor.master_shadow_divergence') }}"},
           "lincoln":{"raw":{{ lincoln_raw }},"smoothed":{{ lincoln_smoothed }},"filt":{{ lincoln_filt }},
                      "raw_dec":"{{ states('sensor.lincoln_shadow_raw_decision') }}",
                      "filt_dec":"{{ states('sensor.lincoln_shadow_filtered_decision') }}",
                      "diverge":"{{ states('sensor.lincoln_shadow_divergence') }}"},
           "lilly":{"raw":{{ lilly_raw }},"smoothed":{{ lilly_smoothed }},"filt":{{ lilly_filt }},
                    "raw_dec":"{{ states('sensor.lilly_shadow_raw_decision') }}",
                    "filt_dec":"{{ states('sensor.lilly_shadow_filtered_decision') }}",
                    "diverge":"{{ states('sensor.lilly_shadow_divergence') }}"}}
```

### 6.4 Implementation constraints

- The Section 17 automation must not appear in the `Manual Override Contract` table
  (`docs/5_runtime_layer.md` §7.8) as an HVAC-writing path — it is observational only and
  never writes HVAC state.
- The 28 shadow template sensors (Section 16) must not be referenced as inputs by any
  existing automation, condition, or template. They are outputs only.
- The shadow automation and sensors do not need an entry in the `docs/5_runtime_layer.md`
  live component tables — they are observational infrastructure, not control runtime.
  They do need a note in §6.6 Evidence / Runtime Observation Components.

---

## 7. Safety Boundaries

### 7.1 Service call prohibition

The Section 17 automation contains exactly one service call: `logbook.log`. No
`climate.*`, `input_boolean.*`, `timer.*`, `input_datetime.*`, `input_text.*`, or
`input_select.*` calls are present. This is verifiable by test (§9.3) and by YAML review.

Template sensors in Section 16 are defined in `template:` sensor blocks; they have no
`action:` context and cannot issue service calls by construction.

### 7.2 Helper and timer isolation

- The shadow evaluator reads `input_boolean.away_mode`, `input_boolean.night_mode_lr_primary`,
  `timer.manual_hvac_override`, and `input_boolean.lr_heating_recovery_boost_active` as
  read-only gate inputs. It does not start, pause, cancel, or toggle any of them.
- The shadow automation does not create or modify any helper entities.
- If a helper is unavailable, the shadow evaluator logs the unavailability and skips that
  zone's shadow decision (§4.5). It does not fall back to a default that changes control state.

### 7.3 Live supervisor isolation

- The supervisor (`v7_5_main_supervisor`) variables block is not modified.
- The 28 shadow template sensors are not added to the supervisor variables block.
- No shadow entity appears in any `condition:` or `trigger:` of any existing automation.
- The shadow automation's `time_pattern minutes: "/15"` trigger fires independently of the
  supervisor's trigger. The supervisor and shadow automation may execute in any order within
  a 15-minute window; this is acceptable because the shadow is reading current state, not
  producing state the supervisor depends on.

### 7.4 Failure containment

- If the shadow automation fails (exception, HA restart, logbook service unavailable), the
  supervisor continues unaffected.
- If the shadow template sensors produce `unavailable` or `unknown` states, no existing
  automation changes behavior (no existing automation reads these entities).
- Disabling the shadow automation (`v_shadow_evaluator`) does not change any HVAC control
  behavior; it only stops evidence collection.

### 7.5 Packet A boundary

Packet A (PRs #135 and #137, unmerged) owns:
- `*_truth_ok` guard sensors
- Shared finite-value validity definition (NaN / ±inf / out-of-range rejection)
- Protective-OFF behavior when truth is invalid
- Reconciliation logic for invalid → valid transitions

Packet B MVP owns nothing from this list. The shadow evaluator does not implement
finite-value guards, protective-OFF, or `*_truth_ok` checks. If raw or filtered truth is
unavailable, the shadow logs `unavailable` and skips the shadow decision (§4.5). The
`float(none) is not none` availability check in the Section 10 control wrappers is preserved
as-is; the shadow reads the wrapper's availability state, not a re-implemented guard.

The known gap — `float(none)` passes `NaN` through the control wrapper (Revision 2 §4.2) —
remains Packet A territory and is not addressed in Packet B MVP.

---

## 8. Documentation Corrections

### 8.1 Contradiction 1 — configuration.yaml Section 12 header (lines ~1078–1082)

**Current text (false):**
```yaml
  # ⚠️  DO NOT DELETE — These lowpass filters smooth the raw truth sensors
  #     to prevent control jitter. The control wrappers in Section 10 read
  #     from these, and the V8.3 supervisor ultimately acts on the
  #     smoothed values. Removing these causes noisy truth spikes to
  #     propagate directly into setpoint decisions.
```

**Corrected text:**
```yaml
  # ⚠️  DO NOT DELETE — These lowpass filters smooth the raw truth sensors
  #     to prevent UI jitter and provide the control-wrapper pass-through
  #     consumed by Section 10. The V8.3 supervisor reads raw truth
  #     directly (sensor.*_temperature_truth); it does NOT read these
  #     smoothed sensors or the Section 10 control wrappers.
  #     Removing these affects the HA UI/dashboard and the shadow evaluator
  #     (Section 16) but does not directly alter supervisor decisions.
  #     See docs/analysis/packet_b_rev3_shadow_evidence_mvp.md §8.1.
  #     Final architecture routing remains deferred pending evidence review.
```

### 8.2 Contradiction 2 — configuration.yaml Section 10 header (lines ~927–937)

**Current text (false):**
```yaml
      # SECTION 10: CONTROL WRAPPERS FOR UI / SUPERVISOR
      # ⚠️  DO NOT DELETE — These sensors pass smoothed truth values
      #     through a template with unique_id so the V8.3 supervisor
      #     and the HA UI can manage them as distinct entities. Without
      #     these wrappers, downstream consumers lose their temperature
      #     input and control stops working.
```

**Corrected text:**
```yaml
      # SECTION 10: CONTROL WRAPPERS FOR UI / DASHBOARD
      # ⚠️  DO NOT DELETE — These sensors expose smoothed truth values as
      #     stable named entities for the HA UI/dashboard. The V8.3
      #     supervisor does NOT read these wrappers; it reads raw truth
      #     (sensor.*_temperature_truth) directly. The Section 16 shadow
      #     evaluator reads these wrappers as the filtered-truth input.
      #     Without these wrappers, the HA UI loses stable temperature
      #     entities; supervisor control is unaffected.
      #     See docs/analysis/packet_b_rev3_shadow_evidence_mvp.md §8.2.
      #     Final architecture routing remains deferred pending evidence review.
```

### 8.3 Contradiction 3 — truth_sensor_architecture.md pipeline diagram

**Current text (false):**
```
Physical Sensors
→ Truth Sensors
→ Smoothed Sensors
→ Control Wrappers
→ HVAC Supervisor
→ Telemetry Logging
```

This diagram implies the supervisor is downstream of the control wrappers, which is false.

**Corrected text:**
```
Physical Sensors
  │
  ▼
Truth Sensors
  ├──────────────────────────────────────────┐
  │                                          │
  ▼                                          ▼
Smoothed Sensors                    HVAC Supervisor V8.3  ←── reads raw truth directly
  │                                  Safety Automations   ←── reads raw truth directly
  ▼                                  Telemetry Export     ←── reads raw truth directly
Control Wrappers
  │
  ▼
UI / Dashboard
Shadow Evaluator (read-only, evidence collection)
```

Add a prose note below the diagram in truth_sensor_architecture.md:

```markdown
## Current Routing (MVP)

The V8.3 supervisor (`automations.yaml` Section 2) reads raw truth
(`sensor.*_temperature_truth`) directly. It does not consume the smoothed
sensors or the control wrappers.

Safety automations (runaway cutoff, emergency floor, ceiling gates) also
read raw truth directly.

The control wrappers (Section 10) and smoothed sensors (Section 12) serve:
- The HA UI / dashboard (stable named entities)
- The shadow evaluator (Section 16, Packet B MVP evidence collection)

This routing is the current MVP runtime behavior. It is not a permanent
architecture doctrine. The final decision on whether the supervisor should
migrate to filtered truth remains deferred pending replay evidence.
See `docs/analysis/packet_b_rev3_shadow_evidence_mvp.md` §12.
```

### 8.4 Bonus correction — configuration.yaml line 36 (top-level comment block)

**Current text (false):**
```yaml
#   - Smoothed output → control wrapper → V8.3 supervisor / HA UI
```

**Corrected text:**
```yaml
#   - Smoothed output → control wrapper → HA UI / dashboard
#     (V8.3 supervisor reads raw truth directly, not the control wrappers)
```

---

## 9. Contract-Test Specification

All tests are pure YAML/text inspection tests, following the existing pattern in `tests/`.
No HA runtime is required. Tests fail if asserted conditions are violated.

### Test 1: `tests/test_packet_b_supervisor_reads_raw_truth.py`

**Purpose:** Prove the live supervisor still reads raw truth after MVP changes.

**Assertions:**
1. `automations.yaml` automation with id `v7_5_main_supervisor` contains a variables block
   with exactly four `*_temperature_truth` entity reads (lr, master, lincoln, lilly).
2. The same variables block contains zero references to `*_temperature_smoothed`.
3. The same variables block contains zero references to `*_temperature_control`.
4. No variable in the supervisor block resolves to a `shadow_*` entity.
5. The supervisor's `float(70)` fallbacks are on the raw truth entities, not on smoothed/control.

### Test 2: `tests/test_packet_b_safety_reads_raw_truth.py`

**Purpose:** Prove safety automations still read raw truth after MVP changes.

**Assertions:**
1. Automation `v8_2_lr_runaway_cooling_cutoff` triggers on `sensor.living_room_temperature_truth`.
2. Automation `v8_2_master_emergency_floor` triggers on `sensor.master_bedroom_temperature_truth`.
3. Automation `v7_5_safety_ceiling_gates` trigger entity list contains only `*_temperature_truth`
   entities (no `*_smoothed`, no `*_control`, no `shadow_*`).
4. Automation `v7_5_ghost_assassin` does not reference any smoothed/control entity.
5. Automation `v9_sleep_priority_interlock` condition checks raw truth, not smoothed/control.

### Test 3: `tests/test_packet_b_shadow_no_climate_calls.py`

**Purpose:** Prove shadow automation cannot issue climate service calls.

**Assertions:**
1. Automation `v_shadow_evaluator` action block contains zero calls to `climate.set_hvac_mode`.
2. Automation `v_shadow_evaluator` action block contains zero calls to `climate.set_temperature`.
3. Automation `v_shadow_evaluator` action block contains zero calls to `climate.turn_on`,
   `climate.turn_off`, or any other `climate.*` service.
4. Automation `v_shadow_evaluator` action block contains zero calls to `input_boolean.*`.
5. Automation `v_shadow_evaluator` action block contains zero calls to `timer.*`.
6. Automation `v_shadow_evaluator` action block contains zero calls to `input_select.*`.
7. Automation `v_shadow_evaluator` action block contains exactly one service call: `logbook.log`.

### Test 4: `tests/test_packet_b_shadow_failure_isolation.py`

**Purpose:** Prove shadow failures cannot block or alter live control.

**Assertions:**
1. No existing automation (excluding `v_shadow_evaluator`) has a `trigger` or `condition` that
   references any `sensor.*_shadow_*` entity.
2. No existing automation variable block reads any `sensor.*_shadow_*` entity.
3. The supervisor automation `v7_5_main_supervisor` has no dependency (trigger, condition,
   wait_for_trigger, or variable) on `v_shadow_evaluator`.
4. Automation `v_shadow_evaluator` does not appear in any `continue_on_timeout`, `wait_for_trigger`,
   or `parallel` block of any other automation.
5. `sensor.*_shadow_*` entities do not appear in any Section 3 (safety) automation.

### Test 5: `tests/test_packet_b_shadow_same_thresholds.py`

**Purpose:** Prove raw and filtered shadow decisions use identical thresholds and gate inputs.

**Assertions:**
1. The `lr_shadow_raw_decision` and `lr_shadow_filtered_decision` template definitions both
   use `on_at=72, off_at=68` for the standard cooling branch.
2. The `lr_shadow_raw_decision` and `lr_shadow_filtered_decision` template definitions both
   use `on_at=76, off_at=74` for the away branch.
3. The `master_shadow_*` templates both include the 18:00–06:00 sleep window branch
   with `on_at=66, off_at=62`.
4. The shadow observation automation variables block reads the same gate helpers
   (`input_select.hvac_season_mode`, `input_boolean.away_mode`, `timer.manual_hvac_override`)
   as the supervisor.
5. No threshold value in the shadow template sensors differs from the corresponding threshold
   in the supervisor variables block (regex check against both files).

### Test 6: `tests/test_packet_b_evidence_schema.py`

**Purpose:** Prove native evidence contains required entities and shadow sensors exist.

**Assertions:**
1. `configuration.yaml` contains template sensor definitions for all 28 shadow entities
   (7 per zone × 4 zones).
2. Each of the 28 shadow sensors has a unique `unique_id` with the `_v1` suffix.
3. The recorder `include.entities` list contains all 28 shadow entity names.
4. The recorder `include.entities` list contains all 8 smoothed/control entity names.
5. `automations.yaml` automation `v_shadow_evaluator` log payload template contains
   the fields `ts`, `season`, `away`, `override`, `lr.raw`, `lr.filt`, `lr.diverge`.

### Test 7: `tests/test_packet_b_documentation_routing.py`

**Purpose:** Prove documentation matches actual MVP routing after corrections.

**Assertions:**
1. `configuration.yaml` Section 12 comment block does not contain the string
   "supervisor ultimately acts on the smoothed values".
2. `configuration.yaml` Section 10 comment block does not contain the string
   "CONTROL WRAPPERS FOR UI / SUPERVISOR".
3. `truth_sensor_architecture.md` does not contain the pipeline sequence
   "Control Wrappers\n→ HVAC Supervisor" (or equivalent without section header).
4. `truth_sensor_architecture.md` contains the string "reads raw truth directly"
   in the context of the supervisor.
5. `configuration.yaml` line 36 (±5 lines) does not contain
   "control wrapper → V8.3 supervisor".
6. `docs/analysis/packet_b_rev3_shadow_evidence_mvp.md` exists and contains
   "PACKET B MVP DESIGN APPROVED FOR IMPLEMENTATION".

### Test 8: `tests/test_packet_b_no_packet_a_duplication.py`

**Purpose:** Prove Packet B MVP does not duplicate Packet A behavior.

**Assertions:**
1. `configuration.yaml` Section 16 (shadow sensors) does not contain any `truth_ok` helper
   reference or sensor definition.
2. `configuration.yaml` Section 16 does not implement a finite-value validity gate
   (no `-90/200` range check, no `is_finite` or NaN check beyond `float(none) is not none`).
3. Automation `v_shadow_evaluator` does not issue `climate.set_hvac_mode` with
   `hvac_mode: off` as a protective-OFF action.
4. No shadow sensor name matches the pattern `*_truth_ok`.
5. The shadow evaluator does not define or reference a shared `VALID_TEMP_RANGE` constant
   or equivalent Packet A construct.

---

## 10. Evidence Timeline and Acceptance Gates

The evidence readiness is defined by conditions, not dates alone. All gates must clear
in sequence. Failing a gate halts the evidence window at that gate.

### Gate 0 — Instrumentation verification (within 24 hours of deployment)

**Condition:** All 28 shadow template sensors are `available` and recording values in
HA history. The shadow observation automation has fired at least four consecutive 15-minute
ticks without error. At least one logbook entry with `name: shadow_evaluator` is visible
and parses as valid JSON.

**Pass criteria:**
- HA Developer Tools → States confirms all 28 `sensor.*_shadow_*` entities have numeric
  or valid string states (not `unknown` or `unavailable` across the board).
- Logbook shows `shadow_evaluator` entries at 15-minute intervals.
- At least one entry contains non-null `lr.raw` and `lr.filt` values.

**Fail action:** Diagnose template sensor rendering errors in HA logs. Do not proceed to
Gate 1 until Gate 0 is clear.

### Gate 1 — 24-hour data integrity review

**Condition:** 24 continuous hours of shadow evidence collected after Gate 0 passes.

**Pass criteria:**
- No gap > 16 minutes in shadow logbook entries (allows for one missed tick).
- Recorder database contains state-change events for all 8 smoothed/control entities
  during the 24-hour window.
- Shadow `raw_decision` agrees with actual climate mode for at least 90% of ticks where
  override is idle and cooling season is active (cross-check against V5.5 export rows).
- No shadow automation exceptions in HA error log during the 24-hour window.

**Fail action:** Identify and fix instrumentation errors. Reset 24-hour clock. Do not begin
the formal evidence window until Gate 1 is clear.

### Gate 2 — 48-hour minimum active cooling

**Condition:** Minimum 48 continuous hours with `Season_Mode = cooling` (or active shoulder-
cooling) and at least one mini-split running in cool mode per day.

**Pass criteria:**
- At least 48 rows in `VTherm_Launch_Data_v5_5` with `Season_Mode = cooling` or equivalent.
- At least one zone shows `LR_Air_Mode = cool` or `Master_Air_Mode = cool` during the window.
- `Outdoor_Temp > 72°F` for at least some portion of each day (confirming real cooling load).

**Note on timing:** As of 2026-06-10, recent telemetry shows shoulder season (May 7–16 data).
June is historically the first reliable cooling month. The evidence window should open no
earlier than the first confirmed 48-hour cooling period.

**Fail action:** Extend observation until 48 hours of active cooling is confirmed.

### Gate 3 — Band-edge crossing requirements

**Condition:** At least 3 band-edge crossing events per controlled zone during active cooling.
A band-edge crossing is a supervisor tick where raw truth is within 1.0°F of either the
on-threshold (72°F day, 66°F sleep, 76°F away) or the off-threshold (68°F day, 62°F sleep,
74°F away).

This requirement exists because divergence between raw and filtered decisions is most likely
near thresholds. A data window with no threshold approaches cannot classify filter lag vs.
chatter suppression.

**Pass criteria:**
- `sensor.*_shadow_raw_threshold_distance` shows values in the range [−1.0, +1.0]°F for
  at least 3 distinct ticks per zone.
- OR: `sensor.*_shadow_divergence = different` fires at least once per zone during the window.

**Fail action:** Extend the observation window until band-edge crossings occur naturally.

### Gate 4 — 7–14 day observation window (preferred)

**Condition:** The formal evidence window spans at least 7 days, with 14 days preferred for
capturing variability in household patterns (occupation, away periods, sleep schedule variation).

**Pass criteria:**
- 7+ days of continuous shadow evidence with Gates 0–3 satisfied throughout.

### Gate 5 — Extension rule

**Trigger:** After 14 days, Gates 2 and 3 are not satisfied for all zones.

**Rule:** Extend the observation window in 7-day increments until either:
- Gates 2 and 3 are satisfied for all zones, OR
- A controlled HA restart is performed (§10.8) to observe filter initialization, after which
  the post-restart data replaces the extension window.

**Maximum extension:** 28 additional days (total window ≤ 42 days). If 42 days passes without
sufficient cooling crossings, document the evidence limitation and proceed to Gate 7 with
partial evidence; the final Fable review must note the limitation.

### Gate 6 — Cross-validation halt gate

**Condition:** Before any architecture conclusion, the offline replay must cross-validate.

**Rule:** Implement `y[n] = round(0.9·y[n−1] + 0.1·x[n], 2)` over the raw truth event
sequence exported from recorder (§5.6). The replayed series must reproduce the recorded
`sensor.*_temperature_smoothed` series within ±0.05°F per event for ≥ 95% of events.

**Halt condition:** If cross-validation fails (replayed series deviates from recorded smoothed
by > 0.05°F for more than 5% of events), halt. The filter model or event-acceptance assumptions
are still wrong. Re-derive before any architecture conclusion. Do not proceed to Gate 7.

### Gate 7 — Divergence and harm/benefit classification

**Condition:** All prior gates cleared. Shadow data is exported and analyzed.

**Classification:**

| Category | Definition | Decision implication |
|---|---|---|
| **Zero divergence** | Raw and filtered produce identical decisions across the entire evidence window | Option A (raw) supported; filter is neutral for supervisor decisions |
| **Beneficial divergence** | Shadow filtered decision avoids cooling ON that raw triggers and reverses within one tick (chatter suppression, no overcooling) | Option B/C becomes a live candidate |
| **Harmful divergence — delayed OFF** | Shadow filtered decision holds cooling ON past the raw off-threshold; observed runtime > raw-only scenario (overcooling °F·min) | Option A (raw) strengthened |
| **Harmful divergence — delayed ON** | Shadow filtered decision delays cooling engagement past raw on-threshold; comfort excursion observed | Option A (raw) strengthened |
| **Ambiguous divergence** | Divergences exist but neither harm nor benefit classification is clear from the evidence | Extend window or perform additional analysis before deciding |

**Quantification required:**
- Divergent-decision rate: fraction of ticks where raw ≠ filtered decision.
- Chatter rate: fraction of raw ON-decisions that reverse at the very next tick.
- Overcooling exposure: sum of °F·min below off-threshold attributable to filter lag.
- Engagement delay: sum of °F·min above on-threshold before filter decision catches up.

### Gate 8 — Final Fable architecture-review handoff

**Condition:** Gates 0–7 cleared. Evidence package prepared.

**Evidence package contents:**
1. Recorder event export CSV (§5.6) for the evidence window.
2. Shadow logbook entries for the evidence window.
3. V5.5 Google Sheets export rows for the same window.
4. Cross-validation result (replay vs. recorded smoothed).
5. Divergence classification table (Gate 7).
6. Zone-by-zone divergence rate, chatter rate, overcooling exposure, engagement delay.
7. At least one band-edge crossing example per zone (annotated timeline).
8. Supervisor execution timestamp reconstruction (from logbook or time_pattern grid).

**Handoff instructions for Fable:**
- Apply the decision rule from Revision 2 §3.4.
- Review the divergence classification (Gate 7).
- Select Option A, B, or C based on evidence.
- If Option A: document raw-truth permanence as final doctrine; close Packet B.
- If Option B/C: specify one-zone shadow-to-staging migration per Revision 2 §3.4 protocol.
- The Revision 2 architecture constraints (§4) remain in force regardless of option selected.

### 10.8 Controlled HA restart (optional)

A controlled HA restart may be included in the evidence window if:
- The operator confirms it is operationally safe (no occupancy event imminent, no active
  cooling demand).
- The restart is timestamped and noted in the evidence package.
- The purpose is to observe filter cold-start behavior: does `y[0]` initialize from recorder
  history or from the first accepted event? What is the smoothed value immediately after start?

A restart is not required. If included, the post-restart event window (minimum 2 hours) must
be clearly labeled in the export so replay analysis can separately characterize cold-start
behavior.

---

## 11. Rollback Plan

### 11.1 Shadow-only rollback (primary path)

If the shadow evaluator produces errors, consumes unexpected resources, or causes HA
instability, rollback requires:

1. Delete or comment out the `v_shadow_evaluator` automation block from `automations.yaml`
   (Section 17). This stops all shadow logbook writes.
2. Delete or comment out the Section 16 block from `configuration.yaml`. This removes all
   28 shadow template sensors. HA will reload configuration.
3. Remove the shadow entity names from the recorder `include` list. This does not delete
   historical data already recorded.

**Time to rollback:** One HA configuration reload (< 1 minute).

**Impact:** All existing control behavior, safety behavior, and V5.5 telemetry export are
unaffected. No climate command is reverted. No helper state is changed. No supervisor tick
is altered. Historical shadow data in the recorder database is preserved for offline analysis
even after the shadow sensors are removed.

### 11.2 Documentation rollback (if corrections introduce confusion)

If the documentation corrections (§8) are later determined to mischaracterize the system,
revert `configuration.yaml` and `truth_sensor_architecture.md` to their previous text via
git revert. The documentation corrections do not change runtime behavior; reverting them
does not alter any control path.

### 11.3 Rollback verification

After shadow removal, verify:
- `automation.v_shadow_evaluator` no longer appears in HA automation list.
- `sensor.lr_shadow_*` (and other zone shadow entities) no longer appear in HA states.
- The supervisor (`v7_5_main_supervisor`) runs its next tick without error.
- V5.5 Google Sheets export continues at the next 15-minute tick.
- No safety automation references a shadow entity (test 4 passes).

### 11.4 Non-rollback scope

The rollback plan applies only to shadow instrumentation. It does not:
- Revert the supervisor to reading filtered truth (the supervisor never read filtered truth).
- Roll back any Packet A changes (Packet A is not deployed).
- Roll back any recorder `purge_keep_days` increase (preserving more recorder history is
  harmless; do not shorten it after the evidence window to avoid losing evidence).

---

## 12. Explicitly Deferred Final Decisions

The following decisions are not made by this MVP and must not be inferred from it:

### 12.1 Final raw-versus-filtered routing decision (primary deferral)

**Deferred until:** Gate 8 evidence review by Fable.

**What this MVP does not decide:**
- Whether the supervisor should permanently stay on raw truth (Option A).
- Whether a migration to filtered truth (Option B) would improve comfort.
- Whether a dual-input architecture (Option C) is warranted.
- Whether any of Options A, B, C, D from Revision 2 §1.3 is correct.

**What this MVP does decide:** nothing about routing. It produces evidence so that the
next Fable review can decide.

### 12.2 Control-wrapper availability enhancement (reclassified in Revision 2)

**Deferred.** The Revision 2 §5 reclassification remains in force. The Section 10 wrappers'
availability semantics are unchanged by this MVP. The `float(none) is not none` availability
gate is preserved as-is. Changing wrapper availability transitions is a separate runtime
behavior change requiring its own analysis of UI/dashboard effects.

### 12.3 Packet A and Packet B composition

**Deferred until Packet A is deployed and its sequencing with Packet B is clear.**

Under Option A (raw truth permanent): Packet A and Packet B are independent.
Under Option B/C (filtered truth migration): Packet A's `*_truth_ok` guards would need
re-pointing at the new supervisor input, requiring coordinated deployment.
The composition question is deferred to the Gate 8 review.

### 12.4 Option B/C shadow-to-staging migration protocol

**Deferred until Gate 7 divergence classification.**

If Gate 7 yields beneficial divergence and Fable selects Option B/C, the migration protocol
specified in Revision 2 §3.4 applies: one-zone shadow-to-staging promotion at a time, with
independent rollback for each zone, and a separate runtime PR per zone. This MVP does not
pre-approve any such migration. The shadow evaluator does not constitute a one-zone shadow
trial — it is observational only and never issues climate commands.

### 12.5 V6 event-oriented telemetry schema (orthogonal)

V6 (`docs/v6_telemetry_schema_proposal.md`, `docs/v6_observability_roadmap.md`) is
out of scope for this MVP. The MVP extends the existing recorder and logbook infrastructure;
it does not implement or require V6. If V6 lands during the evidence window, the shadow
sensors should be added to V6's event export scheme, but V6 is not a prerequisite.

---

## 13. Codex Implementation Handoff

This section is the complete handoff checklist for the implementation PR. Do not open a
runtime PR until this design document is committed and the operator has reviewed.

### 13.1 Files to modify

| File | Change type | Section |
|---|---|---|
| `configuration.yaml` | Add Section 16 block (28 shadow template sensors) | §6.2 |
| `configuration.yaml` | Correct Section 12 header comment | §8.1 |
| `configuration.yaml` | Correct Section 10 header comment | §8.2 |
| `configuration.yaml` | Correct line 36 top-level comment | §8.4 |
| `configuration.yaml` | Add shadow entities to recorder `include` | §5.5 |
| `configuration.yaml` | Verify/increase `recorder: purge_keep_days: 14` | §5.4 |
| `automations.yaml` | Add Section 17 automation block (`v_shadow_evaluator`) | §6.3 |
| `truth_sensor_architecture.md` | Correct pipeline diagram and add routing note | §8.3 |
| `docs/5_runtime_layer.md` | Add shadow sensors to §6.6 Evidence components | §6.4 |

### 13.2 Files to create (new tests)

| File | Purpose | §Ref |
|---|---|---|
| `tests/test_packet_b_supervisor_reads_raw_truth.py` | Supervisor still reads raw truth | §9.1 |
| `tests/test_packet_b_safety_reads_raw_truth.py` | Safety automations still read raw truth | §9.2 |
| `tests/test_packet_b_shadow_no_climate_calls.py` | Shadow cannot issue climate services | §9.3 |
| `tests/test_packet_b_shadow_failure_isolation.py` | Shadow failures cannot alter live control | §9.4 |
| `tests/test_packet_b_shadow_same_thresholds.py` | Same thresholds and gate inputs | §9.5 |
| `tests/test_packet_b_evidence_schema.py` | Evidence schema completeness | §9.6 |
| `tests/test_packet_b_documentation_routing.py` | Documentation matches actual routing | §9.7 |
| `tests/test_packet_b_no_packet_a_duplication.py` | No Packet A behavior duplicated | §9.8 |

### 13.3 Files to NOT modify

- `automations.yaml` Section 2 (`v7_5_main_supervisor`) — no supervisor changes.
- `automations.yaml` Section 3 (safety gates) — no safety changes.
- `automations.yaml` Section 14 (LR boost) — no boost changes.
- Any threshold value (68°F, 72°F, 62°F, 66°F, 74°F, 76°F, 60°F, 58°F).
- Any helper entity definition.
- Any V5.5 telemetry export column or trigger.
- `docs/analysis/packet_b_filter_model_revision.md` — Revision 2 is preserved as-is.

### 13.4 Implementation order

1. Write all 8 tests first — tests must fail (entities/corrections don't exist yet).
2. Add Section 16 shadow template sensors to `configuration.yaml`.
3. Add recorder include entries to `configuration.yaml`.
4. Verify `purge_keep_days` ≥ 14.
5. Apply Section 10 and Section 12 documentation corrections to `configuration.yaml`.
6. Apply line 36 correction to `configuration.yaml`.
7. Add Section 17 automation to `automations.yaml`.
8. Apply `truth_sensor_architecture.md` pipeline diagram correction.
9. Add shadow sensor note to `docs/5_runtime_layer.md` §6.6.
10. Run all 8 new tests — all must pass.
11. Run existing test suite — all existing tests must continue to pass.
12. Run `tests/test_yaml_syntax.py` — no YAML errors.
13. Commit and push.

### 13.5 PR description guidance

The implementation PR should:
- Title: "Packet B MVP: shadow evaluator + documentation corrections (observational only)"
- Reference this design document.
- Confirm verdict: PACKET B MVP DESIGN APPROVED FOR IMPLEMENTATION.
- Note explicitly: no supervisor, safety, threshold, or helper changes.
- Note explicitly: shadow evaluator is observational-only per §7.
- Note explicitly: final raw-versus-filtered routing decision remains deferred (§12.1).

### 13.6 Post-merge operator checklist (before evidence window opens)

1. Confirm Gate 0 conditions (§10) are met within 24 hours of merge.
2. Check HA recorder includes the shadow entities (Developer Tools → Template →
   `{{ state_attr('sensor.lr_shadow_filtered_decision', 'last_changed') }}`).
3. Confirm `purge_keep_days` took effect (HA restart may be needed if recorder config changed).
4. Confirm first shadow logbook entry appears and parses as valid JSON.
5. Note the evidence window start time.
6. Schedule Gate 1 review for 24 hours later.

---

## Telemetry Context (as of 2026-06-10)

The `VTherm_Launch_Data_v5_5` Google Sheets telemetry (last updated 2026-06-10T13:15:02 UTC)
confirms:

- Active data collection is running at 15-minute intervals.
- May 7–16 data shows shoulder season with morning heating cycles (LR heat 65°F→68°F range).
- April 16 data confirms full cooling operation was active (outdoor 88–89°F, all zones cooling).
- June 2026 is the expected transition into sustained cooling season.
- The V5.5 schema confirms `Supervisor_Enabled`, `Manual_Override_State`, and
  `Manual_Override_Remaining_Sec` forensic columns are present.

The cooling season expected to begin in June 2026 provides the first natural evidence window.
The MVP should be deployed before the first sustained cooling period to capture full band-edge
crossing evidence.

---

```
═══════════════════════════════════════════════════════════════
PACKET B MVP DESIGN APPROVED FOR IMPLEMENTATION
═══════════════════════════════════════════════════════════════
```

**Conditions of approval:**

1. Implementation follows §13.4 order exactly.
2. All 8 contract tests pass before PR opens.
3. All existing tests continue to pass.
4. No supervisor, safety, threshold, helper, or V5.5 export changes are included.
5. The implementation PR explicitly states the final routing decision remains deferred.
6. Gate 0 verification is performed within 24 hours of merge.

**What remains blocked:**

- Any live migration of the supervisor to filtered truth.
- Any live migration of safety automations away from raw truth.
- Any claim that Option A (raw truth) has been selected as permanent doctrine.
- Any Option B/C shadow-to-staging promotion without Gate 7 evidence review.
