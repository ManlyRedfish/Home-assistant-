# V8.4 — Heating/Shoulder Recovery Boost with Truth Cap
**Design Document and Implementation Plan**
*Author: Systems Architecture & Control-Logic Design*
*Date: 2026-05-02*
*Status: Design only — no YAML modified*

---

## 1. Problem Statement

### 1.1 Why ordinary setpoint-near-target heating causes long runtime

The V8.3 Section 2 heating deadband uses a top-anchored scheme: turn on at `<64°F`, turn off at `≥68°F`, with the mini-split commanded to `heat@68°F`. This means the setpoint sent to the Samsung unit is **68°F** — nearly identical to the desired room temperature.

Samsung mini-splits regulate compressor output by comparing their **internal thermistor reading** (biased low, typically 2–5°F below truth) against the commanded setpoint. When the setpoint is only a few degrees above what the unit perceives the room to be, the unit enters a **low-demand modulation regime**: compressor speed drops to minimum, airflow drops, and the unit can run continuously at a trickle delivering only ~40–60% of rated capacity.

The result is 19–24 hour/day heating runtimes even when rooms are well below target, because the unit is never given a strong enough demand signal to run at meaningful output.

### 1.2 Why this appears specifically in heating and shoulder behavior

In **cooling**, the comfort target (68°F in LR) is already at the low end of what the unit can achieve, so even modest setpoint signals drive full-speed cooling. In **heating and shoulder**, the gap between indoor truth (~62–65°F at cold engagements) and the commanded setpoint (~68°F) can be as small as 3–6°F — which is within the Samsung's modulation comfort zone, not its recovery zone.

Old farmhouses with poor insulation and envelope leakage also lose heat faster than modern construction, compounding the effect: a barely-modulating unit struggles to hold pace with envelope losses, let alone recover from a setback.

### 1.3 Why high-setpoint recovery differs from raising the comfort target

This is the critical distinction:

| Concept | Comfort Target | Recovery Setpoint |
|---|---|---|
| **Purpose** | Where you want the room to be | How hard you tell the unit to work |
| **Who decides when to stop** | The deadband | The truth sensor |
| **Steady-state value?** | Yes | No — temporary only |
| **Energy intent** | Hold the band | Force recovery, then stop |
| **Risk if it sticks** | Acceptable drift | Overheating |

Setting `heat@77°F` does not mean you want 77°F in the room. It is a **demand command** that forces the Samsung to operate at near-peak output. The room truth sensor is the **stop condition**: once truth reaches the cap, the unit is commanded off or returned to normal supervisor behavior. The high setpoint is never left as a steady-state value.

---

## 2. Doctrine

### 2.1 Foundational principles for V8.4

1. **High setpoint is actuator demand, not desired room temperature.**
   A recovery setpoint of 76–79°F commands the mini-split's compressor to run at high output. It says nothing about where the occupant wants the room to be.

2. **Truth cap is the stop condition.**
   The room truth sensor — the smoothed, audited, multi-sensor weighted average defined in V3.1 — is the sole arbiter of when recovery is complete. If truth reaches the cap, boost ends. The setpoint is irrelevant to the stop decision.

3. **Recovery boost must be bounded on all four axes.**
   - **Truth:** Stop when room truth ≥ cap threshold.
   - **Time:** Stop when max runtime elapsed (prevents runaway if truth sensor fails).
   - **Season:** Active only in `heating` and `shoulder` — never in `cooling`.
   - **Safety:** Yield immediately to WAF/manual override; never fight the safety ceiling gate (Section 3, §5, 76°F).

4. **The boost is a layer, not a replacement.**
   Section 2 Main Supervisor remains the primary control authority. Recovery boost operates as a **pre-condition resolver**: it gets a room above the engagement threshold fast, then hands back to Section 2's normal deadband. It does not bypass, modify, or disable Section 2.

5. **One room at a time is preferred early.**
   Simultaneous multi-room boost is a capacity and energy risk. The initial validation phase should restrict to one room.

---

## 3. Proposed Behavior

This section describes behavior in heating and shoulder seasons only.

### 3.1 Engagement

A recovery boost engages for a given room when ALL of the following are true:

- `input_select.hvac_season_mode` is `heating` or `shoulder`
- Room truth temperature is below the **cold threshold** (candidate: `<64°F`)
- `timer.manual_hvac_override` is NOT active (WAF/manual override idle)
- `input_boolean.away_mode` is `off`
- The room's per-room boost latch (`input_boolean.<room>_heating_recovery_boost_active`) is `off` (not already boosting)
- The per-room compressor cooldown timer is NOT active (prevents boost immediately after compressor cycle)
- Current time is not in a period where boost is explicitly suppressed (e.g., LR bedtime window already has passive source reduction)

### 3.2 Boost action

When engaged:

1. Set the room's boost latch to `on`.
2. Start the room's max-runtime timer (`timer.<room>_heating_recovery_max_runtime`).
3. Command the climate entity: `climate.set_temperature` with `hvac_mode: heat` and `temperature: 77` (candidate value — see §4).
4. Log `heating_recovery_boost_started` to the event journal.

### 3.3 Stop conditions (in priority order)

| Priority | Condition | Action |
|---|---|---|
| 1 | WAF/manual override engaged | Immediately release boost; restore normal supervisor authority; log `heating_recovery_boost_blocked_waf` |
| 2 | Room truth ≥ cap threshold (candidate: `67°F` or `68°F`) | Command `hvac_mode: off`; release latch; log `heating_recovery_boost_stopped_truth_cap` |
| 3 | Max-runtime timer fires (candidate: 90–120 min) | Command `hvac_mode: off`; release latch; log `heating_recovery_boost_stopped_timeout` |
| 4 | Season changes to `cooling` | Immediately release boost; no heat command issued |

### 3.4 After boost ends

- Latch is cleared (`input_boolean.<room>_heating_recovery_boost_active` → `off`).
- Climate entity is set to `hvac_mode: off` (or `fan_only` if room truth is within band — operator decision).
- Section 2 Main Supervisor resumes normal authority on its next 15-minute tick.
- An optional cooldown/no-repeat window may be applied (candidate: 30 minutes) before boost is eligible again in the same room, to prevent rapid re-engagement.

### 3.5 What boost does NOT do

- Does not touch the Nest (`climate.dining_room`).
- Does not engage during cooling season.
- Does not engage while WAF/manual override is active.
- Does not modify Section 2's deadband thresholds.
- Does not alter safety gates (Section 3 ceiling at 76°F remains sovereign).
- Does not implement V9 pre-chill or any event-driven architecture changes.
- Does not touch the LR bedtime setpoint reduction logic.

---

## 4. Candidate Thresholds

> **These are initial starting proposals, not validated operating values.**
> Every threshold requires operator sign-off and empirical validation before lock-in.
> See §11 for the validation plan.

| Parameter | Candidate Value | Rationale |
|---|---|---|
| Cold engagement threshold | `< 64°F` room truth | Below current Section 2 "turn on" point; ensures boost only fires when genuinely cold |
| Truth cap (stop condition) | `67°F` (conservative) or `68°F` (at-target) | 67°F stops just before target, handing off to Section 2; 68°F stops at target boundary |
| Boost setpoint | `77°F` | Forces meaningful Samsung output; well below safety ceiling (76°F ceiling gate uses room truth, not setpoint, so no conflict) |
| Max runtime | `90 minutes` (initial) | Prevents runaway; typical recovery from 62°F to 67°F should complete well inside this |
| No-repeat cooldown | `30 minutes` after latch release | Prevents re-engagement oscillation if truth sensor is slow |
| Per-room boost setpoint | Uniform `77°F` across all rooms (initial) | Simplicity; room-specific tuning deferred to post-validation |

### 4.1 Safety ceiling interaction note

Section 3's safety ceiling gate fires at `76°F room truth` (not setpoint). A boost setpoint of `77°F` does NOT trigger the ceiling gate unless room truth actually reaches 76°F. The ceiling gate remains sovereign: if truth somehow reaches 76°F, it will fire, override the boost, and force `fan_only` for 45 minutes. This is the correct and expected safety behavior. The truth cap (67–68°F) is deliberately far below the ceiling, providing a **9°F safety margin** between boost stop and the hardware ceiling gate.

### 4.2 Why not 76°F setpoint

Setting boost to `76°F` would be directly at the safety ceiling gate's truth threshold. A setpoint of `77°F` is used precisely because setpoint and room truth are different: the room will not reach 77°F because the truth cap stops the unit at 67–68°F. The setpoint choice is about **Samsung output demand**, not expected room temperature.

---

## 5. Scope

### 5.1 In scope

- Heating season and shoulder season only
- Rooms with Samsung mini-splits: `climate.living_room_air`, `climate.master_bedroom_air`, `climate.lincoln_air`, `climate.lilly_air`
- Engagement only when WAF/manual override is idle
- Engagement only when `away_mode` is off
- Per-room independent boost state (one room can boost without requiring others to)
- Max-runtime safety timer per room
- Event journal logging for all boost lifecycle events
- New Section 14 in automations.yaml (preferred architecture — see §6)
- New helpers in configuration.yaml

### 5.2 Explicitly out of scope

- Cooling season behavior — not touched
- Dining room Nest — not touched
- Section 2 Main Supervisor — not modified
- Section 3 Safety Gates — not modified
- Phase 1A Event Journal infrastructure — not modified, only called
- V9 event-driven architecture — not implemented
- V9 pre-chill logic — not implemented
- Truth sensor weights or staleness thresholds — not changed
- Any entity renaming
- Any existing automation removal

---

## 6. Architecture Options

Three architectural patterns are evaluated for implementing the boost layer.

---

### Option A — Append logic inside Section 2 Main Supervisor

**Description:** Add boost threshold checks and high-setpoint commands within the existing `v7_5_main_supervisor` automation's nested `choose` blocks, alongside the existing heating deadband logic.

**Mechanism:** At the point where Section 2 currently evaluates `lr_temp < 64` and issues `heat@68`, add a condition branch: if temp is very cold, issue `heat@77` instead.

**Advantages:**
- Single automation — no inter-automation state to manage
- Section 2 tick (15 min) already provides natural timing
- Fewer helpers needed

**Disadvantages:**
- Section 2 is already the most complex and deeply nested automation in the system; it is explicitly flagged as high regression-risk in Doc 3
- A 15-minute tick is too slow for a truth-cap stop condition — the unit could overshoot by up to 14 minutes after truth crosses the cap
- No boost latch means Section 2 would either boost on every tick (command spam) or require complex in-YAML state memory
- Mixing comfort deadband logic and recovery boost logic in one automation destroys observability: the event journal cannot distinguish supervisor decisions from boost decisions
- Rollback requires editing Section 2 — high risk of breaking unrelated logic
- Fails the "separate new observer/control section" preference stated in operator instructions

**Safety rating:** Medium-low — regression risk is high given Section 2 complexity.
**Regression risk:** High.
**Observability:** Poor — boost and supervisor decisions are entangled.
**WAF interaction:** Relies on Section 2's existing WAF check — adequate but not explicit.
**Rollback:** Requires Section 2 edit — high risk.

**Verdict: Not recommended.**

---

### Option B — Separate Section 14 "Heating Recovery Boost" Automation

**Description:** Add a new section (`Section 14`) to `automations.yaml` consisting of:
- A **trigger automation** that fires on truth sensor state changes (when truth drops below cold threshold, and when truth rises above cap threshold).
- Optionally a **timer expiry automation** that fires when `timer.<room>_heating_recovery_max_runtime` finishes.
- Per-room `input_boolean` latches to track active boost state and prevent re-entry.

**Mechanism:**
- `trigger: state` on `sensor.<room>_temperature_truth` dropping below 64°F → engage boost if conditions met
- `trigger: state` on `sensor.<room>_temperature_truth` rising above 67°F and latch is `on` → stop boost
- `trigger: event: timer.finished` on `timer.<room>_heating_recovery_max_runtime` → stop boost on timeout
- `trigger: state` on `timer.manual_hvac_override` becoming `active` → release any active boost immediately

**Advantages:**
- Completely isolated from Section 2 — zero modification required to existing supervisor
- Event-driven on truth sensor changes → truth cap response is near-immediate (seconds, not 15 minutes)
- Clear separation of concerns: supervisor handles comfort deadband, Section 14 handles recovery boost
- Latch pattern (`input_boolean`) makes boost state visible in HA dashboard and loggable
- Rollback is trivially safe: disable Section 14 automations, turn off latches — Section 2 resumes without any awareness of boost history
- Observer/telemetry integration is clean: Section 14 calls `script.log_event` independently
- No modification to existing Sections 1–13
- Follows the architectural precedent already set by Section 12 (Phase 1A observer)

**Disadvantages:**
- Requires new helpers (per-room latches + per-room timers)
- More automations to maintain (4 rooms × boost-start + boost-stop-truth + boost-stop-timeout + WAF-release = potentially 4–5 automations or one well-conditioned multi-room automation)
- Section 14 and Section 2 can issue conflicting commands in the 15-minute window between ticks if Section 2 fires while boost is active — requires latch check in Section 2 **OR** Section 14 issuing commands that satisfy both (command `heat@77` will not be overwritten by Section 2's `heat@68` in the short term since Section 2 fires every 15 min and the climate entity state survives between ticks)
- Requires careful condition ordering to prevent edge cases at mode boundaries

**Safety rating:** High — isolation preserves all existing safety systems.
**Regression risk:** Low — no existing automation is touched.
**Observability:** High — latch state, timer state, and event journal all visible.
**WAF interaction:** Explicit WAF-release trigger; boost respects override fully.
**Rollback:** Disable Section 14 automations → system reverts completely. Zero risk to Section 2.

**Verdict: Recommended primary architecture.**

---

### Option C — Helper-Based Latch/Timer Boost State Per Room (Distributed Scripts)

**Description:** Use `script.<room>_engage_heating_boost` and `script.<room>_release_heating_boost` called from a lightweight Section 14 automation. Scripts hold the per-room logic; the automation is a thin dispatcher.

**Mechanism:** One Section 14 automation watches truth sensors. When a threshold is crossed, it calls a per-room script. Scripts handle latch set/clear, climate command, timer start/stop, and event journal logging. Mirrors how `script.log_event` already works for telemetry.

**Advantages:**
- Script decomposition makes per-room logic reusable (e.g., a dashboard button could trigger the script for manual recovery)
- Easier to extend to additional rooms without duplicating automation logic
- Clean separation of dispatch (automation) and action (script)

**Disadvantages:**
- Adds another layer of indirection — automation → script → climate/timer/helper — increasing debugging complexity
- Script execution is asynchronous in HA; timing of latch set vs. climate command vs. timer start could produce edge-case race conditions if HA is under load
- For a four-room house, the complexity overhead of scripts vs. inline automation is not justified by the scale
- Harder to trace in HA logbook (script calls don't always show full context)
- Rollback requires disabling both automations and scripts

**Safety rating:** High (same as Option B if implemented carefully).
**Regression risk:** Low — still isolated from Section 2.
**Observability:** Medium — script calls add indirection that can obscure event chains in logbook.
**WAF interaction:** Same as Option B if WAF check is in the dispatcher automation.
**Rollback:** More components to disable vs. Option B.

**Verdict: Viable but overcomplicated for current scale. Prefer Option B. Revisit if V9 script-based architecture is adopted broadly.**

---

### Architecture Comparison Summary

| Criterion | Option A (Section 2 Inline) | Option B (Section 14 Separate) | Option C (Script Dispatch) |
|---|---|---|---|
| Section 2 regression risk | High | None | None |
| Stop-condition latency | Up to 15 min | Seconds | Seconds |
| Rollback safety | Medium-low | High | High |
| Observability | Poor | High | Medium |
| WAF interaction | Implicit | Explicit | Explicit |
| Helper count | Low | Moderate | Moderate |
| Implementation complexity | High | Medium | High |
| Recommended | No | **Yes** | No |

---

## 7. Recommended Phase 1 Implementation

### 7.1 Architecture selection

**Use Option B: Section 14 Heating Recovery Boost**, implemented as a set of event-triggered automations isolated from Section 2.

The operator instruction explicitly states: *"Prefer a separate new observer/control section rather than large Section 2 edits unless evidence strongly supports otherwise."* Option B satisfies this directive and carries the lowest regression risk.

### 7.2 Automation structure

Implement Section 14 as **two automations** (multi-trigger, multi-room, condition-gated):

**14a — `v8_4_heating_recovery_boost_engage`**
- Triggers: `state` on each room truth sensor dropping below 64°F
- Conditions: season is heating/shoulder, WAF idle, away mode off, latch not already on
- Actions: set latch on, start max-runtime timer, command `heat@77`, log event

**14b — `v8_4_heating_recovery_boost_release`**
- Triggers:
  - `state` on each room truth sensor rising to ≥67°F (truth cap)
  - `event: timer.finished` for each `timer.<room>_heating_recovery_max_runtime`
  - `state` on `timer.manual_hvac_override` becoming `active` (WAF override)
  - `state` on `input_select.hvac_season_mode` changing to `cooling`
- Conditions: per-trigger checks (e.g., truth-cap trigger only releases if latch is on)
- Actions: determine release reason, command `hvac_mode: off`, clear latch, stop timer, log event with reason

### 7.3 Are helper latches needed?

**Yes — latches are required for Option B.** Without latches:
- The engage automation would fire repeatedly as truth sensors fluctuate near the threshold (command spam, log noise)
- The release automation cannot know whether a truth-cap crossing is during an active boost or during normal operation
- Section 2 cannot be told to yield during an active boost without checking a shared helper state

Latches are the minimal safe mechanism. They cost one `input_boolean` per room plus one `timer` per room — a small, well-understood HA pattern.

### 7.4 Section 2 co-existence

Section 2 fires every 15 minutes. During an active boost, Section 2 will evaluate the heating deadband and may issue `heat@68` (overwriting the boost's `heat@77`). This is a **command conflict** that must be resolved.

**Proposed resolution (minimal change to Section 2):**

Add a single condition at the top of Section 2's heating branch for each room:

```yaml
- condition: state
  entity_id: input_boolean.<room>_heating_recovery_boost_active
  state: "off"
```

This is a **one-line guard per room**, not a redesign. Section 2's structure is unchanged; it simply skips issuing a heating command to rooms that are currently in active recovery boost. This is the **minimum and safest touch to Section 2** acceptable under these constraints.

**Alternative (no Section 2 touch):** Accept that Section 2 will overwrite `heat@77` with `heat@68` on its 15-minute tick. The unit will continue heating either way; the output may not be maximized for those minutes until the next Section 14 engage fires and reasserts `heat@77`. For the initial validation phase this is acceptable and avoids touching Section 2 at all.

**Recommendation:** Start with **zero Section 2 changes** in Phase 1. Validate that Section 14 produces measurable recovery improvement even with the 15-minute overwrite race. Only add the Section 2 guard if telemetry shows the overwrite is materially degrading recovery.

---

## 8. Required Helpers

### 8.1 Per-room boost latch (input_boolean)

Four helpers, one per mini-split room:

```yaml
input_boolean:
  lr_heating_recovery_boost_active:
    name: "LR Heating Recovery Boost Active"
    icon: mdi:thermometer-plus

  master_heating_recovery_boost_active:
    name: "Master Heating Recovery Boost Active"
    icon: mdi:thermometer-plus

  lincoln_heating_recovery_boost_active:
    name: "Lincoln Heating Recovery Boost Active"
    icon: mdi:thermometer-plus

  lilly_heating_recovery_boost_active:
    name: "Lilly Heating Recovery Boost Active"
    icon: mdi:thermometer-plus
```

> A master `input_boolean.master_heating_recovery_boost_active` is **not recommended** as it creates an ambiguous aggregate state. Per-room granularity is preferred for observability and independent rollback per room.

### 8.2 Per-room max-runtime timer

Four timers, one per mini-split room:

```yaml
timer:
  lr_heating_recovery_max_runtime:
    name: "LR Heating Recovery Max Runtime"
    duration: "01:30:00"
    icon: mdi:timer-sand

  master_heating_recovery_max_runtime:
    name: "Master Heating Recovery Max Runtime"
    duration: "01:30:00"
    icon: mdi:timer-sand

  lincoln_heating_recovery_max_runtime:
    name: "Lincoln Heating Recovery Max Runtime"
    duration: "01:30:00"
    icon: mdi:timer-sand

  lilly_heating_recovery_max_runtime:
    name: "Lilly Heating Recovery Max Runtime"
    duration: "01:30:00"
    icon: mdi:timer-sand
```

Duration is set to the candidate 90-minute value; adjustable after validation.

### 8.3 No-repeat cooldown timer (optional, deferred)

A per-room cooldown timer (`timer.<room>_heating_recovery_cooldown`, 30 min) would prevent re-engagement oscillation. This is **deferred to post-validation** to minimize helper count in Phase 1. The engage condition can check that the latch was not recently active using a `last_changed` template if needed, or the operator can observe and decide.

### 8.4 Helper-free alternative

A helper-free implementation would use only `template` conditions checking `last_changed` timestamps on the climate entity's setpoint attribute to infer boost state. This is **not recommended**: it is fragile, non-debuggable, and produces no visible state for the dashboard or event journal.

---

## 9. Event Telemetry

### 9.1 Integration with Phase 1A event journal

Recovery boost lifecycle events should be logged via the existing `script.log_event` established in Phase 1A. No new logging infrastructure is needed — the existing `notify.file` → `/config/logs/event_journal.csv` pipeline handles everything.

### 9.2 Proposed event types

| Event Type | When | Actor | Key Fields |
|---|---|---|---|
| `heating_recovery_boost_started` | Engage automation fires and boost begins | `supervisor` | `zone`, `reason` (truth below threshold), `requested_setpoint: 77`, `supervisor_branch: heating_recovery_boost` |
| `heating_recovery_boost_stopped_truth_cap` | Truth sensor reaches cap threshold | `supervisor` | `zone`, `reason` (truth cap reached), `actual_mode_after: off` |
| `heating_recovery_boost_stopped_timeout` | Max-runtime timer expires | `supervisor` | `zone`, `reason` (max_runtime_exceeded), `actual_mode_after: off` |
| `heating_recovery_boost_blocked_waf` | WAF/manual override becomes active during boost | `guardrail` | `zone`, `reason` (waf_active), `actual_mode_after: off` |

### 9.3 Event journal row structure

Each event should call `script.log_event` with at minimum:

```yaml
event_type: heating_recovery_boost_started
entity_id: climate.<room>_air
zone: <room>
actor: supervisor
reason: "truth_below_64F"
requested_mode: heat
requested_setpoint: "77"
supervisor_branch: heating_recovery_boost
```

The existing `script.log_event` auto-populates `timestamp`, `season_mode`, `waf_active`, and `correlation_id` from current state.

### 9.4 Implementation note

These event types do not exist in Phase 1A and **must not be added until the boost YAML is ready to generate them**. Logging phantom events is worse than no logging. Event types are defined at the same time as the automation that fires them — no earlier.

---

## 10. Regression Risks

### 10.1 Overheating if truth cap fails

**Risk:** Truth sensor returns stale or erroneously low value → boost runs to timeout instead of stopping at cap → room overheats past 68°F.

**Mitigation:** V3.1 already rejects truth sensors with data older than 2 hours. The 90-minute max-runtime timer is a hard stop regardless of truth. Section 3 safety ceiling gate (76°F room truth) remains fully active and sovereign — it would force `fan_only` if truth reached 76°F.

**Residual exposure:** 67°F cap to 76°F ceiling is 9°F of headroom. Even a full 90-minute timeout in a room starting at 63°F in a cold shoulder-season morning is unlikely to produce 76°F truth in a leaky farmhouse envelope. However, this is an assumption that must be validated empirically.

### 10.2 Stale truth sensor risk

**Risk:** Sensor becomes unavailable mid-boost → truth cap trigger never fires → boost runs to timeout.

**Mitigation:** V3.1 staleness rejection means truth sensor state will go `unknown` after 2 hours of sensor failure. The release automation should include an explicit condition: if `sensor.<room>_temperature_truth` state is `unknown` or `unavailable`, release boost immediately.

**Required implementation action:** Add `trigger: state → unknown/unavailable` for each truth sensor in the release automation, releasing boost with reason `truth_sensor_unavailable`.

### 10.3 WAF/manual override conflict

**Risk:** Occupant adjusts setpoint while boost is active → manual override timer starts → boost release fires → Section 2 resumes on next tick but boost latch may conflict.

**Mitigation:** The WAF-release trigger in Section 14b fires immediately when `timer.manual_hvac_override` becomes active. Boost latch is cleared. Climate entity command authority returns to the occupant's manual setting. Section 2 will read the WAF-active timer on its next tick and defer. No conflict if the WAF release is the first action in the release sequence.

### 10.4 Samsung internal thermistor bias

**Risk:** Samsung internal sensor reads 2–5°F low. Room truth may reach 67°F while unit still perceives room as 62°F → unit does not self-limit → continues high-output heating.

**Analysis:** This is actually the intended behavior for recovery boost. We want the unit to run at high output until the external truth sensor says stop. The thermistor bias is why we use an external truth cap rather than trusting the unit's own governor. No mitigation needed — this is by design.

**Note:** However, if the thermistor bias causes the Samsung to display `heat@77` and the room feels too warm at 67°F, the truth cap threshold may need to be reduced to 66°F after validation. Mark for monitoring.

### 10.5 Interaction with Section 2's 15-minute tick

**Risk:** Section 2 fires 5 minutes into a boost, overwrites `heat@77` with `heat@68`, reducing Samsung output.

**Analysis:** Without a Section 2 guard, the boost setpoint is overwritten once per 15-minute tick, then re-asserted by Section 14 when the truth sensor crosses below 64°F again. Since the boost engage threshold is 64°F, if the room is at 62°F and Section 2 fires `heat@68`, Section 14's engage trigger may not re-fire (room is still below 64°F, but the trigger was already processed). This could leave the room at `heat@68` for the remainder of the supervisor cycle.

**Mitigation options:**
1. (Preferred in Phase 1) Accept the overwrite and monitor whether recovery still measurably improves. Section 2 will re-issue `heat@68` once — the unit runs at moderate output for up to 15 min, then on the next tick Section 2 would issue the same again. If truth is still below 64°F, Section 14 could re-engage.
2. (Phase 1.5 if needed) Add the single-line latch check to Section 2 heating branches.

**This is the highest-priority open question for the operator to decide before implementation.**

### 10.6 Command spam

**Risk:** Truth sensor hovers near 64°F threshold → engage/release fires repeatedly → multiple commands per minute to Samsung unit → compressor short-cycling.

**Mitigation:** V3.1 truth sensors use lowpass filtering (time_constant=10). Sensor jitter near threshold is smoothed. The latch (`input_boolean`) prevents re-engagement while boost is active. The optional no-repeat cooldown timer (§8.3) prevents rapid re-engagement after release. If implemented without the cooldown timer, monitor for oscillation in the event journal.

### 10.7 All rooms boosting simultaneously

**Risk:** All four rooms drop below 64°F simultaneously on a cold morning → all four mini-splits engage recovery boost simultaneously → full electrical load on all heads → capacity/electrical strain, potential grid brownout on rural service.

**Analysis:** This is a real risk in the Moose House thermal profile. A cold morning after a cold night is exactly when all rooms could be simultaneously below threshold.

**Mitigation options:**
1. **Stagger boost engagement** — add a small per-room delay (e.g., LR immediately, Master 5 min, Lincoln 10 min, Lilly 15 min) using `delay:` in the engage action.
2. **Capacity arbitration** — limit simultaneous active boosts to 2 rooms maximum using a global `input_number` counter. More complex.
3. **Priority-ordered boost** — define a room priority order and only boost the coldest room until it reaches cap, then boost the next. Requires capacity arbitration logic.

**Recommendation:** For Phase 1, **stagger by delay** is the simplest safe approach. Simultaneous boost of 4 Samsung mini-splits is worth quantifying before restricting — the operator has additional context on the electrical service.

**This requires operator input before implementation.**

### 10.8 Energy waste if timeout missing

**Risk:** Timer helper not properly initialized → timer never starts → boost runs indefinitely → unit runs at high setpoint for hours on a warm day.

**Mitigation:** Timer is started in the engage automation action, not via a separate trigger. If the engage action runs successfully, the timer starts. Validate via pre-flight YAML check. The truth cap is always active regardless of timer.

### 10.9 Comfort complaints from overshoot

**Risk:** Boost raises room from 62°F to 68°F → Section 2 turns on cooling in shoulder season → occupant is uncomfortable with temperature overshoot.

**Analysis:** The truth cap (67–68°F) is set at or slightly below the Section 2 heating top-anchor (68°F). There should be no overshoot if the cap is properly set. If cap is set at 68°F and Section 2's off-threshold is 68°F, they coincide — the room reaches comfort exactly as Section 2 would declare it satisfied. If cap is 67°F, boost stops 1°F below Section 2's off-threshold, leaving a brief natural float period.

**Recommendation:** Start with cap at `67°F` to create a 1°F buffer below Section 2's off-threshold. This prevents Section 2 from immediately re-engaging heat after boost stops.

### 10.10 Sensor unavailable/unknown behavior

**Risk:** Truth sensor is in `unknown` or `unavailable` state when engage trigger fires → Jinja template evaluation of truth temp fails → automation errors or issues command with null setpoint.

**Mitigation:** 
- All trigger conditions should explicitly exclude `unknown`/`unavailable` states.
- Condition block should use `float(70)` fallback on truth sensor values — a safe default that would not trigger engagement (70°F > 64°F threshold).
- Add `trigger: state → unknown/unavailable` in release automation as a safety net (§10.2).

---

## 11. Validation Plan

### 11.1 Phase 1: Single-room manual validation (Living Room)

**Step 1 — Pre-flight**
- YAML check: `ha core check` with helpers and Section 14 in place
- Verify all four `input_boolean` helpers visible in HA dashboard
- Verify all four `timer.*_heating_recovery_max_runtime` entities visible
- Confirm `event_journal.csv` is receiving rows from existing Phase 1A automations

**Step 2 — Disable all rooms except LR in Section 14 conditions**
- Use an additional condition in the engage automation: `zone == living_room` (or restrict entity_id list to `climate.living_room_air` only)
- Validate with one room before multi-room expansion

**Step 3 — Manual trigger test**
- Temporarily lower the cold engagement threshold to current room truth + 1°F to force engagement without waiting for a cold morning
- Confirm `input_boolean.lr_heating_recovery_boost_active` turns `on`
- Confirm `timer.lr_heating_recovery_max_runtime` starts
- Confirm `climate.living_room_air` shows `heat@77`
- Confirm `heating_recovery_boost_started` row appears in `event_journal.csv`

**Step 4 — Truth cap stop test**
- Wait for room truth to reach cap threshold (or temporarily lower cap to room truth + 1°F)
- Confirm `input_boolean.lr_heating_recovery_boost_active` turns `off`
- Confirm `climate.living_room_air` is commanded `off`
- Confirm `heating_recovery_boost_stopped_truth_cap` row appears in `event_journal.csv`

**Step 5 — WAF/manual override test**
- While boost is active, manually adjust LR setpoint from HA UI
- Confirm `timer.manual_hvac_override` becomes `active`
- Confirm boost releases immediately
- Confirm `heating_recovery_boost_blocked_waf` row appears in `event_journal.csv`

**Step 6 — Timeout test**
- Set timer duration to 2 minutes for testing
- Engage boost, let timer expire without truth cap firing
- Confirm `heating_recovery_boost_stopped_timeout` row appears in `event_journal.csv`
- Restore timer to 90 minutes

**Step 7 — Real-condition 24-hour run**
- Restore real thresholds
- Run for 24 hours on LR only during heating or shoulder season
- Target monitoring period: a morning with outdoor temp below 40°F

**Step 8 — Pass/fail criteria**

| Metric | Pass Condition |
|---|---|
| Recovery time | LR reaches 67°F in ≤90 min from cold engagement at ≤60°F truth |
| Runtime reduction | Daily runtime hours for LR mini-split measurably lower vs. prior week baseline in VTherm_Launch_Data_v5 |
| No overheating | LR truth never exceeds 70°F without occupant command during validation period |
| Stop condition fires | 100% of boosts stopped by truth cap, not timeout (in normal conditions) |
| Event journal | All boost lifecycle events present; no malformed rows |
| Section 2 continuity | No anomalous behavior in non-LR rooms; Section 2 continues normal heating deadband operation |
| Safety gate dormant | Section 3 ceiling gate does not fire during validation |
| WAF respect | Every manual setpoint change immediately releases active boost |

### 11.2 Multi-room expansion criteria

Only expand to Master, Lincoln, Lilly after:
- LR single-room validation passes all criteria above
- Operator reviews at least 3 days of LR event_journal.csv entries
- Simultaneous boost stagger strategy confirmed (§10.7)

### 11.3 What to compare in VTherm_Launch_Data_v5

- `LR_Air_Action` and `Master_Air_Action` columns: compare daily `heating` action hours before/after boost
- `LR_Temp_Truth` trend: confirm truth reaches target faster during recovery periods
- Look for increased `idle` action hours (indicator that units are stopping sooner)
- Check `Deck_Temp_Truth` on validation days vs. baseline days to control for outdoor conditions

### 11.4 What to watch in event_journal.csv

- Ratio of `stopped_truth_cap` vs. `stopped_timeout` events (want >90% truth cap)
- Any `boost_started` rows with no subsequent `stopped_*` row within 95 minutes (indicates timer failure)
- Time delta between `heating_recovery_boost_started` and `stopped_truth_cap` (expected: 20–60 min for a cold morning recovery)
- Any `boost_blocked_waf` events from unexpected triggers

---

## 12. Rollback Plan

### 12.1 Full rollback (zero impact on existing system)

1. **Disable Section 14 automations** in HA UI (toggle off `v8_4_heating_recovery_boost_engage` and `v8_4_heating_recovery_boost_release`).
2. **Clear any active boost latches** via HA UI: set all `input_boolean.*_heating_recovery_boost_active` to `off`.
3. **Cancel any active boost timers** via HA UI: cancel all `timer.*_heating_recovery_max_runtime`.
4. **Verify climate entities** are in expected Section 2 states on its next 15-minute tick.

No changes to Section 2, Section 3, the event journal, or any existing automation are required. The helpers remain in configuration.yaml but are inert when the automations are disabled.

### 12.2 Partial rollback (per-room)

Disable boost for a specific room by adding a condition to Section 14 automations excluding that room's entity. No other rooms are affected.

### 12.3 If Section 2 guard was added (optional Phase 1.5)

Remove the `condition: state` check for the boost latch from Section 2's heating branch. This is a one-line removal per room — low risk, easily isolated with `git diff`.

### 12.4 Rollback does not affect

- Phase 1A event journal infrastructure
- Section 2 Main Supervisor behavior
- Section 3 safety gates
- Truth sensor weights or V3.1 configuration
- VTherm_Launch_Data_v5 telemetry
- Any other existing automation or helper

---

## 13. Implementation PR Plan

> This section describes the intended scope IF the operator approves implementation.
> No code has been written. This is planning only.

### 13.1 Files likely changed

| File | Change Type | Description |
|---|---|---|
| `configuration.yaml` | Additive only | Add 4 `input_boolean` helpers (§8.1) and 4 `timer` helpers (§8.2) in their respective sections |
| `automations.yaml` | Additive only | Add Section 14 (2 automations: engage + release) after Section 13 Event Journal |

### 13.2 Sections likely added

- `Section 14: Heating Recovery Boost (V8.4)` in automations.yaml
- `input_boolean:` entries for 4 rooms in configuration.yaml
- `timer:` entries for 4 rooms in configuration.yaml

### 13.3 Sections forbidden to touch in this PR

| Section | Reason |
|---|---|
| Section 2 (Main Supervisor) | Core control logic — do not modify in Phase 1 |
| Section 3 (Safety Gates) | Safety systems are not changed |
| Section 12 (Phase 1A Observer) | Observability infrastructure is additive-only |
| `script.log_event` | Existing script called, not modified |
| All truth sensor definitions | V3.1 is frozen |
| All existing timer definitions | Add new timers; do not touch cooldown timers |
| Any existing helpers | Add new; never rename existing |

### 13.4 Validation required before merge

- [ ] `ha core check` passes with all new YAML
- [ ] All 8 new helpers visible and responsive in HA dashboard
- [ ] Manual trigger test (Step 3 of §11.1) passes
- [ ] Truth cap stop test (Step 4 of §11.1) passes
- [ ] WAF conflict test (Step 5 of §11.1) passes
- [ ] Event journal rows confirmed for all 4 boost event types
- [ ] Section 2 continues normal operation with no anomalies
- [ ] Operator sign-off on single-room validation before multi-room expansion

### 13.5 PR commit strategy

Single PR with two commits:
1. `config: add V8.4 heating recovery boost helpers (input_boolean + timer)` — configuration.yaml only
2. `automations: add Section 14 heating recovery boost (V8.4)` — automations.yaml only

This allows bisect/rollback at the helper level independently of the automation level.

---

## 14. Open Questions Requiring Operator Confirmation

Before any implementation PR proceeds, the following require explicit operator decisions:

### Q1 — Section 2 co-existence strategy (HIGH PRIORITY)
Should Phase 1 proceed with zero Section 2 changes (accepting that the 15-minute tick may overwrite `heat@77` with `heat@68` once per cycle), or add the minimal per-room latch check to Section 2 from the start?

**Recommendation:** Start with zero Section 2 changes. If telemetry shows the overwrite is materially reducing recovery effectiveness, add the guard in Phase 1.5.

### Q2 — Simultaneous boost policy
If all four rooms are simultaneously below 64°F (cold morning scenario), should all four boosts engage simultaneously, or should engagement be staggered by room priority?

**Recommendation:** Phase 1 is LR-only, so this is deferred. Before multi-room expansion, operator must decide: stagger delay (simple) or max-simultaneous limit (more robust).

### Q3 — Boost setpoint confirmation
Is `77°F` the correct recovery setpoint, or does operator experience with Samsung mini-split behavior suggest a different value (e.g., `76°F` to be further from the safety ceiling appearance, or `79°F` for maximum demand)?

**Recommendation:** Start at `77°F`. The safety ceiling gate responds to room truth, not setpoint, so there is no mechanical conflict up to 76°F truth. Adjust after observing Samsung output behavior in telemetry.

### Q4 — Truth cap value
Start cap at `67°F` (1°F below Section 2's off-threshold of 68°F) or `68°F` (coincides with Section 2's threshold)?

**Recommendation:** `67°F` to create a 1°F buffer and allow Section 2 to resume cleanly without immediately re-engaging heat.

### Q5 — LR bedtime window interaction
The LR bedtime setpoint reduction (18:00–22:00) passively suppresses stack-effect heat. Should recovery boost be suppressed during this window for LR to avoid fighting the passive reduction strategy?

**Analysis:** If LR truth is below 64°F during the bedtime window, that suggests genuine cold, not just setpoint reduction. However, the operator's intent for that window is to reduce LR heat source competition. A time condition excluding boost during 18:00–22:00 in LR would be a conservative safe choice.

**Recommendation:** Add time condition excluding boost during LR bedtime window (18:00–22:00) in Phase 1. Revisit after seeing whether LR truth actually drops below threshold during that period.

### Q6 — Laundry room
The Laundry room has a truth sensor (`sensor.laundry_temperature_truth`) but was not explicitly listed as a target. Should it be included? Does it have a Samsung mini-split?

**Recommendation:** Operator to confirm Laundry room HVAC entity and whether recovery boost applies there.

### Q7 — No-repeat cooldown
Should a 30-minute no-repeat cooldown be included in Phase 1, or deferred to post-validation based on observed oscillation behavior?

**Recommendation:** Defer to post-validation. Monitor the event journal for rapid engage/release cycles during Phase 1 single-room test.

---

## 15. Safety Assessment

### 15.1 Is this safe to proceed to an implementation PR?

**Yes, with the following conditions:**

1. **Documentation review** — Operator reads and approves this document, confirms open questions Q1–Q6.
2. **Single-room Phase 1 scope** — Implementation PR restricts active boost to LR only for initial validation.
3. **No Section 2 changes** in Phase 1.
4. **Truth-sensor unavailable guard** included in release automation.
5. **Max-runtime timer** included and tested before live deployment.
6. **Validation plan §11** executed in full before multi-room expansion.

The architectural isolation of Option B (Section 14) means that the worst-case failure of the boost layer is a room running `heat@77` until the 90-minute timeout, then going to `off`. Section 3's safety ceiling gate at 76°F truth remains fully active throughout. Section 2 resumes normal authority at most 15 minutes after boost ends.

This is a bounded, reversible, observable change with no structural impact on existing safety or control systems.

### 15.2 Risk classification

| Risk Category | Level | Basis |
|---|---|---|
| Regression to existing control | Low | No existing automation modified |
| Overheating | Low | 9°F margin to safety ceiling; truth cap is primary stop; timer is backup stop |
| WAF conflict | Low | Explicit WAF-release trigger in Section 14b |
| Telemetry disruption | None | Phase 1A journal not modified |
| Rollback complexity | Very Low | Disable Section 14 automations + clear latches |
| Comfort overshoot | Low | 67°F cap is below existing comfort target of 68°F |

**Overall risk rating: LOW — safe to proceed to implementation PR upon operator approval.**

---

*End of V8.4 Design Document*
*Next action: Operator review and Q1–Q7 confirmation before implementation PR.*
