You are assisting with Moose House Climate, an experimental Home Assistant HVAC orchestration platform.

IMPORTANT:
This is NOT a normal thermostat setup.
This is an evidence-driven environmental control research system built around telemetry, regression tracking, and iterative experimentation.

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

* Before suggesting any code changes, silently read the Markdown files in the docs/ folder to understand the Moose House thermal constraints and V9 architecture.
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

* VTherm has been deprecated.
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
