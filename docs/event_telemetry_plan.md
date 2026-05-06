# Event Telemetry Plan (V8.3-Compatible, Observability-Only)

> ## ⚠️ STATUS: RETIRED / ARCHIVAL — DO NOT IMPLEMENT
>
> **Retired:** 2026-05-05 (PR #34 — full removal).
>
> **Why retired:** The Phase 1A implementation in PR #19 failed to register
> `notify.event_journal` on this Home Assistant build. PRs #22, #23, #24, and
> #25 each attempted alternative sinks (`notify.send_message`, `shell_command`
> with `b64encode`, `shell_command` with raw `printf`, restored `notify.file`)
> and each failed. PR #26 contained the failure by converting `script.log_event`
> to a no-op and disabling the Section 12 EJ observers. PR #34 then **permanently
> removed** Section 12, Section 13 (`script.log_event`), and the `script.log_event`
> calls in Section 14. No part of the architecture described below is present in
> the live runtime.
>
> **Current evidence pipeline (use these instead):**
> - **HA Logbook** for state transitions and hand-curated narrative.
> - **`VTherm_Launch_Data_v5`** (Google Sheets, 15-minute snapshot) — the live
>   `automations.yaml` Section 1 telemetry.
> - **`docs/telemetry_confounders.md`** for window classification rules
>   (operator-suppressed vs. clean) before drawing doctrine conclusions.
> - **`docs/postmortems/2026-05-02_event_journal_containment.md`** §6 for the
>   live-spike rules any future sink proposal must satisfy.
> - **Section 11 HVAC Transition Logger** for off ⇄ cool/heat audit trails.
>
> **Do not implement this plan.** Do not re-introduce `script.log_event`,
> `notify.event_journal`, `/config/logs/event_journal.csv`, the Section 12 EJ
> observers, or the Phase 1A `notify.file` configuration without:
> 1. A new live-spike issue that satisfies the postmortem §6 rules,
> 2. Explicit operator approval, and
> 3. A successful proof of `notify.event_journal` (or replacement sink) writing
>    a CSV row on the live HA build before any automation is added.
>
> The document below is preserved as an archival record of the original Phase 1A
> design intent. Schema choices, event-type lists, and rollback procedures are
> historical context, not forward guidance.

---

**Plan Date:** May 1, 2026
**Document Role:** Verification / Observability / Systems-Architecture proposal
**Status:** Draft — planning artifact only. No control changes proposed. Safe to merge as documentation.
**Scope Lock:** Observability layer only. Does not touch Section 2 (Main Supervisor), Section 3 (Safety Gates), Section 6 (Destratification), comfort logic, safety thresholds, V9 pre-chill, entity names, or the existing V5 snapshot pipeline.

---

## 1. Executive Summary

Moose House currently captures a 15-minute snapshot of every room truth, every Samsung head state, every runtime counter, presence, shades, and diagnostic counts (`Section 1: vtherm_mega_tracker_v5` → worksheet `VTherm_Launch_Data_v5`). That snapshot is rich but **strobed**: anything that happens between ticks is invisible unless it survives 15 minutes intact, and the snapshot has no notion of *why* a state is what it is.

The Section 11 HVAC Transition Logger (V8.3) closes part of that gap by writing a Logbook entry on every `off ⇄ cool/heat` transition. That is good but suffers from three structural limits:

1. **Logbook is not a durable CSV** — `recorder.purge_keep_days: 30` evicts it, and Logbook formatting is prose, not structured columns.
2. **Logbook is not exportable to Claude/Gemini/ChatGPT** without screen-scraping.
3. **Logbook only sees device state changes**, not the supervisor's *intent* (which branch decided, what reason, what setpoint was requested vs what the device finally reported), and it sees nothing about WAF/SPI/Samsung-guardrail/season/safety events except as ambient state changes.

This plan proposes a parallel **event journal** — a structured, append-only CSV row per meaningful transition or control intent, written alongside the existing snapshot. It is observability-only, it changes no control authority, it is rollback-trivial, and it produces files that Claude can read forensically without re-deriving causality from a strobed snapshot.

**Why this matters for hidden-state and causal analysis:**

- The supervisor sees instantaneous state, but the relevant physics are integrals. A snapshot every 15 minutes can show a head transitioned from `cool` to `off`, but cannot distinguish *who issued that change*: supervisor branch 1.5, the WAF watcher reacting to a Samsung remote press, the Ceiling Gate, the Sleep Priority Interlock, the Samsung Auto Guardrail, or a cloud delay replaying an old command. These are all materially different stories. The current architecture cannot tell them apart after the fact.
- Doc 1 / §6 already names "deadband memory shortcut" as a known imperfection that "degrades gracefully when device and controller intent diverge between 15-minute ticks." A causal event journal is the only way to *measure* that divergence rather than infer it.
- Doc 4 / §17 explicitly notes that safety backstops fire outside the Section 11 logger and won't show that tag, requiring counts via "filtering HA logbook for these climate state-change signatures, not by tag." That is exactly the friction this plan removes.
- Doc 6 / V9 Observability Principle: "High-frequency internal state, low-frequency external telemetry." This event journal is the *high-frequency internal state* layer that V9 will need to validate event-driven control once it lands.

---

## 2. Current State

### 2.1 What the repo already logs (durable, structured)
- **Snapshot** (`automations.yaml` Section 1, `vtherm_mega_tracker_v5`): every 15 min, ~110 columns, → Google Sheets `VTherm_Launch_Data_v5`. Captures truth, per-source contributors, climate `state`/`hvac_action`/`temperature`/`fan_mode` for every head, runtime hours, presence, shades, truth-count diagnostics.
- **Runtime counters** (`configuration.yaml` Section 11): `history_stats` daily hours of operation per head, plus presence-debounced occupancy hours.

### 2.2 What is only visible in the HA Logbook (not durable, not exportable, not structured)
- **HVAC transition events** (`automations.yaml` Section 11, `v8_3_hvac_transition_log`): one prose `logbook.log` entry on `off ⇄ cool/heat` per head, with room temp / setpoint / outdoor.
- **Recorder-default state-change history** for every entity, governed by `recorder.purge_keep_days: 30`.

### 2.3 What is only visible as a one-off mobile push (`notify.notify`)
- LR runaway cutoff fired (`v8_2_runaway_cooling_cutoff_lr`)
- Master emergency cooling floor fired (`v8_2_master_emergency_floor`)
- Ceiling gate consequences (Section 3 `v7_5_safety_ceiling_gates` — note: the *fan_only/cool* branch fires NO notify; only the heating-branch implicit signal exists)
- Ghost Assassin block (Section 4)
- Auto Season Mode change (Section 5)
- Samsung Auto Guardrail blocks: heat in non-heating season, comfort override, high-setpoint, cool in heating season, overcool (Section 8 — five distinct triggers, all only emit `notify.notify`)
- Truth sensor degraded contributor count (Section 9)

These produce no row anywhere a future LLM analysis can read. They survive in the Companion App push history, which is not a data source.

### 2.4 What is completely invisible after the fact (not even a notify)
- **Supervisor intent / branch selection.** Section 2 `v7_5_main_supervisor` runs every 15 min, picks one of three season branches and one of several sub-branches (sleep window, bedtime LR, away, night-mode-LR-primary, outdoor-cold heating overnight). Nothing records *which branch fired this tick or why*.
- **Per-room supervisor decision.** Each tick decides `cool|heat|off` per head from the deadband-via-mode shortcut (Doc 4 §8, Doc 5 §7.1), then issues `climate.set_temperature` unconditionally. There is no record of "intended mode = X, prior mode = Y, sensor-driven branch entered = Z."
- **Manual override engaged.** `v7_5_waf_manual_override` starts `timer.manual_hvac_override` whenever a setpoint changes from a parent-less context (= human or external app), but produces no event row. We can only infer WAF activations after the fact by scanning Logbook for timer state changes.
- **WAF expiration.** Timer idle transition is invisible to logging.
- **SPI engagement.** `v9_sleep_priority_interlock` forces LR off when Master is cooling and LR is heating. No notify, no logbook entry.
- **Section 6 fan-mode commands.** Destratification engages/disengages `fan_only` per head with no event annotation beyond the device state change.
- **Snapshot-written timestamps.** No event marks "snapshot row N was successfully appended to Sheets."
- **Command-issued vs state-changed latency.** Today, the HA history records when the device state actually changed; nothing records when the supervisor *issued* the command. Cloud lag, Samsung API queueing, and ghost replays are therefore indistinguishable from supervisor decisions.

### 2.5 What is "durable enough for analysis"
- Google Sheets snapshot ✅ (durable, structured, but strobed and supervisor-blind).
- HA Logbook ❌ (purges at 30 days, prose, not exportable).
- Mobile push ❌ (not a data source).
- HA history ⚠️ (durable for 30 days, structured per entity, but requires reconstruction from raw state changes and has no causal annotation).

---

## 3. Proposed Event Journal Schema

Single CSV file with one row per event. Stable header order. Empty string for "not applicable." All times UTC ISO-8601 to avoid DST/timezone reconstruction headaches.

### 3.1 Columns

| # | Column                  | Type   | Notes |
|---|-------------------------|--------|-------|
| 1 | `timestamp`             | iso8601| `now().isoformat()` UTC; one canonical clock |
| 2 | `event_type`            | enum   | See §4 |
| 3 | `entity_id`             | string | Primary entity the event is about (`climate.master_bedroom_air`, `sensor.deck_temperature_truth`, `input_select.hvac_season_mode`, etc.) — empty for system-wide events |
| 4 | `zone`                  | string | `living_room` / `master` / `lincoln` / `lilly` / `house` / `outdoor` / `system` |
| 5 | `old_state`             | string | Prior `states()` value or attribute (mode, setpoint, season, etc.) |
| 6 | `new_state`             | string | Post-event `states()` value or attribute |
| 7 | `requested_mode`        | string | What the supervisor or actor *asked for* (`cool`/`heat`/`off`/`fan_only`/empty) |
| 8 | `requested_setpoint`    | float  | What the supervisor or actor *asked for* in °F |
| 9 | `requested_fan_mode`    | string | `auto`/`turbo`/`low`/empty |
| 10| `actual_mode_after`     | string | Climate entity mode immediately after the action (snapshot at log-time) |
| 11| `actual_setpoint_after` | float  | Climate entity setpoint immediately after the action |
| 12| `actor`                 | enum   | `supervisor` / `safety_gate` / `samsung_guardrail` / `spi` / `waf_watcher` / `season_auto` / `human` / `cloud_replay` / `unknown` |
| 13| `reason`                | string | Short tag, machine-friendly: `deadband_engage_cool`, `runaway_floor_60`, `auto_heat_blocked_wrong_season`, `bedtime_lr_target_64`, etc. |
| 14| `supervisor_branch`     | string | Branch label when actor=supervisor: `cooling.master_sleep`, `cooling.lr_normal`, `shoulder.night_lr`, `heating.day_normal`, `heating.day_lr_primary_night`, `heating.bedtime_lr_64`, etc. Empty otherwise. |
| 15| `season_mode`           | string | `cooling`/`shoulder`/`heating` at log-time |
| 16| `waf_state`             | string | `idle`/`active` (current `timer.manual_hvac_override` state) |
| 17| `manual_override_active`| bool   | Convenience: `true` if `waf_state == active` |
| 18| `source_automation`     | string | `automation.v8_3_main_supervisor`, etc. — `automation_id` of the firing automation when known |
| 19| `correlation_id`        | string | Per-tick UUID for supervisor events (so all per-room rows from one tick share an ID); per-event UUID for one-off triggers. Generated by helper (see §7). |
| 20| `notes`                 | string | Free-text, kept short. Extra context that doesn't fit a column. |

### 3.2 CSV format conventions
- Header line written once on file creation (idempotent — see §9).
- Quoting: minimal, but `notes` and `reason` always wrapped in double quotes; embedded `"` doubled per RFC 4180.
- Newline: `\n` only (Linux). HA OS is Linux.
- Encoding: UTF-8, no BOM.
- One file per UTC day: `/config/logs/event_journal_YYYY-MM-DD.csv`. Daily rotation makes archival, partial loss, and Claude ingestion safer than one giant ever-growing file.

### 3.3 Example rows (illustrative only)

```csv
timestamp,event_type,entity_id,zone,old_state,new_state,requested_mode,requested_setpoint,requested_fan_mode,actual_mode_after,actual_setpoint_after,actor,reason,supervisor_branch,season_mode,waf_state,manual_override_active,source_automation,correlation_id,notes
2026-05-01T17:00:01Z,supervisor_decision,climate.master_bedroom_air,master,cool,cool,cool,63,,cool,63,supervisor,deadband_hold_cool,cooling.master_sleep,cooling,idle,false,automation.v7_5_main_supervisor,a3f1-tick-2026050117,"sleep window 18:00-06:00, master_temp=64.2"
2026-05-01T17:00:01Z,command_issued,climate.master_bedroom_air,master,,,cool,63,,cool,63,supervisor,set_temperature,cooling.master_sleep,cooling,idle,false,automation.v7_5_main_supervisor,a3f1-tick-2026050117,""
2026-05-01T17:00:03Z,hvac_mode_changed,climate.master_bedroom_air,master,cool,cool,,,,cool,63,unknown,device_echo,,cooling,idle,false,,a3f1-tick-2026050117,"latency 2s"
2026-05-01T18:14:22Z,manual_override_detected,climate.living_room_air,living_room,68,71,,71,,cool,71,human,setpoint_change_no_parent,,cooling,active,true,automation.v7_5_waf_manual_override,evt-918a,"WAF timer started, 1h"
2026-05-01T18:42:10Z,samsung_auto_guardrail_corrected,climate.lincoln_air,lincoln,auto,off,off,,,off,68,samsung_guardrail,auto_heat_blocked_room_warm,,cooling,idle,false,automation.v8_samsung_auto_guardrail,evt-c44b,"room=70.1, setpoint=72"
2026-05-01T22:00:00Z,spi_engaged,climate.living_room_air,living_room,heat,off,off,,,off,64,spi,master_cool_lr_heat_contention,,shoulder,idle,false,automation.v9_sleep_priority_interlock,evt-d7e2,"lr_truth=63.8 > 60 floor"
2026-05-02T03:14:11Z,safety_gate_triggered,climate.living_room_air,living_room,cool,off,off,,,off,68,safety_gate,runaway_floor_lr_60,,cooling,idle,false,automation.v8_2_runaway_cooling_cutoff_lr,evt-99aa,"lr_truth=59.4"
```

These rows demonstrate (a) one supervisor tick spawning two rows (decision + command), (b) actual state-change echo with measured latency, (c) WAF-detected human override, (d) guardrail correction, (e) SPI and safety events.

---

## 4. Minimum Viable Event Types

These are the only event types Phase 1 must support. Each maps to existing automations and triggers — nothing new needs to be invented in the control layer.

| Event type | Source today | Phase 1 hook |
|---|---|---|
| `supervisor_decision` | Section 2 (no log today) | Inside Section 2 supervisor, after each branch's per-room `set_temperature`, emit a row. Captures branch + intent. *(Read-only addition to Section 2 — see §6 for safety rules.)* |
| `command_issued` | Section 2 / Section 6 / Section 8 (no log today) | Same hook as above; pair with the `set_temperature`/`set_hvac_mode` call so `requested_*` columns are populated at issue-time. |
| `hvac_mode_changed` | Recorder + Section 11 logbook | New `state` trigger on each `climate.*_air` for any mode change → CSV row. Independent of Section 11; coexists. |
| `setpoint_changed` | Recorder only | New `state` trigger on `temperature` attribute → CSV row. |
| `manual_override_detected` | Section 3 `v7_5_waf_manual_override` (only starts a timer) | Same trigger predicate (`trigger.context.parent_id is none`) → CSV row alongside the existing `timer.start`. |
| `waf_started` | Section 3 (timer started, no log) | `state` trigger on `timer.manual_hvac_override` → `active` → CSV row. |
| `waf_expired` | (no log) | `state` trigger on `timer.manual_hvac_override` → `idle` (when from `active`) → CSV row. |
| `spi_engaged` | Section 3 `v9_sleep_priority_interlock` (no log) | Action append to existing automation: emit row when LR is forced off. |
| `spi_released` | (no log) | Optional: trigger on Master leaving cool while SPI history flag is set. Phase 1 may defer. |
| `season_changed` | Section 5 (notify only) | Action append to existing season switcher: emit row. |
| `samsung_auto_guardrail_corrected` | Section 8 (notify only) | Action append: emit row inside each of the five `choose:` branches with the specific `reason` tag. |
| `safety_gate_triggered` | Section 3 LR runaway, Master floor, ceiling gates (notify-or-silent) | Action append on each. Distinguishes `runaway_floor_lr_60`, `runaway_floor_master_58`, `ceiling_gate_76_<room>`. |
| `telemetry_snapshot_written` | Section 1 (no log) | Action append at the end of `vtherm_mega_tracker_v5`: one row marking successful Sheets append, with `correlation_id` carrying the snapshot row index. Lets us reconcile snapshot N with the events that happened between snapshot N and N+1. |

Optional Phase 2 event types (defer; listed to anchor the schema):
- `truth_count_degraded` (Section 9)
- `ghost_blocked` (Section 4)
- `shade_changed` (Section 7/7B)
- `season_auto_threshold_crossed` (precedes `season_changed` by 2h dwell)
- `precool_latch_toggled` (orphaned; only useful if 3B is reactivated)

---

## 5. Implementation Options

Compared on: durability, blast radius, rollback ease, AI-readability, complexity.

| Option | How it works | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A. `notify.file` integration** | Configure `notify: - platform: file, filename: /config/logs/event_journal.csv`. Each event automation calls `notify.event_journal` with a CSV-formatted message. | Pure HA config, no shell. Append-safe by design. Native to HA. | `notify.file` *prepends a timestamp by default* (config option `timestamp: false` required) and writes one line per call. Header line must be seeded manually. No daily rotation built-in (need second file or template-driven filename — but `filename` is static, not templated, in current HA). | **Recommended for Phase 1** with `timestamp: false`, single growing file, handle rotation in Phase 2. |
| **B. `shell_command` append-to-CSV** | `shell_command.log_event: 'printf "%s\n" {{ row | quote }} >> /config/logs/event_journal.csv'`. | Daily rotation easy via filename template. Works around `notify.file` limits. | HA OS sandbox: shell_command runs in supervised container with limited PATH; quoting templates that contain commas, quotes, and unicode is fragile; risk of newline injection if any column carries `\n`. Each call spawns a shell. | Acceptable, but more failure modes than A. Use only if rotation is required in Phase 1. |
| **C. Local file in `/config/logs/`** | Same target either way; this is *where*, not *how*. | `/config/` is HA's persisted volume; bind-mounted to host on HAOS; survives reboots and supervisor updates. | Must `mkdir -p` once; HA does not auto-create `/config/logs/`. | Use in Phase 1 regardless of A vs B. |
| **D. Google Sheets event tab** | Reuse existing `google_sheets.append_sheet` action with a second worksheet `Event_Journal_v1`. | Zero new infrastructure. Same auth path as snapshots. Same backup/sync as VTherm_Launch_Data_v5. Trivially Claude-ingestible. | Per-event API call adds rate-limit pressure (current pipeline is 96 calls/day; events could be 200–2000/day depending on activity). Network failures lose events silently. Latency ~hundreds of ms per event blocks supervisor mode `single`. | **Recommended as a parallel mirror in Phase 1.** Local file is the source of truth, Sheets is a convenience mirror. |
| **E. MQTT event stream** | Publish each event to `moose_house/events/<event_type>` with JSON payload; broker can persist. | Decouples writer from storage; consumers can subscribe (Node-RED, custom dashboards, future V9 components). | Requires broker (Mosquitto add-on); per-event reliability depends on QoS; another moving part. | Defer to Phase 3 once V9 is real. |
| **F. InfluxDB / Grafana** | Write events as line-protocol points. | Excellent for querying time-series and overlaying with snapshot data. | Significant new dependency; doesn't add anything Claude can easily ingest as CSV. | Defer to Phase 4. |
| **G. TrueNAS as archive/warehouse** | Use TrueNAS only as *downstream* storage: nightly `rsync` (or HA backup, or scheduled SMB copy) of `/config/logs/event_journal_*.csv` to a TrueNAS dataset. | Cleanly separates hot (HA) and cold (TrueNAS) storage. No HA dependency on TrueNAS uptime. Write path stays local, fast, and reliable. | Requires nightly copy job (cron on TrueNAS pulling, or HA shell_command pushing via SSH). | **Recommended as the persistent archive layer**, not as the primary writer. HA never blocks on TrueNAS. |

---

## 6. Recommended Phase 1 (Smallest Safe Implementation)

### 6.1 Goals
- Zero change to control authority.
- Zero change to Section 2 supervisor logic, Section 3 safety thresholds, Section 6 destratification logic, Section 8 Samsung guardrail decisions.
- All event-emitting code lives in **new, separate automations** that *observe existing state changes*. The only existing automations touched are those that emit events solely from their own actions (Sections 5 season, 8 guardrail, 3 SPI, 3 safety) — and even there, the event call is *appended* to the action sequence, never inserted in front of any control or safety action.
- Single file destination: `/config/logs/event_journal.csv` (no rotation in Phase 1; rotation comes in Phase 2 once volume is measured).
- Local file is canonical; Sheets mirror is optional.
- Trivially rollback: delete one new automation file include, restart HA, done.

### 6.2 Phase 1 Scope (Pull list)
1. **Helper additions** (one input_text, one input_number, one counter, one timer — see §7).
2. **`notify.file` configuration** entry pointing at `/config/logs/event_journal.csv` with `timestamp: false`.
3. **One new script `script.log_event`** that takes parameters and calls `notify.event_journal` with the CSV-formatted line.
4. **One new "Section 12: Event Journal Observer" automation set** that subscribes to:
   - Each `climate.*_air` `state` change → `hvac_mode_changed` row.
   - Each `climate.*_air` `temperature` attribute change → `setpoint_changed` row.
   - `timer.manual_hvac_override` → `waf_started` / `waf_expired` rows.
   - WAF detection trigger (mirror of `v7_5_waf_manual_override`'s context-parentless filter) → `manual_override_detected` row. **Does not start the timer**; only logs. Existing Section 3 still owns the timer.
5. **Optional appended actions** in Section 5 (season change), Section 3 (SPI, runaway, master floor, ceiling gates), Section 8 (each guardrail branch) — *each appended at the end* of its existing action sequence, *after* the control action has already run, so an event-write failure cannot prevent a safety action.
6. **Optional appended action** in Section 1 (snapshot writer) — last step writes a `telemetry_snapshot_written` row. Failure does not affect snapshot.
7. **Optional appended actions** in Section 2 supervisor — *deferred to Phase 1.5 by default* because it is the largest surface and the section has the strictest "do not modify" doctrine. The cleanest non-touching alternative for Phase 1 is to *infer* supervisor intent from the per-tick `time_pattern` minutes:00/15/30/45 + climate state-change observation. This loses `supervisor_branch` but preserves every other event type. **If and only if** the operator approves a controlled Phase 1.5 patch to Section 2, the supervisor row gains branch + reason. Until then, `supervisor_branch` stays empty.

### 6.3 Why this ordering
- Steps 1–4 are pure additions: no existing automation is opened.
- Steps 5–6 are append-only edits to existing automation `action:` blocks. The action being appended is a no-op at the control layer (just a script call). Even if the script fails or the file write fails, control already executed.
- Step 7 is intentionally deferred to keep Section 2 untouched in Phase 1, honoring the doctrine "Do not modify Section 2 Main Supervisor behavior."

### 6.4 Rollback procedure
1. Disable the new "Event Journal Observer" automations in HA UI.
2. Remove the appended `script.log_event` calls from Sections 1/3/5/8 (single-line additions; trivially identifiable).
3. Remove the `notify.file` config block, the helpers, and `script.log_event`.
4. Restart HA.
5. `/config/logs/event_journal.csv` remains on disk for archive; can be deleted at leisure.

### 6.5 Optional Phase 1 YAML sketch (illustrative — *do not apply*)

> The following is a sketch only, included per the brief's permission. It is **not** to be merged with this planning doc, and it has not been validated against the running HA instance. The exact per-automation diff lands in a follow-up implementation PR if and only if the operator approves it.

```yaml
# configuration.yaml additions (NEW SECTION 13: EVENT JOURNAL HELPERS)
input_text:
  last_event_correlation_id:
    name: Last Event Correlation ID
    max: 64

counter:
  event_journal_seq:
    name: Event Journal Sequence
    initial: 0
    step: 1

# Append to existing notify: block (or create one if absent).
notify:
  - name: event_journal
    platform: file
    filename: /config/logs/event_journal.csv
    timestamp: false

# scripts.yaml or script: block — NEW
script:
  log_event:
    alias: "Log Event Journal Row"
    mode: parallel
    max: 50
    fields:
      event_type: { description: "see plan §4" }
      entity_id:  { description: "primary entity" }
      zone:       { description: "room or system" }
      old_state:  { default: "" }
      new_state:  { default: "" }
      requested_mode: { default: "" }
      requested_setpoint: { default: "" }
      requested_fan_mode: { default: "" }
      actual_mode_after: { default: "" }
      actual_setpoint_after: { default: "" }
      actor:      { default: "unknown" }
      reason:     { default: "" }
      supervisor_branch: { default: "" }
      correlation_id: { default: "" }
      source_automation: { default: "" }
      notes:      { default: "" }
    sequence:
      - variables:
          ts: "{{ utcnow().isoformat(timespec='seconds') }}Z"
          season: "{{ states('input_select.hvac_season_mode') }}"
          waf: "{{ states('timer.manual_hvac_override') }}"
          waf_active: "{{ 'true' if waf == 'active' else 'false' }}"
          # RFC4180-minimal CSV escape for free-text fields
          q_reason: '"{{ reason | replace(''"'', ''""'') }}"'
          q_notes:  '"{{ notes  | replace(''"'', ''""'') }}"'
      - service: notify.event_journal
        data:
          message: >-
            {{ ts }},{{ event_type }},{{ entity_id }},{{ zone }},{{ old_state }},{{ new_state }},{{ requested_mode }},{{ requested_setpoint }},{{ requested_fan_mode }},{{ actual_mode_after }},{{ actual_setpoint_after }},{{ actor }},{{ q_reason }},{{ supervisor_branch }},{{ season }},{{ waf }},{{ waf_active }},{{ source_automation }},{{ correlation_id }},{{ q_notes }}
```

```yaml
# automations.yaml — NEW SECTION 12: EVENT JOURNAL OBSERVER (does not modify control)
- id: ej_hvac_mode_changed
  alias: "EJ: HVAC Mode Changed"
  mode: parallel
  max: 50
  trigger:
    - platform: state
      entity_id:
        - climate.living_room_air
        - climate.master_bedroom_air
        - climate.lincoln_air
        - climate.lilly_air
  condition:
    - condition: template
      value_template: "{{ trigger.from_state.state != trigger.to_state.state }}"
  action:
    - service: script.log_event
      data:
        event_type: hvac_mode_changed
        entity_id: "{{ trigger.entity_id }}"
        zone: >-
          {% if 'living_room' in trigger.entity_id %}living_room
          {% elif 'master' in trigger.entity_id %}master
          {% elif 'lincoln' in trigger.entity_id %}lincoln
          {% elif 'lilly' in trigger.entity_id %}lilly
          {% else %}unknown{% endif %}
        old_state: "{{ trigger.from_state.state }}"
        new_state: "{{ trigger.to_state.state }}"
        actual_mode_after: "{{ trigger.to_state.state }}"
        actual_setpoint_after: "{{ state_attr(trigger.entity_id, 'temperature') }}"
        actor: unknown
        reason: device_state_change
        source_automation: automation.ej_hvac_mode_changed
```

The full set (setpoint_changed, manual_override_detected, waf_started/expired, spi/safety/guardrail/season hooks, snapshot_written hook) follows the same shape — each one tiny, each one append-only at the control layer.

---

## 7. Required Helpers / Entities

Phase 1 prefers minimum helpers. Final list:

| Helper | Type | Purpose | Required? |
|---|---|---|---|
| `input_text.last_event_correlation_id` | input_text | Stores the most recently-issued correlation_id so per-tick supervisor rows (when Phase 1.5 lands) can share an ID. Also lets templates reference "the current correlation context." | Optional Phase 1, required Phase 1.5 |
| `counter.event_journal_seq` | counter | Monotonic event sequence number for `notes` field or for de-duplication validation. Survives restarts. | Optional |
| `input_text.last_supervisor_branch` | input_text | Last branch the supervisor entered (e.g., `cooling.master_sleep`). Lets observer-side automations attribute mid-tick state changes to a branch. | Optional Phase 1.5 |
| `input_boolean.spi_currently_engaged` | input_boolean | Set by SPI when it forces LR off; cleared when Master leaves cool. Enables `spi_released` event without scanning history. | Optional Phase 2 |

No new climate, sensor, or template entities are required. No existing helpers are renamed or repurposed. No timers other than the existing `timer.manual_hvac_override` and `timer.shade_manual_override` are touched.

---

## 8. Validation Plan

Run in this exact order. Each step is rollback-trivial. Do not advance until the current step passes.

### 8.1 Pre-flight
1. `git checkout claude/setup-verification-observability-nd0yl` (this branch).
2. Confirm working tree clean.
3. Confirm `/config/logs/` exists on the HA host: `ls -la /config/logs/ || mkdir -p /config/logs/`.
4. Snapshot the current `automations.yaml` and `configuration.yaml` so a binary diff after Phase 1 = exactly the appended lines.

### 8.2 YAML/config check
1. In HA UI: **Developer Tools → YAML → Check Configuration**.
2. Expected: "Configuration valid!" with no warnings about `notify.file`, `script.log_event`, or new automations.
3. If any error: revert the offending block, do not proceed.

### 8.3 Reload behavior
1. **Developer Tools → YAML → Reload Notify Services** (or full restart if `notify:` was a new top-level key — `notify` requires a restart on first add).
2. **Reload Helpers** for `input_text`, `counter`.
3. **Reload Scripts** for `script.log_event`.
4. **Reload Automations**.
5. Confirm in **Developer Tools → States** that all new helpers and `script.log_event` are present.

### 8.4 Verify file creation
1. In Developer Tools → Services: call `notify.event_journal` with `message: "test_header_check"`.
2. `cat /config/logs/event_journal.csv` → expect exactly one line: `test_header_check`.
3. If expected: append the canonical CSV header as the first line manually (one-time seed):
   ```bash
   { echo 'timestamp,event_type,entity_id,zone,old_state,new_state,requested_mode,requested_setpoint,requested_fan_mode,actual_mode_after,actual_setpoint_after,actor,reason,supervisor_branch,season_mode,waf_state,manual_override_active,source_automation,correlation_id,notes'; cat /config/logs/event_journal.csv; } > /config/logs/event_journal.tmp && mv /config/logs/event_journal.tmp /config/logs/event_journal.csv
   ```
   Then delete the `test_header_check` line.

### 8.5 Trigger one safe test event
1. In Developer Tools → Services: call `script.log_event` with `event_type: validation_test`, `entity_id: none`, `zone: system`, `actor: human`, `reason: phase1_validation`.
2. `tail -1 /config/logs/event_journal.csv` → expect a row with all 20 columns populated according to schema (most empty), `season_mode` reflecting the current state, `waf_state` reflecting the current timer state.

### 8.6 Confirm row format
1. Open the file in a CSV-aware viewer (or `python -c "import csv; list(csv.reader(open('/config/logs/event_journal.csv')))"`).
2. Validate: 20 columns, header matches §3.1 exactly, no embedded literal newlines in any field, `notes` and `reason` properly quoted.

### 8.7 Confirm no control behavior changed
1. Diff `automations.yaml` against the pre-flight snapshot. Expected diff: only the new Section 12 block + appended `service: script.log_event` lines at the end of Section 1, 3, 5, 8 action sequences. **No edits inside Section 2.** **No threshold changes anywhere.** **No entity renames.**
2. Wait one full supervisor tick (15 min). Verify in HA history that every climate entity that should have received a supervisor command this tick *did* receive one (no missing commands). The supervisor tick should look identical to a pre-Phase-1 tick except for the new event rows in the CSV.
3. Wait for one shoulder-season fan destratification cycle (Section 6) and confirm fan engagements still occur on schedule.
4. Manually change a Samsung head's setpoint via the HA UI (this is a controlled WAF test). Expect: WAF timer starts (existing behavior), AND a new `manual_override_detected` row appears in the CSV (new behavior). Existing notify behavior unchanged.

### 8.8 Sustained-run validation
1. Let it run 24 hours.
2. `wc -l /config/logs/event_journal.csv` — sanity check row count against expected event volume (estimate: 100–600 rows/day during normal operation).
3. Spot-check 10 random rows for column alignment and reasonable values.
4. Cross-reference 3 events against HA Logbook to confirm causal continuity.

---

## 9. Risks and Caveats

### 9.1 HA sandbox / file permissions
- **HAOS:** `/config/` is the persisted volume; HA core runs as the user that owns `/config/`. `notify.file` writes successfully to `/config/logs/` once the directory exists.
- **HA Container / Supervised:** same path semantics apply; ensure the bind mount includes `/config/logs/`.
- **HA Core (bare-metal):** path is whatever the user installed to; substitute accordingly. The plan assumes HAOS, the documented Doc 5 runtime.

### 9.2 Append reliability
- `notify.file` performs an O_APPEND write per call. In Linux, single `write()` calls below `PIPE_BUF` (4096 bytes) are atomic with respect to other appenders, so concurrent rows do not interleave. CSV rows here are well under 4 KB.
- Writes are synchronous from HA's perspective, but HA does not block subsequent automations on the call's return — `script.log_event` runs in `parallel` mode.
- **Risk:** disk-full or filesystem-readonly will silently drop the row. Mitigation: monitor `/config/` free space (HA already exposes `sensor.disk_use_percent_config`); add a Section 9-style alert on `< 10%` free.

### 9.3 Duplicate events
- The Section 11 transition logger and the new `hvac_mode_changed` row both fire on the same trigger. They live in different sinks (Logbook vs CSV) and serve different consumers. The CSV is the authoritative event journal; the Logbook entry is the human-readable reflection. Coexistence is intentional, not a duplication bug.
- WAF: the Section 3 `v7_5_waf_manual_override` automation starts the timer; the new `manual_override_detected` event is *informational* and runs independently. Both fire on the same context-parentless setpoint change. Intentional.
- Within the CSV, true duplicates are possible if HA reloads automations mid-tick. `correlation_id` lets analysis dedupe.

### 9.4 Timestamp consistency
- All event rows use `utcnow().isoformat()`. The existing Sheets snapshot uses `now().strftime('%Y-%m-%d %H:%M:%S')` (local time, no timezone marker). **Phase 1 does not change snapshot formatting.** Cross-source analysis must convert: snapshot times are local civil time; event times are UTC.
- A future Phase 2 cleanup could harmonize both to UTC ISO-8601, but that touches Section 1 and is therefore deferred.

### 9.5 Secrets exposure
- The CSV rows contain no API keys, no tokens, no PII beyond room temperatures and presence flags. Same risk profile as the existing snapshot pipeline.
- **Do not** put `!secret` references in `notes`. Templates expand to plaintext on write.

### 9.6 Recorder/Logbook mismatch
- The CSV will diverge from Logbook over time because Logbook prunes at 30 days while CSV is durable until manually rotated. This is the desired property; do not "reconcile" them.

### 9.7 Mobile-readability and AI-ingestion
- A 20-column CSV at 200–600 rows/day is comfortably under Claude's context limits for a week of forensic analysis (~4 K rows ≈ 400 KB).
- For mobile reading, the file is not human-friendly. Mobile users keep using Logbook + push notifications; the CSV is the *machine* observer.
- Exporting to Sheets as a parallel mirror (Option D) makes the same data sortable/filterable on mobile via the Sheets app.

### 9.8 Sandbox stability of `notify.file`
- The `notify.file` integration is a long-standing core integration. If a future HA breaking change deprecates it, fall back to Option B (`shell_command`).

### 9.9 What this plan does *not* mitigate (intentional)
- It does not measure compressor cycle counts (Doc 6 V9 cooldown territory).
- It does not infer thermal-mass integrals (out of scope; that is Doc 4 territory).
- It does not change the Section 2 supervisor's deadband-via-mode shortcut (Doc 1 §6 known imperfection).
- It does not introduce per-room latches or capacity arbitration (Doc 3 §4.5).
- It does not pre-chill (Doc 6 V9 deferred).

These are deliberate non-goals. Observability first, control changes later, in their own PRs, with this journal as evidence.

---

## 10. Future Path

Once Phase 1 is producing rows reliably, the journal feeds:

### 10.1 TrueNAS archive
- Nightly `rsync` (or HA `shell_command` push, or TrueNAS pull via SMB/SSH) of `/config/logs/event_journal_*.csv` to a TrueNAS dataset under (e.g.) `/mnt/tank/moose_house/event_journal/`.
- TrueNAS handles long-term retention, snapshot-based versioning, and ZFS scrub integrity. HA never depends on TrueNAS being up.

### 10.2 Daily CSV exports
- Phase 2 daily rotation: `event_journal_YYYY-MM-DD.csv` per UTC day.
- Phase 2 also adds a small Section 13 automation that, at 23:59 UTC, copies the day's file to a `staging/` subfolder and creates a fresh empty file with the canonical header for the next day.

### 10.3 Claude / Gemini / ChatGPT forensic analysis
- Drop a day's CSV into Claude with prompt "Reconstruct the causal chain for the LR overcool event at 03:14." Claude can correlate `safety_gate_triggered` rows with the immediately preceding `supervisor_decision` rows, the `command_issued` rows, and the actual `hvac_mode_changed` rows by `correlation_id`.
- This is exactly the workflow Doc 4 §11 asks for ("investigate the controller, do not tune this threshold") — but reduces hours of Logbook scraping to one prompt.

### 10.4 GitHub experiment logs
- A weekly markdown summary committed to `docs/experiments/YYYY-WW.md`, generated by an LLM from the week's CSVs, listing safety events, manual override patterns, supervisor branch distribution, Samsung guardrail interventions. Provides the long-form evidence Doc 4 §15 weekly review questions need.

### 10.5 InfluxDB / Grafana (later)
- Same CSV rows can be tailed into InfluxDB by a small forwarder if and when Grafana dashboards become valuable. The CSV remains the canonical, sandbox-independent ground truth; InfluxDB becomes a derived view, not a source.

### 10.6 V9 migration enabler
- Doc 6 §V9 specifies "decoupled control loops" and "explicit hardware protection" with isolated cooldown timers. Both depend on knowing exactly when the supervisor *issued* a command, when the device *executed* it, and when each cooldown timer started/expired. The Phase 1 journal already records issue-time and state-change time. Phase 1.5 (supervisor_branch annotation) adds the intent layer V9 needs to validate event-driven actuation against the prior tick-driven baseline.
- When V9 lands, the journal becomes the regression-comparability layer: V8.3 vs V9 behavior over the same outdoor weeks is a pure CSV diff, not a re-derivation from snapshot strobes.

---

## Appendix A — Mapping current automations to event rows

| Existing automation | Section | Today's output | Phase 1 event row(s) |
|---|---|---|---|
| `vtherm_mega_tracker_v5` | 1 | Sheets row every 15 min | + `telemetry_snapshot_written` |
| `v7_5_main_supervisor` | 2 | `climate.set_temperature` per head per tick | + `supervisor_decision` + `command_issued` (Phase 1.5) |
| `v9_sleep_priority_interlock` | 3 | LR forced off | + `spi_engaged` |
| `v8_2_runaway_cooling_cutoff_lr` | 3 | LR off + notify | + `safety_gate_triggered` (reason=`runaway_floor_lr_60`) |
| `v8_2_master_emergency_floor` | 3 | Master off + notify | + `safety_gate_triggered` (reason=`runaway_floor_master_58`) |
| `v7_5_safety_ceiling_gates` | 3 | Cool/fan_only + 45-min off | + `safety_gate_triggered` (reason=`ceiling_gate_76_<room>`) at engage and disengage |
| `v7_5_waf_manual_override` | 3 | Timer start | + `manual_override_detected` + `waf_started` |
| (timer.manual_hvac_override → idle) | n/a | (no current log) | + `waf_expired` |
| `v7_5_ghost_assassin` | 4 | Off + notify | (Phase 2: `ghost_blocked`) |
| `v7_5_auto_season_mode` | 5 | Season change + notify | + `season_changed` |
| `v8_comfort_fan_destratification` | 6 | fan_only on/off | (covered by `hvac_mode_changed`) |
| Shade automations | 7/7B | Tilt commands | (Phase 2: `shade_changed`) |
| `v8_samsung_auto_guardrail` (5 branches) | 8 | Off + notify | + `samsung_auto_guardrail_corrected` (5 distinct `reason` values) |
| `v8_truth_count_alert` | 9 | Notify | (Phase 2: `truth_count_degraded`) |
| `v8_3_hvac_transition_log` | 11 | Logbook prose | (covered by `hvac_mode_changed` — coexistence intentional) |

---

## Appendix B — Files this plan does *not* touch

Per the brief's hard scope lock, this plan does not propose changes to:
- `automations.yaml` Section 2 (Main Supervisor) — comfort logic untouched.
- `automations.yaml` Section 3 thresholds (60°F, 58°F, 76°F) — safety thresholds untouched.
- `automations.yaml` Section 6 destratification deltas (3.0°F engage, 1.0°F + 2700 s disengage) — comfort logic untouched.
- `configuration.yaml` truth weights, smoothing time_constant, staleness thresholds, recorder retention.
- `AGENTS.md` doctrine — no edits required.
- Entity names anywhere.

Phase 1 implementation, when authorized, will only add:
- New `notify:` entry, new helpers, new `script.log_event`, new "Section 12 / Event Journal Observer" automation block.
- Append-only `service: script.log_event` calls at the *end* of action sequences in Sections 1 (snapshot), 3 (SPI/runaway/floor/ceiling/WAF), 5 (season), 8 (Samsung guardrail). No control behavior changes.
