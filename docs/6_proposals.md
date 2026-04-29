# Doc 6 / Proposals

**Date:** April 19, 2026
**Document Role:** Architecture Proposals & Blueprints
**Status:** Active pipeline for approved architectural shifts awaiting deployment windows.

## 3.2 Proposed Architecture: V9 (Event-Driven / Decoupled)

**Status:** Approved for development (Pending May 5th V8.2 Gate)
**State:** V9 transitions the system from a monolithic 15-minute scheduler to an event-driven, decoupled control loop. It is justified not because V8.2 is failing, but because V8.2 enforces safety and stability through architectural coupling that can now be safely separated.

### Core Architecture Shifts (The V9 Doctrine):

* **Decoupled Control Loops:** The observation, decision, actuation, and protection layers are no longer multiplexed to a single clock tick. Actuation is triggered instantly by state-changes in the smoothed Truth Layer rather than a blind global scheduler.
* **Explicit Hardware Protection:** Scheduler cadence must never be used as a proxy for hardware safety or API protection. Compressor short-cycling and Samsung API DDOS risks are now enforced via explicit, state-aware software guardrails (e.g., isolated 15-minute cooldown timers per unit).
* **Sleep Priority Interlock:** Solves cross-mode contention lockout during shoulder seasons. If the Master Bedroom requires cooling while the Living Room is actively heating, V9 explicitly forces the Living Room to off (provided LR truth remains safely above the 60°F structural floor) to ensure proper mode arbitration at the outdoor compressor.
* **Targeted Pre-Chill:** Replaces step-function temperature drops. Master Bedroom cooling engages aggressively (Target 61°F / Turbo) prior to occupancy at 17:00 to neutralize thermal mass, before transitioning to an asymmetric, cost-saving sleep deadband (62–64.5°F) at 18:00.

### Permanent Architectural Guardrails:

* **Physics vs. Latency:** Truth-layer smoothing is intentionally physics-aligned (thermal mass filtering for an 1894 structure) and must not be conflated with control latency. Control responsiveness must be solved at the actuation/scheduler layer, not by reducing truth-layer stability.
* **Safety Invariant Rule:** If safety systems (e.g., Section 3 Runaway Gates) are firing due to predictable scheduler delay rather than true system faults, control latency is violating system invariants. Safety backstops are strictly for hardware failure, not software lag.
* **Observability Principle:** High-frequency internal state, low-frequency external telemetry. Rapid system evaluations and transition cycle counts are handled via in-memory tracking (RAM scratchpad), while the V5 semantic heritage export remains cleanly gated to 15-minute intervals.

### §12 Current System Snapshot
**Proposals & Blueprints:** Doc 6 / Proposals (Holds the V9 Event-Driven architecture)
