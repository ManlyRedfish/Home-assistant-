Doc 1 / Moose House Startup Canon (V2)
Canon Date: April 25, 2026
Document Role: Startup Canon
Status: Living canon. Update only when settled truths, active doctrine, or the sensor foundation materially change.
1. Purpose of This Document
This is the authoritative startup context for new LLM sessions and new human review sessions.
Its purpose is to preserve the current system identity, active doctrine, major guardrails, and known realities without forcing a full reread of historical archives.
This document is for startup context only. It is not the full topology map (Doc 2), not the regression archive (Doc 3), not the performance tracker (Doc 4), and not the runtime codebase (Doc 5).
2. What Moose House Is
Moose House is an older thermally coupled home, not a clean modern multi-zone build. It must be reasoned about as a structurally linked thermal volume rather than as fully isolated rooms.
The system must respect:
Vertical heat drift
Thermal mass
Cross-room coupling
Lag between control action and observed comfort result
Prime Directive: Software cannot out-calculate structure and gravity.
3. Current Active System Snapshot
3.1 Active Control Layer
Current active runtime control layer: V8.3 automations
Current control posture: Comfort-first deadband + passive stack-effect mitigation
State: V8.2 is an honest hotfix that replaced the old waterfall target ladder with a simpler cooling deadband model and reintroduced explicit safety protections. It is now considered durable doctrine.
3.2 Active Truth Layer
Current active truth layer: V3.1 configuration
High-level truth-layer philosophy: Audited, trimmed, smoothed truth architecture utilizing 2-hour staleness rejection, outlier handling, and explicit removal of hardware like the MSR-2 DPS310 sensors (see Doc 5 / Runtime Layer).
Note: Live YAML defines actual runtime truth.
3.3 Active Telemetry Layer
Current telemetry/export layer: VTherm_Launch_Data_v5
Telemetry naming philosophy: Semantic Heritage naming (room + metric + role + transport) used to objectively validate outcomes like comfort drift and starvation over time (see Doc 4 / Operations Sheet).
Make clear that telemetry is evidence, not doctrine.
4. Startup Non-Negotiables
(The following truths must be inherited by every new session before proposing anything.)
House-level thermal coupling is real.
Room-isolation assumptions are dangerous.
Runtime YAML (Doc 5) outranks prose when they conflict.
Degraded hardware does not automatically mean truth-layer failure if fallback logic is healthy.
Comfort logic and safety logic are separate on purpose.
The current system should be judged by measured evidence, not theoretical elegance.
5. Current Operating Doctrine
5.1 Comfort Contract (Deadbands)
Deadbands are the comfort contract. A deadband is the temperature range a room is allowed to float while not actively heating or cooling. Comfort logic is supervisory and deadband-focused, treating the house as a coupled volume (see Doc 5 / Runtime Layer for code specifics).
Comfort complaints are forensic inputs, not automatic architecture triggers. A complaint such as "my room was too hot/cold last night" reconstructs into a contract-failure investigation per Doc / Comfort Failure Forensics, not into a redesign of the deadband. Repeated, telemetry-backed failures of the same mode are evidence for a targeted change; a single anecdote is not. See Doc 3 / Regression Appendix §4.12.
Deadband philosophy: Comfort-first target ranges (e.g., setpoint 68, off ≤68, on >72).
Room targeting philosophy: Rooms act as engines or spillways, not mathematically isolated zones.
Bedroom sleep logic: Aggressive cool-down targeting a 62–66°F Master sleep window.
Lincoln/Lilly bedtime cooling exception (operator decision 2026-06-07, approved pending implementation): During the bedtime window 18:00–07:00, in cooling and shoulder seasons, Lincoln and Lilly use a tighter room-truth deadband — engage cooling at ≥70°F, release at ≤66°F, hold off between 66–70°F — with the actuator commanded cool/61°F/turbo during an active pull-down. 61/turbo is intentional and required: moderate Samsung setpoints scale back prematurely and can run ~18h without pulling the room down. Lincoln and Lilly are independent; a cooling→shoulder flip must not interrupt an active pull-down before 66°F, and shoulder bulk-off must not override it. This is a narrow room/time exception that supersedes the general "non-Master rooms 68–72 at all hours" rule for this scope only; Master's separate sleep band and the general daytime doctrine are unchanged. Status: approved, pending implementation (live still runs 68–72). See AGENTS.md "Current Operator Decisions", Doc 5 §7.10, and docs/kids-bedroom-overnight-cooling-plan.md.
Always-on comfort assumptions: Away modes relax targets (74–76°F) rather than fully abandoning control.
V8.3 Heating Doctrine: Heating and shoulder daytime paths use a top-anchored deadband (target 68°F, off ≥68, on <64) to prevent compressor short-cycling. To passively mitigate stack-effect heating upstairs, the Living Room target drops to 64°F (deadband 62-64°F) during the bedtime window (18:00–22:00) when the house is occupied.
Manual override contract: `timer.manual_hvac_override` is the household's immediate comfort intent. Comfort-policy automations gate on `idle`; only true safety gates (60°F LR runaway, 58°F Master floor) may override manual intent. See Doc 5 / Runtime Layer Manual Override Contract section and Doc 3 / Regression Appendix §4.15–§4.16.
Comfort bands, not thermostat targets: Moose House controls with comfort bands / deadbands, not a single fixed "comfortable" temperature. The system holds (does nothing) while room truth is inside the active band and acts only when truth leaves the band. Comfort bands are preferences; they are not the same thing as a thermostat setpoint.
Samsung setpoints are actuator commands: The Samsung / mini-split setpoint is an actuator demand, not comfort truth. The comfort target is the band, not the Samsung setpoint, and Samsung's preferred 72–75°F range is not treated as comfort truth for this house.
Comfort bands are preferences; safety gates are physical protection: Comfort bands are tunable household preference. Section 3 safety gates (60°F LR runaway, 58°F Master floor) are absolute physical/equipment protection and remain separate. A comfort band must never be defined as, or weakened into, a safety gate, and a comfort threshold must never alias a safety floor.
Planned comfort profiles (doctrine, not yet runtime): Future comfort control is organized into named profiles, starting with a single global selector (per-room profiles deferred). The planned profiles are `eric_cold` (meat-locker, coldest), `family_normal`, `sleep_cold`, `away_relaxed` (house protection / energy, not comfort optimization), and `safety_only` (comfort bands disabled; only emergency cutoffs and structural protection remain). Draft band numbers are non-binding; a band-number change is a separate evidence-gated conversation per Doc / V9 / V10 Goals §10. See Doc / Comfort Band & Truth-Confidence Plan (`comfort_band_and_truth_confidence_plan.md`) for the full model.
5.2 Safety Doctrine
Safety logic operates independently of comfort optimization.
Floor/ceiling protections: 58°F Master emergency cooling floor.
Runaway protections: 60°F Living Room runaway cutoff.
Separation from comfort arbitration: Safety logic will intervene and forcefully stop HVAC loops regardless of what the comfort logic is requesting.
Explicitly note that safety logic is not the same thing as comfort optimization.
5.3 Deferred Architecture
The following concepts have been intentionally deferred and are not to be reintroduced casually without evidence:
Explicit multi-head capacity arbitration.
Cleaning up command-on-every-tick loops into explicit state transitions.
Complex predictive suppression.
6. Current Known Issues & Hardware Debt
(Preserve known realities that a new session must not “discover” again.)
Degraded BT probes: Bluetooth (BT) is primary in doctrine but currently transport-degraded in spaces like Deck. ST + Matter fallbacks are actively carrying the truth calculations (see Doc 2 / Reference Map).
MSR DPS hardware pending validation / rehab: MSR-2 DPS310 sensors are explicitly removed from truth calculations due to historical hardware failure (see Doc 5 / Runtime Layer).
Transport reliability vs truth-layer logic distinction: Transport degradation (e.g., BT drops) does not mean total truth failure if fallback logic remains healthy. Avoid over-architecting around transient network drops.
Deadband memory shortcut limitations: The current supervisor uses HVAC mode as deadband memory. This degrades gracefully when device and controller intent diverge between 15-minute ticks, but remains a known imperfection.
Remaining sensor debt that affects confidence: Legacy bare ST entities are targeted for retirement, and internal Samsung thermistors are permanently assigned low weight due to hardware bias.
Planned graded truth confidence (doctrine, not yet runtime): The truth layer is planned to expose a graded status — `healthy` (2+ valid primary sources agree), `degraded` (one primary, or primary + fallback), `fallback` (only Samsung/mini-split internal or held-last-good), `failed` (no usable source) — replacing today's binary available/unavailable cliff and hidden 70°F supervisor fallback. Three invariants are doctrine now even though the runtime is deferred: (1) Samsung/mini-split-only truth must never be `healthy`; (2) an unavailable ESP/Apollo source must not equal total truth failure when Matter/Bluetooth/SmartThings remain available; (3) a stable temperature sensor must not be treated as stale merely because its value did not change (freshness should follow report time, not value change). See Doc 5 / Runtime Layer §7.9 and Doc / Comfort Band & Truth-Confidence Plan.
7. Retired Approaches / Do Not Re-Propose
(This is a startup warning layer. See Doc 3 / Regression Appendix for the full breakdown.)
Room-Isolation-First Control (Software cannot ignore shared airflow)
Blind Trust in Unaudited Truth Layers (Sensors must be validated and trimmed)
Presence as Master Governor (The house has too much thermal inertia)
Preemptive Living Room Suppression Without Evidence (Do not solve theoretical starvation)
Over-Architected Arbitration Before Measured Need (Complexity requires evidence)
Offset Stacking Without Hard Boundary Discipline (Leads to limit strikes and hardware oscillation)
Naive Multi-Sensor Fusion Without Aggressive Rejection Logic (Averaging bad sensors ruins control)
Treating Transport Degradation as Total Truth-Layer Failure (Fallbacks exist for a reason)
Treating Historical Doctrine as Live Runtime Truth (YAML is truth)
YAML for Every Discomfort Anecdote (Complaints are forensic inputs, not control specifications — §4.12)
Permanent Comfort Surveys as a Control Mechanism (Surveys are forensic annotation, not a control loop — §4.13)
Treating Human Discomfort as Immediate Automation Input (The WAF watcher is the single legitimate immediate ingest — §4.14)
Letting Comfort-Policy Automation Override Manual Intent (Manual override wins for the override window — §4.15)
Treating Outdoor / Season Logic as Stronger Than Manual Override (Season is one input, not a meta-authority — §4.16)
Accepting Supervisor / Boost Collisions as Normal (Resolve or quantify; do not normalize — §4.17)
Adding Arbitration Before Telemetry Proves the Need (Instrument first; arbitrate second — §4.18)
Algorithmic Control Before Algorithmic Diagnosis (V10 is diagnosis, not control — §4.19)
Closing Rule: Materially similar approaches are considered retired unless new evidence justifies reopening them.
8. Live vs Historical Source Boundary
(What counts as current truth)
8.1 Live / Authoritative for Current Reality
Doc 1 / Moose House Startup Canon (This Document)
Doc 2 / Moose House Climate Reference Map
Doc 5 / Runtime Layer (Active YAML and Control Definitions)
Doc 4 / Operations Sheet (V8.2 Cooling Validation)
VTherm_Launch_Data_v5 (Live Telemetry Evidence)
8.2 Historical / Context Only
Doc 3 / Appendix B — Regression Appendix (For understanding why ideas failed)
Appendix A — V8.1 Truth Layer Audit (For understanding legacy sensor cleanup)
Older telemetry schemas and superseded narrative docs
8.3 Conflict Rule
If historical docs conflict with active canon or live YAML, historical docs lose for current runtime truth.
If prose conflicts with live YAML, YAML wins for runtime behavior.
If telemetry conflicts with expectation, investigate rather than assuming doctrine is correct.
9. Document Routing / What This Canon Does Not Cover
For room-by-room topology and source precedence, use Doc 2 / Reference Map.
For a record of failed approaches to avoid, use Doc 3 / Regression Appendix.
For performance judgment and stability validation, use Doc 4 / Operations Sheet.
For actual implementation behavior, use Doc 5 / Runtime Layer.
For the forensic workflow that investigates comfort complaints against the deadband contract, use Doc / Comfort Failure Forensics (`comfort_failure_forensics.md`).
For updated V9 / V10 direction (simplification, collision reduction, manual-override discipline, transition/latch clarity, provenance completeness; V10 diagnosis-only), use Doc / V9 / V10 Goals (`v9_v10_goals.md`).
10. Startup Handoff Rule
In a new session, begin with this document.
Treat it as the authoritative memory layer for current system identity and doctrine.
Use Doc 2 (Reference Map) for routing and topology, not this document.
Do not reopen retired approaches (Doc 3) unless new evidence is explicitly identified.
Update this canon only when a truth has actually changed, not when wording can be made prettier.
11. Executive Snapshot
Moose House is a highly coupled 1894 farmhouse operating on V8.3 (a comfort-first hotfix with passive stack-effect mitigation) and V3.1 (an audited truth layer). Software cannot out-calculate gravity and structure, so control is supervisory and deadband-focused (68-72°F normally). The system utilizes multi-sensor per-room truth (favoring BT/ST/Matter) but specifically avoids over-architected isolation logic or premature arbitration. Telemetry acts as evidence, YAML acts as runtime truth, and all new sessions must respect these boundaries before proposing changes.
Meta Notes for Document Maintenance
What to keep out of Doc 1:
Do not let this doc absorb full room-by-room sensor tables, weighted truth-layer math, full operational KPI tables, long audit narratives, raw telemetry excerpts, or exhaustive history from V5/V6/V7/V8 docs. That belongs in Docs 2-5.