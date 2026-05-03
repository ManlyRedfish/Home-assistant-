# Postmortem — Event Journal Sink Failure & V8.4 LR Boost Preservation

**Incident Date:** 2026-05-02 (evening session)
**Author Role:** Senior Systems Reviewer
**Document Role:** Postmortem + tomorrow plan
**Status:** Containment confirmed. No code PR required tonight.
**Scope Lock:** Documentation only. No runtime config or automation changes.

---

## 1. Executive Summary

### What happened
Tonight's deployment attempted two coupled changes:
1. Phase 1A Event Journal infrastructure (per `docs/event_telemetry_plan.md`).
2. The V8.4 LR-only Heating Recovery Boost pilot (per `docs/v8_4_heating_recovery_boost_plan.md`).

The event journal sink never came up on the live HA runtime. Five sequential fix attempts (PRs #22–#25) failed. PR #26 contained the failure by collapsing `script.log_event` into a safe no-op and disabling the five Section 12 EJ observers at the automation level (`initial_state: false`).

### What was contained
- The failing event-journal sink. No automation now writes to disk, to a notify integration, or to a shell command for telemetry.
- All five Section 12 EJ observers are off and inert.
- `script.log_event` is preserved as a callable no-op so any caller (Section 14, future appended hooks) returns success without I/O.
- No HA reload or restart is required to keep containment in place.

### What remains working
- Section 1 telemetry pipeline → `VTherm_Launch_Data_v5` (Google Sheets snapshot every 15 min).
- Section 2 Main Supervisor (V8.3 deadband control).
- Section 3 Safety Gates (LR runaway 60°F, Master floor 58°F, ceiling gates 76°F, SPI, WAF watcher).
- Section 11 HVAC Transition Logger (Logbook).
- Section 14 V8.4 LR Heating Recovery Boost engage/release automations. They call `script.log_event` and the no-op stop returns success — the boost itself is uncoupled from event-journal viability.
- Truth sensors and V3.1 truth-layer math.
- All comfort and safety thresholds.

### What remains disabled
- `automation.ej_hvac_mode_changed`
- `automation.ej_setpoint_changed`
- `automation.ej_manual_override_detected`
- `automation.ej_waf_started`
- `automation.ej_waf_expired`
- The conceptual notion of `notify.event_journal` as a registered service — it never registered, and nothing in the live config currently attempts to register it.

---

## 2. Timeline (PRs #18–#26)

| PR | Intent | Outcome |
|----|--------|---------|
| **#18** | Add `docs/event_telemetry_plan.md` (Phase 1A planning artifact). | Documentation merged. No runtime impact. |
| **#19** | Implement Phase 1A: helpers, `notify.file` config, `script.log_event`, five Section 12 EJ observers. | Merged. Live runtime: `notify.event_journal` did not register. `script.log_event` failed at call-time with `Action notify.event_journal not found`. |
| **#20** | Add `docs/v8_4_heating_recovery_boost_plan.md` (V8.4 design). | Documentation merged. No runtime impact. |
| **#21** | Implement Section 14 LR-only V8.4 Heating Recovery Boost (engage + release, helpers). | Merged. Boost logic structurally correct, but observers and the `script.log_event` call still tied to the broken sink. |
| **#22** | Switch `script.log_event` to `notify.send_message` to work around `notify.event_journal` not registering. | Failed: `notify.send_message` is not the right API surface for a configured notify platform; service-style call signature was incompatible. |
| **#23** | Replace notify entirely with a `shell_command` writer using `b64encode` to safely escape the CSV payload. | Failed: `TemplateAssertionError: No filter named 'b64encode'` — Jinja2 in HA does not ship the `b64encode` filter. |
| **#24** | Drop `b64encode`; use `shell_command` with raw `printf`. | Failed silently: file was never created on the live HA OS. The shell_command path either did not run as expected in the supervised container or the redirect target was unreachable in the runtime sandbox. |
| **#25** | Restore the Phase 1A `notify.file` / `notify.event_journal` configuration. | Failed: `Action notify.event_journal not found` after a full restart — the integration still did not register on this HA build, repeating the PR #19 failure mode. |
| **#26** | Containment: convert `script.log_event` to a safe no-op (`sequence: - stop:`); set `initial_state: false` on all five EJ observers; document the failure history in the Section 13 header. | Merged. Containment is live. `script.log_event` is callable as “Log Event (no-op)” and returns without error. Section 14 LR boost continues to call it harmlessly. |

---

## 3. Root Cause

The incident has four distinct layers. Distinguishing them is essential to avoid re-litigating the wrong one tomorrow.

### 3.1 Intended event-journal design (sound)
The design in `docs/event_telemetry_plan.md` is internally coherent: append-only CSV, observability-only, append-at-end semantics, explicit non-touching of Sections 2/3/6. The schema, the event-type list, and the rollback procedure are all defensible. **The plan is not the problem.**

### 3.2 Failed live runtime assumptions
- Assumption that `notify.file` would register on this HA build. It did not.
- Assumption that absence in **Developer Tools → States** would be conclusive evidence about a service. It is not — services and entity states are different surfaces.
- Assumption that the documented HA notify/file integration is uniformly available across HA versions and HAOS variants. It clearly is not on this instance.
- Assumption that `b64encode` would be present in the HA Jinja2 environment. It is not in the default filter set.
- Assumption that `shell_command` with a raw redirect would land a file in `/config/logs/`. Whether due to sandboxing, working directory, or the integration’s execution semantics, the file was never created.

### 3.3 Wrong fix attempts
- **PR #22** swapped `notify.event_journal` for `notify.send_message`. That conflated two different service families and never had a chance of writing CSV to disk.
- **PR #23** introduced `b64encode` without verifying the filter exists in the live Jinja2 environment.
- **PR #24** removed `b64encode` but did not validate the more fundamental question — was the shell_command path actually executing and writing? It was not.
- **PR #25** restored the original `notify.file` approach without new evidence about why it failed in #19. Repeating the same approach against the same runtime produced the same failure.

The pattern is **stacked speculative fixes during a live debugging loop, without a minimal live proof between attempts.**

### 3.4 Final containment
PR #26 stopped the loop. The chosen containment is structurally sound:
- `script.log_event` becomes a no-op so existing callers (Section 14) succeed silently.
- All EJ observers are disabled at the automation level (`initial_state: false`), so even an inadvertent reload cannot run them.
- No `notify:` block, no `shell_command:` writer, no file path is referenced as a live target.
- Section 13 carries a header comment that records why the sink is off, so the next session does not “discover” the problem fresh.

---

## 4. Live Runtime Findings

These are the empirical signals from tonight that future sessions must treat as authoritative.

### 4.1 `notify.event_journal` did not register
After PRs #19 and #25, with restart, the `notify.event_journal` service was not callable. `script.log_event` raised `Action notify.event_journal not found` when invoked. This is the central failure.

### 4.2 Absence in **States** is insufficient evidence
Earlier in the loop, “not visible in Developer Tools → States” was treated as the diagnostic. It is not. The notify platform exposes a service (action), not a state entity. A correctly-registered notify integration may show no state row while still working — and a mis-registered one shows no state row and **also fails when called**. The conclusive test is service execution: **Developer Tools → Actions → call `notify.event_journal` with a one-line message → confirm a CSV row appears**. That step never passed tonight.

### 4.3 Service execution failed (the real evidence)
Calling `script.log_event` returned `Action notify.event_journal not found`. Calling `notify.event_journal` directly produced the same outcome. Service-level evidence is what matters. State-level absence is not.

### 4.4 `b64encode` filter is missing
PR #23 produced `TemplateAssertionError: No filter named 'b64encode'`. The default HA Jinja2 environment does not include this filter. Any future shell-based writer must use a different escape strategy (single-quoted heredocs, `replace` chains, or a hand-rolled CSV escape in pure Jinja2).

### 4.5 Shell command write attempt produced no file
PR #24 used `shell_command` + `printf` with a redirect. No file appeared in `/config/logs/`. Possible causes (none verified tonight): supervised-container path semantics, working directory not being `/config/`, missing parent dir, or output redirect not honored under the `shell_command` integration on this build. **This is unresolved and must be diagnosed live before any retry.**

### 4.6 Containment no-op works
Post-PR #26, calling `script.log_event` from Developer Tools → Actions returns success cleanly. Section 14’s engage and release sequences include `action: script.log_event` calls; those calls now return success rather than raising. The boost path is unblocked.

---

## 5. What Stayed Safe

Verified untouched by tonight's incident and PR #26:

- **Section 2 Main Supervisor** — V8.3 comfort-first deadband logic, all branches, all per-room `set_temperature` calls. Untouched.
- **Section 3 Safety Gates** — LR runaway cutoff at 60°F, Master emergency floor at 58°F, ceiling gates at 76°F, Sleep Priority Interlock, WAF watcher / `timer.manual_hvac_override`. Untouched.
- **Section 14 V8.4 LR Heating Recovery Boost** — engage/release automations, `input_boolean.lr_heating_recovery_boost_active` latch, `timer.lr_heating_recovery_boost_max_runtime`, 77°F setpoint, 67°F truth cap, 90 min hard timeout, WAF release, season-change release, truth-unavailable release. Untouched.
- **Truth sensors and V3.1 layer** — staleness rejection, outlier handling, multi-sensor fusion. Untouched.
- **VTherm_Launch_Data_v5 telemetry** — Section 1 `vtherm_mega_tracker_v5`, Sheets append, all ~110 columns, 15-minute cadence. Untouched.
- **Climate control as the source of truth** — every HVAC decision still flows through Section 2 (comfort), Section 3 (safety), and Section 14 (LR boost) via the climate entities themselves. Event logging never had control authority and is not on the dependency path of any control decision.

The containment posture explicitly preserves the doctrine in Doc 1: *Live YAML outranks prose for runtime truth*, and *Comfort logic and safety logic are separate on purpose*. Neither was disturbed.

---

## 6. Anti-Regression Notes

Add these to the engineering memory layer. Each is a rule, not a suggestion.

1. **Observability must not destabilize control.**
   The event journal is a verification layer. If it cannot be made reliable on the live runtime, it stays off. Control logic must never depend on event-logging viability — and tonight it did not, which is the only reason containment was clean.

2. **Do not re-enable EJ observers until a sink is proven live.**
   The five Section 12 observers stay at `initial_state: false` until **a single end-to-end live proof passes**: a manual call to a new candidate sink writes a real row to a real persistence target, observed in two consecutive sessions across an HA restart. No exceptions.

3. **Do not try another sink without a minimal live proof first.**
   Before any next-sink PR is opened, run a one-line spike against the candidate sink (e.g., a single Developer Tools call that writes one byte). Only after that spike succeeds twice should YAML changes be proposed. This is the rule that PRs #22–#25 violated.

4. **Do not use Developer Tools → States to validate a service or action.**
   Services live in **Developer Tools → Actions**. The conclusive test for a notify integration is calling its service and observing the persistence target change. Treat State-panel absence as inconclusive.

5. **Do not stack speculative fixes during a live HA debugging loop.**
   PRs #22, #23, #24, #25 each layered a new mechanism on top of an unproven previous one. The correct loop is: **revert to last-known-good, isolate the failing layer, add one piece of evidence, then propose one fix.** PR #26 is now the last-known-good; future work starts from that point.

6. **Capture HA build/version evidence before assuming an integration is available.**
   `notify.file` is documented but did not register on this build. Any future sink proposal must record: HA Core version, supervisor version, HAOS version, and a citation of the integration’s availability on that exact stack. If documentation says “use this integration” but the live build does not register it, **the live build wins.**

7. **Containment artifacts are load-bearing.**
   The Section 13 header comment, the no-op `script.log_event`, and the `initial_state: false` flags together encode the containment. Do not remove or “tidy” any of them in passing — they exist precisely so the next session does not retry a known-broken approach.

---

## 7. Tomorrow Morning Checklist

Run these in order. Each step is short. Do not advance until the prior step is green.

1. **Check HA logs for new errors.**
   Settings → System → Logs. Filter for `ERROR` and `WARNING` since last restart. Specifically scan for:
   - `Action notify.event_journal not found` (should be absent — no caller still references it)
   - `script.log_event` errors (should be absent — no-op returns cleanly)
   - Any Section 14 errors on engage/release.

2. **Confirm EJ observers remain off.**
   Settings → Automations & Scenes → filter for `EJ:`. All five (`EJ: HVAC Mode Changed`, `EJ: Setpoint Changed`, `EJ: Manual Override Detected`, `EJ: WAF Started`, `EJ: WAF Expired`) must show **disabled / off**. If any is on, disable it before touching anything else.

3. **Confirm `script.log_event` no-op still returns success.**
   Developer Tools → Actions → `script.log_event`. Submit any trivial payload. Expected: success, no error, alias displays as **“Log Event (no-op)”**. If it errors, stop and investigate before any other work.

4. **Confirm VTherm Sheets telemetry still updates.**
   Open `VTherm_Launch_Data_v5`. Verify the most recent row timestamp is within the last 20 minutes and matches normal column population. The snapshot is independent of EJ; if it has stalled, the cause is in Section 1 or the Sheets credential, not in tonight's incident.

5. **Confirm Section 2 supervisor runs normally.**
   In HA Logbook, scope to the four `climate.*_air` entities for the last 60 minutes. Expect to see the periodic 15-minute supervisor activity (set_temperature commands or steady state on each head consistent with current season and truth temps). No unexpected `off` storms, no rapid mode flips.

6. **Confirm LR boost automations are enabled and not erroring.**
   Settings → Automations & Scenes → `V8.4: LR Heating Recovery Boost Engage` and `V8.4: LR Heating Recovery Boost Release`. Both must be **enabled**. Open each → **Traces** → confirm last trace (if any) ran without exception. The `script.log_event` call inside should show as a successful step.

7. **Watch for LR boost engage/release if conditions occur.**
   If LR truth drops below 64°F during heating/shoulder season today and WAF is idle and away_mode is off, the boost should engage:
   - `input_boolean.lr_heating_recovery_boost_active` flips to `on`
   - `timer.lr_heating_recovery_boost_max_runtime` becomes `active`
   - `climate.living_room_air` shows `heat @ 77°F`
   Release should fire on truth ≥ 67°F (truth cap), 90 min timeout, WAF activation, season change, or truth sensor unavailable. Verify each leg in Logbook + Sheets when a real event occurs. **See Section 9 for the full validation plan.**

### Top 5 checks (executive summary of the above)
1. HA logs clean since last restart.
2. All five EJ observers disabled.
3. `script.log_event` no-op returns success.
4. Sheets telemetry updating on the 15-min cadence.
5. Section 14 LR boost automations enabled and trace-clean.

---

## 8. Event Journal — Future Options (do not implement tonight)

Listed for future evaluation only. Each option is one row of a decision matrix, not a plan.

| # | Option | Pro | Risk |
|---|--------|-----|------|
| 1 | **Google Sheets event tab** (second worksheet on the existing `VTherm_Launch_Data_v5` spreadsheet) | Reuses an integration that is already proven live on this stack — same auth, same backup, same Claude-readability as the existing snapshot. Zero new infrastructure. | Per-event API call adds rate-limit pressure (snapshots are 96/day; events could be 200–2000/day). Network failure silently drops events. |
| 2 | **InfluxDB add-on** | Designed for time-series; native Grafana overlay with snapshot data; durable on HAOS volumes. | Significant new dependency; not natively CSV/Claude-friendly; another moving part to keep alive across HA upgrades. |
| 3 | **MQTT event topic** (Mosquitto add-on) | Decouples writer from storage; future V9 components can subscribe; broker can persist with QoS. | Requires broker uptime; per-event reliability depends on QoS configuration; introduces another integration on the failure path. |
| 4 | **AppDaemon / pyscript file writer** | Bypasses HA notify/shell sandbox issues entirely; full Python access to filesystem; trivial to test in isolation. | New runtime add-on with its own version skew and update cadence; the writer becomes a separate process to monitor; shifts complexity rather than removing it. |
| 5 | **TrueNAS-side collector** (HA pushes via SSH, or TrueNAS pulls via HA REST API) | HA never blocks on the writer; long-term storage isolated from the control plane; ZFS provides snapshot/rollback for free. | Requires SSH key management or a pull job; if the network or the NAS is down, events are lost or queued; cross-host failure modes are harder to reason about. |
| 6 | **Custom HA integration** (pip package or local component implementing a `event_journal` service) | Total control over the schema and the failure semantics; can be unit-tested outside HA. | Highest engineering cost; must track HA breaking changes; review/maintenance burden falls on this household. |

**Selection criteria for whichever option is chosen next:**
- The option must be provable with a single live spike (one byte written and observed) before any YAML lands.
- It must be runnable from inside HA without depending on a service that did not register tonight.
- It must degrade silently — if the sink is down, control is unaffected.
- It must produce data that Claude / Gemini / ChatGPT can ingest without re-derivation.

The Google Sheets event-tab option (Option 1) is the most attractive starting point because the underlying integration is already known to work on this exact runtime — but no decision is needed tonight.

---

## 9. V8.4 LR Boost Validation Plan (event-journal-free)

Because the event journal is contained, validation must rely on the evidence sources that **are** known good on this runtime. The full V8.4 design plan’s pass/fail criteria still apply (`docs/v8_4_heating_recovery_boost_plan.md` §11.1 Step 8), but the evidence pipeline is reduced.

### 9.1 Evidence sources (in priority order)

1. **HA Logbook** — durable for 30 days (per recorder default). Captures every climate state/setpoint change, every `input_boolean` toggle, every timer state, every automation run. This is the primary forensic source while the event journal is off.
2. **VTherm_Launch_Data_v5 (Google Sheets)** — 15-minute snapshots of LR truth, LR setpoint, LR mode/action, LR HP runtime hours, outdoor temp, presence, season. This is the primary trend source.
3. **Manual timestamps** — operator notes in a scratch file or sheet for any event observed live (engage time, release time, perceived comfort response). Treat these as the ground-truth annotations the event journal would have produced.
4. **`sensor.living_room_temperature_truth`** — read live from Developer Tools → States or from a dashboard card.
5. **`climate.living_room_air`** attributes — `temperature` (setpoint), `hvac_mode`, `hvac_action`.
6. **`input_boolean.lr_heating_recovery_boost_active`** — primary latch. Logbook records every transition.
7. **`timer.lr_heating_recovery_boost_max_runtime`** — start, finish, cancel events all in Logbook.
8. **Section 14 automation traces** — Settings → Automations → each automation → Traces. Traces preserve recent invocations with full step-by-step detail.

### 9.2 Validation procedure for a single boost cycle

When LR truth drops below 64°F during heating/shoulder season, capture the following evidence chain:

| Phase | What to capture | Source |
|-------|-----------------|--------|
| Pre-engage | LR truth value, LR setpoint, LR mode/action, outdoor temp, season, WAF timer state, away mode | Sheets row + Developer Tools → States, manual timestamp |
| Engage trigger | Time `input_boolean.lr_heating_recovery_boost_active` flipped on; time `timer.lr_heating_recovery_boost_max_runtime` became active; time `climate.living_room_air` setpoint changed to 77 and mode to heat | Logbook (filter on these three entities), Section 14 engage trace |
| During boost | LR truth trajectory at each Sheets tick; LR mode/action; LR HP runtime delta | Sheets rows during the boost window |
| Release trigger | Which trigger fired (`truth_cap`, `timeout`, `waf`, `season_change`, `truth_unavailable`); time latch flipped off; time setpoint/mode reverted | Section 14 release trace (`trigger.id` is captured), Logbook |
| Post-release | LR truth at release; time to next Section 2 tick; whether Section 2 reissued heat at 68°F or held off; comfort response | Logbook + Sheets + manual note |

### 9.3 Pass/fail criteria

The criteria below are a reduced subset of the full V8.4 plan §11.1, scoped to evidence available without an event journal:

| Metric | Pass condition | Source |
|--------|----------------|--------|
| Recovery time | LR truth reaches 67°F within ≤90 min of engage | Sheets + Logbook |
| Stop-condition fires correctly | 100% of release traces show a recognizable `trigger.id`; no boost runs to silent timeout in normal conditions | Section 14 release traces |
| No overheating | LR truth stays below 70°F absent occupant command | Sheets |
| Section 14 isolation | Section 2 tick during a boost does not break LR comfort or safety; ceiling gate at 76°F never fires | Logbook |
| WAF respect | Manual setpoint change while boost is active immediately flips latch off and the release trace shows `trigger.id == 'waf'` | Logbook + release trace |
| Section 2 continuity | Other rooms (Master, Lincoln, Lilly) show normal V8.3 deadband behavior throughout | Logbook + Sheets |

### 9.4 Cross-source reconciliation

Without `correlation_id`, reconciling Sheets snapshots with Logbook events requires manual time-window joining. Recommended approach:
- Round each Sheets row to its 15-minute timestamp.
- For each boost cycle, list the Logbook events between snapshot N and N+1 in chronological order.
- Annotate manually in a scratch tab. This is tedious but tractable for a single LR pilot.

This is precisely the friction the event journal was designed to eliminate. Accept the friction tonight; do not attempt to rebuild the journal on the strength of how annoying the manual reconciliation feels.

### 9.5 Validation duration

Per the V8.4 plan, the LR-only Phase 1 validation needs at least one cold morning with outdoor < 40°F and at least 24–72 hours of continuous run. Continue to **leave Master, Lincoln, and Lilly out of scope** until LR validation passes its criteria with operator sign-off.

---

## 10. Final Recommendation

1. **Leave the event journal contained.** No code change, no automation toggle, no helper edit tonight or tomorrow. The Section 13 header, the no-op `script.log_event`, and the `initial_state: false` flags stay exactly as PR #26 left them.

2. **Do not attempt another sink until after live HA documentation and runtime research.** Before opening any next-sink PR, gather: HA Core / supervisor / HAOS versions, a confirmation of which file/notify/shell integrations register on this exact stack, and a single-line live spike that proves the candidate sink writes one byte to one persistence target. Two consecutive sessions across an HA restart must observe the spike persist.

3. **Validate LR boost first.** The V8.4 LR pilot is the only behavioral change tonight that affects HVAC. Use HA Logbook + `VTherm_Launch_Data_v5` + Section 14 traces + manual timestamps (per Section 9 above) to build the evidence base for whether the 77°F demand setpoint and 67°F truth cap actually reduce LR runtime and improve recovery. Defer multi-room expansion until LR alone passes the pass/fail criteria.

4. **Use Sheets + Logbook as the evidence base for the next 24–72 hours.** Treat them as the canonical observability layer for now. The event journal can return — or be replaced by Option 1 (Sheets event tab) — only after the live spike requirement above is satisfied.

### Critical safety findings: **None.**
- Section 2 untouched, Section 3 untouched, Section 14 untouched.
- No control path depends on the event journal.
- The no-op `script.log_event` returns success, so the only side-effect of containment on Section 14 is the loss of forensic event rows — not the loss of boost behavior.

### Code PR needed now: **No.**
This is documentation only. The runtime is in a known-good, contained state. Tomorrow's actions are observation and validation, not implementation.

---

*End of postmortem.*
