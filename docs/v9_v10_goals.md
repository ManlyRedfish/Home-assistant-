# V9 / V10 Goals

**Doc Date:** 2026-05-16
**Document Role:** Updated project direction for the V9 and V10 architecture phases.
**Status:** Living. Update when V9 or V10 scope is formally adjusted, when an item moves between "first PR" and "later PR" buckets, or when telemetry evidence justifies promoting a deferred item.
**Scope:** Documentation only. Does not change runtime YAML, thresholds, safety gates, helpers, telemetry schema, or any control authority.

---

## 1. Executive Summary

V9 is **runtime simplification, collision reduction, manual-override
discipline, transition/latch clarity, and provenance completeness.** It is
not a new comfort-aggression phase.

V10 is **algorithm-supported diagnosis only.** Not autonomous HVAC control.
V10 surfaces help operators classify forensic windows faster; they never
command climate state.

TBD / post-V10 work may eventually reconsider richer control authority, but
only after V9 collision reduction lands, V10 diagnosis has produced a
labeled forensic archive over at least one full season, and Eric's deadband
contract is preserved as the comfort surface.

This document complements:

- [`./comfort_failure_forensics.md`](./comfort_failure_forensics.md) — the workflow this direction is built around.
- [`./3_regression_appendix.md`](./3_regression_appendix.md) — what V9 and V10 must not re-propose.
- [`./1_startup_canon.md`](./1_startup_canon.md) — the live doctrine V9 and V10 inherit from.
- [`./5_runtime_layer.md`](./5_runtime_layer.md) — the implementation boundary V9 simplifies and V10 reads from.
- [`./6_proposals.md`](./6_proposals.md) — architecture proposals (now scoped to forensic readiness).

## 2. V9 Goal

V9 is bounded by five themes. Each is candidate-shaped: docs first, runtime
changes only after telemetry evidence supports them.

### 2.1 Simplification

Reduce the structural debt called out in
[`./5_runtime_layer.md`](./5_runtime_layer.md) §7.1–§7.4:

- HVAC-mode-as-memory shortcut.
- Command-on-every-tick supervisor.
- Orphaned / transitional runtime pieces.

The simplification target is reducing the number of ways the same comfort
decision can be expressed in YAML, not increasing the number of comfort
decisions.

### 2.2 Collision Reduction

Document and (only with telemetry proof) reduce the Section 2 ↔ Section 14
overwrite class documented in
[`./5_runtime_layer.md`](./5_runtime_layer.md) §7.4 and
[`./3_regression_appendix.md`](./3_regression_appendix.md) §4.17. Candidate:
a one-line `input_boolean.lr_heating_recovery_boost_active == off` gate in
Section 2's heating branch (per
[`./v8_4_heating_recovery_boost_plan.md`](./v8_4_heating_recovery_boost_plan.md)
§7.4). Requires forensic recurrence evidence first.

### 2.3 Manual-Override Discipline

Doctrinal classification of every HVAC-writing path against
`timer.manual_hvac_override`. Codified in
[`./5_runtime_layer.md`](./5_runtime_layer.md) Manual Override Contract
section. Two ambiguous interlocks (`v9_sleep_priority_interlock`,
`v7_5_ghost_assassin`) require explicit doctrine clarification before any
runtime change to their override authority.

### 2.4 Transition / Latch Clarity

Replace mode-as-memory with explicit per-room latches when the V6
event-oriented telemetry schema lands (see
[`./v6_telemetry_schema_proposal.md`](./v6_telemetry_schema_proposal.md)
and [`./v6_observability_roadmap.md`](./v6_observability_roadmap.md)).
Candidate scope, deferred until V6 schema is live and forensic evidence
supports the change.

### 2.5 Provenance Completeness

Extend the Section 15 provenance logger
([`./hvac_provenance_logger_design.md`](./hvac_provenance_logger_design.md))
to cover, in subsequent observability-only PRs:

- Master / Lincoln / Lilly climate state and `temperature` attribute.
- `input_select.hvac_season_mode` changes.
- `v9_sleep_priority_interlock` fire events (via the LR mode transitions
  it produces, or an explicit observer trigger).
- `v7_5_safety_ceiling_gates` fire events.
- `v7_5_ghost_assassin` fire events.

Pure observability fan-out. No control authority added. Each extension
honors the
[`./hvac_provenance_logger_design.md`](./hvac_provenance_logger_design.md)
forbidden-path discipline: tab is HA-write-only; no automation reads it.

## 3. V9 Non-Goals

V9 is **not**:

- New comfort branches or new aggressive setpoints.
- Targeted Pre-Chill (aggressive 61°F Master / Turbo at 17:00). Per
  [`./6_proposals.md`](./6_proposals.md) this is deferred until forensic
  recurrence evidence supports it.
- Generic HVAC best-practices reshaping of the deadband contract.
- Multi-head capacity arbitration without telemetry proof. Already retired
  per [`./3_regression_appendix.md`](./3_regression_appendix.md) §4.5.
- New manual-vs-policy or cross-mode arbitration without telemetry proof.
  Per [`./3_regression_appendix.md`](./3_regression_appendix.md) §4.18.
- AI or autonomous comfort control of any kind.
- Promotion of Apollo / MSR data into control beyond the documented Lincoln
  fan-only exception
  ([`./apollo_msr_observability_checklist.md`](./apollo_msr_observability_checklist.md)).
- A redesign of Eric's deadbands. Deadbands are the comfort contract, not
  the thing being iterated.

## 4. V10 Goal

V10 is **algorithm-supported diagnosis.** Every V10 surface reads from
telemetry / provenance / annotation tabs and writes forensic outputs. No
V10 surface mutates HA state or commands climate.

Candidate V10 surfaces, each scoped to a specific forensic question:

### 4.1 Expected-vs-Actual Deadband Checker

For each room and time-of-day branch, compute the expected ON/OFF/setpoint
per [`./5_runtime_layer.md`](./5_runtime_layer.md) §6.1 and diff against
the actual `VTherm_Launch_Data_v5_5` rows. Flag tick-level disagreements
as candidate contract-failure signatures for human review.

### 4.2 Provenance Collision Detector

Scan `hvac_provenance_log` for overlapping `automation_candidate` writes
within a short window (e.g., a Section 2 supervisor write within 15
minutes of a Section 14 boost engage on the same entity). Surfaces the
§4.17 collision class quantitatively rather than anecdotally.

### 4.3 Recovery / Slope Analyzer

For each Section 14 boost cycle and each post-override recovery, compute
the truth-temperature slope per minute. Compare against an envelope
baseline. Surfaces "room was recovering but too slowly" candidates per
[`./comfort_failure_forensics.md`](./comfort_failure_forensics.md) §8.8.

### 4.4 Sensor Truth Health Checker

Cross-room aggregate of `<Room>_Truth_Count`, staleness, and
outlier-rejection events. Surfaces degraded contributors before they
cause comfort failures, complementing `v8_truth_count_alert`.

### 4.5 Cross-Room Conflict Classifier

For windows where two or more rooms were in conflicting modes, classify
whether `v9_sleep_priority_interlock` fired, whether stack-effect coupling
was observed, or whether the conflict was transient supervisor mode-flip
noise.

### 4.6 Suggested-Fix Report Generator

Combine the above into a per-complaint forensic report that names the
failure signature(s) from
[`./comfort_failure_forensics.md`](./comfort_failure_forensics.md) §8 and
proposes one targeted fix candidate. The household decides. The report is
forensic; it does not run YAML changes.

## 5. V10 Non-Goals

V10 is **not**:

- Autonomous HVAC control.
- Predictive setpoint control.
- ML-driven season switching.
- A permanent comfort survey routed into HA control. Per
  [`./3_regression_appendix.md`](./3_regression_appendix.md) §4.13.
- Any path that mutates HA state from a derived analytic.
- A replacement for the supervisor, safety gates, or Section 14 boost.

## 6. TBD / Future Intelligence

Anything beyond V10 is explicitly speculative. Reconsidering autonomous
control or richer comfort policy is contingent on:

- V9 collision reduction is complete and verified by telemetry.
- V10 diagnosis has produced a labeled archive of comfort-failure forensic
  notes spanning at least one full season of operation.
- Eric's deadband contract continues to be preserved as the comfort
  surface.
- Any new control authority is preceded by a Doc 6 proposal, a
  regression-appendix reopen-condition check
  ([`./3_regression_appendix.md`](./3_regression_appendix.md) §6), and a
  docs-first design pass.

No TBD item has scope or budget today.

## 7. Manual Override Doctrine

- `timer.manual_hvac_override` is the household's immediate comfort intent
  surface. The WAF watcher (`v7_5_waf_manual_override`) is the single
  legitimate immediate ingest.
- The supervisor (Section 2), the safety ceiling gates (Section 3, 76°F),
  the fan destratification (Section 6), Samsung Auto Guardrail (Section 8),
  and Section 14 boost engage all gate on
  `timer.manual_hvac_override == idle`. This is the contract.
- The LR runaway cutoff (60°F) and Master emergency floor (58°F) do **not**
  gate on override. They are true safety gates and must override manual
  intent.
- `v9_sleep_priority_interlock` and `v7_5_ghost_assassin` do not gate on
  override today. Their authority over manual intent is **ambiguous**
  under the new doctrine; classification is pending and tracked in
  [`./5_runtime_layer.md`](./5_runtime_layer.md) Manual Override Contract
  section.

V9 simplification work must preserve this contract. New comfort-policy
automations must respect it from inception per
[`./3_regression_appendix.md`](./3_regression_appendix.md) §4.15.

## 8. Safety Gate Doctrine

True safety gates (LR runaway 60°F, Master floor 58°F) are equipment
protection. They are not comfort dials. They override manual intent
because their concern is hardware, not preference. They must not be:

- Weakened.
- Re-thresholded toward comfort behavior.
- Suppressed by override timers.
- Made comfort-policy in disguise.

The 76°F ceiling gate is a *comfort* ceiling under the new doctrine (not
equipment protection). It correctly gates on
`timer.manual_hvac_override == idle`. The Manual Override Contract section
in [`./5_runtime_layer.md`](./5_runtime_layer.md) makes this classification
explicit so future agents do not mis-tag it.

Integration-anomaly gates (Samsung Auto Guardrail, Ghost Assassin) protect
against known device misbehavior. They are not true safety gates and not
comfort-policy automations. V9 doctrine work should pick a consistent rule
for whether they gate on override; today the two paths disagree and
classification is part of the Manual Override Contract clarification.

## 9. Provenance Doctrine

- `hvac_provenance_log` is HA-write-only. No automation, condition,
  template, or supervisor branch may read from it. Locked by
  `tests/test_provenance_observability.py::test_no_automation_reads_hvac_provenance_log`.
- `supervisor_state_log` is human narrative. HA does not read it. See
  [`./operator_annotation_design.md`](./operator_annotation_design.md) §6
  forbidden paths.
- Neither tab is a control input. Both are joinable forensic surfaces.
- V10 surfaces consume both tabs plus `VTherm_Launch_Data_v5_5`. V10
  outputs are forensic notes, not control commands.

Provenance completeness (§2.5 above) extends what the logger observes but
does not change what consumes the log. The forbidden-path discipline
applies to all V9 and V10 work.

## 10. Relationship to Current Deadbands

V9 and V10 do not change deadbands. The live deadbands defined in
[`./1_startup_canon.md`](./1_startup_canon.md) §5.1 and
[`./5_runtime_layer.md`](./5_runtime_layer.md) §6.1 are the comfort
contract. V9 simplification preserves them; V10 diagnosis measures them.

A deadband change is a separate, evidence-gated conversation. It
requires:

- Repeated forensic notes (per
  [`./comfort_failure_forensics.md`](./comfort_failure_forensics.md))
  showing the same contract failure mode across multiple independent
  investigations.
- A doctrine update to
  [`./1_startup_canon.md`](./1_startup_canon.md) §5.1 and
  [`./5_runtime_layer.md`](./5_runtime_layer.md) §6.1.
- A regression-appendix check against §4.10 (waterfall doctrine), §4.11
  (V8.3 bedtime reduction note), §4.12 (anecdote-driven YAML), and §4.18
  (arbitration before telemetry) so the change is not a renamed retired
  approach.
- A scoped runtime PR after the docs land.

It does not happen mid-investigation, and it does not happen from a single
complaint.

## 11. First PR / Later PR Separation

This direction is delivered in phases.

### 11.1 First PR (this PR) — Docs-only

- New: [`./comfort_failure_forensics.md`](./comfort_failure_forensics.md).
- New: this document.
- Updates to [`./3_regression_appendix.md`](./3_regression_appendix.md)
  (§4.12–§4.19).
- Updates to [`./1_startup_canon.md`](./1_startup_canon.md) (§5.1
  reframed as Comfort Contract, cross-links added).
- Updates to [`./5_runtime_layer.md`](./5_runtime_layer.md) (Manual
  Override Contract section).
- Updates to [`./4_operations_sheet.md`](./4_operations_sheet.md)
  (friction / complaints / thresholds reframed as forensic inputs).
- Updates to [`./6_proposals.md`](./6_proposals.md) (V9 reframed;
  aggressive comfort proposals deferred).
- **No** `automations.yaml`, `configuration.yaml`, ESPHome, helper,
  threshold, or test changes.

### 11.2 Later PRs (deferred)

- Provenance fan-out (§2.5) — observability-only YAML, scoped to one
  trigger surface at a time.
- Section 2 latch consult against Section 14 (§2.2) — requires forensic
  recurrence evidence and a separate doctrine PR.
- V10 surfaces (§4.1–§4.6) — built outside HA; consumes Sheets tabs;
  produces forensic notes.
- Any deadband change — requires repeated forensic evidence and its own
  doctrine PR per §10.

Each later PR is independent, scoped to one item, telemetry-evidence-
prefaced, and re-checked against
[`./3_regression_appendix.md`](./3_regression_appendix.md) before merge.

---

_End of V9 / V10 Goals Doc._
