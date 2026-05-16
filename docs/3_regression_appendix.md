# Doc 3 / Appendix B — Regression Appendix / Retired Approaches

**Appendix Date:** April 25, 2026
**Document Role:** Regression Appendix
**Status:** Living anti-regression reference. Update when an approach is conclusively retired, materially reframed, or legitimately reopened by new evidence.

## 1. Purpose of This Appendix

This appendix exists to preserve failed approaches, disproved assumptions, and superseded control logic so future sessions do not waste time re-proposing them. It is the compressed anti-regression layer of the Moose House climate documentation system.

The older doctrine and research archive remains valuable and should be preserved, but it is too large and too mixed to serve as an efficient startup memory layer. This appendix extracts the parts of that archive that matter most for avoiding repeat mistakes.

This document does not replace the historical archive. It distills it.

## 2. How to Use This Appendix

Before proposing a new control strategy, truth-layer redesign, sensor-trust change, or house-level climate architecture, check whether a materially similar idea appears here.

If an approach is listed in this appendix, treat it as retired unless new evidence justifies reopening it.

A renamed old idea is still an old idea. A cosmetically simplified failure mode is still a failure mode.

Any proposal that materially resembles a retired approach must satisfy the reopen conditions listed in this appendix before it is treated as viable again.

## 3. Governing Principle

Moose House is an 1894 balloon-frame farmhouse, not a clean modern zone-control environment. The core lesson repeated across the doctrine lineage is that the house behaves as a coupled thermal volume with strong vertical drift, heavy thermal mass, shared airflow pathways, and biased internal sensing.

The archive explicitly warns that attempting to isolate rooms mathematically while ignoring structure, gravity, and shared airflow paths fails in this house type. Control must remain supervisory and house-aware, not naively room-isolated.

## 4. Retired Approaches

### 4.1 Room-Isolation-First Control
* **Retired Approach:** Treating each room as an effectively independent thermal zone that can be optimized in isolation through software logic.
* **Why It Looked Promising:** Mini-split heads are physically distributed by room, so room-level control appears intuitive. It promises fine-grained comfort and neat zone-specific logic.
* **Why It Failed in Moose House:** Moose House is structurally coupled. Vertical heat drift, shared airflow, stairwell spillways, and cross-room coupling mean one room’s behavior materially affects another. The doctrine lineage states that attempts to isolate rooms mathematically fail when software ignores structure, gravity, thermal mass, and shared airflow paths.
* **Observed or Structural Failure Mode:** Adjacent zones fight each other, lower floors become terminal pools rather than isolated endpoints, and control logic overestimates its ability to localize outcomes. This leads to inefficient or misleading optimization efforts.
* **What Replaced It:** Supervisory, house-aware control that treats the building as a coupled thermal volume and reasons in terms of engines, spillways, pools, and structural pathways rather than pretending each room is fully independent.
* **Reopen Only If:** A materially different building envelope, airflow regime, or control architecture is introduced that changes the actual coupling behavior of the house.
* **Source Lineage:** Spatial + Master Doctrine (V8/V8.1); Doc 1 / Startup Canon.

### 4.2 Blind Trust in Unaudited Truth Layers
* **Retired Approach:** Treating any assembled room-truth layer as inherently valid simply because sensors exist and data is flowing.
* **Why It Looked Promising:** Multi-sensor fusion feels more robust than relying on a single biased internal thermistor. Averaging several inputs sounds safer than trusting one.
* **Why It Failed in Moose House:** The truth layer was found to contain phantom entities, dead hardware, and non-reporting sensors. Doc 1 explicitly notes that the V3.1 audit proved unaudited truth layers can corrupt downstream math. Presence of an entity in Home Assistant did not mean it was a valid live source.
* **Observed or Structural Failure Mode:** Downstream control logic consumed invalid or misleading values, leading to bad control decisions, false confidence, and avoidable churn.
* **What Replaced It:** Audited truth layers with explicit staleness rejection, surgical exclusion of dead or phantom sources, and clearer source precedence.
* **Reopen Only If:** A new truth-layer proposal includes explicit validation, auditability, exclusion logic, and a defensible basis for each included source.
* **Source Lineage:** Doc 1 / Startup Canon; Appendix A — V8.1 Truth Layer Audit; adversarial research around sensor disagreement and noisy fusion.

### 4.3 Presence as Master Governor
* **Retired Approach:** Using presence detection as the main strategic governor of climate control.
* **Why It Looked Promising:** Presence-based control appears energy-efficient because conditioning follows actual human occupancy rather than fixed schedules.
* **Why It Failed in Moose House:** The house has high thermal inertia, and primary living/sleeping spaces are not transient spaces. The research lineage explicitly notes that presence-first control works best in short-duration spaces like hallways or bathrooms, but fails in high-inertia rooms where it takes substantial time to reach comfort. The archive also documents mmWave false negatives under blankets and delayed comfort recovery.
* **Observed or Structural Failure Mode:** Cold shock, delayed comfort, false unoccupied states during sleep, and unstable control behavior driven by overly reactive occupancy logic.
* **What Replaced It:** Presence as a modifier or override, not as the governing strategic backbone. Comfort logic remains supervisory and evidence-based.
* **Reopen Only If:** Presence logic is bounded by stronger physical or temporal logic and is no longer being asked to serve as the primary strategic control layer.
* **Source Lineage:** Doc 1 / Startup Canon; Home Assistant HVAC Adversarial Research.

### 4.4 Preemptive Living Room Suppression Without Evidence
* **Retired Approach:** Suppressing the living room preemptively in order to “protect upstairs” without measured proof that upstairs is actually starving under load.
* **Why It Looked Promising:** In a vertically coupled house, it is tempting to assume lower-floor conditioning competes with or undermines upper-floor performance.
* **Why It Failed in Moose House:** Doc 1 explicitly rejects this behavior absent hard telemetry evidence. Preemptive suppression substitutes theory for measured reality and risks sacrificing comfort in the main conditioned pool without proof of actual upstream benefit.
* **Observed or Structural Failure Mode:** Comfort is degraded based on speculation rather than evidence, and the system begins optimizing for imagined conflicts rather than measured ones.
* **What Replaced It:** Evidence-first arbitration. Living room suppression is not justified unless telemetry proves real starvation or harmful interaction under load.
* **Reopen Only If:** Doc 4 (Operations Sheet) or VTherm_Launch_Data_v5 telemetry demonstrates actual repeated starvation behavior under comparable operating conditions.
* **Source Lineage:** Doc 1 / Startup Canon.

### 4.5 Over-Architected Arbitration Before Measured Need
* **Retired Approach:** Introducing explicit multi-head capacity arbitration or more complex supervisory suppression before telemetry shows that such complexity is actually needed.
* **Why It Looked Promising:** More architecture can feel more “complete,” especially in a multi-head mini-split environment with shared compressor constraints.
* **Why It Failed in Moose House:** Complexity was being proposed ahead of evidence. Doc 1 explicitly states that multi-head capacity arbitration is deferred until there is measured evidence of real starvation under load. In Moose House, premature control sophistication increases fragility and cognitive overhead without guaranteeing a better result.
* **Observed or Structural Failure Mode:** Complexity grows faster than evidence, increasing the risk of control collisions, hidden assumptions, and time wasted solving theoretical rather than actual failures.
* **What Replaced It:** Defer complex arbitration until telemetry proves the simpler architecture is insufficient.
* **Reopen Only If:** Evidence from live telemetry and operations review shows repeatable starvation, conflict, or capacity contention that simpler doctrine cannot resolve.
* **Source Lineage:** Doc 1 / Startup Canon; doctrine simplification trajectory.

### 4.6 Offset Stacking Without Hard Boundary Discipline
* **Retired Approach:** Allowing multiple compensation layers to stack setpoint offsets without a strict boundary model tied to hardware limits.
* **Why It Looked Promising:** Offset logic offers an elegant way to compensate for baseline sensor bias, internal thermistor mismatch, and environmental conditions without rewriting the entire control model.
* **Why It Failed in Moose House:** The adversarial research records a concrete failure case where VTherm offset stacking, internal compensation, and regulation logic drove requests into the hardware ceiling, causing oscillation and command rejection. The problem was not merely abstract complexity; it produced brittle runtime behavior.
* **Observed or Structural Failure Mode:** Hardware limit strikes, flap loops, unstable control requests, and decoupling between virtual demand and physical system capability.
* **What Replaced It:** Simpler bounded control logic, explicit safety backstops, and a doctrine that treats elegant additive math with suspicion when it can exceed hardware reality.
* **Reopen Only If:** A proposed offset architecture includes hard caps, transparent traceability, and proof that independent correction layers cannot silently stack into hardware limit behavior.
* **Source Lineage:** Home Assistant HVAC Adversarial Research; control-audit lineage; Doc 5 / Runtime Layer.

### 4.7 Naive Multi-Sensor Fusion Without Aggressive Rejection Logic
* **Retired Approach:** Assuming that more sensors automatically produce a better room truth, especially when simple averaging is used.
* **Why It Looked Promising:** Higher sensor count suggests more data, more redundancy, and better confidence.
* **Why It Failed in Moose House:** The adversarial research explicitly warns that naïve averaging becomes unstable under sensor attrition, drafts, direct solar bias, or noisy hardware. In this house, high sensor count without robust filtering increases volatility instead of reducing it.
* **Observed or Structural Failure Mode:** A single bad input can skew the room truth, inject artificial noise into the control loop, and provoke extreme HVAC reactions.
* **What Replaced It:** Audited source selection, outlier-aware truth logic, staleness rejection, and willingness to prefer fewer high-confidence sources over many unstable ones.
* **Reopen Only If:** A fusion design demonstrates rigorous outlier rejection, attrition tolerance, and stable behavior under degraded source conditions.
* **Source Lineage:** Home Assistant HVAC Adversarial Research; later truth-layer doctrine (Doc 5).

### 4.8 Treating Transport Degradation as Total Truth-Layer Failure
* **Retired Approach:** Assuming that degraded transport on a primary sensor automatically invalidates the room’s truth logic as a whole.
* **Why It Looked Promising:** If the preferred source is unreliable, it is tempting to declare the room’s truth compromised.
* **Why It Failed in Moose House:** Doc 1 and Doc 2 explicitly distinguish between degraded transport and failed truth logic. In rooms like Deck and Laundry, Bluetooth reliability problems do not automatically mean the truth layer has failed when SmartThings or Matter fallbacks continue carrying truth.
* **Observed or Structural Failure Mode:** Overreaction to partial degradation, unnecessary redesign pressure, and confusion between sensor health, transport path health, and truth-layer viability.
* **What Replaced It:** More explicit reasoning about primary, secondary, and fallback transport/source roles.
* **Reopen Only If:** Fallback sources are also shown to be degraded, stale, or structurally invalid.
* **Source Lineage:** Doc 1 / Startup Canon; Doc 2 / Reference Map lineage.

### 4.9 Treating Historical Doctrine as Live Runtime Truth
* **Retired Approach:** Using older doctrine, proposals, or comprehensive documents as though they described the currently running system.
* **Why It Looked Promising:** Older doctrine often contains rich explanation, broader context, and more complete prose than the newer trimmed canon.
* **Why It Failed in Moose House:** Historical docs preserve valuable reasoning and mistakes, but they also preserve superseded assumptions, transitional architectures, and inactive logic. Treating them as current truth collapses the distinction between archive and runtime.
* **Observed or Structural Failure Mode:** Sessions revive retired theories, misread old architectures as active ones, or mistake historical explanations for current implementation.
* **What Replaced It:** Explicit live-vs-historical boundaries in Doc 1 and Doc 2, with live YAML (Doc 5) governing present reality.
* **Reopen Only If:** A historical concept is intentionally re-adopted and formally reintroduced into the active canon or runtime layer.
* **Source Lineage:** Doc 1 / Startup Canon; Doc 2 / Reference Map; archive sprawl itself.

### 4.10 V8 Waterfall Doctrine (LR OFF / Upstairs ON)
* **Retired Approach:** Preemptively shutting off the 1st-floor Living Room to force upstairs units to handle the whole-house load, pulling heat up the stairs to save capacity.
* **Why It Looked Promising:** In a vertically coupled house with warm air rising, it was plausible that upstairs heads could condition the full thermal volume if downstairs was silenced. Doctrine was built around this hypothesis across the V8 phase calendar.
* **Why It Failed in Moose House:** Failed the real-world family comfort test in exactly one day (April 15, 2026), forcing the V8.2 68/72 around-the-clock deadband hotfix the same day. The house's thermal coupling does not cleanly propagate upstairs conditioning downstairs to the degree the waterfall model assumed.
* **Observed or Structural Failure Mode:** Living Room hung warm enough for immediate comfort complaints. The "protect upstairs by silencing downstairs" model sacrificed the main conditioned pool without producing measurable upstream benefit.
* **What Replaced It:** V8.2 comfort-first deadband. LR runs 68/72 around the clock on the same doctrine as the bedrooms; no preemptive suppression of any room.
* **Reopen Only If:** The physical structure of the 1894 farmhouse is fundamentally altered to isolate the first and second floors (e.g., sealed stairwell, independent zone ducting). Materially the same as §4.4's reopen condition — telemetry alone cannot justify it.
* **Source Lineage:** V8 Phase calendar (Apr 7–May 5 plan); V8.1 → V8.2 transition; Doc 1 / Startup Canon §7.

### 4.11 V8.3 LR Bedtime Setpoint Reduction is NOT a §4.10 Waterfall Regression
* **V8.3 LR Bedtime Setpoint Reduction is NOT a §4.10 Waterfall Regression:** While V8.3 lowers the Living Room target at night to favor upstairs comfort, it is fundamentally different from the retired V8 waterfall. It operates in heating/shoulder season (not cooling), uses passive heat-source reduction (dropping the target to 64°F rather than preemptive shutoff or lockout), and avoids compressor contention/mode-flips entirely.

### 4.12 YAML for Every Discomfort Anecdote
* **Retired Approach:** Treating every comfort complaint as an immediate request to add a new YAML automation, branch, or condition.
* **Why It Looked Promising:** Adding YAML feels like decisive progress. Each anecdote presents a concrete moment of discomfort that begs for a concrete fix, and shipping a fix feels like ownership.
* **Why It Is Not Helping:** A single anecdote is one data point of an unknown distribution. Each anecdote-driven automation adds a new collision surface against Section 2 supervisor and Section 14 boost, accelerating the overwrite class of failures already documented in [`5_runtime_layer.md`](5_runtime_layer.md) §7.4. The system grows more entangled without growing more trustworthy.
* **Observed or Structural Failure Mode:** Multiple speculative comfort branches stack across releases; each interacts with the supervisor on a 15-minute tick; collisions become indistinguishable from intended behavior in low-resolution telemetry, and the forensic workflow loses its target.
* **What Replaced It:** The forensic workflow in [`comfort_failure_forensics.md`](comfort_failure_forensics.md). Pull 6–12 hours of telemetry, identify the proven failure mode, recommend one targeted fix only after repeated independent forensic notes show the same mode. Deadbands themselves are not retired — what is retired is iterating them (or stacking branches around them) from isolated anecdotes.
* **Reopen Only If:** Forensic notes (per [`comfort_failure_forensics.md`](comfort_failure_forensics.md) §9) record the same failure mode across at least three independent investigations, and no existing branch is responsible.
* **Source Lineage:** Audit derived from the V8.4 boost contamination pattern ([`5_runtime_layer.md`](5_runtime_layer.md) §7.4, [`telemetry_confounders.md`](telemetry_confounders.md) §5); supervisor/boost collision class in [`v8_4_heating_recovery_boost_plan.md`](v8_4_heating_recovery_boost_plan.md) §7.4.

### 4.13 Permanent Comfort Surveys as a Control Mechanism
* **Retired Approach:** Routing continuous comfort feedback (surveys, voting, "how does it feel" buttons) into Home Assistant as an input that automations consume.
* **Why It Looked Promising:** Continuous comfort feedback "closes the loop." It treats human perception as a sensor and feels like a more sophisticated control input than fixed deadbands alone.
* **Why It Is Not Helping:** Subjective comfort scoring is not a sensor. It conflates contract-violation signals with momentary preference and creates an undocumented state surface inside HA. The annotation doctrine ([`operator_annotation_design.md`](operator_annotation_design.md) §6) explicitly forbids comfort feedback from becoming a control-loop input precisely because of this conflation.
* **Observed or Structural Failure Mode:** An outdated or transient survey vote would suppress valid automation indefinitely; HA accumulates `input_text` / `input_boolean` helpers whose existence invites future automations to consume them, against the §6 forbidden-path list.
* **What Replaced It:** Operator narrative annotations in `supervisor_state_log` (forensic-only, sheet-side, never read by HA) plus the machine `hvac_provenance_log`. Surveys, if used at all, are joined to telemetry windows after the fact for forensic notes per [`comfort_failure_forensics.md`](comfort_failure_forensics.md) §9. Deadbands remain the comfort contract; surveys do not replace them.
* **Reopen Only If:** A survey instrument is proposed strictly as a forensic annotation surface (write-only to a Sheets tab, never read by HA, never gating any automation), and the forbidden-path discipline of [`operator_annotation_design.md`](operator_annotation_design.md) §6 is preserved without modification.
* **Source Lineage:** [`operator_annotation_design.md`](operator_annotation_design.md) §2, §6; [`telemetry_confounders.md`](telemetry_confounders.md) §6.5 forbidden paths.

### 4.14 Treating Human Discomfort as Immediate Automation Input
* **Retired Approach:** Routing real-time human discomfort signals (voice commands, app reactions, generic "I'm cold" buttons) directly into comfort-policy automations as triggers or conditions.
* **Why It Looked Promising:** Reacting immediately to a household member's discomfort feels like the system being responsive and caring.
* **Why It Is Not Helping:** The system already has the single legitimate immediate ingest: the WAF watcher (`v7_5_waf_manual_override`) detects a parent-less setpoint change and starts `timer.manual_hvac_override`, which suspends comfort-policy automations for one hour. Adding a second immediate-discomfort path either duplicates that mechanism (collisions with the WAF watcher) or bypasses it (a manual-override contract violation of the class §4.15 names).
* **Observed or Structural Failure Mode:** Two ingest paths can disagree on whether comfort intent is "active," leaving the supervisor unable to reliably know whether to act and producing forensic ambiguity about which path overruled which.
* **What Replaced It:** The WAF watcher remains the single immediate ingest. Anything else is forensic — recorded as `comfort_complaint` in `supervisor_state_log` and consumed only by the workflow in [`comfort_failure_forensics.md`](comfort_failure_forensics.md).
* **Reopen Only If:** A new ingest is proven to preserve the manual-override contract (it must also start `timer.manual_hvac_override` via the same parent-less context detection), adds no new control path, and is documented against this entry.
* **Source Lineage:** `automations.yaml` Section 3 (`v7_5_waf_manual_override`); [`comfort_failure_forensics.md`](comfort_failure_forensics.md) §10; doctrine alignment with [`operator_annotation_design.md`](operator_annotation_design.md).

### 4.15 Letting Comfort-Policy Automation Override Manual Intent
* **Retired Approach:** Allowing a comfort-policy automation (supervisor branch, destratification, boost engage, ceiling gate, season switch, etc.) to write climate state while `timer.manual_hvac_override` is `active`.
* **Why It Looked Promising:** "The supervisor knows better; surely it should outrank a stale manual setting." Centralized policy is easier to reason about than a household disagreement, and an outdated manual setting looks like a bug to be corrected.
* **Why It Is Not Helping:** During the override window the household has explicitly disagreed with policy. Policy-overriding-policy creates the exact failure mode the forensic doctrine wants captured ("manual cooling was requested, but supervisor killed it because outdoor was too cold"). The contract is that manual intent wins for the override window; comfort policy resumes after expiry.
* **Observed or Structural Failure Mode:** Manual cooling or heating requests are silently reversed within minutes of being set, eroding trust in the system and forcing the household to fight it.
* **What Replaced It:** Every comfort-policy path gates on `timer.manual_hvac_override == idle`. The supervisor (Section 2), the 76°F ceiling gate (Section 3), fan destratification (Section 6), Samsung Auto Guardrail (Section 8), and Section 14 boost engage already follow this rule. New comfort-policy automations must inherit it.
* **Reopen Only If:** A specific path is independently classified as a true safety gate (equipment protection, not occupant comfort) under the updated doctrine, with a doctrine update in [`5_runtime_layer.md`](5_runtime_layer.md) Manual Override Contract section explaining why the path is safety rather than comfort.
* **Source Lineage:** `automations.yaml` Sections 2, 3 ceiling, 6, 8, 14 (all gate on idle); [`5_runtime_layer.md`](5_runtime_layer.md) Manual Override Contract section.

### 4.16 Treating Outdoor / Season Logic as Stronger Than Manual Override
* **Retired Approach:** Allowing outdoor temperature thresholds or `input_select.hvac_season_mode` branches to overrule a manual setpoint while the override window is active, or to immediately reverse a manual setpoint the moment the window expires without considering whether the household intent is still meaningful.
* **Why It Looked Promising:** "It's 30°F outside — obviously the user didn't really mean cool." Outdoor conditions feel like an authoritative input that policy should defer to.
* **Why It Is Not Helping:** Outdoor temperature is one input to comfort policy, not a meta-authority over the household. The recent shoulder-night Master cooling escape (commit `e00013d`) is the reference shape: it preserves manual cooling intent even when the outdoor branch would otherwise bulk-off Master. Failing to honor that intent is a contract failure signature documented in [`comfort_failure_forensics.md`](comfort_failure_forensics.md) §8.6.
* **Observed or Structural Failure Mode:** A manually set Master = `cool/61` in heating-night decays into Master = `off` the moment the supervisor's heating-night branch evaluates the room as "warm enough"; the household experiences the system silently disagreeing.
* **What Replaced It:** Manual override gates every comfort path. Season logic re-asserts only after the override timer expires, and even then, season branches should respect any documented comfort-escape (e.g., shoulder-night Master cooling escape) before bulk-offing a room the household clearly wanted active.
* **Reopen Only If:** A safety equipment limit (not occupant comfort) makes outdoor temperature decisive — and even then, the path belongs in Section 3 with explicit safety framing, not in Section 2 season branches.
* **Source Lineage:** `automations.yaml` Section 2 shoulder-night Master cooling escape (`e00013d`); [`comfort_failure_forensics.md`](comfort_failure_forensics.md) §8.6; doctrine alignment with §4.15.

### 4.17 Accepting Supervisor / Boost Collisions as Normal
* **Retired Approach:** Treating the supervisor's 15-minute overwrite of Section 14 boost commands as an "intentional pilot limitation" indefinitely, without resolving or quantifying the collision.
* **Why It Looked Promising:** Section 14's design doc ([`v8_4_heating_recovery_boost_plan.md`](v8_4_heating_recovery_boost_plan.md) §7.4) and the in-YAML comment treat the overwrite as tolerable for the pilot phase. Pilot patience is a legitimate engineering stance.
* **Why It Is Not Helping:** The four observed V8.4 cycles ([`5_runtime_layer.md`](5_runtime_layer.md) §7.4) all terminated externally, never at `truth_cap` or timeout. Effectiveness remains unmeasured precisely because the collision class is unresolved. Continuing to label the collision "intentional" while the pilot remains uncloseable is doctrine drift dressed as pilot discipline.
* **Observed or Structural Failure Mode:** Boost setpoint 77 → 68 on supervisor boundary ticks while `Section14_Boost_Active = true`. Truth cap is never reached; no clean cycle exists in `VTherm_Launch_Data_v5` per [`analysis/v8_4_lr_boost_v5_evidence_review.md`](analysis/v8_4_lr_boost_v5_evidence_review.md).
* **What Replaced It:** V9 collision-reduction work per [`v9_v10_goals.md`](v9_v10_goals.md) §2.2: either an acknowledged forensic anomaly until Section 14 produces a clean cycle (doctrine-only) or, with telemetry proof of recurrence, a one-line `input_boolean.lr_heating_recovery_boost_active == off` guard in Section 2's heating branch (per [`v8_4_heating_recovery_boost_plan.md`](v8_4_heating_recovery_boost_plan.md) §7.4). Doctrine first; runtime change only after evidence.
* **Reopen Only If:** Section 14 verdict closes (issue #49) with the current collision model, and the next pilot does not depend on overwrite-free runs.
* **Source Lineage:** [`v8_4_heating_recovery_boost_plan.md`](v8_4_heating_recovery_boost_plan.md) §7.4; [`5_runtime_layer.md`](5_runtime_layer.md) §7.4; [`analysis/v8_4_lr_boost_v5_evidence_review.md`](analysis/v8_4_lr_boost_v5_evidence_review.md); [`telemetry_confounders.md`](telemetry_confounders.md) §5.

### 4.18 Adding Arbitration Before Telemetry Proves the Need
* **Retired Approach:** Introducing new explicit arbiters or interlocks (cross-mode, cross-room, manual-vs-policy, season-vs-override) before telemetry shows the conflict they arbitrate is actually a recurring problem.
* **Why It Looked Promising:** Two paths can collide, so adding a referee feels like principled engineering. This is materially the same trap as §4.5 ("Over-Architected Arbitration Before Measured Need"), specialized to the newer surfaces (manual-vs-policy, cross-mode interlocks).
* **Why It Is Not Helping:** A referee added before telemetry proves the conflict frequency just adds another collision surface. `v9_sleep_priority_interlock` is the live example: it forces LR off whenever Master enters cool while LR is at heat, with no telemetry on real conflict frequency vs. transient supervisor mode-flip noise, and no manual-override gate. Whether SPI is helping is currently unmeasured.
* **Observed or Structural Failure Mode:** New interlocks fire on transient states during legitimate supervisor decisions, generating LR-off events that look indistinguishable from real cross-mode conflicts in low-resolution telemetry.
* **What Replaced It:** Provenance fan-out first (per [`v9_v10_goals.md`](v9_v10_goals.md) §2.5): instrument the suspected conflict in `hvac_provenance_log` and V5.5 telemetry. Arbitration second, scoped to documented frequency, and only after the forensic workflow names the recurring contract failure.
* **Reopen Only If:** Provenance + telemetry show repeated cross-mode contention (or whichever class of conflict the arbiter targets) that is not explained by the supervisor's own mode-flip cadence, and a doctrine clarification of the arbiter's authority over manual intent is in place per [`5_runtime_layer.md`](5_runtime_layer.md) Manual Override Contract section.
* **Source Lineage:** Materially extends §4.5 to manual-vs-policy and cross-mode interlocks; `automations.yaml` Section 3 `v9_sleep_priority_interlock`; [`v9_v10_goals.md`](v9_v10_goals.md) §7 Manual Override Doctrine.

### 4.19 Algorithmic Control Before Algorithmic Diagnosis
* **Retired Approach:** Building ML, autonomous comfort AI, predictive setpoint control, or any algorithmic control authority before the equivalent algorithmic diagnosis surfaces exist and have produced a labeled archive of forensic notes.
* **Why It Looked Promising:** Framing the system as solvable end-to-end with an algorithm sounds modern and ambitious. Operator burden looks like something an algorithm could simply absorb.
* **Why It Is Not Helping:** The repo cannot today reliably answer "what set the LR setpoint to 71°F at 03:15?" for every event — the provenance logger ([`hvac_provenance_logger_design.md`](hvac_provenance_logger_design.md)) covers four entities in its first pass and was adopted recently. Adding autonomous control on top of partially-classified provenance compounds opacity. An algorithm whose decisions cannot be diagnosed cannot be trusted with control.
* **Observed or Structural Failure Mode:** Autonomous decisions become indistinguishable from collision artifacts, sensor degradation, or integration anomalies in telemetry; forensic workflows lose their target.
* **What Replaced It:** V10 = algorithm-supported diagnosis only, per [`v9_v10_goals.md`](v9_v10_goals.md) §4. Diagnosis surfaces consume telemetry + provenance + annotations; they never command climate state.
* **Reopen Only If:** Provenance covers every climate entity, every safety surface, and every season-mode change for at least one full season; V10 diagnosis has produced a labeled forensic archive; Eric's deadband contract is preserved; and a separately-documented case for control authority beyond V9 deadbands exists. None of these conditions hold today.
* **Source Lineage:** [`hvac_provenance_logger_design.md`](hvac_provenance_logger_design.md); [`v9_v10_goals.md`](v9_v10_goals.md) §4–§6; doctrine alignment with §4.13, §4.15, §4.18.

## 5. Meta-Guardrails

The following guardrails apply across all proposals, even when a specific retired approach is not directly named:

* **Structure beats neat theory:** Moose House must be reasoned about as a real building with gravity, mass, and flow, not as a clean software abstraction.
* **Live YAML outranks prose for runtime truth:** Narrative docs explain; runtime files (Doc 5) decide actual behavior.
* **Telemetry is evidence, not doctrine:** Observed data (Doc 4) should validate or challenge assumptions, not replace governing logic by itself.
* **Historical retention does not confer current authority:** An old doc may be valuable without being current.
* **Complexity requires evidence:** More logic is not better unless measured outcomes prove it necessary.
* **Presence is a modifier, not a sovereign:** Occupancy can shape control but should not be assumed to be the master explanation for comfort in a high-inertia house.
* **More sensors are not automatically more truth:** Quality, auditability, and graceful degradation matter more than raw count.

## 6. Reopen Conditions

A retired approach may only be reconsidered if at least one of the following is true:

* New telemetry evidence demonstrates that the old rejection no longer holds.
* Hardware reality has changed enough to alter the original failure mode.
* Topology or transport architecture has changed enough that the old conclusion may no longer apply.
* The proposed implementation is materially different, not merely a renamed or cosmetically simplified version of the old idea.
* The proposal explicitly addresses the prior failure mode and explains why it will degrade more safely than the retired version.

*Note: Reopening an idea requires proving that its historical failure mode has been addressed. The burden is on the proposal, not on the archive.*

## 7. Final Principle

This appendix exists so future sessions do not waste time rediscovering known traps. The archive should remain preserved for full context, but this document is the operational memory layer for rejected ideas.

**If a proposal feels familiar, assume it probably is. Check here first.**