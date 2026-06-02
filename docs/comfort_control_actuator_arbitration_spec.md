# Comfort-Control Actuator & Arbitration Spec (Planning / Spec — NOT runtime)

**Doc Date:** 2026-06-02
**Document Role:** Architecture/spec pass for the next comfort-control layer.
**Status:** Planning / specification. **Does NOT change runtime YAML, comfort
thresholds, Section 3 safety gates, truth logic, helpers, or telemetry.**
**Supersedes nothing.** Builds on PR #122 (plan), #123 (doctrine+tests), #124
(report-time freshness).

> Hard guardrail for any future implementer reading this: the failure modes this
> spec exists to prevent are (a) a unit running until Samsung reaches 61/79,
> (b) losing "off inside the band," and (c) simultaneous opposing heat/cool
> across rooms. If a PR does any of those, it is wrong regardless of how clean
> the diff looks.

---

## Executive Summary

The corrected control model separates two ideas the current runtime collapses
together:

1. **Samsung setpoints are shove commands, not comfort targets.** When Moose
   House decides a room must actively cool or heat, it commands the *strongest
   allowed* Samsung setpoint in that direction so the compressor commits and
   actually moves room truth, instead of throttling, satisfying its own biased
   internal thermistor, or coasting. These are fixed actuator saturation
   constants:
   - `cool_command_setpoint = 61°F` (Samsung cooling minimum)
   - `heat_command_setpoint = 79°F` (Samsung heating maximum)
2. **Room truth comfort bands decide when to start and stop** — never the Samsung
   setpoint. The room is **not** supposed to reach 61°F or 79°F. It runs only
   from band-exit until band-return.

Operating rules:

- **Inside the band the system is OFF.** No chasing, no Samsung auto-comfort, no
  "hold 72°F," no continued run because Samsung has not hit its internal target.
- **Season biases, it does not hard-ban modes.** Cooling in winter is valid
  (destratification / air movement / an over-warm room); heating outside winter
  can be valid. Season changes bias, lockouts, and safety assumptions; **room
  truth decides what action is needed.**
- **A house-wide supervisor arbitrates.** Rooms may not command opposing active
  modes independently. Opposing requests are resolved by severity / safety /
  priority; the loser is **deferred, not erased.**

This is a structural change: today's supervisor commands *moderate* setpoints
(e.g. cool@66, heat@67/71) inside a per-season `choose` block, with only a
single narrow cross-mode interlock. The spec below routes that to shove
constants + band thresholds + a real arbitration layer, sequenced so no single
PR can make the system run forever or fight itself.

---

## Current Repository Findings

All line numbers are against `main` at the post-#124 merge (`867d720`).

### 1. Where Samsung command setpoints are hardcoded
- **File:** `automations.yaml` — **Section 2** `v7_5_main_supervisor` (id
  `v7_5_main_supervisor`, alias "V8.3").
- **What it does:** issues `climate.set_temperature` with inline-templated
  setpoints throughout three season branches:
  - Cooling: Master `66` (sleep `61`, away `74`), Lincoln/Lilly/LR `66`
    (away `74`) — lines ~394–467.
  - Shoulder: LR heat `65`/`64`/`62`/`68`, Master cooling-escape `61`,
    warm-day cool `70` — lines ~474–555.
  - Heating: LR `71`/`65`/`60`/`64`/`68`, Master/Lincoln/Lilly `62`/`67`,
    Nest `68` — lines ~563–645.
- **Also:** Section 3 ceiling gate commands `cool, 68` (line ~817); Section 14
  LR boost commands `heat, 77` (line ~1563).
- **Doctrine fit:** **CONFLICT.** These are comfort-target-shaped values, not
  saturation shoves. None command `cool@61` or `heat@79` (the lone `61` is the
  Master *sleep* cooling setpoint, coincidental). Heating commands sit **at**
  the comfort target (`67`, `71`) — the exact throttle/coast risk the new
  doctrine names.

### 2. Whether any runtime uses moderate setpoints instead of shove values
- **Finding:** Yes — every active path uses moderate setpoints. Cooling
  setpoints are ~2°F below their OFF thresholds (cool@66 vs off≤68), which a
  comment at `automations.yaml:368–371` already rationalizes as "pull down
  decisively." Heating setpoints equal the comfort target. **CONFLICT** with
  `61`/`79` shove doctrine; the cooling comment shows partial awareness but the
  magnitude is wrong.

### 3. Where comfort bands are hardcoded
- **File:** `automations.yaml` Section 2 — the `*_on_at` / `*_off_at` inline
  templates (same lines as above).
- **Mirrors (descriptive):** `docs/1_startup_canon.md` §5.1,
  `docs/5_runtime_layer.md` §6.1, `docs/comfort_failure_forensics.md` §8.6
  branch table.
- **Doctrine fit:** AGREES in spirit (bands already drive ON/OFF) but they are
  not separated from the actuator setpoint and there is no profile/abstraction.

### 4. Where seasonal logic assumes heating-only / cooling-only
- **File:** `automations.yaml` Section 2: top-level `choose` on
  `season == 'cooling' | 'shoulder' | 'heating'` (lines 378, 474, 563). In
  `heating` season the cooling sequence is **unreachable**, so compressor
  cooling is effectively hard-banned in winter (only the shoulder-night Master
  cooling escape and the fan-only destrat path provide any cool/air-move).
- **File:** Section 5 `v7_5_auto_season_mode` (lines ~893–926) picks exactly one
  of cooling/heating/shoulder from deck truth (`>72`→cooling, `<45`→heating,
  `50–68`→shoulder).
- **Doctrine fit:** **CONFLICT** with "season biases, does not hard-ban."

### 5. Where shoulder-season logic exists
- **Files:** Section 2 shoulder branch (lines ~474–561); Section 6
  `v8_comfort_fan_destratification` gated `season in ['heating','shoulder']`
  (line ~950); Section 5 `to_shoulder` trigger; several shade automations
  (`season in [...]`). **Reference only** — no change proposed here.

### 6. Where existing interlocks prevent opposite modes
- **File:** `automations.yaml` Section 3 `v9_sleep_priority_interlock` (SPI,
  lines 674–697). Triggers on `master_bedroom_air → cool` **and**
  `living_room_air → heat`; if Master is cooling while LR is heating (LR truth
  > 60°F) it forces **LR off**.
- **Doctrine fit:** PARTIAL. It is the only opposing-mode interlock and it is
  narrow: one specific pair (Master-cool vs LR-heat), one direction, **no**
  settle delay, **no** priority computation, **no** deferred/pending request,
  **no** coverage of Lincoln/Lilly. Insufficient as the house-wide arbiter the
  new model needs. (Also classified "ambiguous interlock" in
  `5_runtime_layer.md` §7.8.)

### 7. Could LR heating run while a bedroom cools / destratifies?
- **Today:** Within the supervisor's single season branch, a tick is
  mode-coherent (all-heat-ish or all-cool-ish), so the supervisor alone does not
  emit opposing compressor modes. Cross-automation opposition is mostly avoided
  because the 76°F ceiling gate uses **fan_only** in heating/shoulder (only
  `cool@68` in cooling season), and destrat is **fan_only** only.
- **Under the NEW model (cooling allowed in winter for destrat):** **YES, it
  could.** Nothing prevents LR heating (heating branch) while Lincoln/Lilly are
  commanded to cool, because SPI covers only Master-cool vs LR-heat. **This is
  the gap PR D must close before any winter-cooling/destrat mode ships.**

### 8. Tests that would break under shove constants + arbitration
- **`tests/test_section2_cooling_setpoint_doctrine.py`** — pins exact moderate
  setpoint strings (`m_setpoint == "{{ 74 if away else (61 if is_master_sleep
  else 66) }}"`, `l_setpoint == "{{ 74 if away else 66 }}"`, etc.). **Will break
  the instant cooling setpoints become `61` shoves.** Must be rewritten in the
  same PR that lands the shove refactor (PR C).
- **`tests/test_supervisor_shoulder_night.py`** — asserts shoulder-night Master
  cooling-escape shape; sensitive to setpoint/threshold edits.
- **Must stay green (do not break):** `test_safety_invariants.py`,
  `test_comfort_band_safety_separation.py` (60/58 floors),
  `test_truth_freshness_report_time.py`, `test_truth_confidence_model_contract.py`,
  `test_msr_observability_boundary.py`, `test_manual_override_contract.py`,
  `test_truth_entity_registry_integrity.py`.

### 9. Safety gates that must remain untouched
- Section 3 `v8_2_lr_runaway_cooling_cutoff` (LR truth < 60°F → off);
  `v8_2_master_emergency_floor` (Master truth < 58°F → off);
  `v7_5_safety_ceiling_gates` (76°F; comfort ceiling, gates on override);
  `v7_5_waf_manual_override`. Locked by `test_safety_invariants.py` and
  `test_comfort_band_safety_separation.py`.

### 10. Docs already stating Samsung setpoints are actuator commands
- `docs/1_startup_canon.md` §5.1 ("the Samsung / mini-split setpoint is an
  actuator demand, not comfort truth"); `docs/5_runtime_layer.md` §7.9;
  `docs/comfort_band_and_truth_confidence_plan.md`; `docs/v8_4_heating_recovery_boost_plan.md`;
  and the inline comment `automations.yaml:368–371`. The doctrine exists; the
  **runtime values do not yet implement saturation.**

---

## Proposed Control Model

### Room call states (per room, derived from truth + band + season bias)
| State | Meaning | Entry condition (conceptual) | Actuator |
|---|---|---|---|
| `idle` | Inside band; do nothing | `cool_off_at < truth < heat... ` i.e. within band | unit `off` |
| `heat_recovery` | Room below band; needs heat | `truth < heat_on_at` | `heat` @ `heat_command_setpoint` (79) |
| `cool_recovery` | Room above band; needs cool | `truth > cool_on_at` | `cool` @ `cool_command_setpoint` (61) |
| `destratification` | Air movement / layering / over-warm room, often in heating season | room over-warm vs house, or stratification signal; **bounded** | `fan_only` (preferred) or `cool`@61 where fan-only insufficient — see Open Questions |
| `safety` | A Section 3 gate is asserting | runaway/floor/ceiling | Section 3 owns it; comfort yields |

Hysteresis is mandatory: a room that entered `heat_recovery` stays in it until
`truth ≥ heat_off_at`; entered `cool_recovery` until `truth ≤ cool_off_at`.
Between on/off it holds its current active state (deadband), and once at the off
threshold it returns to `idle` (off).

### House arbitration states (whole-house supervisor)
| State | Meaning |
|---|---|
| `all_idle` | No room calling; everything off |
| `coherent_heat` | One or more rooms calling heat; no cool/destrat call | 
| `coherent_cool` | One or more rooms calling cool/destrat; no heat call |
| `conflict_resolving` | Opposing calls present; loser being shut down + settling |
| `locked` | A direction is in `opposite_mode_lockout`; opposite calls deferred |
| `safety_override` | Section 3 active; arbitration suspends comfort writes for that room |

### Actuator shove constants
- `cool_command_setpoint = 61` (fixed; Samsung cooling floor)
- `heat_command_setpoint = 79` (fixed; Samsung heating ceiling)
- These are commanded **whenever** the room is in active recovery, independent
  of how close truth is to the band edge. They are never comfort targets.

### Stop thresholds (truth-based, per band)
- Heating stops at `truth ≥ heat_off_at` → `off`.
- Cooling stops at `truth ≤ cool_off_at` → `off`.
- Destratification stops at its own `destrat_off` threshold OR `max_run_minutes`
  OR insufficient-progress, whichever first.
- A unit must **never** be left running toward 61/79; reaching the band edge is
  the stop, not the setpoint.

### Lockout / watchdog rules (per room and per direction)
- `max_run_minutes`: hard cap on a single recovery run; on expiry → `off` +
  alert (do not silently re-engage).
- `minimum_progress_required`: over a progress window, truth must move toward
  the band by ≥ X°F; if not, stop + alert (compressor not effective / bad
  thermistor / wrong mode).
- `minimum_mode_hold_minutes`: once started, hold the mode at least this long
  (anti-short-cycle) unless a safety gate or higher-priority preemption fires.
- `opposite_mode_lockout_minutes`: after a direction stops, the opposite
  direction is blocked house-wide for this interval (compressor protection +
  anti-fight).
- `equipment_settle_delay`: between turning a losing mode off and starting the
  winning mode, wait a short settle interval.

---

## Proposed Helper / Variable Model

**Recommendation: shove constants as `input_number` helpers, bands/timers as a
mix (see rationale).** Reasoning:

- **Shove constants (`61`/`79`) → `input_number` helpers.** They are physical
  device limits that (a) you may need to tune once if a firmware/model changes,
  and (b) benefit from being observable in the UI and exportable to telemetry so
  a forensic note can confirm "we actually commanded 61." They are read in many
  places; a helper avoids 12 copies of a literal. They carry **no** control
  authority by themselves (a setpoint is inert until a mode is commanded), so
  introducing them early (PR B) is low-risk.
- **Band thresholds → start as supervisor YAML variables, migrate to profile
  helpers later (the comfort-profile PR F).** Keeping bands as named variables
  first lets PR C do a pure setpoint refactor without entangling the profile
  system.
- **Watchdog timers → `timer.*` + `input_number.*` helpers** when PR D/E land,
  because they need persistence and observability.

Proposed names (final names TBD with Eric):

```
# Actuator shove constants (PR B) — inert until consumed
input_number.moose_cool_command_setpoint   # = 61   (Samsung cooling floor)
input_number.moose_heat_command_setpoint   # = 79   (Samsung heating ceiling)

# Band thresholds (PR C as YAML vars; PR F as per-profile helpers)
heat_on_at        # room < this  -> heat_recovery
heat_off_at       # room >= this -> stop heating
cool_off_at       # room <= this -> stop cooling
cool_on_at        # room >  this -> cool_recovery

# Watchdog / arbitration (PR D / PR E)
input_number.moose_max_run_minutes
input_number.moose_minimum_progress_required          # °F over the progress window
input_number.moose_minimum_mode_hold_minutes
input_number.moose_opposite_mode_lockout_minutes
input_number.moose_equipment_settle_seconds
# plus per-room latch/pending memory, e.g.
input_text.moose_<room>_call_state          # idle|heat_recovery|cool_recovery|destrat|safety
input_text.moose_house_arbitration_state
timer.moose_<room>_min_hold
timer.moose_opposite_mode_lockout
```

`heat_on_at < heat_off_at ≤ cool_off_at < cool_on_at` is an invariant; and all
band thresholds must stay strictly inside the Section 3 floors (heat_on_at > 60°F
LR runaway, > 58°F Master floor) so comfort never aliases safety.

---

## Arbitration Rules

For each scenario: detect → decide → act → defer → re-evaluate. The hard
invariant — **never simultaneous opposing heat/cool commands across rooms** —
holds in all of them.

1. **No active calls.** House = `all_idle`. All units `off`. Nothing commanded.
2. **One room calls heat.** House = `coherent_heat`. That room → `heat`@79.
   Others idle stay off. No opposite call exists, so no arbitration needed.
3. **One room calls cool/destrat.** House = `coherent_cool`. That room →
   `cool`@61 (or `fan_only` for destrat). Others stay off.
4. **Multiple rooms, same direction.** All may run that direction concurrently
   (same-direction is not a conflict). Each obeys its own band + watchdogs.
5. **One room heat while another cool/destrat.** House = `conflict_resolving`.
   Compute winner by priority (below). Turn the **loser's** mode `off` first,
   start `equipment_settle_delay`, then start the winner if it still qualifies.
   Loser's request becomes **pending** (remembered), not erased.
6. **Severe out-of-band room (e.g. bedroom 81°F).** Severity = distance past the
   band edge. A room far out of band (e.g. ≥ N°F past `cool_on_at`) outranks a
   marginal opposite call. Bedroom 81°F wins; LR heat becomes pending.
7. **Active heat, urgent cool request appears.** If the new cool request's
   severity beats the running heat (and `minimum_mode_hold_minutes` has elapsed
   **or** the request is safety-severe), preempt: stop heat → settle → start
   cool@61. Heat request → pending. If hold not yet elapsed and not safety-
   severe, the cool request waits (pending) until hold expires.
8. **Active cooling, urgent heat request appears.** Symmetric to (7).
9. **Pending/deferred requests.** A pending request is retained with its
   timestamp and re-evaluated when (a) the winning action stops AND (b)
   `opposite_mode_lockout_minutes` has expired. On re-evaluation it must still
   qualify against its band (the room may have drifted back inside the band, in
   which case the pending request is dropped as satisfied).
10. **Return to idle inside band.** When a room's truth re-enters its band, it
    returns to `idle` (off) immediately on the stop threshold; this can release
    a lockout timer that in turn lets a pending opposite request be re-evaluated.

**Priority ordering (proposed, tunable):** `safety` (Section 3) > severity
(distance past band edge, with a configurable preempt margin) > room priority
(e.g. occupied bedroom at night) > current-active-mode incumbency (ties favor
the already-running mode to avoid flapping).

---

## Safety Invariants (must NOT change)

- **Section 3 LR runaway cutoff** — LR truth `< 60°F` → LR `off`. Unchanged,
  no override gate.
- **Section 3 Master emergency floor** — Master truth `< 58°F` → Master `off`.
  Unchanged, no override gate.
- **Manual override doctrine** — comfort policy gates on
  `timer.manual_hvac_override == idle`; true safety gates do not. Any new
  arbitration/comfort automation must respect this from inception.
- **MSR / Apollo observability boundary** — no MSR/Apollo/ESP entity promoted
  into control (Lincoln fan-only exception only). Locked by
  `test_msr_observability_boundary.py`.
- **PR #124 report-time freshness** — truth freshness stays `last_reported`;
  never reintroduce `last_changed` as a freshness clock.
- **No simultaneous opposing modes** — becomes a *new* hard invariant enforced
  by the arbiter (PR D) and a test.

---

## Test Plan (for later PRs — not added now)

- `cool_command_setpoint == 61` and `heat_command_setpoint == 79` (constants).
- Actuator setpoints are **not** comfort thresholds: the commanded setpoint is
  61/79 while the OFF threshold is the band value (assert they differ).
- Cooling stops at `cool_off_at`, not at 61 (a room at 61-ish-but-above-off
  keeps cooling; a room at/below `cool_off_at` goes off even though 61 not
  reached).
- Heating stops at `heat_off_at`, not at 79.
- System remains `off` for truth strictly inside the band (no command emitted).
- Winter (`season == heating`) does **not** hard-ban cool/destrat eligibility:
  a winter room above `cool_on_at` can still produce a cool/destrat call.
- Seasonal mode affects bias/lockout/severity, not hard eligibility.
- **LR `heat` and any bedroom `cool` cannot be simultaneously commanded**
  (arbiter invariant) — assert across all room pairs, not just Master/LR.
- Urgent bedroom 81°F cool request preempts/defers LR heat; LR request becomes
  pending, not erased.
- A pending heat request resumes only after cooling stops **and**
  `opposite_mode_lockout_minutes` expires, and only if it still qualifies.
- Watchdogs: `max_run_minutes` forces off + alert; `minimum_progress_required`
  failure forces off + alert.
- **No change** to Section 3 thresholds/actions (re-assert 60/58 via existing
  tests).
- Existing `test_section2_cooling_setpoint_doctrine.py` is updated (not deleted)
  to assert the new shove/band separation.

---

## Implementation Sequencing

The proposed A→F sequence is sound; I recommend **two refinements** and one
explicit gate. Rationale follows.

- **PR A — Docs/tests only (this spec).** Land actuator-shove + arbitration
  doctrine into canon/runtime docs; add **pure-model** tests (no runtime) that
  encode the shove constants and the no-opposing-modes contract as a model
  contract (mirroring how #123 added the truth-confidence contract). Safe.
- **PR B — Add shove constants as inert helpers.** Introduce
  `input_number.moose_cool_command_setpoint = 61` / `..._heat_... = 79` with
  **no consumer**. Add a test that they exist and equal 61/79. Zero behavior
  change.
- **PR C — Refactor Samsung command setpoints to shove constants.** Replace the
  moderate `set_temperature` values with the shove constants **while preserving
  every existing `*_on_at`/`*_off_at` band and every season branch unchanged.**
  This is the highest-risk single change (it makes units commit harder), so it
  ships **alone**, updates `test_section2_cooling_setpoint_doctrine.py`, and is
  gated behind a **live verification packet** (like #124) confirming rooms still
  stop at the band edge and do not chase 61/79. **Recommended refinement:** do
  PR C **cooling-only first**, then a PR C2 heating-only, because heating @79 is
  the bigger behavioral jump (today's heat setpoints sit at the comfort target).
- **PR D — House-wide opposing-mode interlock.** Add the arbiter that enforces
  the hard invariant (generalizing/【replacing】 SPI). **Recommended gate: PR D
  must merge before PR E**, because PR E (winter cooling/destrat) is what makes
  opposing modes physically reachable. Until D lands, destrat stays fan-only.
- **PR E — Destratification mode.** Allow winter cool/air-move with
  `destrat_off`, `max_run_minutes`, `minimum_progress_required`,
  opposite-mode lockout, and settle. Depends on D.
- **PR F — Comfort profiles.** Only after shove + arbitration are proven safe;
  migrate bands to per-profile helpers (the #122/#123 plan).

**Why this order:** each PR is independently revertible and observable; the
single irreversible-feeling change (harder compressor commitment) is isolated in
C/C2 with a live check; the dangerous capability (winter cooling that can oppose
heating) cannot land until the arbiter (D) that contains it already exists.

---

## Red Flags / Stop Conditions

Stop and re-review if any PR:

- Makes a unit run until Samsung reaches 61/79 (i.e. uses the shove constant as
  a stop threshold). The stop is always the truth band edge.
- Removes or weakens "off inside the comfort band" (any always-on / hold-72
  behavior, or continuing because Samsung's internal target isn't met).
- Allows simultaneous opposing heat/cool commands across rooms at any tick.
- Weakens, re-thresholds, or override-gates Section 3 (60°F / 58°F).
- Promotes any MSR/Apollo/ESP sensor into a control trigger/condition/setpoint
  (beyond the locked Lincoln fan-only exception).
- Reintroduces `last_changed` as a truth freshness clock (undoes #124).
- Lands destratification/winter-cooling **before** the house-wide arbiter (D).
- Deletes (rather than updates) `test_section2_cooling_setpoint_doctrine.py`, or
  drops a pending/deferred request instead of remembering it.

---

## Open Questions for Eric

1. **Shove constants — helpers or YAML constants?** Spec recommends
   `input_number` helpers (tunable + observable + telemetry-visible). Confirm,
   or prefer hard YAML constants for immutability?
2. **Exact comfort bands per profile.** Final `heat_on_at` / `heat_off_at` /
   `cool_off_at` / `cool_on_at` numbers for at least `eric_cold` and
   `family_normal` (PR F needs these; PR C just needs the *current* bands kept).
3. **Opposite-mode lockout duration.** What value for
   `opposite_mode_lockout_minutes` (compressor protection vs responsiveness)?
   And `minimum_mode_hold_minutes` / `equipment_settle_delay`?
4. **Preempt severity.** How far past the band edge must a room be (e.g. the
   81°F bedroom) to preempt an already-running opposite mode — a fixed °F
   margin, and/or an absolute "always preempt above X°F"?
5. **Destratification actuator.** Should destrat use `fan_only` only, `cool`@61
   only, or fan-first-then-cool where fan-only fails to make progress? (Affects
   whether destrat can ever create an opposing-compressor situation, and thus
   how hard PR D must work.)
6. **Room priority.** Is there a fixed room-priority order (e.g. occupied
   bedroom at night > Living Room) for tie-breaks, or should severity alone
   decide?

---

_End of Comfort-Control Actuator & Arbitration Spec. Planning only — no runtime
change in this document._
