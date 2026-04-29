# Doc 4 / Operations Sheet — V8.3 Validation

**Ops Date:** April 25, 2026
**Document Role:** Operational review worksheet
**Status:** Active evaluation framework for the current Moose House climate doctrine. Update when operating thresholds, success criteria, or validation targets materially change.

## 1. Purpose of This Sheet
This document is the operational worksheet for evaluating whether the current climate doctrine is working in practice. It exists to answer whether comfort is improving, if control behavior is stable, if safety backstops remain silent, and if there's evidence to justify a V9 architecture pass.

This sheet sits above raw telemetry and below doctrine. Telemetry provides evidence. This sheet provides judgment.

*   This is not Doc 1 / Startup Canon.
*   This is not Doc 2 / Reference Map.
*   This is not Appendix A or Doc 3 / Regression Appendix.
*   This is not Doc 5 / Runtime Layer or the literal YAML source.

## 2. What This Sheet Measures
This sheet translates observed evidence into operational judgment about:
*   Comfort
*   Stability
*   Safety silence
*   Human friction
*   Capacity or starvation symptoms
*   Whether current imperfections remain tolerable
*   Whether current evidence supports keeping, tuning, or replacing the doctrine

## 3. Evidence Sources
This sheet should be filled out using:
*   Active `automations.yaml` (See Doc 5)
*   Active `configuration.yaml` (See Doc 5)
*   Live helpers and templates where relevant
*   Home Assistant logbook/history
*   `VTherm_Launch_Data_v5` telemetry
*   Direct human comfort observations
*   Appendix A (only when historical clarification is needed)

### 3.1 Interpretation Rule
*   Telemetry is the evidence layer.
*   This sheet is the interpretation layer.
*   If this sheet disagrees with live YAML (Doc 5) about what the system is configured to do, live YAML wins for runtime truth.
*   If this sheet shows poor comfort, instability, or rising annoyance, that is evidence for tuning, closer investigation, or escalation.

## 4. Authority Boundary
This sheet does not redefine doctrine by itself. It evaluates whether doctrine is succeeding.

**Use this sheet when:**
*   Reviewing daily or weekly comfort performance
*   Checking whether manual interventions are decreasing
*   Investigating drift, overshoot, churn, or warm hang
*   Deciding whether V8.2 should remain in place
*   Deciding whether V9 is justified

**Do not use this sheet alone when:**
*   Starting a fresh session (Use Doc 1)
*   Reconstructing sensor-audit history (Use Appendix A)
*   Determining exact runtime control behavior (Use Doc 5)
*   Deciding room topology or source precedence (Use Doc 2)

## 5. Current Validation Target
**Current validation target:**
*   **Active control layer:** V8.2 comfort-first cooling
*   **Active truth layer:** V3.1 audited truth
*   **Evidence layer:** `VTherm_Launch_Data_v5`
*   **Core question:** Is V8.2 operationally good enough to keep, or is a V9 architecture pass justified?

## 6. Primary Operational KPIs

### 6.1 Comfort KPIs
*   Time above upper comfort band by room
*   Time below lower comfort band by room
*   Master time above 66°F overnight
*   Master time below 62°F overnight
*   Repeated warm-hang or overcool patterns
*   Number of direct comfort complaints or manual corrections

### 6.2 Stability KPIs
*   Cool/off transition count per room
*   Longest continuous cooling run
*   Longest continuous off stretch while above target band
*   Number of times a room stayed acceptably inside the deadband without unnecessary intervention
*   Number of times a room drifted outside the band before correction
*   Total visible churn across the system

### 6.3 Safety KPIs
*   Runaway cutoffs fired
*   Emergency floors fired
*   Ceiling gates fired
*(Zero is the only normal number for all core safety backstops. Any non-zero event requires review.)*

### 6.4 Human Friction KPIs
*   Manual turn-backs-on
*   Manual turn-offs
*   Manual setpoint changes
*   “This feels gross” moments
*   Number of times the house felt fussy, confusing, or clearly worse than intended

### 6.5 Capacity / Starvation KPIs
*   Simultaneous heads cooling at the same time
*   Number of periods with 3+ heads cooling
*   Number of periods with all heads cooling
*   Whether one room fails to pull down while others continue normal pull-down
*   Whether the same pattern repeats on legitimately hot days

## 7. Operational Success Criteria

### 7.1 Comfort Success
Primary comfort goals:
*   Living Room stays mostly within 68–72°F
*   Master daytime stays mostly within 68–72°F
*   Master sleep window (6pm–6am) stays mostly within 62–66°F
*   Lincoln’s Room stays mostly within 68–72°F
*   Lilly’s Room stays mostly within 68–72°F

### 7.2 Stability Success
Operational stability means:
*   Deadband behaves predictably
*   Cool/off transitions remain reasonable
*   No repeated obvious thrash
*   No room spends long periods hanging warm above band without cause
*   No room repeatedly overshoots cold below band without cause

### 7.3 Safety Success
Operational safety means:
*   Runaway cutoffs remain silent
*   Emergency floors remain silent
*   Ceiling gates remain silent
*   No safety event becomes a recurring pattern

### 7.4 Human Experience Success
Operational success also means:
*   Manual cooling re-engagements decrease materially
*   Annoyance moments become rare
*   The system feels calmer and less fussy than earlier doctrine
*   The house feels closer to intended comfort without requiring constant babysitting

## 8. Known Deferred Limitations
The following are known limitations and do not automatically count as failure unless they create real operational problems:
*   Deadband memory currently uses HVAC mode rather than explicit latches.
*   Commands are still issued every supervisor tick rather than only on state transitions.
*   Capacity arbitration remains deferred pending measured evidence of real starvation.
*   Diagnostic transition logging is temporary instrumentation, not permanent control logic.

*(These are tolerated debts, not settled ideals.)*

## 9. Core Metrics by Room

### 9.1 Living Room
**Target band:** 68–72°F
**Track:**
*   Avg temp
*   Max temp
*   Min temp
*   Time >72°F
*   Time <68°F
*   Number of complaints/manual interventions
*   Notable drift or hang behavior
**Notes:** [Space for notes]

### 9.2 Master Bedroom
*(Track separately by operating mode.)*
**Day (6am–6pm) | Target: 68–72°F**
**Track:** Avg temp, Max temp, Min temp, Time >72°F, Time <68°F

**Sleep (6pm–6am) | Target: 62–66°F**
**Track:** Avg temp, Max temp, Min temp, Time >66°F, Time <62°F, Number of sleep comfort complaints

**Also track:**
*   Overnight drift behavior
*   Whether sleep cooling feels stable
*   Any “too warm to sleep” or “overcooled” events
**Notes:** [Space for notes]

### 9.3 Lincoln’s Room
**Target band:** 68–72°F
**Track:**
*   Avg temp
*   Max temp
*   Min temp
*   Time >72°F
*   Time <68°F
*   Comfort notes
*   Notable instability
**Notes:** [Space for notes]

### 9.4 Lilly’s Room
**Target band:** 68–72°F
**Track:**
*   Avg temp
*   Max temp
*   Min temp
*   Time >72°F
*   Time <68°F
*   Comfort notes
*   Notable instability
**Notes:** [Space for notes]

## 10. Whole-System Control Behavior
Use logbook/history plus telemetry to review whole-system behavior.
**Track:**
*   Total cool → off transitions across all heads
*   Total off → cool transitions across all heads
*   Longest continuous cooling run by any head
*   Longest above-band off stretch by any affected room
*   Maximum simultaneous heads cooling
*   Number of periods with 3+ heads cooling
*   Number of periods with all heads cooling
*   Any visible churn, timing weirdness, or coordination issues

## 11. Safety Event Review
If any safety event occurs, investigate immediately. Do not casually widen thresholds to hide the problem. For each event type, record:
*   Fired? (Y/N)
*   Count
*   Timestamp(s)
*   Room(s)
*   Notes
*   Whether the event appears to reflect real system failure, edge-case conditions, or noisy interpretation

### 11.1 Safety Mechanisms to Review
*   Living Room runaway cooling cutoff (60°F)
*   Master emergency cooling floor (58°F)
*   Ceiling safety gates (76°F, Master/Lincoln/Lilly)
*   Any other active safety backstop introduced later

### 11.2 Ceiling Gate Exclusion (Living Room)
**Note:** The Living Room is intentionally excluded from the Safety Ceiling Gates (76°F) trigger list. Under normal operation, the main supervisor's 72°F on-trigger ensures the LR engages cooling well before 76°F. If the supervisor is disabled or truth goes stale during a hot stretch, there is no automatic ceiling catch for the LR.

## 12. Human Friction / Manual Override Review
Watch manual actions and direct experience.
**Track:**
*   Number of times cooling was manually turned back on
*   Number of times cooling was manually turned off
*   Number of times setpoints were manually changed
*   Number of “this feels gross” moments
*   Which room
*   What time
*   What symptom caused the intervention
*   Whether the problem was comfort, lag, overshoot, confusion, or distrust

*(This section matters because a technically “working” system that people keep fighting is not operationally successful.)*

## 13. Capacity / Starvation Watch
Use this section only when there are signs of shared-load strain, especially on hotter days.
For each suspected event, record:
*   Outdoor temperature / conditions
*   Which heads were calling
*   Which room failed to pull down
*   How long the room stayed above its upper band
*   Whether another room continued dropping normally
*   Whether a sensor issue can be ruled out
*   Whether the same pattern repeated under similar conditions
*   Notes

### 13.1 Possible Starvation Symptom Checklist
*   [ ] 3–4 heads calling simultaneously
*   [ ] One room remains above target band for an extended period
*   [ ] Another room continues normal pull-down
*   [ ] No obvious sensor failure explains it
*   [ ] Pattern repeats on a hot day
*(Do not call starvation “real” from one weak anecdote.)*

## 14. Daily Log Template
**Date:**
**Outdoor conditions:**
*   High:
*   Low:
*   Humidity / notable weather:
**Overall impression:**
*   [ ] Better than prior doctrine
*   [ ] About the same
*   [ ] Worse
**Notes:**
**Room-by-room notes:**
*   Living Room:
*   Master Bedroom:
*   Lincoln:
*   Lilly:
**Events:**
*   Safety backstops:
*   Weird behavior:
*   Logbook findings:
*   Working hypothesis:

---

## 15. Weekly Review Questions

### 15.1 Comfort
*   Did the house actually feel closer to intended doctrine?
*   Which room felt most stable?
*   Which room felt most annoying?
*   Did any room repeatedly drift outside expectations?

### 15.2 Stability
*   Were cool/off transitions reasonable or excessive?
*   Did the deadband behave as expected?
*   Were any rooms sticky, noisy, or slow to recover?
*   Did command behavior feel calm or fussy?

### 15.3 Safety
*   Did any runaway protections fire?
*   Did any ceiling or floor protections fire?
*   Were any events real issues versus noise?

### 15.4 Architecture Debt
*   Is HVAC-mode-as-memory still good enough?
*   Is command-every-tick producing visible churn?
*   Is there real evidence of multi-head starvation?
*   Is V9 justified now, or is V8.2 still earning more runway?

## 16. Action Thresholds

### 16.1 Keep V8.2 As-Is If
*   No safety backstops fire
*   Manual annoyance drops materially
*   Most rooms stay inside their intended bands most of the time
*   No obvious starvation pattern appears
*   Known deferred limitations remain tolerable rather than costly

### 16.2 Tune V8.2 If
*   One room repeatedly hangs warm
*   One room repeatedly overshoots cold
*   Transition count is clearly excessive
*   Manual annoyance remains noticeable
*   One specific weakness is obvious without requiring a full architectural rethink

### 16.3 Escalate to V9 If
*   Deadband memory clearly misbehaves
*   Command churn causes real integration weirdness
*   Repeated hot-day multi-head starvation appears
*   Safety backstops fire more than once
*   Known deferred limitations stop being tolerable debt and become recurring operational cost

## 17. Active Validation TODOs
*Keep this section limited to items that materially affect fair evaluation of V8.2.*
*   Confirm that telemetry needed for core comfort judgment is trustworthy.
*   Verify that known degraded sensors are not being mistaken for active truth contributors.
*   Ensure room truth sensors used for judgment align with active YAML.
*   Safety backstops fire outside the Section 11 "V8.2 Cooling" logger and won't show that tag. LR runaway (60°F) and Master emergency floor (58°F) send `notify.notify` pushes and force the climate entity to off. Ceiling gates (76°F, Master/Lincoln/Lilly) force the entity to `cool` or `fan_only` for 45 min with no notification. Count fires by filtering HA logbook for these climate state-change signatures, not by tag.

*(This section should not become a dumping ground for all open climate tasks.)*

## 18. Current Verdict Snapshot
At the end of each review period, record a short executive judgment:
**Current recommendation: Tune (V8.3)**

### 18.1 Escalation Trigger Check (Evidence Required)
*(If any are YES, route to Escalate and unlock corresponding V9 block in Doc 6)*
*   Deadband memory misbehaved: [Y/N] (Evidence: _________)
*   Command churn degraded integration/API: [Y/N] (Evidence: _________)
*   Repeated hot-day starvation confirmed: [Y/N] (Evidence: _________)
*   Safety backstops fired due to scheduler lag: [Y/N] (Evidence: _________)
*   Cross-mode contention paths observed: [Y] (Evidence: manual master cool override (cool/61/turbo) reverted within 45 min on 4/22; pattern repeated 3+ nights of stack-effect heating)

### 18.2 Qualitative Assessment & Routing
**Current recommendation:** Tune (V8.3)
**Action Taken:** Addressed stack-effect contention via V8.3 Tune. Implemented passive LR heat-source reduction (Target 64°F, 18:00–22:00) rather than active Master cooling, avoiding compressor mode-flips. Also introduced LR heating deadband to stop 0°F short-cycling, and patched Section 6 destratification turbo-stickiness.

## 19. Final Principle
This sheet exists to decide whether the current doctrine is working, not whether a prettier theory exists.
