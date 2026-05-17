# Comfort Failure Forensics

**Doc Date:** 2026-05-16
**Document Role:** Forensic workflow for comfort-contract investigations.
**Status:** Living. Update when a new canonical failure signature is identified, when a new provenance/telemetry surface lands, or when an existing signature is retired by evidence.
**Scope:** Documentation only. Does not change runtime YAML, thresholds, safety gates, helpers, telemetry schema, or any control authority.

---

## 1. Purpose

This document is the canonical workflow for investigating comfort complaints in
Moose House. It exists so that "the room was too hot/cold last night" produces
a forensic reconstruction of what the system actually did, not a speculative
redesign of what the system should be.

It complements:

- [`./3_regression_appendix.md`](./3_regression_appendix.md) — what not to re-propose.
- [`./telemetry_confounders.md`](./telemetry_confounders.md) — when a window cannot be evaluated against Section 2 doctrine.
- [`./hvac_provenance_logger_design.md`](./hvac_provenance_logger_design.md) — the machine provenance surface.
- [`./operator_annotation_design.md`](./operator_annotation_design.md) — the human narrative annotation surface.
- [`./v9_v10_goals.md`](./v9_v10_goals.md) — why this workflow exists and what V9/V10 should and should not do with it.

## 2. Core Doctrine

- Deadbands are the comfort contract.
- Comfort complaints are not requests to redesign control logic.
- Comfort complaints are contract-failure investigations.
- Telemetry and provenance are the black-box recorder.
- Fixes should target the proven failure mode only.
- Manual comfort intent should beat comfort-policy automations during the override window.
- Only true safety gates may override manual intent.
- Human discomfort is evidence, not a direct control input.

## 3. Deadbands as the Comfort Contract

A deadband is the temperature range a room is allowed to float while not
actively heating or cooling. The live deadbands are defined in
[`./5_runtime_layer.md`](./5_runtime_layer.md) §6.1 and
[`./1_startup_canon.md`](./1_startup_canon.md) §5.1. They are the comfort
*contract* between the system and the household:

- The room is allowed to float inside the deadband without action.
- The system is expected to act when truth crosses the deadband boundary.
- The system is expected to honor manual override (`timer.manual_hvac_override`) for the duration of the override window.
- True safety gates (Section 3 LR runaway 60°F, Master emergency floor 58°F) override everything, including manual intent.

Deadbands are not a draft to be iterated. They are the contract. When a
complaint suggests the contract was violated, the contract is not what is on
trial — the system's adherence to the contract is.

## 4. What a Comfort Complaint Means

A complaint such as "my room was too hot/cold last night" is an *observation*,
not a directive. It means:

> The household experienced something inconsistent with the comfort contract
> during some window. Reconstruct what the system was doing in that window
> and identify which contract clause (if any) was actually broken.

What it does **not** mean:

- It does not mean "add a new automation."
- It does not mean "tighten the deadband."
- It does not mean "lower the setpoint."
- It does not mean "redesign the supervisor."
- It does not mean the deadband contract is wrong.

A single complaint is a forensic input. Repeated, classified,
telemetry-backed failures of the *same* mode are evidence for a targeted
change — and even then, the smallest change that addresses the proven
failure mode is preferred. See
[`./3_regression_appendix.md`](./3_regression_appendix.md) §4.12 for the
retired pattern "YAML for every discomfort anecdote."

## 5. Required Inputs

To investigate a comfort complaint, the following sources are required:

- **`VTherm_Launch_Data_v5_5`** (Google Sheets) — 15-minute snapshot per
  [`./5_runtime_layer.md`](./5_runtime_layer.md) §5.3. Captures truth temps
  per room, climate mode/action/setpoint, HP runtime, presence, shades, and
  Section 14 boost columns.
- **`hvac_provenance_log`** (Google Sheets sibling tab) — per
  [`./hvac_provenance_logger_design.md`](./hvac_provenance_logger_design.md)
  §7. Tags HVAC state/setpoint changes for the observed entities with
  `origin_kind` (`manual_user`, `automation_or_script`,
  `integration_or_device`, `system_restore`, `unknown`).
- **`supervisor_state_log`** (Google Sheets sibling tab) — per
  [`./telemetry_confounders.md`](./telemetry_confounders.md) §6 and
  [`./operator_annotation_design.md`](./operator_annotation_design.md) §4.0.
  Manual operator narrative including `supervisor_disabled`,
  `manual_setpoint_nudge`, `waf_observed`, `boost_observed`, `away_window`,
  `truth_unavailable`, `comfort_complaint`.
- **HA Logbook** — Section 11 HVAC Transition Logger entries plus ambient
  state-change history governed by `recorder.purge_keep_days`.
- **Live YAML** — `automations.yaml` Section 2 (supervisor), Section 3
  (safety gates and WAF watcher), Section 14 (boost), and Section 15
  (provenance logger). Per [`./5_runtime_layer.md`](./5_runtime_layer.md)
  §3, YAML wins for runtime truth.

Before drawing conclusions, run the window through
[`./telemetry_confounders.md`](./telemetry_confounders.md) §4 decision tree.
If the row is classified `operator_suppressed_likely`, doctrine conclusions
about Section 2 cannot be drawn from the window.

## 6. Standard Investigation Window

The default forensic window is **6–12 hours of telemetry around the
complaint**. Narrower windows miss the lead-up; wider windows dilute the
signal.

- If the complaint references "last night," pull from roughly 18:00 the
  prior day through 09:00 the morning of the complaint.
- If the complaint is "today," pull the trailing 6–12 hours from the
  complaint timestamp.
- For Section 14 boost-cycle investigations, the engage minus 30 min through
  release plus 60 min is the canonical span.

Expand the window only when the data inside it is insufficient to classify
the failure mode. Do not widen the window in order to find a signal that
the narrower window did not contain — that is fishing, not forensics.

## 7. Diagnostic Workflow

Walk through each step in order. Do not skip ahead to "recommend a fix"
before classification.

1. **Pin the window.** Choose the 6–12 hour interval. Record the complaint
   timestamp, room(s), and reported symptom (too hot / too cold / sticky /
   fussy).
2. **Classify the window** against
   [`./telemetry_confounders.md`](./telemetry_confounders.md) §4. If it is
   `operator_suppressed_likely` or `waf_or_manual_override_possible`, note
   that explicitly. Do not blame Section 2 for behavior the supervisor was
   disabled for.
3. **Read the deadband contract** for the affected room and time-of-day
   from [`./5_runtime_layer.md`](./5_runtime_layer.md) §6.1 and the live
   YAML. Write down the expected ON-at, OFF-at, and setpoint values for
   that branch.
4. **Pull truth, mode, and setpoint columns** for the room from
   `VTherm_Launch_Data_v5_5`. Compare expected ON/OFF/setpoint to actual
   mode/setpoint at each 15-minute tick. Note every tick where actual
   disagrees with expected.
5. **Inspect `hvac_provenance_log`** for the same window. For each
   disagreement tick, identify the `origin_kind` and `automation_candidate`.
   Distinguish supervisor writes, manual writes, integration pushes, and
   restore traffic. Coverage is currently LR-only and the four narrow
   triggers in
   [`./hvac_provenance_logger_design.md`](./hvac_provenance_logger_design.md)
   §5; do not infer master/lincoln/lilly provenance from absence of rows.
6. **Inspect `supervisor_state_log`** for overlapping annotations. An
   overlapping `manual_setpoint_nudge`, `waf_observed`,
   `supervisor_disabled`, `truth_unavailable`, or `stale_setpoint_artifact`
   annotation generally disqualifies the window from a clean Section 2
   verdict per
   [`./telemetry_confounders.md`](./telemetry_confounders.md) §6.4.
7. **Identify the failure mode** from §8 below. If multiple modes overlap,
   name each. If no signature fires, say so — the contract may have been
   honored and the complaint may be about preference rather than violation.
8. **Recommend one targeted fix** consistent with
   [`./v9_v10_goals.md`](./v9_v10_goals.md). The smallest change that
   addresses the proven mode. If the evidence supports no change — say so.

## 8. Canonical Failure Signatures

Each signature is a candidate explanation, not a verdict. A verdict
requires at least one signature to be supported by telemetry + provenance
evidence inside the investigation window.

### 8.1 Supervisor Overwrite

**Signature.** A non-doctrinal setpoint (operator-set) is replaced by a
doctrinal setpoint on a `:00`/`:15`/`:30`/`:45` boundary.
`hvac_provenance_log` shows `origin_kind = automation_or_script` and
`automation_candidate = v7_5_main_supervisor` on the overwrite tick.

**Diagnosis.** The household setpoint was reasserted as the override
window expired (1 hour default) and the next supervisor tick re-applied
policy.

**Targeted fix candidate.** None unless this failure mode recurs across
multiple independent forensic notes. The 1-hour override decay is the
documented contract; longer windows require explicit manual re-engagement.

### 8.2 Boost Released Too Early

**Signature.** `Section14_Last_Release_Reason ∈ {waf, truth_unavailable,
season_change, unknown_release_reason}` rather than `truth_cap` or
`timeout`. Per [`./5_runtime_layer.md`](./5_runtime_layer.md) §7.4 all
four observed May cycles match this signature.

**Diagnosis.** The boost lifecycle terminated externally before LR truth
reached the 67°F cap or before the 90-minute timeout.

**Targeted fix candidate.** None until
[`./analysis/v8_4_lr_boost_v5_evidence_review.md`](./analysis/v8_4_lr_boost_v5_evidence_review.md)
records a clean cycle. Effectiveness remains unmeasured; do not retune
thresholds.

### 8.3 Boost Overwritten by Supervisor

**Signature.** `Section14_Boost_Active = true` while `LR_Air_Setpoint`
flips from 77 to 68 on a supervisor tick boundary.
`hvac_provenance_log` shows `origin_kind = automation_or_script` and
`automation_candidate = v7_5_main_supervisor` on the flip.

**Diagnosis.** Section 2 issued the doctrinal heating setpoint while
Section 14 was still latched on. This is the documented collision class
in [`./v8_4_heating_recovery_boost_plan.md`](./v8_4_heating_recovery_boost_plan.md)
§7.4 and [`./3_regression_appendix.md`](./3_regression_appendix.md) §4.17.

**Targeted fix candidate.** Doctrine-only acknowledgement first; a
one-line latch consult in Section 2 is a candidate but requires
telemetry proof of recurrence first per
[`./v9_v10_goals.md`](./v9_v10_goals.md) §2.2.

### 8.4 Samsung / Device Integration Anomaly

**Signature.** A climate entity enters `auto` mode, or `hvac_action`
flips without a corresponding HA command. `hvac_provenance_log` shows
`origin_kind = integration_or_device`. Samsung Auto Guardrail
(Section 8) may have fired and issued a `notify.notify`.

**Diagnosis.** Cloud-pushed integration state, not a supervisor or boost
decision.

**Targeted fix candidate.** Confirm Samsung Auto Guardrail caught it.
If a new anomaly pattern is observed, classify under the
"integration-anomaly gate" category in
[`./5_runtime_layer.md`](./5_runtime_layer.md) Manual Override Contract
section before any new automation is proposed.

### 8.5 Manual Override Ignored

**Signature.** A comfort-policy automation wrote climate state while
`timer.manual_hvac_override` was `active`. `hvac_provenance_log` shows
`origin_kind = automation_or_script` on a tick where
`Section14_WAF_Active = true` should have suppressed the write.

**Diagnosis.** The manual override contract was violated. This is a
contract failure, not a comfort tradeoff. See
[`./3_regression_appendix.md`](./3_regression_appendix.md) §4.15.

**Targeted fix candidate.** Add the missing override gate to the
offending automation, scoped to that automation only. See the
Manual Override Contract section in
[`./5_runtime_layer.md`](./5_runtime_layer.md).

### 8.6 Season / Outdoor Branch Overruled Manual Intent

**Signature.** After `timer.manual_hvac_override` expires, the
supervisor's season branch immediately bulk-offs or re-modes the room
the household had manually set. Common signature: heating-night branch
evaluating `master_temp < 67` → false → sets Master to `off` after a
manual `cool/61` setting expired.

**Diagnosis.** Manual intent decayed past the 1-hour override window;
the next supervisor tick honored the season branch instead of any
documented comfort-escape.

**Targeted fix candidate.** Confirm whether the failure is "override
window too short" (household preference, not a contract failure) or
"no comfort-escape branch exists for that season/time combination."
For the latter, see the shoulder-night Master cooling escape (commit
`e00013d`) as the reference shape. Do not generalize without forensic
recurrence per [`./3_regression_appendix.md`](./3_regression_appendix.md)
§4.16.

### 8.7 Sensor Truth Degraded

**Signature.** `<Room>_Truth_Count` is below the room's normal
contributor count for one or more ticks in the window.
`v8_truth_count_alert` may have fired.

**Diagnosis.** Supervisor made decisions on a thinner-than-usual
contributor set; outlier rejection logic may have demoted a real
reading.

**Targeted fix candidate.** Investigate the degraded contributor
(transport, battery, staleness). Per
[`./3_regression_appendix.md`](./3_regression_appendix.md) §4.8,
transport degradation is not total truth-layer failure unless
fallbacks are also degraded. Do not retune the truth-layer math from
a single complaint.

### 8.8 Room Was Recovering But Too Slowly

**Signature.** `<Room>_HP_Runtime_Today_Hrs` delta is non-zero across
the window but `<Room>_Temp_Truth` rise/fall rate is below what the
envelope predicts. No supervisor or boost anomaly is present.

**Diagnosis.** Equipment was working; physics was slow. Stack effect,
infiltration, or low Samsung compressor demand modulation may be at
fault. See [`./v8_4_heating_recovery_boost_plan.md`](./v8_4_heating_recovery_boost_plan.md)
§1.1 for the modulation context.

**Targeted fix candidate.** Doctrine question, not a runtime fix. Do
not retune deadbands from a single forensic note. Repeated identical
notes across many days may justify a separate envelope investigation.

### 8.9 Cross-Room Arbitration / Stack-Effect Conflict

**Signature.** A cross-mode event (e.g., Master cool while LR heat)
intersected the window. `v9_sleep_priority_interlock` may have fired
(LR forced off). SPI fires can now be confirmed by looking for an
`hvac_provenance_log` row tagged
`automation_candidate = v9_sleep_priority_interlock` (Section 15
`spi_last_triggered` observer, PR #98). A dedicated logbook tag for SPI
fires does not exist yet, so for the logbook surface the fire is still
inferred from the LR mode transition signature.

**Diagnosis.** Either SPI fired correctly on a cross-mode contention,
or a stack-effect interaction was visible, or a transient
supervisor mode-flip looked like a conflict in low-resolution
telemetry.

**Targeted fix candidate.** SPI does not gate on
`timer.manual_hvac_override` today. Check whether the LR mode it killed
was manual or supervisor-derived. Cross-reference
[`./3_regression_appendix.md`](./3_regression_appendix.md) §4.4 and
§4.18 before proposing any change to SPI authority.

### 8.10 Shade / Solar / Fan Side Effect

**Signature.** Solar harvest tilt at 100 + LR truth rising faster than
the envelope predicts, or destratification `fan_only` entered during a
heating call, or solar rejection tilt without the expected downstream
behavior.

**Diagnosis.** A side-effect path (Section 6 fan destratification,
Section 7 solar shade protection, Section 7B solar harvest) was
active.

**Targeted fix candidate.** Confirm the gate conditions actually
evaluated as intended. Do not weaken Section 6's Lincoln MSR fan-only
exception (Apollo MSR observability boundary in
[`./apollo_msr_observability_checklist.md`](./apollo_msr_observability_checklist.md)).

## 9. Output Format

Every forensic investigation should produce a short, structured note. The
recommended structure:

```
Complaint: <verbatim or paraphrased>
Window: <start_local> to <end_local>
Room(s): <list>

Window classification (per telemetry_confounders.md §4):
  <clean_auto | operator_suppressed_likely | waf_or_manual_override_possible
   | boost_engaged | unknown>

Expected (deadband contract for this room/branch):
  - ON-at: ...
  - OFF-at: ...
  - Setpoint: ...

Actual (VTherm_Launch_Data_v5_5):
  - Notable disagreements: ...

Provenance (hvac_provenance_log; LR-only coverage today):
  - Origin kinds observed: ...
  - Automation candidates: ...

Annotations (supervisor_state_log):
  - Overlapping kinds: ...

Failure mode(s) identified: <one or more from §8, or "none — within contract">

Recommended targeted fix: <one item, or "none — within contract">

Open questions / unmeasured: ...
```

Forensic notes belong in the operator's workflow (notebook, ticket,
`supervisor_state_log` as a `comfort_complaint` kind, etc.). They are not
stored in Home Assistant. They are not control inputs.

## 10. What Not to Do

- **Do not add YAML for one anecdote.** A single complaint is a forensic
  input, not a control specification. See
  [`./3_regression_appendix.md`](./3_regression_appendix.md) §4.12.
- **Do not redesign deadbands without repeated forensic evidence.**
  Deadbands are the comfort contract. A deadband change is a separate
  doctrine PR with its own evidence record per
  [`./v9_v10_goals.md`](./v9_v10_goals.md) §10.
- **Do not route comfort votes / surveys directly into Home Assistant
  control.** Annotations are forensic-only. See
  [`./operator_annotation_design.md`](./operator_annotation_design.md) §6 and
  [`./3_regression_appendix.md`](./3_regression_appendix.md) §4.13.
- **Do not bypass `timer.manual_hvac_override` in a new comfort-policy
  automation.** See
  [`./3_regression_appendix.md`](./3_regression_appendix.md) §4.15.
- **Do not treat outdoor temperature or season as authoritative over manual
  intent.** See
  [`./3_regression_appendix.md`](./3_regression_appendix.md) §4.16.
- **Do not promote a single forensic finding to a doctrine change.** Doctrine
  changes require repeated proven cases per
  [`./3_regression_appendix.md`](./3_regression_appendix.md) §4.18.
- **Do not assume the deadband is wrong before the contract was tested.** The
  contract is the deadband honored during the override window and after,
  unless a true safety gate intervenes.

## 11. Example Investigation

> **Complaint.** "Master was too warm last night. I had to set it to cool
> myself around 02:30."
>
> **Window.** 2026-05-13 22:00 → 2026-05-14 08:00. Heating season.
>
> **Step 1 — Pin window.** Master Bedroom, 10-hour span.
>
> **Step 2 — Classify window.** Pull V5.5 rows. No full-day zero-runtime
> signal. `Master_Air_Setpoint` shows non-doctrinal `61` at 02:30, doctrinal
> `67` before and after. Classification: `waf_or_manual_override_possible`
> for the 02:30 row; `clean_auto` for prior rows per
> [`./telemetry_confounders.md`](./telemetry_confounders.md) §4.5.
>
> **Step 3 — Read contract.** Heating-night branch with `lr_night_primary =
> off`: Master target 67°F, ON-at `<67`, OFF-at `≥67`. (Section 2
> heating-night default; see [`./5_runtime_layer.md`](./5_runtime_layer.md)
> §6.1.)
>
> **Step 4 — Compare.** `Master_Temp_Truth` 68.4 → 68.7°F across 22:00–02:30.
> Mode `off` (per `Master_Air_Mode`). Expected per contract: off (truth ≥
> OFF-at). Actual: off. Per-tick agreement is correct against the contract.
>
> **Step 5 — Provenance.** No LR boost active.
> [`./hvac_provenance_logger_design.md`](./hvac_provenance_logger_design.md)
> §5 narrow first pass does not yet cover Master state/setpoint, so the
> 02:30 manual `cool/61` write is not surfaced in the provenance tab today.
> The manual write is still observable in HA Logbook.
>
> **Step 6 — Annotations.** Operator should add a `comfort_complaint` row
> covering the full window and a `manual_setpoint_nudge` row at 02:30 in
> `supervisor_state_log`.
>
> **Step 7 — Failure mode.** None of §8.1–§8.10 cleanly fires. The room was
> *inside* the contract (68.4–68.7°F, deadband 67–72°F nominal). The
> complaint is about preference, not contract violation.
>
> **Step 8 — Recommended fix.** None. The room was within the deadband. If
> household preference is now a tighter Master sleep target than 67°F in
> heating season, that is a deadband-change conversation requiring
> repeated forensic evidence per
> [`./v9_v10_goals.md`](./v9_v10_goals.md) §10, not a one-off YAML edit.
> Capture as `comfort_complaint` and watch for a recurring pattern over
> several weeks.

---

_End of Comfort Failure Forensics Doc._
