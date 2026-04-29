# Doc 2 / Moose House Climate Reference Map (V3)
Map Date: April 25, 2026
Document Role: Reference Map
Status: Living reference. Update when topology, naming, sensor routing, or document routing materially changes.

## 1. Purpose of This Document
This is the routing and topology document for the Moose House climate system. Its purpose is to prevent multiple docs competing as "the truth", old doctrine being treated as current runtime behavior, raw telemetry being mistaken for instructions, and startup sessions pulling the wrong level of detail.
This map defines the hierarchy of authority and the exact operational topology of the sensor network. It tells future LLM sessions and human operators which document is authoritative for startup context, which documents are supporting evidence, and which sources describe live runtime behavior.
This is not the startup canon (Doc 1), not the full forensic archive (Doc 3), and not the implementation code (Doc 5).

## 2. What This Document Covers
* Document routing across the canon hierarchy
* Live runtime truth sources
* Room-by-room sensor/source precedence
* Naming truth and entity/source conventions
* Operational lookup for per-room trust decisions

## 3. Documentation Hierarchy

### 3.1 Tier 1 — Startup Canon
Document: Doc 1 / Moose House Startup Canon (V2)
Role: Primary startup context. Preserves settled truths, retired approaches, active doctrine, open questions, and guardrails for future sessions.
Use when: Opening a fresh session, briefing a new LLM, establishing current system identity.
Do not use it as: Raw telemetry, forensic audit evidence, full config source.

### 3.2 Tier 2 — Supporting References
(Use these only when deeper detail is needed.)

**A. Operations Sheet**
Document: Doc 4 / Operations Sheet — V8.2 Cooling Validation
Role: Operational scorecard and review framework.
Use when: Reviewing comfort outcomes, deciding whether V8.2 is stable, deciding whether V9 is justified.

**B. Runtime Layer**
Document: Doc 5 / Runtime Layer
Role: Implementation boundary reflecting active YAML logic.
Use when: Verifying literal system behavior, safety triggers, and automated logic.

**C. Regression Appendix**
Document: Doc 3 / Appendix B — Regression Appendix
Role: Condensed record of retired approaches, failed strategies, and regression guardrails.
Use when: Evaluating whether a new proposal is materially similar to something already disproved.

**D. Audit Appendix**
Document: Appendix A — V8.1 Truth Layer Audit
Role: Forensic historical record of the V8.1 truth-layer audit. Explains phantom entities, dead sensors, and methodology.
Use when: A session needs to understand why the truth layer changed or validating historical sensor integrity.

## 4. Runtime Truth Sources

### 4.1 Active Automations
Source: automations.yaml (See Doc 5 / Runtime Layer)
Current Runtime Doctrine: V8.2 — Comfort-First Hotfix with Safety Backstops
Role: Authoritative source of actual live control behavior.
Rule: If doctrine and automations disagree, automations win for runtime truth.

### 4.2 Active Configuration
Source: configuration.yaml (See Doc 5 / Runtime Layer)
Current Truth Layer: V3.1 — Audited Truth / Smoothed / Control
Role: Authoritative source of truth-sensor design, weights, and outlier logic.

### 4.3 Live Helpers / Templates
Sources: Helpers, template sensors, derived entities
Role: Operational support layer between configuration logic and surface behavior.

### 4.4 Raw Telemetry
Source: Google Sheets export (VTherm_Launch_Data_v5)
Role: Raw evidence layer utilizing Semantic Heritage headers ([Room]_[Metric]_[Role]_[Transport]).
Use when: Checking room temperatures over time or validating starvation/churn.

## 5. Naming and Source Truth
* Home Assistant entity IDs remain authoritative for runtime identity.
* Exported telemetry uses Semantic Heritage headers for analysis ([Room]_[Metric]_[Role]_[Transport]).
* Naming cleanup should not overwrite runtime identity without deliberate migration.
* If multiple names exist for the same operational source:
  * Identify the runtime name.
  * Identify any export/analysis alias.
  * Identify whether older names are historical only.

## 6. Room-by-Room Operational Topology
Each room's truth layer is composed from a ranked stack. Entries in any given tier may be weighted down or excluded in the live V3.1 configuration; this list is the topology, not the weight sheet.

### 6.1 Living Room
* Primary source: BT hub
* Secondary source: ST hub mirror
* Low-weight only: Samsung internal
* Excluded / notes: MSR CO2 separate, MSR DPS excluded pending hardware rehab.

### 6.2 Master Bedroom
* Primary source: sensor.master_bedroom_temp_temperature_2 (7C3F I/O Meter, w=1.0)
* Secondary source: sensor.master_bedroom_temperature_temperature_2 (WonderLabs, w=0.9)
* Low-weight only: sensor.master_bedroom_air_temperature (Samsung internal, w=0.20)
* Excluded / notes: The legacy SmartThings (ST) entity without a suffix was successfully retired in the V3.1 audit.

### 6.3 Lincoln's Room
* Primary source: BT
* Secondary source: ST
* Fallback source: Matter
* Low-weight only: Samsung internal
* Excluded / notes: MSR DPS explicitly excluded.

### 6.4 Lilly's Room
* Primary source: BT
* Secondary source: ST
* Fallback source: Matter
* Low-weight only: Samsung internal

### 6.5 Laundry
* Primary source: sensor.laundry_temperature (SwitchBot WoTHP, w=1.0)
* Secondary source: sensor.bathroom_downstairs_temperature (WonderLabs, w=0.8)
* Excluded / notes: The Primary BT source is currently transport-degraded; the WonderLabs sensor is carrying the truth calculation. SwitchBot Outdoor Meter 7C fallbacks were removed.

### 6.6 Deck
* Primary source: sensor.deck_temp_temperature (SwitchBot 4481) and sensor.deck_temp_temperature_2 (WonderLabs). Both are weighted equally in configuration.yaml with an OR fallback.
* Excluded / notes: The "BT primary, ST secondary" framing is doctrinal aspiration, not config reality. Both are actively carrying truth. sensor.deck_temp_temperature_3 (Outdoor Meter 81) was removed from truth but is still exported into the Deck_Temp_RoomProbe_Matter telemetry column.

### 6.7 Office
* Primary source: sensor.indoor_temperature (Netatmo anchor, w=1.0)
* Secondary source: sensor.office_temp_temperature (Signify/Hue, w=0.95)
* Tertiary source: sensor.office_temperature_2 (Signify/Hue, w=0.95)
* Excluded / notes: There is no BT or Matter in the actual truth calculation. SwitchBot Outdoor Meter 79 fallbacks were removed in STEP 2.

## 7. Topology Interpretation Rules
* This document records source precedence and operational role, not the full numeric weighting sheet (check configuration.yaml via Doc 5 for math).
* If a source is listed as degraded, that means transport or reliability concerns exist even if truth remains operationally healthy.
* A source being present in Home Assistant does not automatically make it valid for truth calculations.
* Phantom entities, stale entities, and non-reporting hardware must be treated as excluded unless explicitly restored.
* When in doubt, check live YAML for final implementation truth.

## 8. Authority Rules
* Rule 1: Startup sessions begin with Doc 1 / Startup Canon.
* Rule 2: Runtime behavior comes from live YAML (Doc 5).
* Rule 3: Audit answers "why the truth layer changed" (Appendix A).
* Rule 4: Tracking answers "is it working" (Doc 4 / Operations Sheet).
* Rule 5: Raw telemetry (V5) is evidence, not instruction.
* Rule 6: Room topology (§6) answers "which sensor to trust".

## 9. What Each Source Is Not
* Doc 1 (Canon) is not: A forensic audit, a YAML file, or a telemetry table.
* Doc 3 (Regression) is not: The startup prompt or active runtime specification.
* Doc 4 (Operations) is not: Strategic doctrine or the raw telemetry export.
* Doc 5 (Runtime) is not: The narrative explanation.
* Telemetry is not: Doctrine or instruction.
* Room topology (§6) is not: The numeric weight sheet.
* Inventory artifacts are not: Automatically current truth.

## 10. Historical Archive Boundary
* Older doctrine, proposal, and comprehensive docs may be preserved for regression prevention and forensic context.
* Historical retention does not confer present authority.
* If a historical doc conflicts with Doc 1, Doc 2, or Doc 5, the historical doc loses for current-state interpretation.

## 11. Suggested Workflow for New Sessions

### 11.1 For a Brand New Session
1. Start with Doc 1 / Moose House Startup Canon (V2).
2. Use this Doc 2 / Reference Map (V2) to determine whether deeper source material is needed.
3. Pull supporting sources as required (e.g., §6 for topology, Doc 4 for evaluation, Doc 5 for code architecture).

### 11.2 For Debugging a Claim
1. Use Doc 5 / Runtime Layer (automations/config) to determine 'what should happen'.
2. Use Telemetry (V5) for "what actually happened".
3. Use Room Topology (§6) for "which sensor was responsible".

### 11.3 Evaluating a New Proposal
1. Check Doc 1 / Startup Canon for current doctrine.
2. Check Doc 3 / Regression Appendix for retired approaches.
3. Check Doc 2 / Reference Map for source/topology reality.
4. Check Doc 4 / Operations Sheet and telemetry for evidence.

## 12. Current System Snapshot
*(As of April 16, 2026)*
* Startup Canon: Doc 1 / Moose House Startup Canon (V2)
* Reference Map: Doc 2 / Moose House Climate Reference Map
* Regression Appendix: Doc 3 / Appendix B — Regression Appendix
* Operations Sheet: Doc 4 / Operations Sheet — V8.2 Cooling Validation
* Runtime Layer: Doc 5 / Runtime Layer
* Active Runtime Control: V8.3 automations
* Active Truth Layer: V3.1 audited configuration
* Room-by-Room Source Topology: §6 of this document
* Evidence Layer: VTherm_Launch_Data_v5 (Semantic Heritage)
* Historical Audit Record: Appendix A — V8.1 Truth Layer Audit

## 13. Final Routing Principle
If a future session is confused, use this order:
1. Doc 1 (Canon) — What should be assumed at startup
2. Doc 2 (Reference Map) — Which source should answer this question
3. Room Topology (§6) — Which sensor layer to trust in a given room
4. Doc 5 (Runtime Layer) — What the system is actually configured to do
5. Appendix A (Audit Appendix) — Why the truth layer changed
6. Doc 4 (Operations Sheet) — Whether current doctrine is working
7. Telemetry — What really happened in practice

*(This map exists so Moose House climate work stays cumulative rather than repetitive.)*
