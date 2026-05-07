# HVAC Provenance Logger — Adopted / Implemented (Issue #66)

**Doc Date:** 2026-05-07
**Document Role:** Design + acceptance record for issue #66 (automatic
operator provenance logging for manual HVAC changes).
**Status:** Adopted / Implemented. Section 15 of `automations.yaml` now
contains the `v8_5_hvac_provenance_logger` automation that fulfills this
design. Implementation PR: "Add v8.5 HVAC provenance logger (issue #66) —
observability-only, narrow first pass".
**Scope Lock:** The implementation pass added exactly one new section
(Section 15) to `automations.yaml` and four new tests in
`tests/test_provenance_observability.py`. It did not modify
`configuration.yaml`, helpers, ESPHome, thresholds, Section 2 supervisor
behavior, Section 3 safety gates, or Section 14 boost behavior. It did not
promote any annotation/provenance data into a control loop input. Issue #49
remains open.

---

## 1. Purpose

Issue #66 asks for an **observability-only** mechanism that automatically
records whether key HVAC state/setpoint changes look user/manual,
automation/script-driven, or integration/system-originated, so that the
forensic surface used by `supervisor_state_log` (#50) is no longer
manual-entry only. Manual rows are not compatible with the set-and-forget
goal.

Home Assistant state-change triggers expose
`trigger.to_state.context.user_id`, `trigger.to_state.context.parent_id`,
and `trigger.to_state.context.id`. The Section 3 WAF watcher
(`v7_5_waf_manual_override`) already uses
`trigger.context.parent_id is none` to detect operator nudges and start
`timer.manual_hvac_override`. That precedent confirms HA context metadata
is reliable enough on this stack — including the Samsung climate entities
— to power a separate, write-only provenance tab.

This doc plans that logger. It does **not** add it.

## 2. Why machine provenance lives next to, not inside, `supervisor_state_log`

`supervisor_state_log` is the human narrative annotation surface adopted
in #50 (`docs/operator_annotation_design.md` §4.0,
`docs/telemetry_confounders.md` §6). Its schema is interval-shaped
(`start_local`, `end_local`, `kind`, `note`, `created_at`) and its rows
are author-of-record context that the analyst trusts as ground truth.

The provenance stream is event-shaped (one row per HA state change), is
machine-generated, and uses a different vocabulary (`origin_kind` vs.
`kind`). Mixing the two in a single tab would:

- pollute the human-curated row set with high-frequency machine rows,
- conflate `kind = manual_setpoint_nudge` (human's claim about what
  happened) with `origin_kind = manual_user` (HA's classification of the
  context that produced the state change),
- make the operator's append flow brittle (a human typing into a sheet
  that automation is also writing into is a recipe for row collisions),
- make join semantics ambiguous (interval-overlap vs. point-event).

The recommendation is therefore to use a **new sibling tab**,
`hvac_provenance_log`, in the same Google Sheets workbook. The two tabs
remain joinable by time and entity, while preserving:

1. `supervisor_state_log` as the human annotation surface (read-only from
   HA's perspective; written only by operators).
2. `hvac_provenance_log` as the machine event surface (write-only from
   HA's perspective; never read back by HA).

Both tabs remain forensic output. Neither is ever consumed by Section 2,
Section 3, Section 14, truth-sensor math, or any other control surface.

## 3. Current relevant inventory

### 3.1 Automations that already reference these entities

| Automation `id`                              | Entities of interest                          | Why relevant to #66                                                                                          |
| -------------------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `vtherm_mega_tracker_v5`                     | All four climate entities, Section 14 helpers | The proven Google Sheets sink (`google_sheets.append_sheet` + `!secret google_sheets_config_entry`). Pattern to mirror. |
| `v7_5_main_supervisor`                       | All climate entities, `timer.manual_hvac_override` | Must not be touched. Reads `manual_hvac_override` as a gate.                                          |
| `v7_5_waf_manual_override`                   | All four climate entities (`temperature` attr) | **Validates `trigger.context.parent_id is none` works on this stack.** Starts `timer.manual_hvac_override` when an operator nudges a setpoint. |
| `v8_3_hvac_transition_log`                   | All four climate entities (state changes)     | Logbook-only diagnostic logger. Provenance logger should mirror its `mode: parallel, max: 20` shape.         |
| `v8_4_lr_heating_recovery_boost_engage`      | `climate.living_room_air`, `input_boolean.lr_heating_recovery_boost_active`, `timer.lr_heating_recovery_boost_max_runtime` | Boost path. Must not be touched. Provenance logger will *observe* its writes, not modify it. |
| `v8_4_lr_heating_recovery_boost_release`     | Same                                          | Same.                                                                                                        |
| `v8_2_runaway_cooling_cutoff_lr`             | `climate.living_room_air`                     | Section 3. Must not be touched.                                                                              |

### 3.2 Entities relevant to the first pass

- `climate.living_room_air` — state (`heat`/`cool`/`off`) and `temperature` attribute.
- `timer.manual_hvac_override` — UI-defined helper (not declared in `configuration.yaml`); state changes between `idle` and `active`.
- `input_boolean.lr_heating_recovery_boost_active` — declared `configuration.yaml:1066`.
- (Out of first-pass scope) `climate.master_bedroom_air`, `climate.lincoln_air`, `climate.lilly_air`, `timer.lr_heating_recovery_boost_max_runtime`.

### 3.3 Postmortem-driven sink discipline

`docs/postmortems/2026-05-02_event_journal_containment.md` documents the
event-journal sink failure that ended in PR #26 disabling all five
Section 12 EJ observers and converting `script.log_event` to a no-op.
That postmortem rules out, for the foreseeable future, any provenance
sink that depends on `notify.file`, `notify.event_journal`,
`shell_command`, or any custom Jinja filter unavailable on this HA
build. The implementation must reuse the **already-proven** sink:
`google_sheets.append_sheet` with `config_entry: !secret google_sheets_config_entry`.

## 4. Recommended sheet / tab target

- **Workbook:** the existing **Home Assistant** Google Sheets workbook
  (the same workbook that hosts `VTherm_Launch_Data_v5_5` and
  `supervisor_state_log`).
- **Tab:** **`hvac_provenance_log`** (new).
- **Auth:** reuse `!secret google_sheets_config_entry` as Section 1
  does. This keeps the existing `test_google_sheets_actions_use_secrets`
  guarantee intact for the new write path.
- **Header-row deployment:** as with Section 1 / v5.5, the worksheet
  header row must be created in Sheets **before** the implementation PR
  ships, in the column order specified in §7 below, otherwise rows will
  be misaligned. The implementation PR header comment will repeat this
  warning.

`hvac_provenance_log` is **not** a renamed `supervisor_state_log`. It is
a sibling tab. `supervisor_state_log` continues to receive operator
narrative rows under the schema in
`docs/telemetry_confounders.md` §6.2.

## 5. Recommended first observed entities / attributes

Start narrow. The first-pass observer should listen to **exactly** the
following triggers, no more:

1. `climate.living_room_air` — state changes (captures `hvac_mode`
   transitions naturally; `to_state.state` is the new mode).
2. `climate.living_room_air` — `attribute: temperature` changes (captures
   setpoint nudges; this is the same trigger shape Section 3 WAF uses).
3. `timer.manual_hvac_override` — state changes (`idle` ↔ `active`).
4. `input_boolean.lr_heating_recovery_boost_active` — state changes
   (`off` ↔ `on`).

Explicitly **not** in the first pass:

- `climate.master_bedroom_air`, `climate.lincoln_air`,
  `climate.lilly_air` (state or `temperature` attr) — defer until LR
  noise profile is understood.
- `attribute: hvac_action` on any climate entity — this is a noisy
  device-driven attribute that flips during compressor cycling and
  would dominate the row count without adding provenance value.
- `attribute: fan_mode` — same noise concern; defer.
- `timer.lr_heating_recovery_boost_max_runtime` — already covered
  indirectly by `lr_heating_recovery_boost_active` and by the v5.5
  `Section14_Timer_State` / `Section14_Timer_Remaining` columns.
- `input_select.hvac_season_mode`, `input_boolean.away_mode`,
  `input_boolean.night_mode_lr_primary` — these are operator-driven
  mode toggles whose provenance is already self-evident; defer until
  the LR pass is stable.
- All MSR / radar / occupancy / truth sensors. Provenance logging must
  never become a path for promoting MSR data into control, even
  observationally; keeping these off the trigger list eliminates the
  temptation entirely.

This narrow set covers the four classifications that #49 cycle review
actually needs: was the LR setpoint change a person, the supervisor,
Section 14, or a Samsung integration push?

## 6. `origin_kind` classification rules

The classifier reads `trigger.to_state.context`. Context fields are
populated by Home Assistant on every state change.

```
context.user_id      = the HA user who originated the call (UI / API / mobile)
context.parent_id    = the parent context id, set when an automation/script
                       fired the call (chains back to the originating context)
context.id           = this state change's own context id
old_state, new_state = pre/post state objects
```

Decision rules (evaluated in order; first match wins):

| Order | Condition (Jinja, evaluated against `trigger`)                                                                                          | `origin_kind`            | Notes                                                                                                                                                                  |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | `trigger.from_state is none` **or** `trigger.from_state.state in ['unknown', 'unavailable']` **and** HA has been up < ~5 min            | `system_restore`         | Guards the cold-start window where every entity transitions from `unknown`/`unavailable` to its restored value. Avoids classifying restore traffic as `manual_user`.   |
| 2     | `trigger.to_state.context.user_id is not none`                                                                                          | `manual_user`            | The Section 3 WAF watcher already implicitly leans on the inverse of this. UI / API / mobile actions stamp `user_id`.                                                  |
| 3     | `trigger.to_state.context.user_id is none` **and** `trigger.to_state.context.parent_id is not none`                                     | `automation_or_script`   | Section 2, Section 3, Section 14, Section 6, Section 7/7B, Section 8 calls all chain through a parent context.                                                         |
| 4     | `trigger.to_state.context.user_id is none` **and** `trigger.to_state.context.parent_id is none` **and** the entity is a Samsung climate | `integration_or_device`  | Cloud-pushed updates from the Samsung integration arrive without `user_id` or `parent_id`. (`timer` / `input_boolean` entities almost never see this branch.)         |
| 5     | else                                                                                                                                    | `unknown`                | Defensive default. Should be rare; an `unknown` row is not a bug, it is a labelled “did not classify” row.                                                             |

This taxonomy matches the issue body and lets Section 14 release-cause
rows (e.g., `lr_heating_recovery_boost_active` flipping `off` because
the WAF trigger fired) classify as `automation_or_script` rather than
`manual_user`, which is the desired behavior.

The implementation must compute `automation_candidate` as a **best-guess
hint string only**, not a control input. Suggested values:

- `"v7_5_main_supervisor"` when the changed entity is a climate setpoint
  or mode and `origin_kind = automation_or_script` and the time matches
  the `:00 / :15 / :30 / :45` supervisor cadence.
- `"v8_4_lr_heating_recovery_boost_engage"` when
  `climate.living_room_air` state goes to `heat` with setpoint moving to
  77 and `origin_kind = automation_or_script`.
- `"v8_4_lr_heating_recovery_boost_release"` when the boost latch flips
  off and `origin_kind = automation_or_script`.
- `"v7_5_waf_manual_override"` when `timer.manual_hvac_override` flips
  to `active` and `origin_kind = automation_or_script` (the watcher
  itself starts the timer).
- `""` (blank) otherwise.

`automation_candidate` is forensic guidance, not authoritative. Analysts
must still join against actual automation logbook entries to confirm.

## 7. Proposed `hvac_provenance_log` row schema

Header row, in column order. Snake-case, mirroring
`supervisor_state_log` style.

| Column                | Type                | Source                                                                                                                                                       | Empty when                                            |
| --------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------- |
| `event_local`         | `YYYY-MM-DD HH:MM:SS` | `now().strftime('%Y-%m-%d %H:%M:%S')` at the moment the trigger fires.                                                                                       | never                                                 |
| `entity_id`           | string              | `trigger.entity_id`.                                                                                                                                         | never                                                 |
| `attribute`           | string              | `"state"` for state-change triggers; `"temperature"` for the climate `temperature` attribute trigger; etc.                                                   | never                                                 |
| `old_value`           | string              | `trigger.from_state.state` for state triggers, or `trigger.from_state.attributes.<attr>` for attribute triggers; coerced to string; blank if unavailable.    | when `from_state` is missing or `unavailable`         |
| `new_value`           | string              | `trigger.to_state.state` or `trigger.to_state.attributes.<attr>`; coerced to string.                                                                         | when `to_state` is missing                            |
| `origin_kind`         | enum                | One of `manual_user`, `automation_or_script`, `integration_or_device`, `system_restore`, `unknown` per §6.                                                   | never                                                 |
| `context_id`          | string              | `trigger.to_state.context.id`.                                                                                                                               | when context is missing                               |
| `context_parent_id`   | string              | `trigger.to_state.context.parent_id`.                                                                                                                        | when not set                                          |
| `context_user_id`     | string              | `trigger.to_state.context.user_id`.                                                                                                                          | when not set                                          |
| `automation_candidate`| string              | Best-guess label per §6; blank when no candidate matches.                                                                                                    | often blank                                           |
| `related_issue`       | string              | Static `"#66"` for the first-pass logger; future passes may set `"#66,#49"` etc.                                                                             | never                                                 |
| `note`                | string              | Free-form, computed in template (e.g., `"setpoint changed during boost"`); blank by default.                                                                 | typically blank                                       |
| `created_at`          | `YYYY-MM-DD HH:MM:SS` | `now().strftime('%Y-%m-%d %H:%M:%S')` evaluated at the action step (separate variable from `event_local` for ordering checks).                              | never                                                 |

`event_local` and `created_at` will be near-identical in the common case
but separated for the same forensic reason `created_at` exists in
`supervisor_state_log` — it lets analysts detect re-entry, queueing,
or replay if the logger ever gets restarted with backlog.

## 8. Noise-control strategy

The first pass aims for ≤ ~50 rows per day in steady state. Strategies:

1. **Narrow trigger list.** Section 14 boosts, supervisor ticks, and WAF
   nudges are the high-signal events. Excluding `hvac_action` and
   `fan_mode` removes the bulk of device-side chatter.
2. **Skip identical-value writes.** Add a condition that drops the row
   when `trigger.from_state` and `trigger.to_state` produce the same
   `(attribute, value)` pair — HA usually filters these, but Samsung
   integration pushes can occasionally re-emit the same temperature.
3. **Skip `unavailable` ↔ value transitions during the first ~5 min
   after HA boot.** Classify as `system_restore` and write **one** row
   per entity (then suppress further restore rows for that entity until
   a non-restore origin kind appears). Implementation uses a startup
   timestamp comparison; no helper required.
4. **Skip `temperature` attribute changes when `from_state` is
   `unavailable`.** These are restore artifacts.
5. **`mode: parallel, max: 20`** to mirror Section 11; never `mode:
   single` (which would coalesce events) and never `mode: queued` with
   long delays (which would lag).
6. **No `delay` in the action block.** A pure synchronous append keeps
   row count predictable.
7. **No fan-out triggers across all rooms in the first pass.** Adding
   the other three climate entities is explicitly deferred until LR's
   noise profile is observed in production for at least one week.

## 9. Risks

| Risk                                                                                                          | Severity | Mitigation                                                                                                                                                                                                            |
| ------------------------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Provenance row becomes a control input.** Someone later writes a Section 2/3/14 condition that reads from this tab. | High     | Test asserts no automation has a `template`/`condition`/`trigger` body that mentions `hvac_provenance_log` or its derived state. Doc explicitly forbids it. Tab is **outside HA's read path**: it is sheet output only. |
| **Sink failure cascades.** Repeat of the 2026-05-02 EJ failure mode.                                          | Medium   | Reuse the proven `google_sheets.append_sheet` sink; do not introduce `notify`, `shell_command`, or new Jinja filters. Adds zero new sinks vs. Section 1.                                                              |
| **Header row drift.** New columns ship before Sheets header is updated; rows misalign.                         | Medium   | Mirror the Section 1 v5.5 deployment-warning comment in the new section header. Implementation PR description includes a pre-deploy checklist.                                                                       |
| **Context misclassification.** Some integration version pushes a state change with a stray `parent_id`.        | Low      | The Samsung integration has been observed not to populate `parent_id` (Section 3 WAF works). If it ever does, the misclassification is forensic-only — it does not affect control. Worst case: an `automation_or_script` row that should be `integration_or_device`. |
| **Row volume grows unexpectedly.** A device starts emitting 1Hz pushes.                                        | Low      | First-pass row count is bounded by trigger entity count. If row count exceeds expectations, implementation PR can add a `condition` to dedupe within a 5 s window without re-triggering.                              |
| **Write loop.** Logger triggers off something the logger writes.                                                | Zero     | The logger writes only to Google Sheets (external). It changes no HA entity state. There is no entity for the logger to listen to that it itself produces.                                                            |
| **Test guard regressions.** New automation breaks `test_google_sheets_actions_use_secrets` or `test_all_automations_have_mode`. | Low      | Reuse `!secret google_sheets_config_entry` and declare `mode: parallel`; both tests stay green by construction.                                                                                                      |

## 10. Acceptance criteria for the implementation PR

The implementation PR is **out of scope for this planning pass**. When
it lands, it must satisfy all of the following:

1. Adds exactly one new automation, e.g., `id: v8_5_hvac_provenance_logger`,
   under a clearly labelled new section header in `automations.yaml`. No
   other automation is modified.
2. Triggers exactly the four observation points listed in §5. No more.
3. Action body contains exactly one `google_sheets.append_sheet` call,
   targeting worksheet `hvac_provenance_log`, using
   `config_entry: !secret google_sheets_config_entry`.
4. Action body does **not** contain any of the following service calls:
   `climate.set_temperature`, `climate.set_hvac_mode`, `timer.start`,
   `timer.cancel`, `timer.finish`, `input_boolean.turn_on`,
   `input_boolean.turn_off`, `input_text.set_value`,
   `input_datetime.set_datetime`, `notify.*`, `shell_command.*`,
   `script.log_event` (kept as a no-op per the EJ postmortem).
5. Row schema matches §7 exactly.
6. Origin classification matches §6 exactly. The cold-start guard from
   §6 row 1 must be present.
7. New automation declares `mode: parallel`, `max: 20`.
8. New tests exist:
   - `test_provenance_logger_exists` — automation id present, mode set.
   - `test_provenance_logger_uses_sheets_secret` — already covered by
     the existing `test_google_sheets_actions_use_secrets`, but verify
     by running the existing suite.
   - `test_provenance_logger_does_not_mutate_control` — asserts the
     action block contains no service call from the forbidden list in
     acceptance criterion 4.
   - `test_no_automation_reads_hvac_provenance_log` — greps the file
     to ensure no other automation references the string
     `hvac_provenance_log` (i.e., the tab is write-only from HA).
9. Section 2, Section 3, Section 14 diffs are **byte-for-byte zero**.
10. `configuration.yaml` diff is **byte-for-byte zero**. No new helpers.
11. Doc updates:
    - `docs/operator_annotation_design.md` adds a paragraph distinguishing
      `supervisor_state_log` (human) from `hvac_provenance_log`
      (machine). Forbidden-path list is unchanged in spirit, extended
      to mention the new tab is also forensic-only.
    - `docs/telemetry_confounders.md` adds a §6.6 cross-reference.
    - This planning doc is updated to status `Adopted`.
12. Worksheet header row is created in Sheets **before** PR merge.
13. Issue #49 stays open. The PR description must say so explicitly.

## 11. Files likely touched by the implementation PR

- `automations.yaml` — one new section, one new automation. No edits to
  existing sections.
- `tests/test_automations.py` (or new `tests/test_provenance_observability.py`) —
  the four new tests in §10.
- `docs/operator_annotation_design.md` — clarifying paragraph + sibling
  tab note.
- `docs/telemetry_confounders.md` — new §6.6 cross-reference.
- `docs/hvac_provenance_logger_design.md` (this file) — status flip
  Planning → Adopted.

## 12. Files that must NOT be touched by the implementation PR

- `configuration.yaml` (no helpers, no new timers, no new
  input_text/input_boolean/input_datetime).
- `automations.yaml` Section 2 (`v7_5_main_supervisor`).
- `automations.yaml` Section 3 (`v9_sleep_priority_interlock`,
  `v8_2_runaway_cooling_cutoff_lr`, `v8_2_master_emergency_floor`,
  any ceiling gate, `v7_5_waf_manual_override`).
- `automations.yaml` Section 14
  (`v8_4_lr_heating_recovery_boost_engage`,
  `v8_4_lr_heating_recovery_boost_release`).
- `automations.yaml` Section 1 — leave `vtherm_mega_tracker_v5`
  untouched. The provenance logger does not belong inside the v5.5
  wide-table schema.
- ESPHome YAML.
- Any truth-sensor template.
- Any threshold (64 °F engage, 67 °F truth_cap, 90-min boost timer,
  60 °F runaway, 58 °F floor, 76 °F ceiling, 68/72 deadband).
- `script.log_event` (must remain a no-op per
  `docs/postmortems/2026-05-02_event_journal_containment.md`).

## 13. Recommended PR title for the implementation PR

> `Add v8.5 HVAC provenance logger (issue #66) — observability-only, narrow first pass`

Body should reference §10 acceptance criteria from this doc, link
issue #66, link `docs/operator_annotation_design.md`, and confirm
`#49 remains open`.

## 14. Copy/paste comment for issue #66

The following block is intended to be pasted as a single comment on
issue #66 once the planning pass is approved.

```markdown
### Planning pass — `hvac_provenance_log` observer (docs-only)

Planning artifact: `docs/hvac_provenance_logger_design.md`. Summary:

**Tab target.** New sibling tab `hvac_provenance_log` in the existing
Home Assistant Google Sheets workbook, alongside
`VTherm_Launch_Data_v5_5` and `supervisor_state_log`. Rationale:
`supervisor_state_log` is human narrative annotation; the provenance
log is machine event provenance. Different schemas, different write
patterns, different consumers. Keep them separate but joinable by time.

**First observed entities/attributes (narrow).**
- `climate.living_room_air` state changes (captures `hvac_mode`).
- `climate.living_room_air` `attribute: temperature` changes.
- `timer.manual_hvac_override` state changes.
- `input_boolean.lr_heating_recovery_boost_active` state changes.

Explicitly deferred: master/lincoln/lilly climates, `hvac_action`,
`fan_mode`, season/away/night-mode toggles, all MSR sensors. Row
volume target ≤ ~50 rows/day in steady state.

**`origin_kind` classification.** Decision order:
1. `system_restore` — `from_state` is `none`/`unknown`/`unavailable`
   and HA boot age < ~5 min.
2. `manual_user` — `to_state.context.user_id is not none`.
3. `automation_or_script` — `user_id is none` and `parent_id is not
   none`. (Section 3 WAF watcher already validates this signal works
   on this stack.)
4. `integration_or_device` — both ids are `none` and the entity is a
   Samsung climate.
5. `unknown` — defensive default.

**Schema.** `event_local`, `entity_id`, `attribute`, `old_value`,
`new_value`, `origin_kind`, `context_id`, `context_parent_id`,
`context_user_id`, `automation_candidate`, `related_issue`, `note`,
`created_at`. Worksheet header row must be created in Sheets before
the implementation PR ships, in this column order.

**Sink discipline.** Reuse `google_sheets.append_sheet` with
`config_entry: !secret google_sheets_config_entry` (Section 1
pattern). No new sinks. No `notify.*`, no `shell_command.*`, no
revival of `script.log_event` (per the 2026-05-02 EJ
postmortem). The existing `test_google_sheets_actions_use_secrets`
covers the new write path automatically.

**Forbidden by this design.**
- No control surface mutation in the action block (no
  `climate.set_*`, no `timer.*`, no `input_*.set_*`/`turn_*`).
- No automation, condition, template, or supervisor branch may
  read from `hvac_provenance_log`. The tab is HA-write-only.
- No new helpers. No `configuration.yaml` change.
- Section 2 / Section 3 / Section 14 byte-for-byte unchanged.

**Acceptance criteria for the future implementation PR** are in
`docs/hvac_provenance_logger_design.md` §10 (13 items). Tests added:
existence + mode, no control mutation in the action block, and a grep
guard that no other automation references `hvac_provenance_log`.

**#49 stays open.** This logger improves cycle classification inputs
for #49 but does not satisfy its close criteria.

**Recommended PR title for the implementation PR:**
`Add v8.5 HVAC provenance logger (issue #66) — observability-only, narrow first pass`
```

## 15. Hard constraints honored by this planning pass

- Docs-only. No `automations.yaml` change. No `configuration.yaml`
  change. No helper added. No threshold tuned.
- Section 2 supervisor behavior unchanged.
- Section 3 safety gates unchanged.
- Section 14 boost behavior unchanged.
- No MSR data promoted into control.
- No annotation/provenance data routed into a control loop input.
- No Google Sheets read from HA. Only writes.
- `#49` remains open and is not addressed by this doc.

## 16. Cross-references

- Issue #66 — originating request.
- Issue #50 — operator annotation surface (`supervisor_state_log`).
- Issue #49 — V8.4 LR boost clean-cycle close criteria (unaffected).
- `docs/operator_annotation_design.md` — adopted manual annotation
  workflow; forbidden-path list to be extended in implementation PR.
- `docs/telemetry_confounders.md` §6 — `supervisor_state_log` schema
  and §6.4 join semantics.
- `docs/postmortems/2026-05-02_event_journal_containment.md` — sink
  discipline that this doc honors.
- `docs/analysis/v8_4_lr_boost_v5_evidence_review.md` — why richer
  provenance signals improve future cycle classification, and why
  effectiveness remains unmeasured today.
- `automations.yaml` Section 1 — pattern to mirror for the
  Google Sheets sink.
- `automations.yaml` Section 3 (`v7_5_waf_manual_override`) —
  precedent for `trigger.context.parent_id is none` detection.
- `automations.yaml` Section 11 (`v8_3_hvac_transition_log`) —
  `mode: parallel, max: 20` shape to mirror.
- `automations.yaml` Section 14 — boost engage/release; observed by,
  not modified by, the planned logger.

---

_End of HVAC Provenance Logger Planning Doc._
