# Packet B — Shadow Evidence MVP

```
═══════════════════════════════════════════════════════════════
PACKET B — SHADOW EVIDENCE MVP
Moose House HVAC — Temperature Input Path: Staged Observational MVP
═══════════════════════════════════════════════════════════════

Status:  APPROVED FOR IMPLEMENTATION (observational MVP only)
Routing: Final raw-vs-filtered decision REMAINS BLOCKED
         See companion memo: packet_b_architecture_decision_review.md
Date:    2026-06-10
Revision: pre-implementation safety corrections applied 2026-06-10
═══════════════════════════════════════════════════════════════
```

---

## 1. Purpose and Staged-Product Rationale

### 1.1 The architecture decision status

The companion memo `packet_b_architecture_decision_review.md` established
that the PR §138 §3.4 evidence gate cannot be cleared: the claimed Hermes
replay evidence was not delivered in any verifiable form, the only accessible
telemetry (15-minute Google Drive snapshots, ≤4.6 hours of cooling coverage)
is structurally incapable of reproducing the event-count filter dynamics, and
no cross-validation against `*_temperature_smoothed` is possible from that
data. The final raw-versus-filtered routing decision **remains blocked**.

### 1.2 Why the block does not prevent this MVP

The block targets any change that routes a live control or safety consumer to
filtered truth. It does not target a strictly observational MVP whose only
purpose is to produce the native-granularity event data the gate actually
requires.

This MVP is approved because it:

- makes **zero changes** to any live supervisor or safety input path;
- adds **read-only instrumentation** that cannot issue services, modify
  helpers, affect timers, change overrides, or become a live control input;
- produces the **native-granularity recorder data** that the §3.4 replay
  specification requires but that has never existed in any shared location;
- corrects **three objectively false documentation statements** that are wrong
  under every candidate architecture and that create active misdirection risk.

### 1.3 What this MVP is not

- It is not a declaration that Option A (raw truth permanently) has won.
- It is not a declaration that filtered truth is better.
- It does not authorize any routing change, threshold change, or supervisor
  modification.
- It is not a substitute for the replay evidence required by §3.4. It is the
  instrumentation that makes collecting that evidence possible.
- Preservation of raw routing in the MVP is a **safety boundary for the
  observation window**, not permanent architectural doctrine.

---

## 2. Current Behavior Preserved

### 2.1 Raw-truth supervisor route (preserved, unchanged)

The V8.3 supervisor (`automations.yaml`, id `v7_5_main_supervisor`, Section 2)
reads raw truth in its variables block:

```yaml
variables:
  outdoor:      "{{ states('sensor.deck_temperature_truth')           | float(50) }}"
  lr_temp:      "{{ states('sensor.living_room_temperature_truth')    | float(70) }}"
  master_temp:  "{{ states('sensor.master_bedroom_temperature_truth') | float(70) }}"
  lincoln_temp: "{{ states('sensor.lincoln_s_room_temperature_truth') | float(70) }}"
  lilly_temp:   "{{ states('sensor.lilly_s_room_temperature_truth')   | float(70) }}"
```

This block is **not modified**. No variable is added, renamed, or redirected.

### 2.2 Raw-truth safety routes (preserved, unchanged)

| Automation id | Entity read | Safety threshold |
|---|---|---|
| `v8_2_lr_runaway_cooling_cutoff` | `sensor.living_room_temperature_truth` | < 60°F |
| `v8_2_master_emergency_floor` | `sensor.master_bedroom_temperature_truth` | < 58°F |
| `v7_5_safety_ceiling_gates` | Zone `*_temperature_truth` entities | > 76°F |
| `v7_5_ghost_assassin` | `sensor.lincoln_s_room_temperature_truth` | state trigger |
| `v9_sleep_priority_interlock` | `sensor.living_room_temperature_truth` | > 60°F condition |

All trigger expressions, condition expressions, and threshold values are
**not modified**. The companion memo (Section 6, Unchanged Constraints)
notes that an event-count filter introduces unbounded wall-clock lag in
frozen-lag mode, making raw truth categorically more appropriate for safety
automations regardless of what the final supervisor routing decision is.

### 2.3 Filtered/control chain remains non-authoritative

The smoothed sensors (`sensor.*_temperature_smoothed`, Section 12) and
control wrappers (`sensor.*_temperature_control`, Section 10) currently have
no automation consumers other than the HA UI. The MVP preserves this
property. The shadow evaluator **reads** these entities but does not promote
them to control authority. Adding a read-only observer does not make the
chain authoritative.

### 2.4 Preserved behavior is documented fact, not permanent doctrine

This document describes current routing as MVP runtime behavior. It does not:
- freeze raw routing as permanent architecture;
- encode Option A as a doctrine decision;
- prevent a future migration after the §3.4 gate clears with verified evidence.

---

## 3. MVP Architecture and Home Assistant Surfaces

### 3.1 Architecture diagram

```
Physical Sensors
  │
  ▼
Truth Sensors (» sensor.*_temperature_truth)
  ├─────────────────────────────────────────────────────────┐
  │                                                        │
  │ (read raw)                                             │ (read raw)
  ▼                                                        ▼
V8.3 Supervisor (Section 2) ─── climate.*       Safety Automations (Section 3)
15-min V5.5 Export (Section 1) ─ Google Sheets  (unchanged, on raw truth)
  │
  ▼
Smoothed Sensors (» sensor.*_temperature_smoothed, Section 12)
  │
  ▼
Control Wrappers (» sensor.*_temperature_control, Section 10)
  ├─────────────────────────────────────────────────────────┐
  │                                                        │
  ▼                                                        ▼
UI / Dashboard                              Shadow Evaluator [NEW — read-only]
(unchanged)                                 config.yaml §16: 28 template sensors
                                            automations.yaml §17: logbook.log only
                                            recorder: no change (records all by default)
```

### 3.2 New constructs (observational only)

**A — Shadow template sensors** (`configuration.yaml`, new Section 16)

28 read-only template sensors (7 per zone × 4 zones: LR, Master, Lincoln, Lilly).
They compute and expose the shadow filtered decision and divergence classification.
They update reactively; HA recorder captures their state-change history automatically
because the recorder currently records all entities by default (see §5.5).
They cannot issue service calls. They cannot become supervisor inputs.

| Entity pattern | Role |
|---|---|
| `sensor.<zone>_shadow_filtered_decision` | cool/off/hold from filtered truth |
| `sensor.<zone>_shadow_raw_decision` | cool/off/hold from raw truth (cross-check) |
| `sensor.<zone>_shadow_divergence` | `same` or `different` |
| `sensor.<zone>_shadow_raw_threshold_distance` | (raw − active\_on\_threshold), signed °F |
| `sensor.<zone>_shadow_filtered_threshold_distance` | (filtered − active\_on\_threshold), signed °F |
| `sensor.<zone>_shadow_raw_value` | raw truth snapshot |
| `sensor.<zone>_shadow_filtered_value` | control wrapper value snapshot |

Zone prefix mapping: `lr_` / `master_` / `lincoln_` / `lilly_`.

**B — Shadow observation automation** (`automations.yaml`, new Section 17)

Automation id: `v_shadow_evaluator`. Triggers on `time_pattern minutes: "/15"`
and `homeassistant: start`. Variables block mirrors the supervisor variables
block exactly (same entity reads, same gate inputs). One service call only:
`logbook.log`. Zero `climate.*` calls. Zero `input_*` or `timer.*` writes.

**C — Recorder: no change required**

The current repository recorder configuration is:

```yaml
recorder:
  purge_keep_days: 30
  commit_interval: 5
```

There is no `include:` or `exclude:` block. HA recorder therefore already
captures all entities — including all truth, smoothed, control, and new
shadow template sensor entities — by default at native event granularity.

**The Codex implementation PR must not add a `recorder: include:` block.**
Adding an include allow-list would immediately stop HA from recording every
entity not in that list, destroying history for the rest of the system.

The Codex implementation PR must:
1. Preserve `purge_keep_days: 30` exactly (already ≥ the 14-day evidence minimum).
2. Preserve `commit_interval: 5` exactly.
3. Add no `include:` or `exclude:` sub-key to the recorder block.
4. Verify — by inspection only, no YAML change — that no `exclude:` block
   exists that would suppress truth, smoothed, control, or shadow entities.
5. If the live system’s running configuration diverges from the repository
   (e.g. an include list was added out-of-band), reconcile by appending to
   the existing list without removing any existing entries; never replace
   an include list with a shorter one.

### 3.3 Existing constructs NOT modified

| File | Sections | Status |
|---|---|---|
| `automations.yaml` | 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 14, 15 | Unchanged |
| `configuration.yaml` | 3–9 (truth sensors), 10 (wrappers), 12 (filters) | Logic unchanged; comments corrected (§8) |
| `configuration.yaml` | recorder block | Unchanged |
| All threshold values (60°F, 58°F, 68°F, 72°F, 62°F, 66°F, 74°F, 76°F) | | Unchanged |
| All helper definitions | | Unchanged |
| V5.5 telemetry export columns and cadence | | Unchanged |

---

## 4. Per-Zone Shadow Decision Contract

### 4.1 Decision function

The shadow evaluator implements the same decision function as the V8.3
supervisor for the cooling and shoulder-cooling branches, substituting
`sensor.*_temperature_control` (the filtered input) for
`sensor.*_temperature_truth` (the raw input) in the filtered path:

```
For each zone at each evaluation:

  1. Read gate inputs: season_mode, away_mode, time-of-day, override_state,
     lr_boost_active (LR only).

  2. Determine active thresholds (same rule as supervisor):
     if away_mode:
       on_at = 76, off_at = 74          # all zones
     elif zone == master and 18:00–06:00:
       on_at = 66, off_at = 62          # master sleep window
     elif zone == lr and night_mode_lr:
       on_at = 72, off_at = 64          # LR stack-effect reduction
     else:
       on_at = 72, off_at = 68          # standard day cooling

  3. If not cooling/shoulder-cooling season: record not_applicable; skip.

  4. Compute raw_decision (from sensor.*_temperature_truth):
     > on_at  → cool
     ≤ off_at → off
     else     → hold

  5. Compute shadow_filtered_decision (from sensor.*_temperature_control):
     if control wrapper unavailable: record filtered_unavailable; skip filtered path.
     > on_at  → cool
     ≤ off_at → off
     else     → hold

  6. divergence = different  if  raw_decision != shadow_filtered_decision
                 same        otherwise

  7. divergence_direction:
     none                     if divergence == same
     raw_more_aggressive      if raw==cool and filtered==hold/off,
                                 or raw==hold and filtered==off
     filtered_more_aggressive if filtered==cool and raw==hold/off,
                                 or filtered==hold and raw==off
```

**Heating branches:** if `season_mode` is `heating` and no cooling branch fires,
log gate inputs and record `decision = not_applicable` for all zones. Heating
branch divergence is not the object of the §3.4 gate.

### 4.2 Entities consumed per zone (read-only)

```
Raw inputs:
  sensor.living_room_temperature_truth
  sensor.master_bedroom_temperature_truth
  sensor.lincoln_s_room_temperature_truth
  sensor.lilly_s_room_temperature_truth
  sensor.deck_temperature_truth          # outdoor; shoulder branch

Filtered inputs (read-only):
  sensor.living_room_temperature_control
  sensor.master_bedroom_temperature_control
  sensor.lincoln_s_room_temperature_control
  sensor.lilly_s_room_temperature_control

Smoothed (cross-validation only; supervisor never reads these):
  sensor.living_room_temperature_smoothed
  sensor.master_bedroom_temperature_smoothed
  sensor.lincoln_s_room_temperature_smoothed
  sensor.lilly_s_room_temperature_smoothed

Gate helpers (read-only):
  input_select.hvac_season_mode
  input_boolean.away_mode
  input_boolean.night_mode_lr_primary
  timer.manual_hvac_override
  input_boolean.lr_heating_recovery_boost_active

Current climate mode (read-only, for hold detection):
  climate.living_room_air
  climate.master_bedroom_air
  climate.lincoln_air
  climate.lilly_air
```

---

## 5. Native Evidence Schema

### 5.1 Per-evaluation record (captured per tick per zone)

| Field | Type | Source |
|---|---|---|
| `eval_timestamp` | ISO8601 | `now().isoformat()` |
| `zone` | string | literal |
| `raw_truth` | float ❘ null | `sensor.<zone>_temperature_truth` |
| `smoothed_value` | float ❘ null | `sensor.<zone>_temperature_smoothed` |
| `control_wrapper_value` | float ❘ null | `sensor.<zone>_temperature_control` |
| `active_on_threshold` | float | computed from gate inputs |
| `active_off_threshold` | float | computed from gate inputs |
| `season_mode` | string | `input_select.hvac_season_mode` |
| `away_state` | bool | `input_boolean.away_mode` |
| `night_mode_lr` | bool | LR only |
| `sleep_window_active` | bool | Master only (18:00–06:00) |
| `manual_override_state` | idle/active/paused | `timer.manual_hvac_override` |
| `lr_boost_active` | bool | LR only |
| `current_climate_mode` | string | `climate.<zone>_air` state |
| `raw_decision` | cool/off/hold/unavailable | computed |
| `shadow_filtered_decision` | cool/off/hold/unavailable | computed |
| `divergence` | same/different | derived |
| `divergence_direction` | none/raw\_more\_aggressive/filtered\_more\_aggressive | derived |
| `raw_threshold_distance_on` | signed float | raw_truth − on_threshold |
| `raw_threshold_distance_off` | signed float | raw_truth − off_threshold |
| `filtered_threshold_distance_on` | signed float | control_value − on_threshold |
| `filtered_threshold_distance_off` | signed float | control_value − off_threshold |
| `raw_truth_available` | bool | state not unknown/unavailable |
| `filtered_truth_available` | bool | control wrapper available |

### 5.2 Logbook event structure

The Section 17 automation emits one `logbook.log` event per evaluation.
The payload is a JSON string in the `message` field containing all fields
from §5.1 for all four zones plus the gate-input block. `entity_id` is set
to `sensor.living_room_temperature_truth` (required by `logbook.log`; does
not modify that entity’s state).

```yaml
- service: logbook.log
  data:
    name: "shadow_evaluator"
    entity_id: sensor.living_room_temperature_truth
    message: >-
      {"ts":"{{ now().isoformat() }}",
       "season":"{{ season }}","away":{{ away }},
       "override":"{{ override }}","cooling":{{ cooling_season }},
       "lr":   {"raw":{{ lr_raw }},  "smo":{{ lr_smo }},  "ctl":{{ lr_ctl }},
                "raw_dec":"{{ lr_raw_dec }}","filt_dec":"{{ lr_filt_dec }}",
                "div":"{{ lr_div }}","div_dir":"{{ lr_div_dir }}",
                "dist_raw":{{ lr_dist_raw }},"dist_filt":{{ lr_dist_filt }}},
       "master":{"raw":{{ m_raw }},  "smo":{{ m_smo }},  "ctl":{{ m_ctl }},
                "raw_dec":"{{ m_raw_dec }}","filt_dec":"{{ m_filt_dec }}",
                "div":"{{ m_div }}","sleep_win":{{ sleep_master }}},
       "lincoln":{"raw":{{ li_raw }},"smo":{{ li_smo }},"ctl":{{ li_ctl }},
                  "raw_dec":"{{ li_raw_dec }}","filt_dec":"{{ li_filt_dec }}",
                  "div":"{{ li_div }}"},
       "lilly": {"raw":{{ ll_raw }},"smo":{{ ll_smo }},"ctl":{{ ll_ctl }},
                 "raw_dec":"{{ ll_raw_dec }}","filt_dec":"{{ ll_filt_dec }}",
                 "div":"{{ ll_div }}"}}
```

### 5.3 Recorder evidence (native granularity)

HA recorder already captures state-change events for all
`sensor.*_temperature_truth`, `sensor.*_temperature_smoothed`,
`sensor.*_temperature_control`, and — after the implementation PR adds
Section 16 — all `sensor.*_shadow_*` entities, all at native event granularity.
This requires no recorder YAML change because the recorder has no include/exclude
block and records all entities by default.

For the replay to be correctly executed:

1. **`purge_keep_days`** is already 30, which exceeds the 14-day evidence minimum.
   Preserve it. Do not reduce it.
2. **No exclude block** currently exists. Verify by inspection that the implementation
   PR does not introduce one. If an out-of-band live exclude block is ever discovered,
   treat it as an instrumentation failure and do not execute the replay until it is
   removed or corrected.
3. **`last_reported`** (not `last_changed`) is the correct column for distinguishing
   value-change events from re-reports. Verify the recorder schema exposes this column
   before the replay is attempted.
4. **`automation.v7_5_main_supervisor`** logbook entries must be retained across the
   evidence window to reconstruct supervisor execution timestamps.

### 5.4 Event-level export specification

Extend `tools/export_ha_nuisance_evidence.ps1` with a new `-EventLevel` flag
that produces a separate CSV file (not replacing the 15-minute wide-table output)
containing the per-event recorder query:

```sql
SELECT s.entity_id, s.state, s.last_updated, s.last_reported, s.last_changed
FROM states s
JOIN states_meta sm ON s.metadata_id = sm.metadata_id
WHERE sm.entity_id IN (
  -- truth (4 zones + deck)
  'sensor.living_room_temperature_truth',
  'sensor.master_bedroom_temperature_truth',
  'sensor.lincoln_s_room_temperature_truth',
  'sensor.lilly_s_room_temperature_truth',
  'sensor.deck_temperature_truth',
  -- smoothed (cross-validation)
  'sensor.living_room_temperature_smoothed',
  'sensor.master_bedroom_temperature_smoothed',
  'sensor.lincoln_s_room_temperature_smoothed',
  'sensor.lilly_s_room_temperature_smoothed',
  -- control wrappers
  'sensor.living_room_temperature_control',
  'sensor.master_bedroom_temperature_control',
  'sensor.lincoln_s_room_temperature_control',
  'sensor.lilly_s_room_temperature_control',
  -- shadow sensors (all 28)
  'sensor.lr_shadow_filtered_decision',
  'sensor.lr_shadow_raw_decision',
  'sensor.lr_shadow_divergence',
  'sensor.lr_shadow_raw_threshold_distance',
  'sensor.lr_shadow_filtered_threshold_distance',
  'sensor.lr_shadow_raw_value',
  'sensor.lr_shadow_filtered_value',
  'sensor.master_shadow_filtered_decision',
  'sensor.master_shadow_raw_decision',
  'sensor.master_shadow_divergence',
  'sensor.master_shadow_raw_threshold_distance',
  'sensor.master_shadow_filtered_threshold_distance',
  'sensor.master_shadow_raw_value',
  'sensor.master_shadow_filtered_value',
  'sensor.lincoln_shadow_filtered_decision',
  'sensor.lincoln_shadow_raw_decision',
  'sensor.lincoln_shadow_divergence',
  'sensor.lincoln_shadow_raw_threshold_distance',
  'sensor.lincoln_shadow_filtered_threshold_distance',
  'sensor.lincoln_shadow_raw_value',
  'sensor.lincoln_shadow_filtered_value',
  'sensor.lilly_shadow_filtered_decision',
  'sensor.lilly_shadow_raw_decision',
  'sensor.lilly_shadow_divergence',
  'sensor.lilly_shadow_raw_threshold_distance',
  'sensor.lilly_shadow_filtered_threshold_distance',
  'sensor.lilly_shadow_raw_value',
  'sensor.lilly_shadow_filtered_value',
  -- supervisor execution clock
  'automation.v7_5_main_supervisor'
)
AND s.last_updated >= :window_start
AND s.last_updated <= :window_end
ORDER BY s.last_updated ASC;
```

Do not resample. The per-event `last_updated` timestamps are the object of study.

### 5.5 Recorder safety rule

**Do not add `recorder: include: entities:`.**

The current recorder configuration records all HA entities by default. Introducing
an `include: entities:` allow-list would immediately restrict recording to only the
listed entities and would silently stop retaining history for every other entity in
the system — including all entities unrelated to Packet B.

The implementation PR is compliant if and only if:
- `recorder: purge_keep_days: 30` is preserved.
- `recorder: commit_interval: 5` is preserved.
- No `recorder: include:` key is added.
- No `recorder: exclude:` key is added.
- The recorder block in `configuration.yaml` is byte-for-byte identical to
  the pre-implementation version except for purely cosmetic whitespace.

If the Codex implementer believes an include list is needed, that belief is
wrong: all shadow entities are template sensors defined in `configuration.yaml`
and HA automatically records all template sensors. No configuration nudge is needed.

---

## 6. Service-Call and Control-Isolation Guarantees

### 6.1 Absolute service-call prohibition

The Section 17 automation (`v_shadow_evaluator`) contains **exactly one service call**:
`logbook.log`. The following are absolutely prohibited:

```
climate.set_hvac_mode         FORBIDDEN
climate.set_temperature       FORBIDDEN
climate.turn_on / turn_off    FORBIDDEN (any climate.* service)
input_boolean.turn_on/off     FORBIDDEN
timer.start / timer.cancel    FORBIDDEN
input_select.select_option    FORBIDDEN
input_datetime.set_datetime   FORBIDDEN
input_text.set_value          FORBIDDEN
```

Template sensors (Section 16) are defined in `template: sensor:` blocks. They
have no `action:` context and cannot call services by construction.

### 6.2 Live supervisor isolation

- The supervisor variables block is not modified.
- No shadow entity appears in any existing automation trigger, condition, or variable.
- No shadow entity is added to any `continue_on_timeout`, `wait_for_trigger`, or
  `parallel` block of any existing automation.
- The shadow automation’s `time_pattern` trigger fires independently of the supervisor;
  execution order within a 15-minute window is non-deterministic and immaterial (the
  shadow reads current state; it does not produce state the supervisor depends on).

### 6.3 Helper and timer isolation

The shadow evaluator reads `input_boolean.away_mode`, `input_boolean.night_mode_lr_primary`,
`timer.manual_hvac_override`, and `input_boolean.lr_heating_recovery_boost_active` as
read-only gate inputs. It does not start, pause, cancel, toggle, or reset any of them.

### 6.4 Packet A boundary (no duplication)

Packet A (PRs §135, §137, unmerged) owns: `*_truth_ok` guard sensors, the shared
finite-value validity definition (NaN/±inf/out-of-range rejection, −90/200°F band),
protective-OFF behavior, and reconciliation logic.

Packet B MVP owns none of this. The shadow evaluator does not implement any finite-value
guard beyond reading the control wrapper’s existing `float(none) is not none` availability
state. The known `float(none)`-passes-NaN gap in Section 10 wrappers remains Packet A
territory.

### 6.5 Failure containment

If the shadow automation fails (exception, HA restart, logbook service unavailable):
- The supervisor continues unaffected.
- No safety automation changes behavior.
- No climate command is reverted.
- Disabling `v_shadow_evaluator` has zero effect on HVAC control.

---

## 7. Failure Behavior When Observational Inputs Are Missing

| Input missing | Shadow action | Live control effect |
|---|---|---|
| `sensor.*_temperature_control` unavailable | log `filtered_unavailable=true`; skip shadow filtered decision; do **not** fall back to raw | None |
| `sensor.*_temperature_truth` unavailable | log `raw_unavailable=true`; compute shadow from filtered if available; log raw decision as `unavailable` | None |
| `input_select.hvac_season_mode` unavailable | log `gate_input_unavailable=season`; skip all zone decisions for this tick | None |
| `timer.manual_hvac_override` unavailable | log `gate_input_unavailable=override`; proceed with override assumed `idle`; flag in record | None |
| `logbook.log` service unavailable | logbook entry lost silently; template sensors continue updating from Jinja2 | None |
| Template sensor referenced entity unavailable | template sensor state becomes `unavailable`; recorder captures the gap | None |
| Shadow automation disabled or deleted | all shadow logbook writes stop; all shadow template sensors become `unavailable` | None |

No shadow failure propagates to the supervisor, any safety automation, or any HVAC entity.

---

## 8. The Three Documentation Corrections

All three are verified against the repository. They are false under every candidate
architecture. Correcting a false present-tense statement is decision-neutral.

### 8.1 Correction 1 — `configuration.yaml` Section 12 header

**Location:** lines ~1078–1082 (within the `# SECTION 12: SMOOTHED SENSORS` block)

**Current text (false):**
```
# ⚠️  DO NOT DELETE — These lowpass filters smooth the raw truth sensors
#     to prevent control jitter. The control wrappers in Section 10 read
#     from these, and the V8.3 supervisor ultimately acts on the
#     smoothed values. Removing these causes noisy truth spikes to
#     propagate directly into setpoint decisions.
```

**Replacement text:**
```
# ⚠️  DO NOT DELETE — These lowpass filters smooth the raw truth sensors.
#     The control wrappers in Section 10 read from these for UI display.
#     The V8.3 supervisor reads raw sensor.*_temperature_truth directly;
#     it does NOT consume these smoothed sensors or the Section 10 wrappers.
#     Removing these affects dashboards and the Section 16 shadow evaluator
#     only; supervisor and safety control are unaffected.
#     Routing: current MVP behavior. Final architecture decision deferred.
#     See docs/analysis/packet_b_shadow_evidence_mvp.md §8.1.
```

### 8.2 Correction 2 — `configuration.yaml` Section 10 header

**Location:** lines ~927–937 (within the `# SECTION 10` block)

**Current text (false):**
```
# SECTION 10: CONTROL WRAPPERS FOR UI / SUPERVISOR
# ⚠️  DO NOT DELETE — These sensors pass smoothed truth values
#     through a template with unique_id so the V8.3 supervisor
#     and the HA UI can manage them as distinct entities. Without
#     these wrappers, downstream consumers lose their temperature
#     input and control stops working.
```

**Replacement text:**
```
# SECTION 10: CONTROL WRAPPERS FOR UI / DASHBOARD
# ⚠️  DO NOT DELETE — These sensors expose smoothed truth values as
#     stable named entities for the HA UI and dashboard. The V8.3
#     supervisor does NOT consume these wrappers; it reads raw
#     sensor.*_temperature_truth directly. Without these wrappers,
#     UI/dashboard temperature displays are affected; HVAC control
#     and safety automations are unaffected.
#     The Section 16 shadow evaluator reads these as its filtered input.
#     See docs/analysis/packet_b_shadow_evidence_mvp.md §8.2.
```

### 8.3 Correction 3 — `truth_sensor_architecture.md` pipeline diagram

**Location:** lines 38–40 (pipeline block) and the `# Important Dependencies`
section listing `Main Supervisor` as a consumer of the control-wrapper chain.

**Current diagram (false):**
```
Physical Sensors
→ Truth Sensors
→ Smoothed Sensors
→ Control Wrappers
→ HVAC Supervisor
→ Telemetry Logging
```

**Replacement diagram:**
```
Physical Sensors
  │
  ▼
Truth Sensors
  ├──────────────────────────────────────┐
  │                                      │
  ▼                                      ▼
Smoothed Sensors                    HVAC Supervisor   ← reads raw truth
  │                                Safety Automations ← reads raw truth
  ▼                                Telemetry Export   ← reads raw truth
Control Wrappers
  │
  ▼
UI / Dashboard
Shadow Evaluator (read-only, Packet B MVP)
```

**Add after the diagram:**
```markdown
## Routing Note (MVP)

The V8.3 supervisor (`automation.v7_5_main_supervisor`) reads raw
`sensor.*_temperature_truth` entities directly. Safety automations
(runaway cutoff, emergency floor, ceiling gates) also read raw truth.

The smoothed sensors (Section 12) and control wrappers (Section 10) are
consumed by the HA UI/dashboard and the Packet B shadow evaluator only.

This is current MVP runtime behavior. The final decision on permanent
routing remains deferred pending replay evidence.
See `docs/analysis/packet_b_shadow_evidence_mvp.md`.
```

**Also update** the `# Important Dependencies` section listing:
replace `Main Supervisor` with `Safety Gates` and `Telemetry Pipeline` in the
critical-consumer list for truth sensors; remove `Main Supervisor` from any
list that implies it consumes the smoothed/wrapper chain.

### 8.4 Bonus — `configuration.yaml` line ~36 (top-level comment block)

**Current text (false):**
```
#   - Smoothed output → control wrapper → V8.3 supervisor / HA UI
```

**Replacement text:**
```
#   - Smoothed output → control wrapper → HA UI / dashboard
#     (V8.3 supervisor reads raw sensor.*_temperature_truth directly;
#      it does NOT read smoothed or control-wrapper entities)
```

---

## 9. Contract Tests

All eight tests follow the existing repository pattern: pytest over parsed YAML,
no HA runtime required. Style is consistent with `test_truth_freshness_report_time.py`
and siblings in `tests/`.

**Classification:** These eight tests are **MVP isolation and evidence tests**. They
are not routing-doctrine tests. They do not encode Option A as permanent doctrine.
They verify that the shadow evaluator is genuinely observational, that the existing
supervisor and safety inputs are untouched, that the recorder default coverage is
preserved, and that documentation matches actual runtime routing. All eight are
authorized for implementation in the Codex implementation PR.

The six routing-invariant tests described in the companion memo §7 remain deferred
until Gate 8 clears with an Option A result. Those tests are separate from and
additional to the eight tests below.

---

### Test 1: `tests/test_packet_b_supervisor_reads_raw_truth.py`

**Asserts:**
1. In `automations.yaml`, automation id `v7_5_main_supervisor` contains a variables block
   with entity reads matching `sensor.*_temperature_truth` for all four zones and deck.
2. That same variables block contains zero matches for `*_temperature_smoothed`.
3. That same variables block contains zero matches for `*_temperature_control`.
4. No shadow entity (`sensor.*_shadow_*`) appears in the supervisor variables block.
5. `float(70)` fallbacks are on `*_temperature_truth` entities, not on smoothed/control.

### Test 2: `tests/test_packet_b_safety_reads_raw_truth.py`

**Asserts:**
1. `v8_2_lr_runaway_cooling_cutoff` trigger entity is `sensor.living_room_temperature_truth`.
2. `v8_2_master_emergency_floor` trigger entity is `sensor.master_bedroom_temperature_truth`.
3. `v7_5_safety_ceiling_gates` trigger entity list contains only `*_temperature_truth`
   entities (no `*_smoothed`, `*_control`, or `*_shadow_*`).
4. `v7_5_ghost_assassin` references no `*_smoothed` or `*_control` entity.
5. `v9_sleep_priority_interlock` condition references `sensor.living_room_temperature_truth`
   and no smoothed/control entity.

### Test 3: `tests/test_packet_b_shadow_no_climate_calls.py`

**Asserts:**
1. Automation `v_shadow_evaluator` action block matches zero `climate.set_hvac_mode` calls.
2. Automation `v_shadow_evaluator` action block matches zero `climate.set_temperature` calls.
3. Automation `v_shadow_evaluator` action block matches zero `climate.*` service calls of
   any kind.
4. Automation `v_shadow_evaluator` action block matches zero `input_boolean.*` calls.
5. Automation `v_shadow_evaluator` action block matches zero `timer.*` calls.
6. Automation `v_shadow_evaluator` action block contains exactly one service call total:
   `logbook.log`.

### Test 4: `tests/test_packet_b_shadow_failure_isolation.py`

**Asserts:**
1. No automation other than `v_shadow_evaluator` has a trigger, condition, variable, or
   action referencing any `sensor.*_shadow_*` entity.
2. The supervisor automation `v7_5_main_supervisor` has no trigger, condition, wait, or
   variable that depends on `v_shadow_evaluator` or any shadow entity.
3. No Section 3 (safety) automation references any shadow entity.
4. `v_shadow_evaluator` does not appear in any `wait_for_trigger` or `parallel` block of
   any other automation.

### Test 5: `tests/test_packet_b_shadow_same_thresholds.py`

**Asserts:**
1. Shadow template `lr_shadow_filtered_decision` uses `on_at = 72, off_at = 68` for the
   standard (non-away, non-night-mode) cooling branch.
2. Shadow template `lr_shadow_filtered_decision` uses `on_at = 76, off_at = 74` for the
   away branch.
3. Shadow template `master_shadow_filtered_decision` includes a sleep-window branch
   (18:00–06:00) with `on_at = 66, off_at = 62`.
4. No threshold value in any shadow template differs from the corresponding value in the
   supervisor variables block (regex against both files).
5. `v_shadow_evaluator` variables block reads the same gate helpers as the supervisor
   (season, away, override).

### Test 6: `tests/test_packet_b_recorder_safety.py`

**Purpose:** Guard that the implementation PR does not introduce a restrictive recorder
include allow-list into a configuration that previously recorded all entities by default.

**Asserts:**
1. `configuration.yaml` defines template sensors for all 28 shadow entities (7 × 4 zones).
2. Each shadow sensor has a `unique_id` ending in `_v1`.
3. **FAIL if** `configuration.yaml` contains a `recorder:` block with an `include:` sub-key.
   Rationale: adding an include allow-list would stop recorder history for every entity
   not in that list, destroying system-wide observability.
4. **FAIL if** `configuration.yaml` contains a `recorder:` block with an `exclude:`
   sub-key that matches any of: `*_temperature_truth`, `*_temperature_smoothed`,
   `*_temperature_control`, `*_shadow_*`, or `automation.v7_5_main_supervisor`.
5. `configuration.yaml` recorder block contains `purge_keep_days: 30` (not reduced).
6. `configuration.yaml` recorder block contains `commit_interval: 5` (not changed).

### Test 7: `tests/test_packet_b_documentation_routing.py`

**Asserts:**
1. `configuration.yaml` Section 12 comment block does **not** contain
   `"supervisor ultimately acts on the smoothed values"`.
2. `configuration.yaml` Section 10 comment block does **not** contain
   `"CONTROL WRAPPERS FOR UI / SUPERVISOR"`.
3. `truth_sensor_architecture.md` does **not** contain the sequence
   `Control Wrappers` immediately followed (within 3 lines) by `HVAC Supervisor`
   in the pipeline diagram.
4. `truth_sensor_architecture.md` contains `"reads raw truth"` near the supervisor entry.
5. `configuration.yaml` near line 36 does **not** contain
   `"control wrapper → V8.3 supervisor"`.
6. This file (`docs/analysis/packet_b_shadow_evidence_mvp.md`) exists.

### Test 8: `tests/test_packet_b_no_packet_a_duplication.py`

**Asserts:**
1. Section 16 (shadow sensors) in `configuration.yaml` contains no `truth_ok` sensor
   definition or helper reference.
2. Section 16 contains no finite-value range check (`-90`, `200`, `is_finite`, or `NaN`
   references beyond `float(none) is not none`).
3. `v_shadow_evaluator` does not call `climate.set_hvac_mode` with `hvac_mode: off` as
   a protective action.
4. No shadow entity name matches `*_truth_ok`.

---

## 10. Evidence Checkpoints

### Gate 0 — Instrumentation verification (within 24 hours of deployment)

**Pass condition:** All 28 shadow template sensors appear in HA states with non-`unknown`
values. The Section 17 automation has fired at least four consecutive 15-minute ticks
without error. At least one logbook entry with `name: shadow_evaluator` is visible and
parses as valid JSON with non-null `lr.raw` and `lr.ctl` values.

**Fail action:** Diagnose template rendering errors in HA log. Do not open the evidence
window until Gate 0 is clear.

### Gate 1 — First 24-hour data integrity review

**Pass condition:** 24 continuous hours of shadow evidence after Gate 0 passes. No gap
> 16 minutes in shadow logbook entries. Recorder holds state-change events for all
8 smoothed/control entities during the window. Shadow `raw_decision` agrees with actual
climate mode in ≥ 90% of ticks where override is idle and cooling is active.

**Fail action:** Identify and fix instrumentation errors. Reset 24-hour clock.

### Gate 2 — 48 hours active cooling minimum

**Pass condition:** At least 48 continuous hours with `Season_Mode = cooling` (or active
shoulder-cooling with outdoor > 70°F). At least one zone running `cool` per day.
Minimum 48 rows in `VTherm_Launch_Data_v5_5` meeting these criteria.

**Context (2026-06-10):** May telemetry showed shoulder season. June is the expected
transition to sustained cooling season. The evidence window should open no earlier
than the first confirmed 48-hour cooling period.

**Fail action:** Extend observation until 48 active cooling hours are confirmed.

### Gate 3 — Band-edge crossings per zone

**Pass condition:** At least 3 ticks per controlled zone where
`sensor.<zone>_shadow_raw_threshold_distance` is in the range [−1.0, +1.0]°F, OR
at least one `sensor.<zone>_shadow_divergence = different` per zone during the window.

Rationale: divergence between raw and filtered decisions concentrates near thresholds.
A window with no threshold approaches cannot characterize lag versus chatter suppression.

**Fail action:** Extend the observation window.

### Gate 4 — 7–14-day collection window (preferred)

**Pass condition:** 7+ days of continuous shadow evidence with Gates 0–3 satisfied.
14-day window preferred to capture household behavioral variability.

### Gate 5 — Extension rule for insufficient cooling

If 14 days pass without satisfying Gates 2 and 3 for all zones: extend in 7-day
increments until satisfied, up to a maximum of 42 total days. If 42 days passes without
sufficient cooling crossings, document the limitation, proceed to Gate 6 with partial
evidence, and require the Fable review to note the gap.

### Gate 6 — Replay cross-validation (halt gate)

Before any architecture conclusion:

1. Implement `y[n] = round(0.9·y[n−1] + 0.1·x[n], 2)` over the native-granularity
   truth event sequence from the recorder export (§5.4).
2. Compare replayed series against recorded `sensor.*_temperature_smoothed` series.
3. **Halt condition:** if the replayed series deviates from recorded smoothed by > 0.05°F
   for more than 5% of events, the filter model or event-acceptance assumptions are wrong.
   Re-derive before any architecture conclusion. This is the halt gate from PR §138 §3.2(2)
   that the companion review memo confirmed was never run against the claimed evidence.

**This gate is the primary instrument for clearing the §3.4 decision block.** Passing it
produces the cross-validated per-event replay that the companion review requires.

### Gate 7 — Divergence and harm/benefit classification

Apply PR §138 §3.4 decision rule to the cleared evidence:

| Result | Classification | Decision implication |
|---|---|---|
| Divergence ≈ 0, small tick deltas | Zero-divergence | Option A supported |
| Divergence > 0, delayed-OFF/ON dominates | Harmful divergence | Option A strengthened |
| Divergence > 0, chatter suppression dominates | Beneficial divergence | Option B/C candidate |
| Divergence > 0, neither harm nor benefit clear | Ambiguous | Extend window or reanalyze |

Required metrics: divergent-decision rate, chatter rate (raw ON reversals within one tick),
overcooling °F·min (filter lag past off-threshold), engagement delay °F·min, per-zone
counts (companion review finding: concentration matters).

### Gate 8 — Fable final architecture review handoff

**Evidence package:** recorder event export CSV, shadow logbook entries, V5.5 export rows,
cross-validation result (Gate 6), per-zone divergence table (Gate 7), annotated band-edge
crossing examples, supervisor execution timestamp reconstruction.

**Fable applies** PR §138 §3.4 branch logic to the verified evidence and selects Option A,
Option B/C, or strengthens the block. This MVP design does not pre-approve any option.

**Optional restart:** A controlled HA restart inside the evidence window (operationally safe,
timestamped) may be included to observe filter cold-start / recorder-priming behavior.

---

## 11. Rollback Plan

### Primary rollback (shadow-only)

**Step 1:** Remove `v_shadow_evaluator` automation block from `automations.yaml` Section 17.
Stops all shadow logbook writes.

**Step 2:** Remove Section 16 block from `configuration.yaml`.
Removes all 28 shadow template sensors. Because the recorder has no include list,
removing the shadow template sensors automatically stops recording them — no recorder
YAML change is needed and none should be made.

**Time to rollback:** one HA configuration reload, < 60 seconds.

**Effect on live control:** zero. No climate command is reverted. No helper state is
changed. No supervisor tick is altered. V5.5 export continues. Safety automations
continue. Recorder continues recording all remaining entities as before.

### Documentation rollback

The §8 documentation corrections change comments and markdown, not logic. If they
introduce confusion, revert via `git revert` on the commit that landed them.
Reverting documentation does not change any control path.

### Post-rollback verification

- `automation.v_shadow_evaluator` no longer appears in HA automation list.
- `sensor.lr_shadow_*` (and other zone shadow entities) no longer appear in HA states.
- The supervisor fires its next tick without error.
- V5.5 export continues at the next 15-minute tick.
- `configuration.yaml` recorder block is unchanged from pre-implementation.
- Contract test 4 (shadow failure isolation) and test 6 (recorder safety) still pass.

### Non-rollback scope

The rollback applies to shadow instrumentation only. It does not revert the supervisor to
filtered truth (the supervisor never read filtered truth). It does not change the recorder
configuration in either direction.

---

## 12. Explicitly Deferred Decisions

### 12.1 Final raw-versus-filtered routing (primary deferral)

Not decided here. The companion memo and PR §138 block this decision until the Gate 6
cross-validation and Gate 7 divergence classification clear with verified evidence. This
MVP does not constitute a routing decision and must not be read as one.

### 12.2 Control-wrapper availability enhancement

Deferred per PR §138 §5 reclassification. Section 10 wrapper availability semantics
(`float(none) is not none`) are unchanged. Any change to wrapper availability transitions
requires its own analysis of UI/dashboard effects and its own PR.

### 12.3 Packet A and Packet B composition

Deferred until both Packet A is deployed and the routing decision is made. Under Option A
(raw truth permanent) the packets are independent. Under Option B/C, Packet A guards would
need re-pointing at the new supervisor input. Sequencing depends on Gate 8.

### 12.4 Option B/C migration protocol

If Gate 7 yields net-beneficial divergence, PR §138 §3.4 migration protocol applies: one-zone
shadow-to-staging promotion per PR, independent rollback, full gate sequence per zone. This
MVP does not constitute a shadow trial and must not be cited as one. The shadow evaluator is
observational only and issues zero climate commands.

### 12.5 Routing-invariant contract tests (companion review §7)

The companion memo (Section 7) specifies six routing-invariant tests contingent on Option A
landing from Gate 8. Those tests encode Option A as permanent doctrine and must not be
implemented until Gate 8 produces an Option A result.

**They are distinct from §9 Tests 1–8.** Tests 1–8 in §9 are MVP isolation and evidence
tests authorized now. The six companion-memo routing-invariant tests are a separate set,
authorized only after Gate 8.

---

## 13. Codex Implementation Handoff

### Phase 1: This design PR (#139) — already complete

PR #139 contains two design documents only. It does **not** contain any test files,
YAML changes, or implementation artifacts. Nothing in PR #139 should be interpreted as
an instruction to create files in this PR.

### Phase 2: Codex implementation PR — what Codex must do next

A separate implementation PR must make exactly the changes in §13.2 and create all eight
tests from §9 with full implementations. The implementation PR is not ready until every
test passes.

### 13.1 Authorized scope (exact, applies to the Codex implementation PR)

| Action | File | Detail |
|---|---|---|
| Add Section 16 shadow template sensors | `configuration.yaml` | 28 entities, 7 per zone, per §3.2A |
| **Preserve recorder block unchanged** | `configuration.yaml` | `purge_keep_days: 30`, `commit_interval: 5` — add no `include:` or `exclude:` key; see §5.5 |
| Correct Section 12 comment | `configuration.yaml` | Replace text per §8.1 exactly |
| Correct Section 10 comment | `configuration.yaml` | Replace text per §8.2 exactly |
| Correct line ~36 comment | `configuration.yaml` | Replace text per §8.4 exactly |
| Add Section 17 shadow automation | `automations.yaml` | `v_shadow_evaluator`, logbook.log only, per §3.2B |
| Correct pipeline diagram | `truth_sensor_architecture.md` | Replace diagram and add routing note per §8.3 |
| Update §6.6 note | `docs/5_runtime_layer.md` | Add shadow sensors to Evidence components list |
| Create and fully implement all 8 tests | `tests/` | Per §9.1–9.8; all assertions real, all tests passing |

### 13.2 Tests: implementation requirements for the Codex implementation PR

PR #139 is a design document. It contains no test files. The eight test files listed below
must be **created and fully implemented** in the Codex implementation PR.

| File | §Ref |
|---|---|
| `tests/test_packet_b_supervisor_reads_raw_truth.py` | §9.1 |
| `tests/test_packet_b_safety_reads_raw_truth.py` | §9.2 |
| `tests/test_packet_b_shadow_no_climate_calls.py` | §9.3 |
| `tests/test_packet_b_shadow_failure_isolation.py` | §9.4 |
| `tests/test_packet_b_shadow_same_thresholds.py` | §9.5 |
| `tests/test_packet_b_recorder_safety.py` | §9.6 |
| `tests/test_packet_b_documentation_routing.py` | §9.7 |
| `tests/test_packet_b_no_packet_a_duplication.py` | §9.8 |

**Requirements:**
- All assertions must be fully implemented. No TODO placeholders. No `pass` bodies.
  No `pytest.mark.skip`. No `@unittest.expectedFailure`.
- All eight new tests must pass before the implementation PR is ready for review.
- The full existing test suite must continue to pass.
- `tests/test_yaml_syntax.py` must pass.

**Classification:** these eight tests are MVP isolation and evidence tests, not routing-doctrine
tests. They verify observational isolation, recorder safety, and documentation accuracy — not
which input path the supervisor uses as permanent doctrine. All eight are authorized now.
Only the six routing-invariant tests from the companion memo §7 remain deferred.

### 13.3 Prohibited scope (exact, applies to the Codex implementation PR)

| Prohibited action | Reason |
|---|---|
| Modifying `automations.yaml` Section 2 supervisor variables block | Routing decision blocked |
| Modifying any threshold value | No evidence; no authority |
| Modifying any safety automation trigger, condition, or threshold | Safety invariant; routing blocked |
| Adding shadow entities as supervisor inputs | Would constitute a routing change |
| Calling any `climate.*` service from shadow | Absolute prohibition per §6.1 |
| Calling any `input_*` or `timer.*` service from shadow | Absolute prohibition per §6.3 |
| **Adding `recorder: include: entities:`** | **Would immediately stop recording all entities not in the list; destroys system-wide observability** |
| **Adding `recorder: exclude:`** | **Would suppress evidence entities from recorder** |
| **Reducing `purge_keep_days` below 30** | **Would lose evidence before the observation window completes** |
| Implementing routing-invariant tests (companion memo §7) | Encodes Option A as doctrine; blocked until Gate 8 |
| Implementing or citing a one-zone pilot migration | Not authorized until Gate 7 |
| Modifying control wrapper availability logic | Deferred per §12.2 |
| Opening a second PR from this design document | User instruction: do not open another PR |

### 13.4 Codex implementation PR: ordered steps

These steps apply to the **Codex implementation PR**, not to PR #139.

1. Create all 8 test files from §9 with full assertion implementations (not stubs).
2. Add Section 16 shadow template sensors to `configuration.yaml`.
3. Verify `configuration.yaml` recorder block is unchanged: `purge_keep_days: 30`,
   `commit_interval: 5`, no `include:`, no `exclude:`. Make no recorder YAML change.
4. Apply comment corrections 1, 2, and bonus (4) to `configuration.yaml` (§8.1, §8.2, §8.4).
5. Add Section 17 automation to `automations.yaml`.
6. Apply correction 3 to `truth_sensor_architecture.md` (§8.3).
7. Update `docs/5_runtime_layer.md` §6.6 with shadow sensor note.
8. Run `tests/test_yaml_syntax.py` — must pass.
9. Run all 8 new tests — all must pass with real assertions.
10. Run full existing test suite — all must continue to pass.
11. Confirm `test_packet_b_recorder_safety.py` assertions 3 and 4 pass (no include/exclude
    introduced).
12. Commit and push.

### 13.5 Post-merge operator checklist (after the Codex implementation PR merges)

1. Confirm Gate 0 within 24 hours of merge.
2. Note evidence window start time.
3. Schedule Gate 1 review for 24 hours later.
4. Confirm recorder is capturing `sensor.*_shadow_*` entities in HA history —
   no configuration change should have been needed; if entities are absent from
   history, the implementation PR introduced a recorder regression and must be reverted.
5. Do not perform offline replay until Gate 6 data exists (recorder data for the full window).
6. Do not interpret any divergence finding as an architecture decision until Gate 8 Fable review.

---

```
═══════════════════════════════════════════════════════════════
PACKET B MVP DESIGN APPROVED FOR IMPLEMENTATION
Final raw-vs-filtered routing decision: REMAINS BLOCKED
See companion memo: packet_b_architecture_decision_review.md
═══════════════════════════════════════════════════════════════
```
