# Issue #91 — Section 2 ↔ Section 14 Collision Measurement Plan (four-week, executable)

**Doc Date:** 2026-08-07
**Issue:** #91 — *Section 14 supervisor / boost collision quantifier (V10
analytic, outside-HA).*
**Class:** Analytic (outside-HA). Read-only. **No** `automations.yaml` change,
**no** helper, **no** threshold, **no** HA write, **no** HA read of the output.
**Runtime risk:** None.
**Doctrine posture:** Arbitration follows telemetry, never precedes it
([`3_regression_appendix.md`](3_regression_appendix.md) §4.18). This plan
produces the telemetry that a future Section 2 latch-consult decision would
require; it authorizes **no** runtime change on its own.

> **Adopt-before-build (AGENTS.md 2026-08-03).** This plan uses off-the-shelf
> tooling only — `pandas` in a notebook (or equivalently a Google Apps Script /
> Sheets pivot over the same tabs). **No new parser, harness, scheduler, or
> library is built.** The analytic reads two existing Google Sheets tabs and
> writes one new tab / notebook. If an existing Sheets pivot can produce §7's
> counters, prefer it; a notebook is the fallback when the join in §4 exceeds
> what a pivot expresses cleanly.

---

## 1. Purpose and exit

Quantify the Section 2 ↔ Section 14 supervisor/boost overwrite collision class
documented anecdotally in [`3_regression_appendix.md`](3_regression_appendix.md)
§4.17, [`comfort_failure_forensics.md`](comfort_failure_forensics.md) §8.3, and
[`5_runtime_layer.md`](5_runtime_layer.md) §7.4. The four observed May cycles all
terminated externally; the collision has never been measured at a rate. Per
[`v9_v10_goals.md`](v9_v10_goals.md) §2.2, no runtime change (the candidate
Section 2 latch consult) may be justified until this quantifier reports a
measurable recurrence rate.

**Issue #91 closes when, and only when:** (a) ≥ 4 weeks of data are tabulated,
(b) collision frequency is reported with median and p95 engage→overwrite
minutes, and (c) the report is linked from
[`3_regression_appendix.md`](3_regression_appendix.md) §4.17 source-lineage line.

---

## 2. Collision — exact definition

A **collision** is a single, fully-qualified event defined on the boost-active
interval, not on a raw tick. It requires **all** of:

1. **Boost active.** `Section14_Boost_Active = true` in `VTherm_Launch_Data_v5_5`
   for the row(s) spanning the event minute (equivalently
   `input_boolean.lr_heating_recovery_boost_active = on`).
2. **Doctrinal setpoint overwrite.** `LR_Air_Setpoint` transitions **from `77`**
   (the boost demand) **to a non-77 supervisor-doctrinal value** — typically
   `68`, but any value the Section 2 heating/deadband branch legitimately writes
   counts (`68`, `61` shove, `off`→setpoint-cleared). The transition is measured
   between consecutive samples straddling the boundary in §3.
3. **Supervisor attribution.** A `hvac_provenance_log` row exists on the **same
   wall-clock minute** as the overwrite with `origin_kind = automation_or_script`
   **and** `automation_candidate = v7_5_main_supervisor`, for
   `entity_id = climate.living_room_air`.
4. **During the active interval.** The overwrite minute lies strictly between the
   boost **engage** minute and the boost **release/termination** minute of the
   same cycle (not on the engage tick itself).

An event failing **any** of 1–4 is **not** a collision and is routed to a
category in §5. Requiring all four is what separates a true supervisor overwrite
from a WAF nudge, a truth-cap release, or a timeout.

---

## 3. Sampling, event boundaries, and the collision window

- **Setpoint cadence / boundaries.** Section 2 writes on `time_pattern
  minutes:"/15"` and on season flips. Overwrites are therefore expected on
  `:00`/`:15`/`:30`/`:45` boundaries. The analytic **anchors overwrite detection
  to these quarter-hour boundaries** and inspects the boost-interval sample
  immediately before and after each boundary. Non-boundary setpoint changes are
  recorded separately (§5, `off_cadence_change`) — they cannot be the 15-minute
  supervisor tick and usually indicate WAF/manual or Section 19.
- **Cycle = engage → termination.** A boost **cycle** opens on the
  `Section14_Boost_Active false→true` edge and closes on the `true→false` edge.
  Every collision is attributed to exactly one cycle. Overlapping/re-armed cycles
  within the same clock hour are kept distinct by their engage edge.
- **Engage→overwrite latency.** For each collision, `latency_min = overwrite_minute
  − engage_minute` (integer minutes). Feeds the median/p95 in §7.
- **Join key.** Truncate every timestamp to the **minute** (`YYYY-MM-DD HH:MM`,
  house-local tz) before joining `VTherm_Launch_Data_v5_5` setpoint transitions
  to `hvac_provenance_log` attribution rows. The provenance log is the
  attribution authority; the launch-data tab is the setpoint/boost-state
  authority.

---

## 4. Telemetry inputs (read-only)

| Source tab | Fields consumed | Role |
|---|---|---|
| `VTherm_Launch_Data_v5_5` (Section 1 export) | `timestamp`, `LR_Air_Setpoint`, `Section14_Boost_Active`, `LR_HP_Runtime_Today_Hrs`, `LR_Air_Temperature_Truth`, season mode, `Supervisor_Enabled`, `Manual_Override_State`* | Setpoint transitions, boost-active interval, denominator, exclusions |
| `hvac_provenance_log` (Section 15) | `timestamp`, `entity_id`, `origin_kind`, `automation_candidate` | Overwrite attribution to `v7_5_main_supervisor` |

\* `Manual_Override_State` / `Manual_Override_Remaining_Sec` are **historical
telemetry remnants**. The WAF watcher and `timer.manual_hvac_override` were
removed in `cc720ab` (see
[`manual_override_and_v9e_reconciliation.md`](manual_override_and_v9e_reconciliation.md)).
For any window on/after 2026-07-11 these columns are effectively constant/blank
and **must not** be used to attribute external terminations to "WAF." This is a
change from the §4.17 anecdote, which pre-dates the removal.

**Forbidden inputs / outputs (Provenance Doctrine, `v9_v10_goals.md` §9):**
The analytic **reads** the two tabs above. It **never** writes to Home
Assistant, and **no HA automation, template, or condition may read this plan's
output.** Output lives outside HA (a Sheets tab, notebook, or forensic note).

---

## 5. Categories (every boost-interval setpoint event lands in exactly one)

| # | Category | Rule | Counts toward |
|---|---|---|---|
| C1 | **Supervisor collision** | Meets all §2 conditions 1–4 | Numerator (collision rate) |
| C2 | **Clean cycle** | Cycle engaged **and** released by `truth_cap` (LR truth ≥ 67°F) **or** the 90-min timeout, with **zero** C1 overwrites during the active interval | "Clean cycles observed" counter |
| C3 | **External non-supervisor termination** | Cycle ends with no C1 overwrite and no truth_cap/timeout signature (e.g. Section 19 Heat Wave Override seizing actuators, HA restart, truth-unavailable failsafe) | Excluded from numerator; reported separately |
| C4 | **Off-cadence setpoint change** | Setpoint left `77` **not** on a `:00/:15/:30/:45` boundary, or with no matching `v7_5_main_supervisor` provenance row on the minute | Excluded; §6 false-positive audit |
| C5 | **Attribution-ambiguous** | Setpoint transition present but provenance row missing/`origin_kind` unresolved/`automation_candidate` names a different automation | Excluded; §6 audit |

A cycle can produce ≥ 1 C1 events; only the **first** C1 per cycle sets that
cycle's `latency_min`. Additional C1 overwrites in the same cycle are counted in
the raw collision count but not re-counted in the latency distribution.

---

## 6. False-positive and exclusion rules

Exclude from **both** numerator and denominator:

1. **Pre-removal window.** Any data before **2026-07-11** (`cc720ab`) is a
   *different runtime* (WAF timer live, supervisor gated on it). The four-week
   measurement window must lie entirely on/after this date. Mixing regimes
   invalidates the rate.
2. **Supervisor disabled.** Rows with `Supervisor_Enabled = false` (or blank/
   unknown) — the supervisor cannot collide when it is not running
   ([`deferred_until_telemetry.md`](deferred_until_telemetry.md) rule 3).
3. **Operator-suppressed / manual windows** per
   [`telemetry_confounders.md`](telemetry_confounders.md): Heat Wave Override
   (Section 19) active, and any explicitly logged manual-cool window. During
   Section 19 the supervisor stands down (`heat_wave_override` gate,
   `automations.yaml:399-401`), so a `77→61` change there is Section 19, **not**
   a Section 2 collision → route to C3.
4. **Truth-unavailable intervals.** `LR_Air_Temperature_Truth` invalid
   (None/NaN/out of [-90,200]) — the per-zone `*_truth_ok` guard forces off and
   the setpoint change is a failsafe artifact, not a collision.
5. **Boundary double-count guard.** If a single `77→non-77` transition spans two
   adjacent samples, count it **once**, keyed on the first sample below `77`.
6. **Provenance clock skew.** Allow a **±1-minute** join tolerance for
   `hvac_provenance_log` vs. launch-data timestamps; a match within ±1 min on
   the same `climate.living_room_air` entity qualifies. Wider gaps → C5.

Every excluded event is logged with its exclusion reason so the audit is
reproducible; exclusions are reported as counts alongside the numerator.

---

## 7. Denominator, counters, and success/failure thresholds

**Denominator.** The unit of rate is the **boost cycle**, not the tick.
`eligible_cycles` = all cycles whose engage edge falls in the four-week window
and that survive §6 exclusions. Report also `eligible_active_minutes` (sum of
boost-active minutes) as a secondary denominator for a per-hour rate.

**Primary counters (weekly and cumulative):**

- `collision_cycles` = cycles with ≥ 1 C1 event.
- `collision_rate = collision_cycles / eligible_cycles`.
- `collisions_per_active_hour = total_C1_events / (eligible_active_minutes/60)`.
- `latency_median_min`, `latency_p95_min` over first-C1-per-cycle `latency_min`.
- `clean_cycles` (C2) and `clean_cycle_rate = clean_cycles / eligible_cycles`.
- Category tallies C3, C4, C5 and total excluded with reasons.

**Success / failure thresholds (verdict rule, decided *before* looking at data):**

| Outcome | Condition after ≥ 4 weeks | Consequence |
|---|---|---|
| **Collision confirmed recurrent** | `eligible_cycles ≥ 8` **and** `collision_rate ≥ 0.30` **and** `latency_median_min ≤ 15` | Recurrence is measured. The Section 2 latch-consult candidate ([`v9_v10_goals.md`](v9_v10_goals.md) §2.2, [`3_regression_appendix.md`](3_regression_appendix.md) §4.17) becomes *eligible* for a separately-scoped runtime issue. **Still not auto-authorized** (register rule 4). |
| **Collision rare / not recurrent** | `eligible_cycles ≥ 8` **and** `collision_rate < 0.10` | §4.17 anecdote is downgraded; no latch consult. The collision is recorded as a non-recurring forensic curiosity. |
| **Indeterminate** | `eligible_cycles < 8` (too few boost cycles fired) **or** `0.10 ≤ collision_rate < 0.30` | Extend the window (up to +4 weeks) before any verdict. Report as inconclusive; do **not** close #91. |
| **Clean cycle finally observed** | any C2 with `clean_cycle_rate > 0` | Independently unblocks the Section 14 effectiveness verdict track (Issue #49), which requires an overwrite-free cycle. Report but keep separate from the collision verdict. |

Thresholds are stated up front so the verdict is not chosen after seeing the
numbers. If the eligible-cycle floor (`≥ 8`) is not met in eight weeks, escalate
to Eric: the boost may simply be firing too rarely to measure, which is itself
the finding.

---

## 8. Exact final evidence (what closing #91 must produce)

1. **A labeled collision table** (one row per C1 event): `engage_minute`,
   `overwrite_minute`, `latency_min`, `setpoint_from`(=77), `setpoint_to`,
   `provenance_automation_candidate`(=`v7_5_main_supervisor`), `cycle_id`,
   `week`.
2. **A cycle ledger** (one row per eligible cycle): `cycle_id`, `engage_minute`,
   `termination_minute`, `termination_reason` ∈ {supervisor_overwrite, truth_cap,
   timeout, section19, restart, truth_unavailable, other}, `category` (C1..C5),
   `n_C1_events`.
3. **A counters block** (weekly × 4 + cumulative): every counter in §7, plus the
   exclusion tally with reasons.
4. **A verdict line** stating which §7 outcome was reached and the exact numbers
   supporting it.
5. **Placement outside HA:** a `Collision_Quantifier_91` Sheets tab **or** a
   committed notebook `docs/analysis/…` **or** a posted forensic note. No HA
   automation consumes it.
6. **Lineage link added** to [`3_regression_appendix.md`](3_regression_appendix.md)
   §4.17 source-lineage line pointing at the produced report (this is the closing
   act for #91, done in a follow-up docs PR once the four weeks are tabulated).

---

## 9. Four-week execution schedule

| Week | Action |
|---|---|
| 0 (setup) | Confirm both tabs export the §4 fields on/after 2026-07-11. Freeze the notebook/pivot logic (§2–§7). Dry-run on one historical post-`cc720ab` week to validate the join and category routing. **No thresholds evaluated.** |
| 1–4 | Weekly: pull the week's rows, run the analytic, append weekly counters. Do **not** call a verdict mid-window. |
| 4 (close) | Compute cumulative counters, median/p95, apply the §7 verdict rule, emit the §8 evidence bundle, and open the follow-up docs PR to add the §4.17 lineage link. |

**Non-goals (verbatim from #91):** adds no automation, no helper; does not change
`automations.yaml`; does not retune thresholds (64°F engage, 67°F truth_cap, 77°F
setpoint, 90-min timer); does not claim Section 14 effectiveness; does not weaken
any safety gate; does not propose deadband changes or autonomous control; does
not read `hvac_provenance_log`/`supervisor_state_log` **from** Home Assistant
(reads the exported Sheets tabs only).

## 10. Cross-references

- [`3_regression_appendix.md`](3_regression_appendix.md) §4.17, §4.18
- [`comfort_failure_forensics.md`](comfort_failure_forensics.md) §8.3
- [`5_runtime_layer.md`](5_runtime_layer.md) §7.4
- [`v9_v10_goals.md`](v9_v10_goals.md) §2.2, §4.2, §9
- [`analysis/v8_4_lr_boost_v5_evidence_review.md`](analysis/v8_4_lr_boost_v5_evidence_review.md)
- [`telemetry_confounders.md`](telemetry_confounders.md)
- [`manual_override_and_v9e_reconciliation.md`](manual_override_and_v9e_reconciliation.md)
  (WAF removal — governs the §6 exclusion of "WAF-attributed" terminations)
</content>
