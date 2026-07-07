You are assisting with Moose House Climate, an experimental Home Assistant HVAC orchestration platform.

IMPORTANT:
This is NOT a normal thermostat setup.
This is an evidence-driven environmental control research system built around telemetry, regression tracking, and iterative experimentation.

---

## Current Operator Decisions (HIGHEST PRIORITY — read first)

Explicit, dated operator decisions override older general doctrine when they are
narrowly scoped. A scoped operator decision is authoritative for its room/time
slice even if a general rule elsewhere (canonical docs, older deadband doctrine)
still describes the prior behavior. When you find such a decision, update the
affected canonical docs to record the exception; do not treat the older general
rule as a reason to ignore or "correct" the decision.

### 2026-06-07 — Lincoln & Lilly bedtime cooling (66–70 room-truth deadband)

- **Scope:** `climate.lincoln_air` and `climate.lilly_air`, **bedtime window
  18:00–07:00**, in **cooling and shoulder** seasons. Daytime (07:00–18:00) and
  heating-season behavior are unchanged.
- **Room-truth deadband:** engage cooling at room truth **≥ 70 °F**, release at
  **≤ 66 °F**, hold off between 66–70 °F. Lincoln and Lilly operate
  **independently**.
- **Actuator during an active pull-down:** **`cool` / `61 °F` / `turbo`** —
  intentional and required. Moderate Samsung setpoints let the head scale back
  prematurely and can run ~18 h without effectively pulling the room down.
- **Season rule:** a `cooling → shoulder` flip must **not** interrupt an active
  pull-down before the room reaches 66 °F; shoulder bulk-off logic must not
  override this contract.
- **This is a room/time-specific exception, NOT a global deadband redesign.** The
  older "all non-Master rooms 68–72 at all hours" rule and the "do not tighten a
  deadband from a complaint" caution remain valid outside this scope. Section 2
  stays the sole comfort-policy writer; no new controller/helpers; manual override
  and Section 3 safety unchanged.
- **Status: approved, pending implementation** (planning/docs only; live YAML
  still runs the legacy 68–72). See `docs/kids-bedroom-overnight-cooling-plan.md`,
  Doc 1 §5.1, and Doc 5 §7.10.

---

You are being given a production automations.yaml file.
DO NOT rewrite the entire file unless explicitly requested.
Preserve all unrelated systems and sections.

Architecture Summary:

* Multi-zone Samsung mini-split system
* Home Assistant OS
* ESPHome + Matter + Bluetooth + Netatmo sensors
* Truth-sensor fusion architecture
* Telemetry-first experimentation workflow
* Google Sheets logging pipeline
* Dynamic seasonal logic
* Safety watchdogs independent from comfort logic
* Manual override protection
* Occupancy-aware airflow experiments
* Regression-aware engineering process

Core Philosophy:

* Evidence over assumptions
* Observability over hidden logic
* Stability over aggressiveness
* Graceful degradation over brittle optimization
* Maintainability over cleverness

Critical Rules:

* Before suggesting any code changes, silently read the Markdown files in the `docs/` folder to understand the Moose House thermal constraints and V9 architecture.
* NEVER remove unrelated automations
* NEVER rename entities unless explicitly instructed
* NEVER collapse sections together
* NEVER simplify away telemetry or safety systems
* Preserve comments and architectural documentation
* Explain WHY changes are being made
* Flag possible regression risks
* Prefer incremental refactors over rewrites

This file contains multiple independent systems:

1. Data telemetry pipeline
2. Main HVAC supervisor
3. Safety watchdogs
4. Ghost automation suppression
5. Auto season switching
6. Airflow destratification
7. Solar shade logic
8. Samsung auto-mode guardrails
9. Sensor health monitoring
10. Experimental legacy/orphaned systems
11. HVAC transition logging

Key Architectural Notes:

* The current architecture uses custom orchestration logic.
* The system intentionally separates:

  * comfort logic
  * safety logic
  * telemetry
  * diagnostics
  * experimental branches
* Safety gates operate independently from comfort logic.
* Google Sheets telemetry collection is mission-critical and must not break.
* The HVAC system is treated as a partially observable thermal system, not a simple thermostat.

Current Engineering Goals:

* Reduce compressor short-cycling
* Improve thermal stability
* Reduce stack-effect overheating
* Improve observability
* Improve transition-based logic
* Reduce command spam
* Build evidence before introducing complexity
* Improve telemetry quality for future experiments

**Before suggesting any code changes, silently read the Markdown files in the `docs/` folder to understand the Moose House thermal constraints and V9 architecture.**

When reviewing or modifying automations:

1. Explain the current behavior
2. Identify strengths and weaknesses
3. Identify hidden assumptions
4. Identify telemetry gaps
5. Identify regression risks
6. Suggest incremental improvements
7. Generate ONLY the changed sections unless asked otherwise

Special Attention Areas:

* Section 2 Main Supervisor
* Section 3 Safety Gates
* Section 6 Shoulder Season Fan Destratification
* Section 11 HVAC Transition Logger

Known Future Goals:

* Transition-based HVAC control instead of tick-based
* Explicit controller-state latches
* Evidence-based capacity arbitration
* Better runtime observability
* More granular telemetry
* Dynamic thermal modeling
* Better occupancy weighting

Attached below is the production automations.yaml file.

Analyze the architecture before making changes.
Do not hallucinate missing entities.
If assumptions are unclear, explicitly state uncertainty instead of inventing behavior.

FILE STARTS BELOW:

(Production automations moved to `automations.yaml`. Keep AGENTS.md doctrine-only.)

---

## AI Context Instruction

**Before suggesting any code changes, silently read the Markdown files in the `docs/` folder to understand the Moose House thermal constraints and V9 architecture.**
