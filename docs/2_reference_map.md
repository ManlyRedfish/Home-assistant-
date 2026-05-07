# Doc 2 / Moose House Climate Reference Map

**Canon Date:** 2026-05-06
**Document Role:** Reference Map — canonical routing entry point.
**Status:** Index. Update when topology, sensor naming, source precedence, or entity routing materially changes.

---

## 1. Purpose

This is the canonical Doc 2 entry point referenced from `1_startup_canon.md`
(§9 Document Routing, §6 hardware-debt notes, §10 Startup Handoff Rule).

Doc 2 is the **routing and topology layer** of the Moose House documentation
hierarchy:

- **Doc 1 / Startup Canon** — `1_startup_canon.md` — what to believe.
- **Doc 2 / Reference Map** — *this document* — where to look.
- **Doc 3 / Regression Appendix** — `3_regression_appendix.md` — what not to reinvent.
- **Doc 4 / Operations Sheet** — `4_operations_sheet.md` — whether current doctrine is working.
- **Doc 5 / Runtime Layer** — `5_runtime_layer.md` — what is actually live now.
- **Doc 6 / Proposals** — `6_proposals.md` — V9 architectural proposals.
- **Telemetry Confounders** — `telemetry_confounders.md` — analysis guardrail.
- **Apollo MSR Observability Checklist** — `apollo_msr_observability_checklist.md` — observability-only doctrine and validation checklist for Apollo MSR sensors (proposed; no control-loop promotion).
- **Operator Annotation Design** — `operator_annotation_design.md` — proposed out-of-band forensic annotation workflow (Status: Proposed).
- **V6 Telemetry Schema Proposal** — `v6_telemetry_schema_proposal.md` — proposed `VTherm_Launch_Data_v6` schema (planning only; V5 remains active).
- **V6 Observability Roadmap** — `v6_observability_roadmap.md` — phase order and guardrails for V5 → V6 observability work.
- **V8.4 LR Boost V5 Evidence Review** — `analysis/v8_4_lr_boost_v5_evidence_review.md` — tab-by-tab forensic review of Section 14 (V8.4) boost cycles in `VTherm_Launch_Data_v5` and prior versioned tabs. Verdict: effectiveness remains unmeasured; #49 close criteria not met.
- **Postmortems** — `postmortems/` — historical incidents.

If a new session needs to know **which sensor feeds which truth calculation,
which entity is downstream of which, or where a given concept's source-of-truth
lives**, Doc 2 is the routing layer that answers that.

## 2. What belongs in Doc 2

- Static topology (rooms, sensors, mini-split heads, Nest dining/boiler).
- Sensor naming truth and aliases.
- Source precedence per room (BT primary / ST + Matter fallbacks / Samsung internal low-weight / MSR-2 DPS310 excluded).
- Entity-id routing (truth → smoothed → control wrapper → supervisor consumer).
- Helper inventory and what writes/reads each helper.
- Worksheet and column-name mapping for `VTherm_Launch_Data_v5`.

What does **not** belong in Doc 2:
- Doctrine and active control posture (Doc 1).
- Runtime-layer implementation boundaries (Doc 5).
- Deferred/retired approaches (Doc 3).
- Performance verdicts (Doc 4).
- Architectural proposals (Doc 6).
- Telemetry classification rules (`telemetry_confounders.md`).

## 3. Current detailed truth-sensor architecture

The detailed truth-sensor architecture currently lives at the repository root in
[`../truth_sensor_architecture.md`](../truth_sensor_architecture.md). That
document covers:

- The truth-sensor pipeline: physical sensors → truth → smoothed → control wrappers → supervisor → telemetry.
- Sensor-freshness policy (2-hour staleness rejection).
- Weighting philosophy (human-space sensors prioritized; Samsung internal kept low-weight).
- Lincoln pilot architecture (outlier rejection, contributor diagnostics).
- Smoothed-sensor lowpass filter parameters (`time_constant=10`, `precision=2`).
- Control-wrapper rationale.
- Critical consumers of truth sensors.

That file is the authoritative source for the truth-sensor part of Doc 2 until
or unless it is migrated into `docs/`. **This PR does not move it.** A future
PR may relocate it as `docs/2a_truth_sensor_architecture.md` (or fold its
content directly into this file) — the move is deferred to keep this PR narrow.

## 4. Pointers (interim, until topology content lands here)

For the topology and routing slices Doc 2 is meant to cover, current sources are:

| Topic | Authoritative source today | Notes |
|---|---|---|
| Truth-sensor pipeline / weighting / freshness | [`../truth_sensor_architecture.md`](../truth_sensor_architecture.md) | Detailed architecture. |
| Live truth/control/telemetry versions | [`5_runtime_layer.md`](5_runtime_layer.md) §5, §6 | V8.3 control, V3.1 truth, V5 telemetry. |
| Helper inventory (live) | [`5_runtime_layer.md`](5_runtime_layer.md) §6.5 + `automations.yaml` header | Helpers required for runtime. |
| Sensor exclusions (MSR-2 DPS310 etc.) | `configuration.yaml` Sections 3–9 (live source); summarized in [`5_runtime_layer.md`](5_runtime_layer.md) §7.5 | Live config wins. |
| Telemetry worksheet / column names | `automations.yaml` Section 1 (`vtherm_mega_tracker_v5`) | Worksheet `VTherm_Launch_Data_v5`. |
| Operator-suppressed window classification | [`telemetry_confounders.md`](telemetry_confounders.md) | Read before joining columns to behavior. |
| Apollo MSR observability validation (proposed) | [`apollo_msr_observability_checklist.md`](apollo_msr_observability_checklist.md) | Observability-only; not a control authority. |
| Operator annotation workflow (proposed) | [`operator_annotation_design.md`](operator_annotation_design.md) | Out-of-band; no HA helpers. Adoption tracked in #50. |
| V6 telemetry schema (proposed) | [`v6_telemetry_schema_proposal.md`](v6_telemetry_schema_proposal.md) | Planning only. V5 remains active. |
| V6 observability roadmap (proposed) | [`v6_observability_roadmap.md`](v6_observability_roadmap.md) | Phase order and guardrails. |
| V8.4 LR boost V5 evidence review | [`analysis/v8_4_lr_boost_v5_evidence_review.md`](analysis/v8_4_lr_boost_v5_evidence_review.md) | Forensic review of Section 14 boost cycles in `VTherm_Launch_Data_v5`. Verdict: effectiveness unmeasured; #49 not yet closeable. |

## 5. Conflict rule

If Doc 2 (this file) and the detailed source it routes to disagree, **the
detailed source wins** for routing accuracy and Doc 2 should be updated. If Doc
2 and live YAML disagree, **YAML wins** for runtime truth — re-route Doc 2.

## 6. Maintenance rule

Update Doc 2 when:

- A sensor is added to or removed from a room's truth calculation.
- An entity is renamed (e.g., the Lilly/Lincoln slug fix in PR #35/#39).
- A helper is added, removed, or repurposed.
- A worksheet column is added, removed, or renamed.
- The Reference Map's authoritative-source link list (§4) needs a new row.

Do not update Doc 2 merely to improve prose. Doc 2 is an index, not a narrative.
