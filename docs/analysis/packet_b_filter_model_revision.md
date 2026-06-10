# Packet B — Architecture Review, Revision 2 (Filter Model Correction)

```
═══════════════════════════════════════════════════════════════
PACKET B — ARCHITECTURE REVIEW (REVISION 2)
Moose House HVAC — Temperature Input Path Selection
═══════════════════════════════════════════════════════════════

Author: Fable (control-system architect)
Supersedes: Packet B Design 1-8 of 2026-06-10 (Revision 1)
Reason: Revision 1's low-pass filter model was incorrect.
        Operator-verified HA 2026.6.1 behavior is event-based.
Status: No Codex prompt produced. No repository runtime changes
        proposed in this revision.
═══════════════════════════════════════════════════════════════
```

## 0. Withdrawal of Revision 1 Claims

Revision 1 modeled the Home Assistant `filter` integration's `lowpass` as
elapsed-time-based:

```
smoothed += (input - smoothed) * min(1, elapsed_since_last_eval / 10)   ← WRONG
```

The verified HA 2026.6.1 implementation is event-based. On every accepted
source-state event:

```
new_weight      = 1.0 / time_constant
previous_weight = 1.0 - new_weight
output          = previous_weight * previous_output + new_weight * new_input
```

With `time_constant: 10` (configuration.yaml Section 12):

```
y[n] = 0.9 · y[n-1] + 0.1 · x[n]        (per accepted source event)
```

There is no `elapsed_since_last_eval`, no `min(1, elapsed/time_constant)`,
no automatic convergence after ten seconds, and no reset or forced
convergence at the supervisor's 15-minute tick. The filter subscribes to
source state-change events; the supervisor independently samples the
current filtered value every 15 minutes (`time_pattern minutes: "/15"`).

The following Revision 1 claims are **withdrawn in full**:

1. The Nyquist/sampling argument (Section 2 of Revision 1), including
   `sampling_factor = min(1, 900/10) = 1.0` and "every supervisor tick
   sees the filter fully converged."
2. "The lowpass provides EXACTLY ZERO marginal damping relative to
   reading raw truth directly." Unsupported. Marginal damping depends on
   the truth entity's accepted-event rate, which is unmeasured.
3. "The filter converges fully within 10 seconds of each input change"
   and "steady-state lag ≈ 0–5 seconds." False under the actual model.
4. "Cold-start gap = negligible / converged within 10 seconds."
   Unsupported. Startup behavior (recorder-history priming, first
   accepted source events) must be evaluated separately by observation.
5. The "transient" explanation of the 1.13 °F Master truth/smoothed
   snapshot delta. Reclassified UNKNOWN: under the event recurrence, a
   1.13 °F delta is equally consistent with persistent recursive lag at
   a low event rate. The snapshot alone establishes neither duration nor
   benefit.
6. "No one-zone shadow needed — no consumer paths changed." Contingent
   on an architecture decision that is no longer made in this revision.
7. The control-wrapper validity/availability enhancement described as a
   "risk-free, test-covered doc + code change." Withdrawn from default
   scope and reclassified (Section 5 below).

## 1. Surviving Evidence (model-independent, repo-verified)

These findings do not depend on the filter model and are re-affirmed
against the repository at this revision:

- The V8.3 supervisor reads raw `sensor.*_temperature_truth` with
  `float(70)` fallbacks (`automations.yaml` supervisor variables block,
  lines ~372–376).
- No automation references `*_temperature_smoothed` or
  `*_temperature_control`.
- Control wrappers (configuration.yaml Section 10) are pass-throughs of
  the smoothed sensors with `| round(2)` and
  `float(none) is not none` availability.
- Smoothing filters (configuration.yaml Section 12): `lowpass`,
  `time_constant: 10`, `precision: 2`, one per truth sensor.
- Documentation contradicts code in three places:
  - Section 12 header: "the V8.3 supervisor ultimately acts on the
    smoothed values" — false.
  - Section 10 header: "CONTROL WRAPPERS FOR UI / SUPERVISOR ...
    downstream consumers lose their temperature input and control stops
    working" — false for the supervisor.
  - `truth_sensor_architecture.md` pipeline diagram routes the
    supervisor downstream of the control wrappers — false.
- Safety automations (runaway cutoff, emergency floor, ceiling gates,
  Ghost Assassin) read raw truth via `numeric_state` / direct truth
  references, independent of the supervisor.
- Packet A is not deployed (PR#135 unmerged, PR#137 unmerged draft;
  PR#135 explicitly excludes Packet B).
- The consumer classification inventory from Revision 1 Section 3
  survives **as a description of current routing only**. Its
  prescriptions ("keep unchanged") are deferred, except for the safety
  class (Section 4 below).

## 2. Corrected Dynamic Analysis

### 2.1 The recurrence and what actually governs convergence

```
y[n] = 0.9 · y[n-1] + 0.1 · x[n]
```

For a step input of size Δ, the residual error after N accepted events
is `0.9^N · Δ`:

| Accepted events N | Residual | Converged |
|---|---|---|
| 1  | 90.0 % | 10 % |
| 7  | 47.8 % | 52 % |
| 10 | 34.9 % | 65 % |
| 22 | 9.8 %  | 90 % |
| 29 | 4.7 %  | 95 % |
| 44 | 1.0 %  | 99 % |

Convergence is measured in **events, not seconds**. Wall-clock
convergence time = N × (mean interval between accepted truth events).
The truth sensors are template sensors that emit state-change events
only when their computed value changes, so the accepted-event rate is a
function of physical sensor activity and rounding — and it is
**unmeasured**.

Two illustrative regimes (neither confirmed — this is exactly the gap):

- Truth event every ~5 s during active temperature movement:
  95 % convergence in ~2.5 min. Filter is effectively converged at most
  supervisor ticks; Revision 1's conclusion would hold *empirically*,
  not by construction.
- Truth event every ~2 min in a thermally quiet or slowly drifting
  room: 95 % convergence takes ~1 hour ≈ 4 supervisor cycles. Tick-time
  deltas of ~1 °F can persist across multiple supervisor decisions, and
  threshold crossings can be delayed by one or more 15-minute cycles.

### 2.2 Consequences the corrected model introduces

1. **Frozen-lag mode.** The filter updates only on accepted events. If
   truth steps and then plateaus (no further value changes), the filter
   freezes at a partially converged value indefinitely, and the
   supervisor samples that stale value at every subsequent tick. The
   withdrawn model predicted the opposite (full convergence between
   ticks).
2. **Cadence coupling is real.** The supervisor cadence and the filter
   update cadence are different sampling processes driven by different
   clocks (wall time vs. event arrival). They cannot be collapsed into
   one analysis, and the filter's effect on supervisor decisions cannot
   be bounded analytically without the event-rate distribution.
3. **Quantization floor.** With `precision: 2` applied per update, a
   per-event increment `0.1 · (x − y)` below ~0.005 °F can round away,
   leaving a small persistent offset (order ≤ 0.05 °F). Negligible
   against 2–4 °F hysteresis bands, but it means "exact" convergence
   never completes; replay cross-validation must tolerate it.
4. **Cold start is an open question.** Whether and how the filter
   primes from recorder history at startup, and what the first accepted
   events do to the output, must be observed — not assumed in either
   direction.

### 2.3 What this does to the Revision 1 decision

Revision 1 concluded Option A because the filter allegedly contributed
nothing at a 15-minute cadence. That premise is gone. The filter *may*
contribute damping (beneficial: suppressing nuisance crossings that
reverse within a tick window) and *may* contribute lag (harmful:
delaying a desirable OFF and overcooling, or delaying a desirable ON).
Which effect dominates is an empirical property of this house's sensor
event streams during cooling operation.

**No option (A, B, C, D) is selected in this revision.** The decision
is blocked on offline replay evidence.

## 3. Offline Replay Specification

The next step is an offline replay over recorded data. **No live
configuration change.**

### 3.1 Minimum dataset

Raw recorder events at native granularity. **Do not resample** — the
event-count dynamics are the object of study; resampling destroys them.

Required fields per record: `entity_id`, `state`, `last_updated` (and
`last_reported` where available, to distinguish value-change events
from re-reports).

| # | Entities | Purpose |
|---|---|---|
| 1 | `sensor.{living_room,master_bedroom,lincoln_s_room,lilly_s_room}_temperature_truth` | Replay input event stream |
| 2 | `sensor.*_temperature_smoothed` and `sensor.*_temperature_control` (same zones) | Replay cross-validation |
| 3 | Supervisor execution timestamps: recorder/logbook `automation_triggered` events for `automation.v7_5_main_supervisor` (traces alone are insufficient — only the last runs are retained) | Tick sampling instants |
| 4 | `climate.master_bedroom_air`, `climate.lincoln_air`, `climate.lilly_air`, `climate.living_room_air` state history + `climate.set_temperature` / `set_hvac_mode` service events (or v8.5 provenance-logger output) | Commands actually issued |
| 5 | Decision-gate inputs: `input_select.hvac_season_mode`, `input_boolean.away_mode`, night/sleep booleans, `timer.manual_hvac_override` | Evaluate the decision function correctly at each tick |
| 6 | One controlled HA restart inside the export window (timestamped), if operationally acceptable | Cold-start / recorder-priming observation |

Period: a cooling period containing threshold approaches and crossings —
target 7–14 days; absolute minimum 48 hours of active cooling with at
least a handful of band-edge crossings per controlled zone. If
supervisor `automation_triggered` events are not retained, reconstruct
the tick grid from `time_pattern /15` minus override-timer windows and
flag those ticks as reconstructed.

The existing export tooling (`docs/ha_nuisance_export.md`,
`tools/export_ha_nuisance_evidence.ps1`) should be reused/extended
rather than building a new exporter.

### 3.2 Replay procedure

1. Per zone, implement `y[n] = round(0.9·y[n−1] + 0.1·x[n], 2)` over
   the raw truth event sequence, skipping non-numeric/unavailable
   states, initialized from the first accepted event in the window.
2. **Cross-validate first:** the replayed series must reproduce the
   recorded `*_temperature_smoothed` series within precision rounding.
   If it does not, the model or the event-acceptance assumptions
   (unavailable handling, `last_reported` vs `last_changed`, recorder
   priming) are still wrong — **halt and re-derive before any
   architecture conclusion.**
3. At every actual supervisor execution time, evaluate the cooling
   decision function from `automations.yaml` (per zone:
   `temp > on_at → cool; temp ≤ off_at → off; else hold current`),
   with the band edges active at that instant (Master: away 74/76,
   sleep 18:00–06:00 62/66, day 68/72; Lincoln/Lilly: away 74/76,
   else 68/72; LR per its branch), using:
   - (a) the raw-truth value,
   - (b) the replayed filtered/control value,
   and record (c) the command actually issued, (d) distance of each
   input from the active on/off thresholds, and (e) whether raw and
   filtered inputs produce different COOL/OFF/HOLD results.

### 3.3 Metrics to quantify

1. Accepted-event count (and wall-clock time) to 90 %/95 % convergence
   after representative step inputs, per zone.
2. Truth-vs-filter delta at supervisor ticks: mean, P95, max, and
   persistence (max consecutive ticks with |delta| > 0.3 °F).
3. Threshold-crossing delay measured in supervisor cycles (raw crossing
   tick vs. filtered crossing tick), per band edge, per zone.
4. Nuisance raw crossings: raw-truth band-edge crossings that reverse
   before the next tick.
5. Cases where filtering prevents chatter: divergent ticks where the
   filtered decision avoided an ON/OFF flip that raw would have taken
   and immediately reversed.
6. Cases where filtering delays a desirable OFF or ON: divergent ticks
   where lag extended runtime past the off threshold (overcooling
   °F·min, added runtime) or delayed engagement (comfort excursion
   °F·min).

### 3.4 Decision rule after replay

Primary statistic: **divergent-decision rate** — fraction of supervisor
ticks where raw and filtered inputs yield different COOL/OFF/HOLD.

- Divergence ≈ 0 and small tick deltas → Option A (supervisor stays on
  raw truth). Packet B scope defaults to documentation corrections
  (the three contradictions in Section 1) plus routing-invariant
  contract tests. **No control-wrapper availability changes, no
  validity semantics** absent a separate, evidenced requirement.
- Divergence > 0, net harmful (delayed OFF/ON dominates) → Option A,
  strengthened; additionally document the filter as UI-only and
  consider UI-side retuning as a separate, non-control change.
- Divergence > 0, net beneficial (chatter suppression dominates,
  delays acceptable) → Option B/C becomes a live candidate. Any such
  migration is a runtime control change requiring the full protocol:
  one-zone shadow, staged rollout, independent rollback. Revision 1's
  "no shadow needed" does not apply.

## 4. Architecture Constraints (hold regardless of replay outcome)

1. **Safety stays on raw truth.** The runaway cutoff (60 °F), emergency
   floor (58 °F), ceiling gates (76 °F), and Ghost Assassin remain on
   `*_temperature_truth` via `numeric_state` unless separately
   justified. Under the event recurrence this is stronger than before:
   an event-count filter delays a safety-relevant reading by ≥1 event
   and a potentially unbounded wall-clock time (frozen-lag mode).
2. **No duplication of Packet A.** Packet A (unmerged, unproven) owns
   invalid-truth protection: `*truth_ok` guards, the shared
   finite-value definition (NaN/±inf rejection, −90/200 °F band),
   protective-OFF, and reconciliation. Packet B defines compatibility
   only and implements none of it. The known `float(none)`-passes-NaN
   gap in the control wrapper is recorded as Packet A territory.
3. **Composition claim weakened.** Revision 1 declared Packet A and
   Packet B unconditionally independent. True only under Option A
   (guards and supervisor target the same raw-truth entities). Under
   Option B/C, Packet A's guards would need re-pointing at the new
   supervisor input. Sequencing therefore depends on the replay
   outcome; the independence claim is deferred with the decision.

## 5. Control-Wrapper Enhancement — Reclassified

The Revision 1 proposal (validity attribute + finite-value
availability on the Section 10 wrappers) is **removed from Packet B's
default scope**. If re-proposed, it must be treated as:

- a **separate runtime behavior change**, not documentation: wrapper
  availability transitions are visible to the HA UI/dashboards (the
  wrappers' current consumers) and to any future consumer;
- accompanied by an analysis of current UI/consumer effects (entities
  flipping to `unavailable` under the new gate);
- covered by its own tests and its own rollback procedure;
- never described as risk-free or documentation-only.

## 6. Verdict

Until the offline replay (Section 3) is executed, cross-validated, and
its metrics evaluated against the decision rule, no input-path
architecture can be certified and no implementation prompt will be
produced.

```
═══════════════════════════════════════════════════════════════
DESIGN BLOCKED — OFFLINE REPLAY EVIDENCE REQUIRED
═══════════════════════════════════════════════════════════════
```
