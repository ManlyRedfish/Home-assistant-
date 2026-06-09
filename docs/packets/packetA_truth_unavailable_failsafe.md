# Packet A — Design Audit: Truth Sensor Unavailable During Active Cooling

**Type:** Design / engineering audit. **Read-only — DO NOT APPLY.**
**Date:** 2026-06-09  **Branch:** `claude/compassionate-davinci-8ly5pv`  **PR:** #135
**Audit provenance:** `docs/audits/v8_3_supervisor_audit_2026-06-09.md`
**Scope guard:** This packet designs the sensor-loss fail-safe **only**. It does
**not** touch raw-vs-smoothed/control input (Packet B), compressor cooldown
enforcement (V9 backlog), thresholds, the 61 °F target, or hardware. Proposed
YAML is illustrative and must not be committed to `automations.yaml` /
`configuration.yaml` until separately approved.

**Status (2026-06-09):** All three design decisions **APPROVED** (see §Decisions).
Static contract tests added in `tests/test_packetA_truth_unavailable_failsafe.py`
— implementation-facing checks are `xfail(strict=False)` until Codex applies the
runtime change; healthy-state/doctrine checks pass now and must stay green.

---

## 0. Audit source verification

Verified directly against the repository (not inferred from live HA):

- Supervisor `v7_5_main_supervisor`, alias *"V8.3: Main Supervisor"*
  (`automations.yaml:358`), `mode: single`, trigger `time_pattern /15` + state
  change on `input_select.hvac_season_mode` (`:361-365`), gated on
  `timer.manual_hvac_override == idle` (`:366-369`).
- Inputs read **raw** `sensor.*_temperature_truth` with `float(70)` fallback,
  no unavailable handling (`automations.yaml:372-376` — re-read 2026-06-09).
- Cooling deadband + operators per zone (`:417-492`), thresholds test-locked by
  `tests/test_section2_cooling_setpoint_doctrine.py` (9/9 green).
- Truth-based safety gates are `numeric_state` triggers: LR runaway 60 °F
  (`:737-753`), Master floor 58 °F (`:778-792`), ceiling 76 °F (`:810-856`).
- Repo automation IDs: `v8_2_lr_runaway_cooling_cutoff`,
  `v8_2_master_emergency_floor`. The packet's live entity IDs
  (`…_lr_equipment_protection_2`, `…master_emergency_cooling_floor`) are
  HA-registry slugs; the `_2` suffix implies a duplicate registration to confirm
  live (see Unknowns).

## 0.1 Failure mode — arithmetic confirmed

When a zone's truth is `unavailable`/`unknown`, `states()` returns a non-numeric
string and `| float(70)` yields **70**. Per operating band:

| Mode (not away) | off_at / on_at | 70 vs band | Supervisor result | Hazard |
|---|---|---|---|---|
| Standard (LR/Lincoln/Lilly, Master day) | 68 / 72 | between | **HOLD prior state** | False HOLD — cooling persists with no truth shutoff |
| Master sleep 18:00–06:00 | 62 / 66 | above on_at | **COOL** | False COOL — spurious cooling created |
| Away | 74 / 76 | ≤ off_at | **OFF** | False OFF — masks the fault, but unit stops |

Compounding hazard: every truth-based safety gate (`numeric_state` on the same
truth entity) is **inert** while that entity is non-numeric. During a truth
outage the supervisor may HOLD/COOL **and** the 60/58/76 °F gates cannot fire —
cooling toward the 61 °F demand has **no truth-based shutoff** until recovery.
Classification: **likelihood Low, severity Moderate, no observed incident.**

---

## 1. Recommended design + rationale

**Two coordinated, additive parts — Design 1 (recommended):**

**(1a) Supervisor per-zone truth-validity guard (tick-level correctness).**
Before the deadband comparison, compute a per-zone `*_truth_ok` flag and, when
false, force a protective decision (**never COOL; drop active cooling to OFF**).
This eliminates the `float(70)` false-HOLD and false-COOL paths at every 15-min
tick and is per-zone independent.

**(1b) Event-triggered protective-OFF automation (speed + cross-season).**
A new dedicated automation triggers on each truth entity transitioning to
`unavailable`/`unknown` (short debounce via `for:`), and if the matching climate
entity is `cool`, forces it OFF — **regardless of season**, **never creating a
cooling command**.

**Why both, and why this is the safest default:**
- The supervisor guard alone is **tick-bound** (≤15 min, and only inside the
  cooling branch). It cannot meet "act sooner" or cross-season protection.
- The event automation alone races the supervisor: in **Master sleep**, an
  unguarded supervisor re-issues COOL every tick (false-COOL), fighting the
  fail-safe's OFF → oscillation. The guard removes that re-cool, so the two
  **only ever drive toward OFF** when truth is bad — **no conflicting commands.**
- Both are **per-zone independent** (one failed sensor never touches the other
  three). When truth is healthy, behavior is **byte-for-byte unchanged**, so
  regression comparability is preserved.
- **Recovery authority stays with the V8.3 supervisor**: the fail-safe never
  turns anything ON. When truth becomes numeric again, the guard passes and the
  supervisor resumes on its next trigger, subject to all existing gates.

**Debounce = `for: "00:02:00"` — APPROVED.** The truth `availability` template
only goes false when **every** contributor is stale (>7200 s) or absent
(`configuration.yaml:248-257`), so a genuine `unavailable` is already a sustained
fault, not a value blip. The 2-minute window exists mainly to ride out **HA
restart / integration reload**, where entities are briefly `unavailable` before
first report. 2 min of extra cooling is acceptable because this fail-safe is the
*only* live protection during the outage and is far inside the 60 °F runaway
margin. A 60 s alternative is offered for operators who prefer faster action.

**Manual-override interaction — APPROVED: ignore override.** The protective-OFF
fires **regardless of `timer.manual_hvac_override`**, matching the runaway/floor
equipment-protection precedent (those gates do **not** check override). Manual
override is a comfort/control authority, not an equipment-safety bypass.

---

## 2. Options comparison (all five required)

| Option | Time to protective OFF | False-shutdown risk | Recovery | Race risk | Restart behavior | Helpers/timers | Supervisor-fail behavior | Flapping behavior | Std / Sleep / Away |
|---|---|---|---|---|---|---|---|---|---|
| **1. Immediate forced OFF** (no debounce) | seconds | Higher (HA-restart blips trip it) | Supervisor resumes | Low (with guard) | None (never restarts) | none | Still protects (independent automation) | Can fire on every blip | Off in all; guard stops re-cool |
| **2. Debounce → forced OFF** *(recommended, with guard)* | ~2 min | Low (rides out restarts) | Supervisor resumes | **None** (both drive OFF) | None | none (guard inline) | Still protects | Bounded by `for:`+15-min cadence | Correct in all three |
| **3. Timeout-degraded → OFF** | up to N min running "blind" | Low | Supervisor resumes | Low | None | 1 timer/zone | Protects after timeout | Timer churn | Allows blind cooling during timeout — weaker |
| **4. Alert-only** | never (human) | n/a | Manual | n/a | n/a | none | **No protection** | n/a | **Rejected** — leaves the hazard live |
| **5. Per-zone inhibit helper** | event speed | Low | Supervisor resumes when inhibit clears | Low | None | 4 `input_boolean` | Protects | Helper toggle churn | Needs supervisor to read inhibit; +4 helpers |

**Selected: Option 2 + supervisor guard.** Option 4 rejected (no protection).
Option 3 rejected (intentionally permits blind cooling). Option 5 is the viable
**alternative (Design 2)** if the operator prefers not to edit the supervisor's
hvac_mode templates — but it adds 4 helpers and still requires a supervisor read,
so it is more moving parts for the same outcome.

---

## 3. Proposed YAML / pseudocode — **DO NOT APPLY**

### 3a. Supervisor guard (illustrative edit to `automations.yaml`)
Add per-zone validity flags to the top variables block (`:371-380`):
```yaml
# DO NOT APPLY — illustrative
lr_truth_ok:      "{{ has_value('sensor.living_room_temperature_truth')   and states('sensor.living_room_temperature_truth')   | float(none) is not none }}"
master_truth_ok:  "{{ has_value('sensor.master_bedroom_temperature_truth') and states('sensor.master_bedroom_temperature_truth') | float(none) is not none }}"
lincoln_truth_ok: "{{ has_value('sensor.lincoln_s_room_temperature_truth') and states('sensor.lincoln_s_room_temperature_truth') | float(none) is not none }}"
lilly_truth_ok:   "{{ has_value('sensor.lilly_s_room_temperature_truth')   and states('sensor.lilly_s_room_temperature_truth')   | float(none) is not none }}"
```
Then prepend a guard to each zone's cooling `hvac_mode` template (Master shown;
LR/Lincoln/Lilly identical pattern):
```yaml
# DO NOT APPLY — illustrative (Master, cf. automations.yaml:426-431)
hvac_mode: >-
  {% if not master_truth_ok %}off
  {% elif master_temp > m_on_at %}cool
  {% elif master_temp <= m_off_at %}off
  {% elif m_current == 'cool' %}cool
  {% else %}off{% endif %}
```
`has_value()` returns false for `unknown`/`unavailable`; the `float(none) is not
none` clause also rejects any other non-numeric. When `*_truth_ok` is true the
template is unchanged → **healthy behavior identical**. This does **not** alter
the variables checked by `test_section2_cooling_setpoint_doctrine.py` (it asserts
`*_setpoint`/`*_off_at`/`*_on_at`, not the hvac_mode string), so that suite stays
green.

### 3b. Event protective-OFF automation (new block — DO NOT APPLY)
```yaml
# DO NOT APPLY — illustrative new automation
- id: v8_6_truth_unavailable_cooling_failsafe
  alias: "V8.6: Truth-Unavailable Cooling Fail-Safe (Per-Zone Protective OFF)"
  mode: parallel
  max: 4
  trigger:
    - platform: state
      entity_id: sensor.living_room_temperature_truth
      to: ["unavailable", "unknown"]
      for: "00:02:00"
      id: climate.living_room_air
    - platform: state
      entity_id: sensor.master_bedroom_temperature_truth
      to: ["unavailable", "unknown"]
      for: "00:02:00"
      id: climate.master_bedroom_air
    - platform: state
      entity_id: sensor.lincoln_s_room_temperature_truth
      to: ["unavailable", "unknown"]
      for: "00:02:00"
      id: climate.lincoln_air
    - platform: state
      entity_id: sensor.lilly_s_room_temperature_truth
      to: ["unavailable", "unknown"]
      for: "00:02:00"
      id: climate.lilly_air
  condition:
    # Only act if the matching unit is actually cooling. Cross-season by design:
    # no season gate — protective OFF allowed even in heating/shoulder.
    - condition: template
      value_template: "{{ is_state(trigger.id, 'cool') }}"
  action:
    - action: climate.set_hvac_mode
      target: { entity_id: "{{ trigger.id }}" }
      data: { hvac_mode: "off" }
    - action: notify.notify
      data:
        title: "🌡️⚠️ Truth-Unavailable Cooling Fail-Safe"
        message: >
          {{ trigger.id }} forced OFF — its truth sensor went
          unavailable/unknown for >2 min while the unit was cooling.
          Truth-based safety gates (runaway/floor/ceiling) are blind until
          the sensor recovers. Investigate the sensor/integration; the V8.3
          supervisor will resume control automatically on recovery.
```
Notes: `mode: parallel, max: 4` keeps zones independent; the automation **only
ever commands OFF** (never `cool`); commands carry an automation context so the
`v7_5_waf_manual_override` watcher (which requires `context.parent_id is none`)
is **not** tripped. If the climate entity is already `off`/`heat`/`unavailable`,
the `cool`-only condition skips it (no needless command).

---

## 4. Entity & automation dependency map

```
TRUTH (raw, control input)         CLIMATE (writes)            SAFETY (numeric_state on truth)
sensor.living_room_temperature_truth ─┬─► climate.living_room_air      v8_2_lr_runaway_cooling_cutoff (LR, <60)
sensor.master_bedroom_temperature_truth ─► climate.master_bedroom_air  v8_2_master_emergency_floor (Master, <58)
sensor.lincoln_s_room_temperature_truth ─► climate.lincoln_air         v7_5_safety_ceiling_gates (M/Lin/Lil, >76)
sensor.lilly_s_room_temperature_truth ──► climate.lilly_air
            │                                   ▲
            │ (unavailable/unknown >2m)          │ resumes on recovery
            └─► [NEW] v8_6_truth_unavailable_cooling_failsafe ─► protective OFF (cool-only, any season)
            └─► [GUARD] v7_5_main_supervisor *_truth_ok → OFF (cooling branch, per tick)
Gating helper: timer.manual_hvac_override (supervisor only; fail-safe recommended to IGNORE)
Diagnostic-only (NOT used here): binary_sensor.*_heat_pump_firing, sensor.*_temperature_{smoothed,control}
```

---

## 5. Race / conflict analysis

- **Supervisor vs fail-safe (truth bad):** both target the same entity toward
  **OFF** (guard → off; fail-safe → off). No opposing command. Without the guard,
  Master-sleep would race (supervisor COOL vs fail-safe OFF) — the guard is what
  removes the race.
- **Recovery window:** when truth returns numeric, the fail-safe condition is
  false (won't fire) and the guard passes; the supervisor's next tick/trigger is
  sole re-enable authority. No independent restart.
- **WAF manual-override watcher:** fail-safe commands have a parent context →
  `parent_id` not none → watcher does not start `timer.manual_hvac_override`. No
  false override.
- **Existing safety gates:** unaffected; they remain blind during the outage
  (their limitation, not a new conflict) and re-arm on recovery. Fail-safe
  complements them by covering exactly the blind window.
- **`mode` choices:** fail-safe `parallel/max:4` → no cross-zone queueing.
  Supervisor stays `single`.

---

## 6. Exact sequence (unavailable → debounce → OFF → recovery)

1. `t0`: zone truth → `unavailable` (all contributors stale/absent).
2. `t0…t0+2m`: debounce. Supervisor, if it ticks here, sees `*_truth_ok=false`
   → commands OFF (cooling branch) — early protection in-season.
3. `t0+2m`: fail-safe fires **iff** climate entity == `cool` → `set_hvac_mode
   off` + notify. Cross-season.
4. Outage persists: each supervisor tick keeps the zone OFF (guard); fail-safe
   won't re-fire unless the truth re-enters then re-exits the unavailable state
   for >2 min while cooling (cannot, since it's OFF).
5. `tR`: truth → numeric. Fail-safe inert. Next supervisor trigger: guard passes,
   normal deadband resumes; COOL only if `temp > on_at` and all season/away/
   sleep/safety gates permit.

---

## 7. Tests

### 7a. Static (repo-style, pytest over parsed YAML — proposed)
- `test_truth_unavailable_failsafe_present`: automation
  `v8_6_truth_unavailable_cooling_failsafe` exists; 4 state triggers to
  `['unavailable','unknown']` with `for >= 60s`, each `id` = a `climate.*_air`;
  condition gates on `is_state(trigger.id,'cool')`; action sets
  `hvac_mode: off`; **no** action sets `cool`.
- `test_supervisor_truth_guard_present`: top variables define
  `lr_/master_/lincoln_/lilly_truth_ok` using `has_value(...)`; each cooling
  `hvac_mode` template begins with `{% if not <zone>_truth_ok %}off`.
- `test_doctrine_unchanged`: `test_section2_cooling_setpoint_doctrine.py` still
  green (thresholds/targets untouched).

### 7b. Acceptance (runtime / trace — operator-executed)
| # | Scenario | Expected |
|---|---|---|
| 1 | Std, cooling, truth→unavail | Fail-safe OFF ≤2 min; cooling not indefinite |
| 2 | Std, off, truth→unavail | No COOL created (guard) |
| 3 | Master sleep, off, truth→unavail | **No false-COOL** (guard) — key fix |
| 4 | Away, truth→unavail | Explicit OFF via guard, not float-OFF accident |
| 5 | One zone fails | Other 3 controlled normally |
| 6 | Healthy truth | `<=off_at`/`>on_at`/HOLD unchanged |
| 7 | Cooling while season=heating/shoulder | Protective OFF allowed; no COOL |
| 8 | Truth restored | Supervisor resumes ≤1 cycle; fail-safe doesn't restart |

### 7c. Recovery tests
- Restored truth ≤ band → no inappropriate restart.
- Restored truth > on_at → supervisor MAY restart only if all gates permit.
- Repeated flap → no rapid cycling (bounded by `for:` + 15-min cadence).
- Supervisor disabled while fail-safe active → unit not stuck cooling (fail-safe
  already forced OFF; nothing re-cools).

### 7d. Failure-mode tests
- All 4 truths unavailable, all 4 cooling → all forced OFF independently.
- Unavailable during Master sleep / during away → §7b #3/#4.
- HA restart mid-outage → debounce rides startup; on restore, supervisor resumes.
- Fail-safe automation disabled/errors → supervisor guard still prevents
  re-cool in-season (defense in depth); cross-season gap noted.
- Truth restores just before/at a supervisor run → guard passes; normal decision.

---

## 8. Rollback plan

1. Pre-change state captured here + audit doc + trace
   `2cc51682fc628808ecb3a00c6b499204`.
2. Revert: `git revert <commit>` or `git checkout -- automations.yaml`
   (removes the `v8_6_…` block and the supervisor guard lines).
3. `python -m pytest tests/` must return to the prior green set (and the two new
   static tests are removed/skipped with the revert).
4. `ha core check` (or HA *Developer Tools → YAML check*) clean; reload
   automations.
5. Confirm supervisor trace shows the original `float(70)` path restored.

## 9. Post-change observation plan

- Watch `notify` events + `hvac_provenance_log` for any `v8_6_…` firing.
  Expectation under healthy sensors: **~0 firings**. Any firing ⇒ investigate the
  sensor/integration, not the threshold.
- For ≥7 days, count: fail-safe firings/zone, supervisor `*_truth_ok=false`
  ticks, and confirm **zero false shutdowns** (fail-safe fired while truth was
  actually numeric — should be impossible by construction).
- Confirm regression comparability: healthy-state runtime/setpoint telemetry
  unchanged vs. pre-change baseline.

---

## 10. Codex implementation prompt (self-contained — use only after operator approval)

> **Task:** Apply **only** Packet A Design 1 (truth-unavailable cooling fail-safe)
> to the live Moose House HAOS repo. Design source of truth:
> `docs/packets/packetA_truth_unavailable_failsafe.md` on branch
> `claude/compassionate-davinci-8ly5pv` (PR #135). Decisions are APPROVED:
> 2-minute persistence, ignore manual override, Design 1 (no inhibit helpers).
>
> **Hard exclusions:** make **no** Packet B smoothing/control changes; **no** V9
> compressor-cooldown changes; do **not** alter any threshold, equality operator
> (`<= off_at`, `> on_at`, else HOLD), the 61 °F target, away logic, the Master
> 18:00–06:00 sleep band, or four-zone independence; add no hardware; do not
> treat `binary_sensor.*_heat_pump_firing` as physical proof.
>
> 1. **Inspect first, edit second.** Read the live `automations.yaml` in full
>    before any change. Resolve the supervisor identity: repository `id:
>    v7_5_main_supervisor` vs live entity `automation.v7_5_main_supervisor_rev_b`
>    — match by `id:`, `alias:` ("V8.3: Main Supervisor (Deadband Cooling +
>    Heating)"), and YAML source location. Confirm you are editing the single
>    canonical supervisor block before proceeding.
> 2. **Create a Git checkpoint:** `git rev-parse HEAD` (record), and
>    `git stash list`/`git status` clean check; tag or branch as needed so the
>    pre-change state is recoverable.
> 3. **Add four per-zone truth-validity guards** in the supervisor's first
>    `variables:` block: `lr_truth_ok`, `master_truth_ok`, `lincoln_truth_ok`,
>    `lilly_truth_ok`, each = `{{ has_value(<truth>) and states(<truth>) |
>    float(none) is not none }}` for the matching `sensor.*_temperature_truth`.
>    This validation must occur **before** any `float(70)` fallback is used as a
>    control value.
> 4. **Guard each cooling-branch `hvac_mode` template** (LR, Master, Lincoln,
>    Lilly) by prepending `{% if not <zone>_truth_ok %}off` as the **first**
>    branch, ahead of the existing `> on_at`/`<= off_at`/HOLD logic, which must
>    remain byte-identical otherwise. Result: unavailable/non-numeric truth ⇒
>    that zone is commanded OFF (never COOL, never HOLD-on-stale).
> 5. **Add the event automation** `v8_6_truth_unavailable_cooling_failsafe`
>    exactly per design §3b: `mode: parallel, max: 4`; four `state` triggers, one
>    per `sensor.*_temperature_truth`, `to: ['unavailable','unknown']`,
>    `for: "00:02:00"`, `id:` = the matching `climate.*_air`; condition
>    `is_state(trigger.id,'cool')`; action `climate.set_hvac_mode` →
>    `hvac_mode: off` on `{{ trigger.id }}` + a `notify.notify`. It must have
>    **no** condition referencing `timer.manual_hvac_override`, and **no** action
>    that issues `cool` or otherwise restores cooling.
> 6. **Configuration validation:** run `ha core check` (HAOS) — must be clean.
> 7. **Repository tests:** run the full suite `python -m pytest tests/`. All
>    previously-green tests stay green; the Packet A `xfail` contract tests in
>    `tests/test_packetA_truth_unavailable_failsafe.py` must now **xpass/pass**.
>    (Once confirmed, flip them from `xfail(strict=False)` to plain asserts.)
> 8. **Reload minimally if safe:** reload the `automation` domain (and `template`
>    only if touched — it is not in this packet). If a full restart is required
>    in your environment, state that instead of forcing a reload.
> 9. **Verify via traces, not by endangering rooms:** inspect the supervisor
>    trace to confirm the guard path renders `off` for a simulated
>    unavailable/non-numeric truth and that healthy-truth traces are unchanged;
>    confirm the fail-safe automation registers its four triggers. Do **not**
>    physically force a real sensor offline in a way that leaves an occupied room
>    unsafe. Capture `run_id`s.
> 10. **Exact rollback (if any step fails or review rejects):**
>     `git checkout -- automations.yaml` (discard the guard + new automation), or
>     `git revert <checkpoint-range>` if already committed; re-run
>     `python -m pytest tests/` and `ha core check`; reload the `automation`
>     domain; confirm the supervisor trace shows the original `float(70)` path.
>
> Do not merge or deploy without operator sign-off. Produce a diff for review
> first; report files changed, `ha core check` output, full pytest results, and
> the verifying `run_id`s.

---

## Decisions — APPROVED 2026-06-09
1. **Debounce:** 2-minute persistent unavailable/non-numeric requirement on the
   event-triggered protective-OFF automation. ✅ APPROVED. (Filters brief
   SmartThings/template glitches; acts well before the 15-min supervisor cycle;
   within the accepted maximum response window.)
2. **Manual override:** the fail-safe **ignores** `timer.manual_hvac_override`,
   following the runaway-cooling / emergency-floor equipment-protection
   precedent. ✅ APPROVED.
3. **Architecture — Design 1.** ✅ APPROVED. Per-zone `*_truth_ok` validation
   inside the V8.3 supervisor **before** any `float(70)`/deadband comparison;
   unavailable/non-numeric truth ⇒ that zone is commanded OFF. Plus a separate
   event-triggered protective-OFF automation (2-min persistence, **OFF-only**,
   never COOL, never independently restores cooling). Recovery authority remains
   solely with the V8.3 supervisor once truth is numeric again. Do **not** add
   four persistent inhibit helpers unless repository constraints prove Design 1
   cannot be implemented safely.

## Remaining unknowns (not silently resolved)
- Live entity ID of the supervisor (`…` vs `…_rev_b`) and the `_2` suffix on the
  LR runaway automation — resolve in live HA registry before Codex applies.
- `input_select.hvac_season_mode` / `input_boolean.*` / `timer.manual_hvac_override`
  are UI/storage helpers, not in repo YAML — option lists unverifiable here.
- Whether a climate entity can report a transient `cool` during its own
  `unavailable` recovery (Samsung cloud) — minor edge; condition `cool`-gate
  handles it conservatively.

**Reconciliation result:** Packet A design complete; no production change made.
Packet B (raw vs smoothed/control) and V9 cooldown enforcement remain separate
and out of scope here.
