# Packet A — Design Audit: Truth Sensor Unavailable During Active Cooling

**Type:** Design / engineering audit. **Read-only — DO NOT APPLY.**
**Date:** 2026-06-09  **Branch:** `claude/compassionate-davinci-8ly5pv`  **PR:** #135
**Audit provenance:** `docs/audits/v8_3_supervisor_audit_2026-06-09.md`
**Scope guard:** This packet designs the sensor-loss fail-safe **only**. It does
**not** touch raw-vs-smoothed/control input (Packet B), compressor cooldown
enforcement (V9 backlog), thresholds, the 61 °F target, or hardware. Proposed
YAML is illustrative and must not be committed to `automations.yaml` /
`configuration.yaml` until separately approved.

**Status (2026-06-09, pass 3 — hardened):** All three design decisions
**APPROVED** (see §Decisions). Pass-3 hardening applied on top of pass 2:

1. **Finite-value validity (BLOCKER 1 fixed).** The shared validity test no
   longer relies on `float(none) is not none` alone — that wrongly **accepted**
   `"NaN"`, `"inf"`, `"Infinity"`, etc., because they parse to floating-point
   values. The supervisor guard, the event automation, and the reconciliation
   sweep now use **one shared finite-value definition** (§3.0) that rejects
   `unknown`, `unavailable`, empty/non-numeric strings, **NaN**, **+infinity**,
   and **−infinity**.
2. **Reconciliation preserves the 2-minute persistence (BLOCKER 2 fixed).** The
   `/5` periodic sweep and the startup sweep now force OFF **only** when truth
   has been invalid for **≥ 2 minutes** (state-age check on the truth entity's
   current invalid-state timestamp), so an automation reload can no longer turn
   a unit off on a brief invalid blip. Worst-case reconciliation response stays
   well under the 15-minute maximum.
3. A restart/reload-safe **reconciliation** automation (§3c) still closes the
   `for:`-reset blind spot; (4) the test gate is **enforceable** (a
   normal-priority gate test fails the suite if the guard is implemented but
   `xfail` markers remain); (5) the notifier is **non-blocking** and must be
   verified, never gating the protective OFF.

Contract tests: `tests/test_packetA_truth_unavailable_failsafe.py` — **design-only
baseline: 156 passed, 17 xfailed** (23 design-proving Packet A checks pass now —
including behavioral proof that NaN/±infinity are rejected and that the
reconciliation 2-minute persistence holds; 17 `xfail(strict=False)` are the
implementation contracts that flip to passing once the YAML lands). **Expected
post-implementation: 173 passed, 0 xfailed, 0 xpassed** once Codex applies the
YAML and removes the markers.

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
A new dedicated automation triggers on each truth entity becoming **invalid**
under the shared finite-value definition (§3.0) — i.e. `unavailable`, `unknown`,
a parse failure, **NaN**, or **±infinity** (short debounce via `for:`), and if
the matching climate entity is `cool`, forces it OFF — **regardless of season**,
**never creating a cooling command**.

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

### 3.0 Shared finite-value validity definition (BLOCKER 1) — **one definition, three users**

A truth value is a **valid control temperature** only if it is a **finite
number**. The earlier `float(none) is not none` test is **insufficient**:
`"NaN"`, `"nan"`, `"inf"`, `"-inf"`, `"Infinity"` all parse to floating-point
values and would slip through. NaN makes every threshold comparison evaluate
false (false HOLD); ±infinity forces extreme threshold outcomes. So the test must
reject **all** of:

`unknown`, `unavailable`, empty/non-numeric strings, **NaN**, **+infinity**,
**−infinity**.

There is no single universally-portable finite predicate in older HA Jinja, so
the canonical definition uses a **clearly documented combination**, verified
against HA template behavior (Home Assistant's own `is_number()` test also
rejects NaN/inf on modern cores; the explicit form below is version-robust and
self-documenting):

* parse with `float(none)` → `none` on any non-numeric/`unknown`/`unavailable`/empty,
* `x is not none` → rejects all parse failures,
* `x == x` → **rejects NaN** (NaN is the only value not equal to itself),
* `SAFETY_TEMP_MIN_F <= x <= SAFETY_TEMP_MAX_F` → **rejects ±infinity** (and any
  absurd reading), because no finite comparison admits `inf`/`-inf`.

**SAFETY plausibility band — validity only, NOT a comfort/control threshold:**

| Constant | Value (°F) | Purpose |
|---|---|---|
| `SAFETY_TEMP_MIN_F` | **−90** | lower validity bound; far below any real indoor reading |
| `SAFETY_TEMP_MAX_F` | **+200** | upper validity bound; far above any real indoor reading |

These two bounds are **deliberately broad safety-validation limits**. They are
intentionally documented **here, apart from every HVAC threshold** (the 61 °F
target; 68/72 home; 74/76 away; 62/66 Master sleep; 60/58/76 safety gates) and
must never be confused with or narrowed toward comfort thresholds. Their only job
is to reject `±inf`/absurd values while never rejecting a genuine temperature.

```jinja
{# Canonical VALID form (supervisor `*_truth_ok`) — truth is finite & usable #}
{% set x = states('<truth_entity>') | float(none) %}
{{ x is not none and x == x and -90 <= x <= 200 }}

{# Canonical INVALID form (event trigger / reconciliation) — exact negation #}
{% set x = states('<truth_entity>') | float(none) %}
{{ x is none or x != x or x < -90 or x > 200 }}
```

The supervisor guard uses the VALID form; the event automation and reconciliation
use the INVALID form. They are **exact logical negations** of one another
(proven across `err`/`NaN`/`nan`/`inf`/`-inf`/`Infinity`/empty/`unknown`/
`unavailable` and ordinary signed & decimal temperatures by
`test_supervisor_and_event_validity_are_semantically_identical`), so **no value
is rejected by one path but missed by another**.

### 3a. Supervisor guard (illustrative edit to `automations.yaml`)
Add per-zone validity flags to the top variables block (`:371-380`), each using
the **canonical VALID form** from §3.0:
```yaml
# DO NOT APPLY — illustrative (finite-value validity; SAFETY band -90..200 °F)
lr_truth_ok: >-
  {% set x = states('sensor.living_room_temperature_truth') | float(none) %}
  {{ x is not none and x == x and -90 <= x <= 200 }}
master_truth_ok: >-
  {% set x = states('sensor.master_bedroom_temperature_truth') | float(none) %}
  {{ x is not none and x == x and -90 <= x <= 200 }}
lincoln_truth_ok: >-
  {% set x = states('sensor.lincoln_s_room_temperature_truth') | float(none) %}
  {{ x is not none and x == x and -90 <= x <= 200 }}
lilly_truth_ok: >-
  {% set x = states('sensor.lilly_s_room_temperature_truth') | float(none) %}
  {{ x is not none and x == x and -90 <= x <= 200 }}
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
The `float(none)` parse rejects `unknown`/`unavailable`/empty/non-numeric, `x ==
x` rejects NaN, and the `-90..200` band rejects ±infinity (see §3.0). When
`*_truth_ok` is true the template is unchanged → **healthy behavior identical**.
This does **not** alter the variables checked by
`test_section2_cooling_setpoint_doctrine.py` (it asserts
`*_setpoint`/`*_off_at`/`*_on_at`, not the hvac_mode string), so that suite stays
green.

### 3b. Event protective-OFF automation (new block — DO NOT APPLY)

Uses **template triggers**, not `state … to: [unavailable, unknown]`, so the
validity test matches the supervisor guard **exactly** and catches **every**
invalid value — `unavailable`, `unknown`, a parse failure (`"err"`), **NaN**, and
**±infinity** — not only the two known states. Shared **INVALID** form from §3.0
(truth is INVALID iff):
`{% set x = states(<truth>) | float(none) %}{{ x is none or x != x or x < -90 or x > 200 }}`.
```yaml
# DO NOT APPLY — illustrative new automation
- id: v8_6_truth_unavailable_cooling_failsafe
  alias: "V8.6: Truth-Unavailable Cooling Fail-Safe (Per-Zone Protective OFF)"
  mode: parallel
  max: 4
  trigger:
    # Each value_template is the canonical INVALID form (§3.0): true when truth
    # is unavailable/unknown/parse-failure/NaN/±infinity.
    - platform: template
      value_template: >-
        {% set x = states('sensor.living_room_temperature_truth') | float(none) %}
        {{ x is none or x != x or x < -90 or x > 200 }}
      for: "00:02:00"
      id: climate.living_room_air
    - platform: template
      value_template: >-
        {% set x = states('sensor.master_bedroom_temperature_truth') | float(none) %}
        {{ x is none or x != x or x < -90 or x > 200 }}
      for: "00:02:00"
      id: climate.master_bedroom_air
    - platform: template
      value_template: >-
        {% set x = states('sensor.lincoln_s_room_temperature_truth') | float(none) %}
        {{ x is none or x != x or x < -90 or x > 200 }}
      for: "00:02:00"
      id: climate.lincoln_air
    - platform: template
      value_template: >-
        {% set x = states('sensor.lilly_s_room_temperature_truth') | float(none) %}
        {{ x is none or x != x or x < -90 or x > 200 }}
      for: "00:02:00"
      id: climate.lilly_air
  condition:
    # Only act if the matching unit is actually cooling. Cross-season by design:
    # no season gate — protective OFF allowed even in heating/shoulder.
    - condition: template
      value_template: "{{ is_state(trigger.id, 'cool') }}"
  action:
    # Protective OFF FIRST — it must not depend on any notification succeeding.
    - action: climate.set_hvac_mode
      target: { entity_id: "{{ trigger.id }}" }
      data: { hvac_mode: "off" }
    # Notification is SECONDARY and non-blocking. continue_on_error guarantees a
    # missing/failed notifier cannot invalidate the protective OFF above.
    # Codex must verify the live notify service (see §10); if none is approved,
    # drop this step entirely — the OFF action stands alone.
    - action: notify.notify          # VERIFY-OR-REPLACE (non-blocking)
      continue_on_error: true
      data:
        title: "🌡️⚠️ Truth-Unavailable Cooling Fail-Safe"
        message: >
          {{ trigger.id }} forced OFF — its truth input was invalid
          (unavailable/unknown/parse failure/NaN/±infinity) for >2 min while the
          unit was cooling. Truth-based safety gates are blind until recovery. The
          V8.3 supervisor resumes control automatically once truth is finite again.
```
Notes: `mode: parallel, max: 4` keeps zones independent; the automation **only
ever commands OFF** (never `cool`); commands carry an automation context so the
`v7_5_waf_manual_override` watcher (requires `context.parent_id is none`) is
**not** tripped. The `cool`-only condition skips units already `off`/`heat`.
**`for: "00:02:00"` resets on automation reload / HA restart — §3c covers that.**

### 3c. Restart / reload reconciliation (new block — DO NOT APPLY)

HA template (and `for:`) edges are **not** re-fired for a condition that was
already true before an automation reload or HA restart — a sensor already
invalid across that boundary would otherwise sit in a blind spot until the
15-min supervisor tick. This automation closes that gap with two restart-safe
triggers and an all-zone sweep. **Chosen approach: `homeassistant` start trigger
(with a bounded settle delay) + a periodic reconciliation sweep.** Rationale:
the start trigger handles HA restart promptly; the periodic `time_pattern`
handles **automation reload** (which fires no start event), and the supervisor's
15-min tick remains the final scheduled backstop.

**BLOCKER 2 — reconciliation must honour the 2-minute persistence.** The pass-2
sweep forced OFF whenever truth was invalid **at that instant**. That bypassed
the approved 2-minute debounce: right after an automation reload, a *brief*
invalid blip could shut a cooling unit down immediately. The corrected sweep
forces OFF only when **all three** hold:

* the climate entity state is `cool`,
* truth is invalid under the **shared finite-value definition** (§3.0), **and**
* that invalid state has **persisted ≥ 2 minutes**, measured from the truth
  entity's **current invalid-state timestamp** (`last_changed`).

**Why `last_changed` is a safe age basis (verified against HA behavior):** when a
sensor's value transitions from a number to an invalid state (e.g. `unavailable`,
or a `NaN`/`inf` string), HA updates that entity's `last_changed`. So
`now() - states[truth].last_changed` is the age of the **current** invalid
episode. An **automation reload does not touch entity states**, so this age
*survives a reload* and the debounce is genuinely preserved (it is **not** reset
by the reload, unlike a trigger `for:` timer). After a **full HA restart**,
`last_changed` re-initialises to the restart time; the start path therefore keeps
its **3-minute settle delay**, and after that delay the **same ≥ 2-minute
invalid-age rule still applies explicitly** — startup cannot bypass persistence.

**Worst-case timing:** the periodic sweep fires at the first `/5` tick at which
the invalid age has already reached 2 minutes, so the worst-case reconciliation
response is **≈ 7 minutes** (a `/5` cadence plus the 2-minute floor), comfortably
**under the 15-minute maximum**. The event automation (§3b) still handles the
ordinary case at 2 minutes; reconciliation only matters across the reload/restart
boundary where the event `for:` edge is not re-fired.
```yaml
# DO NOT APPLY — illustrative new automation
- id: v8_6b_truth_unavailable_cooling_reconciliation
  alias: "V8.6b: Truth-Unavailable Cooling Reconciliation (Restart/Reload Safe)"
  mode: single
  trigger:
    - platform: homeassistant
      event: start
      id: reconcile_start
    - platform: time_pattern
      minutes: "/5"
      id: reconcile_periodic
  action:
    # On HA start, let sensors report before judging validity (avoid startup
    # false-positives from briefly-unavailable entities). Periodic runs: no wait.
    - choose:
        - conditions: "{{ trigger.id == 'reconcile_start' }}"
          sequence:
            - delay: "00:03:00"
    # Sweep all four zones; force OFF any unit cooling while its truth has been
    # invalid for >= 2 minutes. Per-item condition preserves four-zone
    # independence. OFF-only. The age gate (last_changed) makes this safe across
    # an automation reload — a brief invalid blip will NOT force OFF.
    - repeat:
        for_each:
          - { truth: sensor.living_room_temperature_truth,    climate: climate.living_room_air }
          - { truth: sensor.master_bedroom_temperature_truth, climate: climate.master_bedroom_air }
          - { truth: sensor.lincoln_s_room_temperature_truth, climate: climate.lincoln_air }
          - { truth: sensor.lilly_s_room_temperature_truth,   climate: climate.lilly_air }
        sequence:
          - if:
              - condition: template
                value_template: >-
                  {% set x = states(repeat.item.truth) | float(none) %}
                  {% set invalid = x is none or x != x or x < -90 or x > 200 %}
                  {% set st = states[repeat.item.truth] %}
                  {% set invalid_age = (now() - st.last_changed).total_seconds()
                     if st is not none else 0 %}
                  {{ is_state(repeat.item.climate, 'cool')
                     and invalid and invalid_age >= 120 }}
            then:
              - action: climate.set_hvac_mode
                target: { entity_id: "{{ repeat.item.climate }}" }
                data: { hvac_mode: "off" }
```
The reconciliation also covers "**reload mid-persistence**": if a reload drops a
pending 2-min `for:` edge, the next periodic sweep re-evaluates the zone — and
because the age basis (`last_changed`) survives the reload, a zone that has been
cooling+invalid for ≥ 2 min is forced OFF on that sweep, while a zone that only
*just* went invalid is left alone until its age reaches 2 min. No persistent
inhibit helpers are required.

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
  Supervisor stays `single`; reconciliation `single`.
- **Reconciliation (`v8_6b`) vs event fail-safe vs supervisor:** all three only
  ever command **OFF** on a cooling+invalid zone, so they converge — no opposing
  commands. Reconciliation exists solely to cover the restart/reload boundary
  where the event automation's `for:` edge is not re-fired; it shares the exact
  **finite-value validity definition** (§3.0), so it never disagrees about
  validity. It also shares the **same 2-minute persistence**: its `≥120 s`
  invalid-age gate means it never forces OFF faster than the event path would —
  removing the post-reload "instant shutdown on a blip" hazard (BLOCKER 2). Its
  start-path settle `delay` prevents startup-unavailable false positives; its
  `/5` sweep + 2-minute floor bounds the worst-case response (~7 min) below the
  15-min supervisor backstop.

---

## 6. Exact sequence (invalid → debounce → OFF → recovery)

1. `t0`: zone truth → **invalid** (`unavailable`/`unknown`/parse failure/NaN/
   ±infinity — all contributors stale/absent, or a non-finite reading). HA stamps
   `last_changed = t0`.
2. `t0…t0+2m`: debounce. Supervisor, if it ticks here, sees `*_truth_ok=false`
   → commands OFF (cooling branch) — early protection in-season.
3. `t0+2m`: event fail-safe fires **iff** climate entity == `cool` → `set_hvac_mode
   off` + notify. Cross-season. (If an automation reload dropped the `for:` edge,
   the reconciliation sweep takes over: it forces OFF on the next `/5` tick at
   which the invalid age is already ≥ 2 min — never sooner.)
4. Outage persists: each supervisor tick keeps the zone OFF (guard); event
   fail-safe won't re-fire unless the truth re-enters then re-exits the invalid
   state for >2 min while cooling (cannot, since it's OFF).
5. `tR`: truth → finite again. Event fail-safe inert; reconciliation inert
   (invalid age resets). Next supervisor trigger: guard passes, normal deadband
   resumes; COOL only if `temp > on_at` and all season/away/sleep/safety gates
   permit.

---

## 7. Tests

### 7a. Static + behavioral (implemented: `tests/test_packetA_truth_unavailable_failsafe.py`)
40 tests. **23 pass now and must stay green** (doctrine + design-proving
behavioral checks of the canonical validity/reconciliation expressions); **17 are
`xfail(strict=False)`** until the runtime change lands (Codex removes the marks
at implementation). Design-only run: **156 passed, 17 xfailed** suite-wide.

*Always-green — doctrine preservation:*
- `test_healthy_state_doctrine_unchanged` — setpoints 61, thresholds, away,
  Master sleep band all unchanged.
- `test_healthy_deadband_behavior_unchanged` — renders the Master template:
  `>on_at`→cool, `<=off_at`→off, else HOLD, with healthy truth.

*Always-green — design-proving finite-value validity (BLOCKER 1):*
- `test_finite_validity_rejects_invalid_values` (parametrized) — proves
  `err`, **`NaN`**, **`nan`**, **`inf`**, **`-inf`**, `Infinity`, empty,
  `unknown`, `unavailable` are all rejected by the canonical definition.
- `test_finite_validity_accepts_healthy_temperatures` (parametrized) — ordinary
  **signed and decimal** temperatures (`70`, `61.5`, `-3.2`, `0`, …) stay valid.
- `test_supervisor_and_event_validity_are_semantically_identical` — the
  supervisor VALID form and the event/reconciliation INVALID form are exact
  negations across every candidate ⇒ one shared definition.

*Always-green — design-proving reconciliation persistence (BLOCKER 2):*
- `test_reconciliation_decision_holds_off_when_invalid_age_under_two_minutes` —
  invalid for 60 s / 119 s while cooling ⇒ **no OFF**.
- `test_reconciliation_decision_forces_off_when_invalid_age_at_least_two_minutes`
  — invalid for 120 s / 600 s (incl. `NaN`) while cooling ⇒ **OFF**.
- `test_reconciliation_decision_ignores_healthy_and_noncooling` — healthy truth,
  or a non-cooling unit ⇒ never OFF.

*Always-green — enforceable gate:*
- `test_packet_a_xfail_markers_removed_once_implemented` — **enforceable gate.**
  If the supervisor guard is present in YAML (implemented) it asserts **zero**
  `xfail` markers remain in this module; in design phase it asserts the markers
  are present. This fails the suite if YAML is implemented but markers are left
  (the dangerous strict=False XPASS state).

*xfail until implemented — supervisor guard:*
- `test_supervisor_defines_per_zone_truth_ok` — each `*_truth_ok` carries the
  **finite-value** definition (`float(none)`, NaN self-test, ±90/200 bounds).
- `test_supervisor_guard_rejects_nan_and_infinity` — renders each live
  `*_truth_ok` expression and confirms **NaN / +inf / −inf** read invalid while
  ordinary temperatures read valid.
- `test_cooling_hvac_templates_guard_unavailable_before_cool`,
  `test_unavailable_truth_forces_off_each_zone` (behavioral render),
  `test_master_sleep_unavailable_cannot_create_cool` (behavioral render).

*xfail until implemented — event fail-safe:*
- `test_event_failsafe_present_per_zone_validity_triggers` — **template**
  triggers, one per zone, `id` = climate entity, `for` = 2 min.
- `test_event_failsafe_validity_uses_finite_value_definition` — trigger templates
  carry the finite-value definition and render `NaN`/`inf`/`-inf`/`err`/
  `unavailable` as invalid (not just `unavailable`/`unknown`).
- `test_event_failsafe_two_minute_persistence`,
  `test_event_failsafe_only_commands_off_and_gates_on_cooling`,
  `test_event_failsafe_ignores_manual_override`,
  `test_event_failsafe_recovery_never_turns_cooling_on`.
- `test_protective_off_not_blocked_by_notification` — climate OFF precedes any
  notify, and any notify carries `continue_on_error: true`.

*xfail until implemented — restart/reload reconciliation:*
- `test_reconciliation_present_restart_and_reload_safe` — `v8_6b…` has a
  `homeassistant` **start** trigger **and** a `time_pattern` trigger.
- `test_reconciliation_startup_settle_delay` — start path has a bounded `delay`.
- `test_reconciliation_uses_finite_value_definition` — sweeps all four zones,
  OFF-only, with the **shared** finite-value definition.
- `test_reconciliation_requires_two_minute_invalid_persistence` — the sweep
  checks `last_changed` and requires **≥ 2 min** of persistent invalid truth
  (BLOCKER 2).
- `test_reconciliation_startup_does_not_bypass_persistence` — every OFF is inside
  an `if` whose condition carries the `last_changed` age gate; no unconditional
  OFF; the start path keeps its settle `delay`.

### 7b. Acceptance (runtime / trace — operator-executed)
| # | Scenario | Expected |
|---|---|---|
| 1 | Std, cooling, truth→invalid | Fail-safe OFF ≤2 min; cooling not indefinite |
| 2 | Std, off, truth→invalid | No COOL created (guard) |
| 3 | Master sleep, off, truth→invalid | **No false-COOL** (guard) — key fix |
| 4 | Away, truth→invalid | Explicit OFF via guard, not float-OFF accident |
| 5 | One zone fails | Other 3 controlled normally |
| 6 | Healthy truth | `<=off_at`/`>on_at`/HOLD unchanged |
| 7 | Cooling while season=heating/shoulder | Protective OFF allowed; no COOL |
| 8 | Truth restored | Supervisor resumes ≤1 cycle; fail-safe doesn't restart |
| 9 | Truth = `NaN`/`inf` string (cooling) | Treated as invalid → protective OFF |
| 10 | Reload while truth invalid <2 min (cooling) | Reconciliation does **not** OFF until age ≥2 min |

### 7c. Recovery tests
- Restored truth ≤ band → no inappropriate restart.
- Restored truth > on_at → supervisor MAY restart only if all gates permit.
- Repeated flap → no rapid cycling (bounded by `for:` + 15-min cadence).
- Supervisor disabled while fail-safe active → unit not stuck cooling (fail-safe
  already forced OFF; nothing re-cools).

### 7d. Failure-mode tests
- All 4 truths invalid, all 4 cooling → all forced OFF independently.
- Invalid during Master sleep / during away → §7b #3/#4.
- Truth reports a `NaN`/`inf`/`Infinity` string → treated as invalid (BLOCKER 1).
- HA restart mid-outage → 3-min settle then ≥2-min age gate; on restore,
  supervisor resumes. Automation reload mid-outage → reconciliation re-evaluates
  but only OFFs once invalid age ≥ 2 min (BLOCKER 2).
- Fail-safe automation disabled/errors → supervisor guard still prevents
  re-cool in-season (defense in depth); cross-season gap noted.
- Truth restores just before/at a supervisor run → guard passes; normal decision.

---

## 8. Rollback plan

1. Pre-change state captured here + audit doc + trace
   `2cc51682fc628808ecb3a00c6b499204`.
2. Revert: `git revert <commit>` or `git checkout -- automations.yaml`
   (removes the `v8_6_…` and `v8_6b_…` blocks and the supervisor guard lines).
3. `python -m pytest tests/` — if the contract-test file is also reverted to the
   design state, the suite returns to **156 passed, 17 xfailed**; if only the
   YAML is reverted while the un-marked tests remain, the Packet A contracts will
   fail (re-add the `xfail` marks to return to the design baseline).
4. `ha core check` (or HA *Developer Tools → YAML check*) clean; reload
   automations.
5. Confirm supervisor trace shows the original `float(70)` path restored.

## 9. Post-change observation plan

- Watch `notify` events + `hvac_provenance_log` for any `v8_6_…` firing.
  Expectation under healthy sensors: **~0 firings**. Any firing ⇒ investigate the
  sensor/integration, not the threshold.
- For ≥7 days, count: fail-safe firings/zone, supervisor `*_truth_ok=false`
  ticks, and confirm **zero false shutdowns** (fail-safe fired while truth was
  actually a finite number — should be impossible by construction).
- Confirm regression comparability: healthy-state runtime/setpoint telemetry
  unchanged vs. pre-change baseline.

---

## 10. Codex implementation prompt (self-contained — two-stage, operator-gated)

> **Task:** Apply **only** Packet A Design 1 (truth-unavailable cooling fail-safe)
> to the live Moose House HAOS repo. Design source of truth:
> `docs/packets/packetA_truth_unavailable_failsafe.md` (this document, pass-3
> hardened) plus its contract tests
> `tests/test_packetA_truth_unavailable_failsafe.py`. Decisions are APPROVED:
> 2-minute persistence, ignore manual override, Design 1 (no inhibit helpers),
> **shared finite-value validity** (rejects NaN/±infinity), and **reconciliation
> that preserves the 2-minute persistence**.
>
> **Hard exclusions:** make **no** Packet B smoothing/control changes; **no** V9
> compressor-cooldown changes; do **not** alter any threshold, equality operator
> (`<= off_at`, `> on_at`, else HOLD), the 61 °F target, away logic, the Master
> 18:00–06:00 sleep band, or four-zone independence; add no hardware; do not
> treat `binary_sensor.*_heat_pump_firing` as physical proof. **Do not narrow the
> SAFETY validity band (−90/200 °F) toward comfort values** — it is a validity
> bound only.
>
> ### Repository workflow (run BEFORE any edit — do not assume the checkout already has PR #135)
>
> A. **Record the starting point:** `git branch --show-current`, `git rev-parse
>    HEAD`, and `git status --porcelain` (must be clean). Note them in your report.
> B. **Fetch the approved design:** `git fetch origin
>    claude/compassionate-davinci-8ly5pv` (PR #135), **or** the branch the
>    operator names if this correction was pushed elsewhere (e.g.
>    `claude/awesome-babbage-bokpj0`). Do not delete or rewrite local branches.
> C. **Verify the design commit:** confirm design commit `cac37b0` **or its
>    pass-3 successor** is present (`git log` / `git show <sha> --stat`). If the
>    operator points you at a successor commit, use that; record which.
> D. **Ensure the inputs exist before implementing:** confirm
>    `docs/packets/packetA_truth_unavailable_failsafe.md` and
>    `tests/test_packetA_truth_unavailable_failsafe.py` are present at the design
>    commit. If either is missing, **STOP** and report.
> E. **Branch from current production:** create a **separate implementation
>    branch** from the **current production base** (the live-deployed `main`/HEAD),
>    e.g. `git switch -c codex/packetA-impl <production-base>`. Do **not** implement
>    directly on the design branch.
> F. **Bring in design + tests without clobbering newer config:** copy/cherry-pick
>    **only** the Packet A doc and the contract-test file onto the implementation
>    branch. Do **NOT** let the design branch's older `automations.yaml` /
>    `configuration.yaml` overwrite **newer production** YAML — diff first and keep
>    production runtime config.
> G. **Divergence guard:** if repository history or the live `automations.yaml`
>    has **diverged materially** from what this design assumes (supervisor block
>    moved/renamed, thresholds changed, truth entities renamed), **STOP** and
>    report the divergence instead of forcing the change.
>
> ---
> ### STAGE 1 — Review-only implementation (NO live changes; STOP for approval)
>
> 1. **Inspect first, edit second.** Read the live `automations.yaml` in full.
>    Resolve the supervisor identity: repository `id: v7_5_main_supervisor` vs a
>    possible live entity `automation.v7_5_main_supervisor_rev_b` — match by
>    `id:`, `alias:` ("V8.3: Main Supervisor (Deadband Cooling + Heating)"), and
>    YAML source location. Confirm you are editing the single canonical
>    supervisor block before proceeding.
> 2. **Add four per-zone truth-validity guards** in the supervisor's first
>    `variables:` block — `lr_truth_ok`, `master_truth_ok`, `lincoln_truth_ok`,
>    `lilly_truth_ok` — each the **canonical VALID form** from §3.0 for the
>    matching `sensor.*_temperature_truth`:
>    `{% set x = states(<truth>) | float(none) %}{{ x is not none and x == x and
>    -90 <= x <= 200 }}`. This validation must occur **before** any `float(70)`
>    fallback is used as a control value. (`x == x` rejects NaN; the −90/200 band
>    rejects ±infinity.)
> 3. **Guard each cooling-branch `hvac_mode` template** (LR, Master, Lincoln,
>    Lilly) by prepending `{% if not <zone>_truth_ok %}off` as the **first**
>    branch, ahead of the existing `> on_at`/`<= off_at`/HOLD logic, which must
>    remain byte-identical otherwise. Result: invalid truth (unavailable /
>    unknown / parse failure / NaN / ±infinity) ⇒ that zone is commanded OFF
>    (never COOL, never HOLD-on-stale).
> 4. **Add the event automation** `v8_6_truth_unavailable_cooling_failsafe`
>    exactly per §3b: `mode: parallel, max: 4`; **four `template` triggers** (NOT
>    `state … to:[unavailable,unknown]`), one per zone, each the **canonical
>    INVALID form**: `{% set x = states(<truth>) | float(none) %}{{ x is none or x
>    != x or x < -90 or x > 200 }}`, `for: "00:02:00"`, `id:` = the matching
>    `climate.*_air`. This validity must be the **exact negation** of the
>    supervisor guard so no value (incl. NaN/±infinity) is caught by one path but
>    missed by the other. Condition `is_state(trigger.id,'cool')`. Action:
>    **`climate.set_hvac_mode off` FIRST**, then an optional **non-blocking**
>    notification (`continue_on_error: true`) — the OFF must never depend on it.
>    **No** condition on `timer.manual_hvac_override`; **no** action issuing
>    `cool` or restoring cooling.
> 5. **Notifier — do not hard-code an unverified service.** Before using
>    `notify.notify`, confirm an approved notify service resolves in the live
>    config. If verified, keep it with `continue_on_error: true`. If not, **omit
>    the notify step entirely** — the protective OFF stands alone.
> 6. **Add the reconciliation automation** `v8_6b_truth_unavailable_cooling_reconciliation`
>    exactly per §3c: triggers = `homeassistant` `event: start` **and**
>    `time_pattern minutes:"/5"`; on the start path apply a bounded settle
>    `delay: "00:03:00"` before sweeping; then a `repeat.for_each` over the four
>    `{truth, climate}` pairs forcing `hvac_mode: off` only where the per-item
>    `value_template` is true: unit `is_state(climate,'cool')` **and** truth is
>    invalid (shared §3.0 definition) **and** the invalid state has persisted
>    **≥ 120 s** via `(now() - states[truth].last_changed).total_seconds() >=
>    120`. **The age gate is mandatory** — without it an automation reload could
>    instantly shut a unit off on a brief blip (BLOCKER 2). OFF-only; four-zone
>    independent; **no** inhibit helpers.
> 7. **Static + parse validation:** parse the YAML
>    (`python -c "import yaml,glob; [yaml.safe_load(open(f)) for f in
>    ['automations.yaml']]"` with the repo's custom-tag loader, or the test
>    suite's loader) and run **`ha core check` when it is available**; report its
>    output. If `ha core check` is unavailable in this environment, say so — do
>    not fake it.
> 8. **Make the test gate enforceable — in this order:**
>    a. implement the YAML (steps 2–6);
>    b. **remove all `xfail` markers** in
>       `tests/test_packetA_truth_unavailable_failsafe.py` (leave none);
>    c. run the full suite `python -m pytest tests/ -rA`;
>    d. **require every Packet A test to PASS as a normal assertion** — **zero
>       Packet A XFAIL and zero XPASS**. A green exit with remaining XPASS/XFAIL is
>       **not** acceptance; the `test_packet_a_xfail_markers_removed_once_implemented`
>       gate fails the suite if markers remain after the guard is implemented.
>    Expected final result (no unrelated test-count changes): **173 passed, 0
>    xfailed, 0 xpassed** (design-only baseline is **156 passed + 17 xfailed**;
>    the 17 convert to passes once implemented and un-marked).
> 9. **Produce the exact diff and rollback plan, then STOP.** Output the full
>    `git diff` of the implementation branch and a concrete rollback (`git
>    checkout -- automations.yaml tests/test_packetA_truth_unavailable_failsafe.py`
>    or `git revert <range>`; re-run pytest + `ha core check`). **Do NOT reload
>    automations, do NOT merge, and do NOT touch live HA state.** Wait for
>    explicit operator approval.
>
> ---
> ### STAGE 2 — Deployment (ONLY after explicit operator approval)
>
> 1. **Apply/merge** the approved implementation branch to the live configuration.
> 2. **Minimum safe reload:** reload the **`automation`** domain only. An
>    automation reload **registers the new automations and their `time_pattern`
>    periodic trigger without a full HA restart** — a restart is **not** required
>    to arm the reconciliation sweep. Only the `homeassistant` **start** trigger
>    itself waits for the next actual HA start to fire (its job is solely the
>    post-restart settle sweep); the periodic `/5` trigger covers the interim. Do
>    not force a restart.
> 3. **Confirm registration:** verify `automation.v8_6_truth_unavailable_cooling_failsafe`
>    shows four template triggers and `automation.v8_6b_truth_unavailable_cooling_reconciliation`
>    shows its start + `/5` periodic triggers, and that the supervisor reloaded
>    with the four `*_truth_ok` guards.
> 4. **Observe ordinary behavior:** confirm the supervisor trace renders `off`
>    for a (template-simulated) invalid truth and is **unchanged** for healthy
>    truth; watch normal traces and state for one or more ordinary cycles.
> 5. **Do not fabricate evidence by endangering rooms.** Do **not** disable a real
>    sensor or force a unit offline to manufacture a live `run_id`. A live trigger
>    trace is welcome **post-deployment evidence when it occurs safely on its
>    own**, but it is **not** a prerequisite and must not be coerced.
> 6. **Report:** files changed, reload method, registration confirmation, the
>    pytest summary (0 XFAIL / 0 XPASS for Packet A), and any naturally-observed
>    traces. Keep the Stage-1 rollback plan ready.

---

## Decisions — APPROVED 2026-06-09 (pass-3 hardened)
1. **Debounce:** 2-minute persistent **invalid-truth** requirement on the
   event-triggered protective-OFF automation, **and** the same 2-minute
   invalid-age requirement on the reconciliation sweep (BLOCKER 2). ✅ APPROVED.
   (Filters brief SmartThings/template glitches; acts well before the 15-min
   supervisor cycle; reconciliation can no longer instant-OFF after a reload.)
2. **Manual override:** the fail-safe **ignores** `timer.manual_hvac_override`,
   following the runaway-cooling / emergency-floor equipment-protection
   precedent. ✅ APPROVED.
3. **Architecture — Design 1.** ✅ APPROVED. Per-zone `*_truth_ok` validation
   inside the V8.3 supervisor **before** any `float(70)`/deadband comparison;
   **invalid** truth ⇒ that zone is commanded OFF. Plus a separate
   event-triggered protective-OFF automation (2-min persistence, **OFF-only**,
   never COOL, never independently restores cooling) and a reconciliation sweep.
   Recovery authority remains solely with the V8.3 supervisor once truth is
   finite again. Do **not** add four persistent inhibit helpers unless repository
   constraints prove Design 1 cannot be implemented safely.
4. **Validity = finite value (BLOCKER 1).** ✅ APPROVED. The shared definition
   rejects `unknown`, `unavailable`, parse failures, **NaN**, **+infinity**, and
   **−infinity**, using `float(none)` + self-equality + a broad **safety**
   plausibility band (−90/200 °F) that is **not** an HVAC comfort/control
   threshold. The supervisor guard, event automation, and reconciliation all use
   semantically identical logic.

## Remaining unknowns (not silently resolved)
- Live entity ID of the supervisor (`…` vs `…_rev_b`) and the `_2` suffix on the
  LR runaway automation — resolve in live HA registry before Codex applies.
- `input_select.hvac_season_mode` / `input_boolean.*` / `timer.manual_hvac_override`
  are UI/storage helpers, not in repo YAML — option lists unverifiable here.
- Whether a climate entity can report a transient `cool` during its own
  `unavailable` recovery (Samsung cloud) — minor edge; condition `cool`-gate
  handles it conservatively.
- **`last_changed` edge:** if truth oscillates between two *different* invalid
  values (e.g. `unavailable` → `NaN`), `last_changed` resets and the
  reconciliation age can read <2 min even though truth was continuously invalid.
  The event automation's template `for:` rides this (it stays true across the
  switch); reconciliation is only the reload/restart backstop, so this is an
  accepted minor edge. Confirm in live HA whether the truth template can emit
  more than one distinct invalid string.

**Reconciliation result:** Packet A design complete; no production change made.
Packet B (raw vs smoothed/control) and V9 cooldown enforcement remain separate
and out of scope here.
