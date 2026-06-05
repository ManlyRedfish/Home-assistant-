# Doc 6 / Proposals

**Date:** April 19, 2026 (V9 reframe 2026-05-16)
**Document Role:** Architecture Proposals & Blueprints
**Status:** Active pipeline for approved architectural shifts awaiting deployment windows. The V9 scope was reframed on 2026-05-16 around simplification and forensic readiness; see [`./v9_v10_goals.md`](./v9_v10_goals.md) for the authoritative V9 / V10 direction.

## 3.2 Proposed Architecture: V9 (Simplification + Forensic Readiness)

**Status:** Reframed 2026-05-16. V9 is no longer a new comfort-aggression phase. V9 is **simplification, collision reduction, manual-override discipline, transition/latch clarity, and provenance completeness** per [`./v9_v10_goals.md`](./v9_v10_goals.md) §2. V10 is **algorithm-supported diagnosis only** per [`./v9_v10_goals.md`](./v9_v10_goals.md) §4 — not autonomous HVAC control. Any item below that is not in the V9 §2 scope is deferred pending forensic justification per the workflow in [`./comfort_failure_forensics.md`](./comfort_failure_forensics.md).

**State:** V9 transitions the runtime toward clearer transitions, fewer collisions between Section 2 / Section 14, and more complete provenance — not toward more aggressive comfort policy. It is justified because the supervisor/boost collision class is unresolved ([`./3_regression_appendix.md`](./3_regression_appendix.md) §4.17) and the manual-override contract needs explicit classification ([`./5_runtime_layer.md`](./5_runtime_layer.md) Manual Override Contract section), not because V8.3 deadbands are failing as a contract.

### Core Architecture Shifts (V9, Reframed):

* **Decoupled Control Loops (candidate, requires telemetry proof).** Moving observation, decision, actuation, and protection off a single 15-minute clock tick is structurally appealing because it reduces the supervisor/boost collision class. It is **not** approved as an end in itself, and it must not be used as cover for introducing new comfort branches. Tied to V6 event-oriented telemetry ([`./v6_telemetry_schema_proposal.md`](./v6_telemetry_schema_proposal.md)).
* **Explicit Hardware Protection.** Scheduler cadence must never be used as a proxy for hardware safety or API protection. Compressor short-cycling and Samsung API DDOS risks are addressed via explicit, state-aware software guardrails (e.g., isolated 15-minute cooldown timers per unit). This is design-only doctrine; it does not weaken any existing Section 3 safety gate.
* **Sleep Priority Interlock — classification pending.** The live `v9_sleep_priority_interlock` is currently classified as an **ambiguous interlock** in [`./5_runtime_layer.md`](./5_runtime_layer.md) Manual Override Contract section. It does not gate on `timer.manual_hvac_override`. Whether it should is a doctrine-clarification question, not a comfort-policy expansion question. See [`./3_regression_appendix.md`](./3_regression_appendix.md) §4.18 (arbitration before telemetry proves the need).
* **Targeted Pre-Chill (Deferred pending forensic justification).** Aggressive 61°F / Turbo Master pre-chill at 17:00 is a new comfort branch. Under the reframed V9 scope it is a candidate for deferral, not a V9 deliverable. Its current deferred status is tracked in the canonical [`./deferred_until_telemetry.md`](./deferred_until_telemetry.md) register. It will only be reconsidered once repeated forensic notes (per [`./comfort_failure_forensics.md`](./comfort_failure_forensics.md)) classify a Master pre-occupancy thermal-mass failure mode that is not addressed by the existing 18:00–06:00 Master sleep deadband. Pre-chill must not be re-proposed as a generic "better comfort" feature; see [`./3_regression_appendix.md`](./3_regression_appendix.md) §4.12.

### Permanent Architectural Guardrails:

* **Physics vs. Latency:** Truth-layer smoothing is intentionally physics-aligned (thermal mass filtering for an 1894 structure) and must not be conflated with control latency. Control responsiveness must be solved at the actuation/scheduler layer, not by reducing truth-layer stability.
* **Safety Invariant Rule:** If safety systems (e.g., Section 3 Runaway Gates) are firing due to predictable scheduler delay rather than true system faults, control latency is violating system invariants. Safety backstops are strictly for hardware failure, not software lag. True safety gates may override manual intent; comfort-policy automations may not — see [`./5_runtime_layer.md`](./5_runtime_layer.md) Manual Override Contract section.
* **Observability Principle:** High-frequency internal state, low-frequency external telemetry. Rapid system evaluations and transition cycle counts are handled via in-memory tracking (RAM scratchpad), while the V5 semantic heritage export remains cleanly gated to 15-minute intervals.
* **Provenance Discipline:** `hvac_provenance_log` and `supervisor_state_log` are HA-write-only and HA-read-never respectively. No V9 deliverable may consume either as a control-loop input ([`./hvac_provenance_logger_design.md`](./hvac_provenance_logger_design.md), [`./operator_annotation_design.md`](./operator_annotation_design.md) §6).
* **Diagnosis-Before-Control:** V10 is diagnosis-supporting algorithm work, not autonomous HVAC control ([`./v9_v10_goals.md`](./v9_v10_goals.md) §4, §5). Autonomous comfort AI is retired pending preconditions per [`./3_regression_appendix.md`](./3_regression_appendix.md) §4.19.

### §12 Current System Snapshot
**Proposals & Blueprints:** Doc 6 / Proposals (V9 scope reframed to simplification + forensic readiness; aggressive comfort proposals such as Targeted Pre-Chill are deferred pending forensic justification). Authoritative V9 / V10 direction lives in [`./v9_v10_goals.md`](./v9_v10_goals.md).
