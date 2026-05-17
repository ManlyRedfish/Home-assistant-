# Open Issue Validation Against V9 / V10 Direction

**Report Date:** 2026-05-17
**Document Role:** Audit of the GitHub issue backlog against the current V9/V10
doctrine in `docs/v9_v10_goals.md`, `docs/3_regression_appendix.md`,
`docs/5_runtime_layer.md`, `docs/comfort_failure_forensics.md`,
`docs/telemetry_confounders.md`, `docs/hvac_provenance_logger_design.md`,
`docs/v6_observability_roadmap.md`, `docs/apollo_msr_observability_checklist.md`,
and `docs/6_proposals.md`.
**Status:** One-shot audit. Docs-only. **No runtime YAML, no automation,
no helper, no threshold, no test, and no GitHub-issue state was changed by
this report.** All recommendations are advisory and require operator action
before any close / reopen / merge / split decision lands on GitHub.
**Scope Lock:** Reading-only against repo files plus the GitHub issue surface.
Does not modify `automations.yaml`, `configuration.yaml`, ESPHome YAML, or
any test. Does not promote Apollo MSR data into HVAC control. Does not
weaken Section 3 safety gates. Does not select an SPI doctrinal position.
Does not select a Ghost Assassin / Samsung Auto Guardrail rule. Does not
reintroduce event-journal architecture. Does not promote
`hvac_provenance_log` / `supervisor_state_log` into a control surface.

---

## 1. Executive Summary

The repo currently has **12 open GitHub issues**. Of the 19 issue numbers the
task brief enumerated, **7 are already closed** (#49, #52, #62, #66, #69, #85,
#88) and **12 are open** (#33, #50, #51, #53, #54, #63, #86, #87, #89, #90,
#91, #92).

Against the V9/V10 direction the picture is:

- **Two issues are pure-actionable docs work that an agent can pick up
  today** without doctrine decisions: **#90** (per-branch season/outdoor
  expected-value table in `docs/comfort_failure_forensics.md`) and **#92**
  (Deferred-Until-Telemetry Register, content known; operator picks
  surface).
- **One issue is partially landed and ready to either close or extend**:
  **#86** (manual-override contract tests). The structural checks in
  `tests/test_manual_override_contract.py` already cover the 8 listed
  acceptance tests and the Codex tightening landed via PRs #93 / #99 /
  #103 — close candidate, with optional one-PR extension to also pin SPI
  / Ghost Assassin via *negative* tests once #87 / #89 doctrine lands.
- **One issue is partially landed and should remain open with a narrowed
  next PR**: **#51** (semantic safety tests). The file
  `tests/test_safety_invariants.py` covers 3 of the planned ~9 invariants
  (LR runaway 60°F, Master floor 58°F, ID-presence). The remaining
  Section 14 thresholds (64 / 67 / 77 / 90-min), ceiling 76°F,
  event-journal anti-regression, and Lincoln/Lilly slug positive
  coverage are still mechanical PyYAML checks worth one tests-only PR.
- **Two issues require operator doctrine decisions, not agent picks**:
  **#87** (SPI α/β/γ) and **#89** (Ghost Assassin vs. Samsung Auto
  Guardrail rule α/β). Both are explicitly framed in
  `docs/5_runtime_layer.md` §7.8 as classification-pending; agent-driven
  selection violates `docs/3_regression_appendix.md` §4.18 (arbitration
  before telemetry proves the need).
- **Four issues are conceptually valid but must defer until telemetry
  matures**: **#53** (Apollo MSR observability field set), **#54** (V6
  schema), **#63** (May 6 stale setpoint=77 root cause), **#91**
  (Section 14 collision quantifier). Each is gated either on v5.5 data
  accumulation, on the V6 schema not yet being justified, or on outside-HA
  analytic work.
- **One issue is planning-only and should be rewritten or replaced**:
  **#33** (docs-only PR guardrail) — the risk is real, the implementation
  is concrete enough today, but the issue is framed as "planning only" so
  it never gets actioned. Convert it to a concrete CI-implementation
  issue with explicit acceptance criteria, or close as superseded by code
  review.
- **One issue is superseded by completed work and ready to close**:
  **#50** (operator annotation practice). The `supervisor_state_log`
  worksheet exists with a seeded row, and `docs/operator_annotation_design.md`
  + `docs/telemetry_confounders.md` §6 both moved the practice from
  *Proposed* to *Adopted (sheet-side)*. Close as completed.
- **One previously-closed issue may have been closed prematurely under
  current doctrine**: **#49**. The on-disk evidence review at
  `docs/analysis/v8_4_lr_boost_v5_evidence_review.md` §10 / §13 still
  says "**#49 close criteria not met**" and "**Issue #49 remains open.**"
  The GitHub close at 2026-05-07 17:00 happened 5 minutes after the
  comment that ended "Keep #49 open." Operator should decide whether
  to reopen, or whether the doc-side evidence-pending state is now the
  durable tracking surface (with #91 supplying the recurring analytic).
  **Either way, the docs must not be edited to claim V8.4 effectiveness
  is measured.**

The remaining closed-but-listed issues (#52, #62, #66, #69, #85, #88) are
correctly closed under V9/V10 doctrine and need no action beyond noting
them here as completed dependencies.

**No issue in the open set proposes anything that violates V9/V10 hard
constraints** (no autonomous control, no Apollo MSR control promotion, no
event-journal revival, no `hvac_provenance_log` read-back, no Section 3
safety-gate relaxation, no deadband retune). The backlog is doctrinally
clean; the action items are about pace and sequencing, not direction.

## 2. Recommended Close List

Close as completed (no further code work required):

- **#50** — Operator annotation practice. Sheet-side adopted; seeded row
  present; doctrine docs updated to *Adopted*. (`docs/operator_annotation_design.md`
  §0, §4.0; `docs/telemetry_confounders.md` §6.)

Close as superseded by completed work (no longer the right tracking
surface):

- **#33** — Docs-only PR guardrail. The "planning only" framing has been
  stable for ~12 days with no implementation movement. Either rewrite as
  a concrete CI implementation issue (see §5 below) or close as
  superseded by code review. Operator picks.

Confirm existing closures are correct under current doctrine (no action
required, just record):

- **#52** — R9 slug verification. Closed correctly; live HA states export
  confirms the apostrophe-safe slug pattern.
- **#62** — Section 14 boost-state telemetry. Closed correctly; v5.5
  schema is live with the 10 Section 14 observability columns per
  `docs/5_runtime_layer.md` §5.3.
- **#66** — V8.5 provenance logger. Closed correctly; Section 15 of
  `automations.yaml` implements `v8_5_hvac_provenance_logger` per
  `docs/hvac_provenance_logger_design.md`.
- **#69** — Manual-run trigger guard. Closed correctly; the top-level
  `trigger.from_state is defined`-style guard is present in
  `automations.yaml` Section 15 at lines 1776–1784.
- **#85** — Master/Lincoln/Lilly provenance fan-out. Closed correctly;
  the six new triggers (state + temperature attribute) are present in
  Section 15 at lines 1739–1759.
- **#88** — SPI observability hook. Closed correctly; the
  `spi_last_triggered` observer trigger and the
  `automation_candidate_v == 'v9_sleep_priority_interlock'` classifier
  branch are present in Section 15 at lines 1771–1774 and 1860, and
  `tests/test_provenance_observability.py::test_provenance_logger_observes_spi_last_triggered`
  + `::test_provenance_classifier_includes_spi` lock the contract.

**#49** is listed separately under §5 (Operator-Decision-Needed) because
the doc-vs-GitHub state has drifted and the operator should pick which
surface tracks evidence-pending state going forward.

## 3. Recommended Tackle-Now List

These are actionable under current V9/V10 doctrine, do not need operator
doctrine selection, do not require new telemetry, and have clear
acceptance criteria. **Sequenced safest-first; see §10 for the three-PR
plan.**

1. **#90** — Season / outdoor branch forensic signature documentation
   *(docs-only)*. Subsection added to
   `docs/comfort_failure_forensics.md` §8.6 (or companion doc) listing,
   **read from live YAML**, the per-branch expected ON/OFF/setpoint for
   each room. No new numeric truth introduced; the doc reads
   `automations.yaml` Section 2 verbatim. Estimated change set: one
   new subsection, ~120 lines of markdown, no runtime touch.
2. **#92** — Deferred-Until-Telemetry Register *(docs-only)*. Operator
   picks the surface (new `docs/deferred_until_telemetry.md` vs. issue
   body). Content is already enumerated in the issue body and is
   doctrinally consistent with `docs/v9_v10_goals.md` §11.2 and
   `docs/3_regression_appendix.md` §6.
3. **#51 part B** — Extend `tests/test_safety_invariants.py` to cover
   the remaining §A invariants from the issue body (Section 14
   thresholds 64/67/77/90-min, ceiling 76°F, event-journal
   anti-regression, Lincoln/Lilly slug positive coverage). Pure
   tests-only PR; no YAML change. Each failure message cites the
   doctrine source per the issue body design.

Conditional (after operator doctrine):

- **#86 extension** — Once #87 / #89 land doctrine, add *negative*
  assertions to `tests/test_manual_override_contract.py` confirming that
  the deliberately-ambiguous interlocks (SPI, Ghost Assassin) match
  whichever rule was selected. Today the structural framework already
  passes the listed acceptance criteria for the 8 unambiguous
  automations; the ambiguous-interlock pinning is the only remaining
  work and it cannot happen before #87 / #89.

## 4. Recommended Deferred List

Conceptually valid under V9/V10, but must not be implemented yet because
evidence, schema, or analytic input is still being gathered:

- **#53** — Apollo MSR observability *(defer pending telemetry surface
  inventory)*. The MSR boundary is locked by
  `tests/test_msr_observability_boundary.py` and the Lincoln fan-only
  exception is explicitly preserved. The proposed Section 1 telemetry
  field set largely overlaps with what `vtherm_mega_tracker_v5` already
  exports today. Defer the issue until an operator review confirms which
  proposed fields are still missing from v5.5; then either close as
  superseded or open a narrow telemetry-only PR.
- **#54** — V6 telemetry schema *(defer)*. Authoritative V9/V10 doctrine
  says V6 work is gated until telemetry evidence justifies migrating off
  the v5.5 wide table (`docs/v9_v10_goals.md` §2.4, §11.2;
  `docs/v6_observability_roadmap.md` §3). v5.5 has only been live for a
  short time; insufficient evidence today.
- **#63** — May 6 stale setpoint=77 investigation *(defer)*. The
  classification is already in
  `docs/analysis/v8_4_lr_boost_v5_evidence_review.md` §8 (disqualified
  as stale-setpoint artifact). Now that v5.5 records
  `Section14_Boost_Active` and release reasons, a recurrence will be
  diagnosed directly rather than inferred. Defer the root-cause
  investigation until v5.5 telemetry surfaces a second example, or
  close as already-explained.
- **#91** — Section 14 supervisor / boost collision quantifier
  *(defer; V10 analytic, outside-HA)*. Acceptance criteria explicitly
  require ≥4 weeks of joined v5.5 + `hvac_provenance_log` data. Output
  must live outside HA per `docs/v9_v10_goals.md` §9 Provenance Doctrine.
  Defer.
- **#49** — V8.4 LR boost effectiveness *(defer pending evidence,
  regardless of GitHub state)*. Per
  `docs/analysis/v8_4_lr_boost_v5_evidence_review.md` §10 and §13,
  fewer than 3 clean cycles have been recorded and the verdict is
  *effectiveness remains unmeasured*. v5.5 starts collecting the data
  that could eventually satisfy the criteria; the issue is doctrinally
  in the deferred-pending-telemetry bucket. See §5 for whether to
  reopen the GitHub issue or rely on the on-disk evidence surface.

## 5. Operator-Decision-Needed List

These require an explicit operator choice. **Agents must not pick.**
Any agent-driven selection here would violate
`docs/3_regression_appendix.md` §4.18 (arbitration before telemetry
proves the need) or §4.17 (collision class).

- **#33** — Docs-only PR guardrail. **Decision:** rewrite as a concrete
  GHA-implementation issue with acceptance criteria, or close as
  superseded by code review. Both are defensible; the current "planning
  only" framing is neither actionable nor closable. Operator picks.
- **#49** — V8.4 boost effectiveness tracking. **Decision:** reopen on
  GitHub so the issue state matches the on-disk doctrine, or formally
  archive the GitHub issue and let
  `docs/analysis/v8_4_lr_boost_v5_evidence_review.md` + #91 (collision
  quantifier) carry the evidence-pending state. Either is defensible.
  Neither permits docs to claim "V8.4 is effective." See §11 for
  detailed notes.
- **#87** — SPI doctrine classification (α / β / γ). **Decision:** pick
  Position α (comfort policy; gate on override), β (cross-mode /
  compressor protection; remain authoritative), or γ (observability-only
  candidate). Per `docs/5_runtime_layer.md` §7.8 SPI doctrine note, the
  pick requires ≥3 logged SPI fires plus context (manual vs. supervisor
  on each side). The #88 hook is live; data is accumulating.
- **#89** — Ghost Assassin vs. Samsung Auto Guardrail consistency.
  **Decision:** pick rule α (both yield to manual override) or rule β
  (integration-anomaly always wins). The two paths disagree today; both
  rules are defensible.
- **#92** — Deferred-Until-Telemetry Register surface. **Decision:**
  keep the register as long-lived issue-body tracking, or codify it as
  a new `docs/deferred_until_telemetry.md`. Content is the same either
  way; the question is the durable home for it.

For #87 and #89 specifically: a docs-only PR that *records* the chosen
rule is appropriate once operator decides, but the operator's pick is
the prerequisite, not the artifact. The PR body must cite the rule
chosen and the rationale, and `docs/5_runtime_layer.md` §7.8 must update
the "Ambiguity status" / doctrine-notes paragraphs to reflect the
resolution.

## 6. Per-Issue Table

| # | Title | State | V9/V10 Classification | Tackle / Defer / Close / Decision / Rewrite | Blocker / Dependency | Agent-Safe? | Operator Decision? |
|---|---|---|---|---|---|---|---|
| 33 | Docs-only PR guardrail | OPEN | NEEDS REWRITE / SPLIT | Rewrite as concrete CI implementation issue, or close as superseded | None | Partial (impl is mechanical once decision lands) | Yes (rewrite vs. close) |
| 49 | V8.4 LR boost effectiveness | CLOSED | VALID — DEFER UNTIL TELEMETRY | Reopen, or accept doc-side tracking via §10 / §13 of analysis doc + #91 | v5.5 ≥3 clean cycles | No (evidence-pending) | Yes (reopen vs. archive) |
| 50 | Operator annotation practice | OPEN | SUPERSEDED / PROBABLY CLOSE | Close as completed | None | Yes | No |
| 51 | Semantic safety tests design | OPEN | VALID — TACKLE NOW (part B) | Tackle remaining §A invariants in one tests-only PR | None | Yes | No |
| 52 | R9 slug verification | CLOSED | SUPERSEDED / PROBABLY CLOSE | Confirm closure | n/a | n/a | No |
| 53 | Apollo MSR observability fields | OPEN | VALID — DEFER UNTIL TELEMETRY | Defer; review whether v5.5 already covers proposed fields | v5.5 field-coverage review | Partial (telemetry-only) | No |
| 54 | V6 telemetry schema | OPEN | VALID — DEFER UNTIL TELEMETRY | Defer per `v6_observability_roadmap.md` §3 | v5.5 evidence; V9 simplification | No | No |
| 62 | Section 14 boost-state telemetry | CLOSED | SUPERSEDED / PROBABLY CLOSE | Confirm closure (v5.5 columns live) | n/a | n/a | No |
| 63 | May 6 stale setpoint=77 | OPEN | VALID — DEFER UNTIL TELEMETRY | Defer; classification already in analysis doc §8 | v5.5 release-reason data | No | No |
| 66 | V8.5 provenance logger | CLOSED | SUPERSEDED / PROBABLY CLOSE | Confirm closure | n/a | n/a | No |
| 69 | Manual-run trigger guard | CLOSED | SUPERSEDED / PROBABLY CLOSE | Confirm closure (fix is in Section 15 lines 1776–1784) | n/a | n/a | No |
| 85 | Bedroom provenance fan-out | CLOSED | SUPERSEDED / PROBABLY CLOSE | Confirm closure | n/a | n/a | No |
| 86 | Manual-override contract tests | OPEN | SUPERSEDED / PROBABLY CLOSE (with optional extension) | Close as completed; optional extension after #87/#89 | #87/#89 for ambiguous-interlock pinning | Yes (close); No (extension) | No (close); Yes (extension) |
| 87 | SPI doctrine classification | OPEN | VALID — DOCS/DOCTRINE DECISION NEEDED | Operator picks α/β/γ; then docs-only PR | ≥3 SPI fires via #88 hook (now live) | No | **Yes** |
| 88 | SPI observability hook | CLOSED | SUPERSEDED / PROBABLY CLOSE | Confirm closure | n/a | n/a | No |
| 89 | Ghost Assassin vs Samsung guardrail | OPEN | VALID — DOCS/DOCTRINE DECISION NEEDED | Operator picks rule α/β; then docs-only PR | None | No | **Yes** |
| 90 | Season/outdoor branch forensic table | OPEN | VALID — TACKLE NOW | Tackle now | None | Yes | No |
| 91 | Section 14 collision quantifier | OPEN | VALID — DEFER UNTIL TELEMETRY (outside-HA) | Defer until ≥4 weeks of v5.5 + provenance data | v5.5 + `hvac_provenance_log` ≥4 weeks | Partial (outside-HA analytic) | No |
| 92 | Deferred-Until-Telemetry Register | OPEN | VALID — TACKLE NOW (operator picks surface) | Tackle as docs file or issue body | None | Mostly (operator picks surface) | Yes (surface only) |

## 7. Detailed Per-Issue Notes

### #33 — Add docs-only PR guardrail for Moose House repository

- **State:** OPEN, labels `documentation`, `ci`.
- **Doctrine check:** No V9/V10 doc conflicts. The risk #33 names is
  real and consistent with V9 doctrine that "Software cannot
  out-calculate structure and gravity" — code review is the last line
  of defense and structural CI checks reduce drift.
- **Drift signal:** The issue says "Planning only for now. Do not
  implement the workflow as part of this issue." This planning framing
  has not produced an implementation issue in the 12 days since filing.
  Either the implementation is concrete enough to file directly, or the
  risk has been accepted via code-review discipline.
- **Recommendation:** **NEEDS REWRITE / SPLIT**. Operator picks:
  1. Rewrite #33 as a concrete CI-implementation issue with acceptance
     criteria (e.g., "GHA fails when a PR with label `docs-only`
     touches `*.yaml`, `*.py`, `configuration.yaml`, `automations.yaml`,
     `secrets.yaml`, `custom_components/**`, `packages/**`, or
     `blueprints/**`"). Then this issue becomes a normal tackle-now
     item, agent-safe.
  2. Close #33 as superseded by code-review discipline and the existing
     `git diff -- '*.yaml'` workflow.
- **Agent-safe to implement once decision lands:** Yes, the GHA file is
  mechanical.
- **Operator decision needed:** Yes (rewrite vs. close).

### #49 — Track V8.4 LR boost effectiveness as evidence-pending

- **State:** **CLOSED** (state_reason: `completed`, closed_at
  2026-05-07T17:00:29Z).
- **Doctrine check:** **Conflicts with current on-disk doctrine.**
  - `docs/analysis/v8_4_lr_boost_v5_evidence_review.md` §10: "Issue
    #49 remains open. This review does not propose to close it."
  - §13 addendum: "The verdict in §10 — #49 close criteria not met —
    is unchanged. Issue #49 remains open. v5.5 enables the future
    evidence pipeline that could eventually satisfy the #49 criteria;
    this addendum does not."
  - `docs/3_regression_appendix.md` §4.17 source-lineage references
    issue #49 as the close criterion for the supervisor/boost
    collision retired pattern: "Reopen Only If: Section 14 verdict
    closes (issue #49) with the current collision model…"
  - `docs/v6_observability_roadmap.md` §4: "No V8.4 effectiveness claim
    without evidence: Any claims regarding the Living Room boost (#49)
    must be backed by clean V6 telemetry evidence."
  - `docs/5_runtime_layer.md` §7.4: "Boost effectiveness on recovery
    time is therefore still unmeasured."
- **Issue body close-condition:** "≥3 clean cycles per the criteria
  above are recorded in `VTherm_Launch_Data_v5` + HA Logbook, **and**
  an effectiveness verdict (positive, neutral, or negative) is written
  into `docs/5_runtime_layer.md` §7.4 and `docs/4_operations_sheet.md`."
  Neither condition is satisfied today.
- **GitHub vs. doc state mismatch:** The second comment on #49
  (2026-05-07T16:55) ends with "Keep #49 open." The closure at 17:00
  is 5 minutes later. The on-disk evidence review preserves
  evidence-pending state, but a future reader of just the GitHub
  surface would conclude the question is settled.
- **Recommendation:** **VALID — DEFER UNTIL TELEMETRY** doctrinally,
  with an **operator-decision needed** on the GitHub surface:
  1. Reopen the GitHub issue so the issue state matches the on-disk
     doctrine. v5.5 + #91 will eventually satisfy the close criteria.
  2. Or formally archive the GitHub issue and let the analysis doc plus
     `docs/5_runtime_layer.md` §7.4 + #91 carry the
     evidence-pending state. Add a note to `docs/2_reference_map.md`
     pointing analysts to the analysis doc rather than the closed
     issue.
- **Either way:** No doc may claim V8.4 boost is "proven," "validated,"
  "working," or "effective" without the evidence-pending caveat. The
  prohibition in the original issue body remains in force regardless of
  GitHub state.
- **Agent-safe to implement:** No (operator decision; agent may not
  reopen/archive issues without explicit instruction).

### #50 — Define operator annotation practice for telemetry confounders

- **State:** OPEN.
- **Doctrine check:** Fully consistent with V9/V10. The adopted
  sheet-side practice satisfies the forbidden-path discipline
  (HA-never-reads-Sheets) per `docs/operator_annotation_design.md` §6
  and `docs/telemetry_confounders.md` §6.5.
- **Completion evidence:**
  - `docs/operator_annotation_design.md` §0 table marks "Sheet-side
    annotation surface (`supervisor_state_log`)" as **Adopted**.
  - `docs/telemetry_confounders.md` §6 title is now "Operator
    Annotation Practice (**Adopted — Sheet-Side**)."
  - The comment on #50 confirms the worksheet exists, the five-column
    header is seeded, and the first annotation row covers the
    2026-04-28 → 2026-05-01 canonical contaminated window.
  - The issue's own close criterion is met: "a first row has been
    written to a `supervisor_state_log` (or chosen-name) worksheet…
    **and** `docs/telemetry_confounders.md` §6 has been updated to
    point to that worksheet as the live annotation surface."
- **Recommendation:** **SUPERSEDED / PROBABLY CLOSE** as completed.
- **Agent-safe:** Yes (state-change only).
- **Operator decision needed:** No.

### #51 — Design semantic safety tests for Moose House YAML

- **State:** OPEN.
- **Doctrine check:** Fully consistent with V9. Semantic tests are the
  executable form of the comfort/safety contract.
- **Partial completion:** `tests/test_safety_invariants.py` exists and
  covers:
  - `test_lr_runaway_cooling_cutoff_exists` (LR runaway 60°F + LR-off
    action; §A row 1 + 2 + structural)
  - `test_master_emergency_cooling_floor_exists` (Master floor 58°F +
    Master-off action; §A row 1 + 3 + structural)
  - `test_required_safety_automations_are_present_by_unique_id` (§A
    row 1, partial)
- **Remaining §A invariants (issue body):**
  - Row 4 (ceiling 76°F).
  - Row 5 (Section 14 engage threshold 64°F).
  - Row 6 (Section 14 release cap 66.99°F, intentional rounding noted).
  - Row 7 (Section 14 commanded setpoint 77°F + `hvac_mode: heat`).
  - Row 8 (Section 14 max runtime `01:30:00`).
  - Row 10 (event-journal anti-regression: no `script.log_event`
    call in any automation action; no `notify:` block named
    `event_journal`; no script key `log_event`; no automation id
    prefixed `ej_`).
  - Row 12 extension (Lincoln/Lilly slug positive coverage in
    `configuration.yaml`; negative coverage extended to
    `configuration.yaml`).
- **Recommendation:** **VALID — TACKLE NOW (part B)**. One tests-only
  PR extending `tests/test_safety_invariants.py` to cover the remaining
  invariants. Each test cites the doctrinal source per the issue body
  design.
- **Agent-safe:** Yes; pure pytest against parsed YAML. No runtime
  touch. Pattern already established by the existing file.
- **Operator decision needed:** No.

### #52 — Record R9 slug-continuity verification (CLOSED)

- **State:** CLOSED, state_reason `completed`.
- **Task-specific question:** "Check whether #52 is merely a recorded
  evidence breadcrumb and can be closed." **Yes**, that is exactly what
  the issue body says ("This issue is a reporting breadcrumb only").
- **Recommendation:** **SUPERSEDED / PROBABLY CLOSE** — closure
  confirmed correct. No further action.

### #53 — Add Apollo MSR observability to Moose House telemetry

- **State:** OPEN.
- **Doctrine check:** Consistent with V9/V10 *as observability only*.
  The Apollo MSR observability-only doctrine is locked by
  `docs/apollo_msr_observability_checklist.md` and
  `tests/test_msr_observability_boundary.py`, which enforces:
  - No MSR-derived entity may appear in any non-telemetry,
    non-Lincoln-fan-only automation.
  - The Lincoln fan-only exception is `climate.set_hvac_mode` for
    `climate.lincoln_air` between `fan_only` and `off` only.
  - Safety automations and `v7_5_main_supervisor` must remain MSR-free.
  - A pattern sweep blocks new `_msr_` / `apollo` / `dps310` / `mmwave`
    / `ld2410` / `scd40` / `radar_zone` / `co2` references.
- **Live status:** Section 1 telemetry exporter
  (`vtherm_mega_tracker_v5` → `VTherm_Launch_Data_v5_5`) already exports
  MSR fields in the allow-listed observability path. The issue's
  proposed first field set largely overlaps with what is exported
  today; a careful operator review is required to confirm.
- **Recommendation:** **VALID — DEFER UNTIL TELEMETRY (review)**. Defer
  pending an operator review of which proposed fields are already in
  v5.5 vs. genuinely missing. If all fields are already present, close
  as superseded; otherwise open a narrow telemetry-only PR.
- **Hard constraint reaffirmed:** Apollo MSR must not be promoted into
  HVAC control beyond the documented Lincoln fan-only exception.
- **Agent-safe:** Partial. An agent can survey v5.5 column coverage,
  but the final close-vs-extend decision should be operator.
- **Operator decision needed:** Not strictly (it's a coverage audit).

### #54 — Design VTherm_Launch_Data_v6 telemetry schema

- **State:** OPEN, planning issue.
- **Doctrine check:** V9/V10 explicitly defers V6 work.
  - `docs/v9_v10_goals.md` §2.4: V6 schema "deferred until V6 schema is
    live and forensic evidence supports the change."
  - `docs/v6_observability_roadmap.md` §3: V6 phase order: docs → tests
    → V6 schema scaffold → annotations → MSR → runtime changes later.
  - `docs/v9_v10_goals.md` §11.2: V6 is in the "Later PRs (deferred)"
    bucket.
- **v5.5 status:** The current wide-table interim schema has been live
  for a short time and is the appropriate place to collect data for
  some weeks before V6 work is justified.
- **Recommendation:** **VALID — DEFER UNTIL TELEMETRY**. Hold the
  planning issue open until v5.5 produces enough forensic evidence
  (e.g., #91 collision quantifier output, ≥3 clean Section 14 cycles
  per #49 criteria) to justify the migration cost.
- **Agent-safe:** No; agent should not advance V6 work.
- **Operator decision needed:** Not yet.

### #63 — Investigate May 6 stale LR setpoint=77 artifact

- **State:** OPEN, labels `bug`, `observability`, `diagnostic`.
- **Doctrine check:** Already classified. The window is disqualified in
  `docs/analysis/v8_4_lr_boost_v5_evidence_review.md` §8 ("May 6
  Setpoint=77 Window — Disqualified") with the reasoning: zero HP
  runtime, mode off, LR truth above target, null truth for first 13
  rows. Pattern consistent with stale or stuck setpoint artifact, not
  active V8.4 boost.
- **Why the root cause is now lower-priority:** v5.5 adds
  `Section14_Boost_Active`, `Section14_Timer_State`,
  `Section14_Last_Release_Reason`, and the engage/release timestamp
  helpers (per `docs/5_runtime_layer.md` §5.3). A future stale-setpoint
  recurrence will be diagnosed directly rather than inferred from
  setpoint alone.
- **Recommendation:** **VALID — DEFER UNTIL TELEMETRY**. Defer the
  root-cause investigation until v5.5 surfaces a second example, or
  close as already-explained by the analysis doc §8. The window is
  already correctly excluded from #49 effectiveness analysis.
- **Agent-safe:** No (depends on operator-side investigation if a
  second case appears).
- **Operator decision needed:** Not yet.

### #62, #66, #69, #85, #88 — All CLOSED, correctly under V9/V10

- **#62:** v5.5 schema is live with Section 14 columns
  (`Section14_Boost_Active`, `Section14_Timer_State`,
  `Section14_Timer_Remaining`, `Section14_Last_Engage_Reason`,
  `Section14_Last_Release_Reason`, `Section14_Last_Engage_At`,
  `Section14_Last_Release_At`, `Section14_Engage_Eligible`,
  `Section14_WAF_Active`, `Section14_Truth_Available`). The control
  actions write observability helpers AFTER the existing control
  actions per `docs/5_runtime_layer.md` §6.5. **Closure confirmed.**
- **#66:** `v8_5_hvac_provenance_logger` is live in
  `automations.yaml` Section 15. The four acceptance tests in
  `tests/test_provenance_observability.py` enforce: existence + mode,
  Google Sheets secret usage, no control-surface mutation, no
  automation reads `hvac_provenance_log`. **Closure confirmed.**
- **#69:** The top-level condition guard
  (`trigger is defined and trigger.from_state is defined and
  trigger.to_state is defined and trigger.entity_id is defined and
  trigger.id is defined`) is present in `automations.yaml` lines
  1776–1784. Manual-run trigger UndefinedError no longer occurs.
  **Closure confirmed.**
- **#85:** Section 15 triggers now include `master_state`,
  `master_temp_attr`, `lincoln_state`, `lincoln_temp_attr`,
  `lilly_state`, `lilly_temp_attr`. Test
  `tests/test_provenance_observability.py::test_provenance_logger_includes_bedroom_climate_triggers`
  locks it. **Closure confirmed.**
- **#88:** Section 15 contains the `spi_last_triggered` state observer
  on `automation.v9_sleep_priority_interlock` `attribute:
  last_triggered`. The `automation_candidate_v` classifier branches on
  `trigger.id == 'spi_last_triggered'` → `v9_sleep_priority_interlock`.
  Locked by `test_provenance_logger_observes_spi_last_triggered` and
  `test_provenance_classifier_includes_spi`. **Closure confirmed.**
  This is the SPI fire provenance hook that #87 will draw on for the
  doctrine pick.

The task brief explicitly asked: "Check whether #66 is superseded by
the V8.5 provenance logger work and newer follow-up issues like #69,
#85, and #88." **Yes.** #66 is the design + adoption surface; #69
fixed the manual-run regression; #85 extended fan-out to the bedroom
heads; #88 added SPI fire provenance. All landed. The V8.5 logger now
covers four climate entities × {state, temperature} + override timer +
boost latch + SPI fires, classified by the §6 design-doc taxonomy. No
follow-up implementation work is open against #66.

### #86 — Manual-override contract test coverage

- **State:** OPEN.
- **Doctrine check:** Fully consistent with V9/V10. The Manual Override
  Contract in `docs/5_runtime_layer.md` §7.8 is the doctrine these
  tests protect.
- **Implementation status:** `tests/test_manual_override_contract.py`
  exists and contains:
  - `test_supervisor_respects_manual_override` ✓
  - `test_ceiling_gates_respect_manual_override` ✓
  - `test_destratification_respects_manual_override` ✓
  - `test_samsung_guardrail_respects_manual_override` ✓
  - `test_boost_engage_respects_manual_override` ✓
  - `test_boost_release_yields_to_manual_override` ✓ (this test
    verifies the WAF trigger exists AND the climate-off action is
    wrapped in a `choose` branch guarded by
    `not(state(timer.manual_hvac_override == active))`, which is the
    strict structural check, not "condition exists somewhere")
  - `test_lr_runaway_does_not_gate_on_override` ✓ (negative)
  - `test_master_floor_does_not_gate_on_override` ✓ (negative)
  - Plus six regression tests that exercise the AND / OR / NOT analyzer
    semantics, including
    `test_regression_or_branch_can_not_bypass_manual_override` and
    `test_regression_shorthand_or_branch_can_bypass_manual_override`.
- **Codex feedback handled:** The structural analyzer
  (`_condition_tree_requires_manual_override_idle`) explicitly handles
  the AND / OR / NOT collapse semantics: "An OR implies idle only if
  **all** branches imply idle." This is the strict version. The
  shorthand `and:` / `or:` / `not:` forms are normalized. Recent
  commits d1c00ee (Strengthen manual override contract structure
  checks) and 9802dc7 (tests: support shorthand HA logical conditions
  in override analyzer) are precisely this hardening. **No
  weak-check failure mode visible.**
- **Recommendation:** **SUPERSEDED / PROBABLY CLOSE** as completed. The
  body's "≥7 passing tests" criterion is exceeded (8 contract tests +
  6 regression tests = 14 passing).
- **Optional future extension** *(do not file under #86)*: once #87 /
  #89 doctrine lands, add positive/negative assertions for SPI and
  Ghost Assassin matching whichever rule was selected. That belongs to
  #87 / #89's runtime-alignment PRs, not to #86.
- **Agent-safe:** Yes (close).
- **Operator decision needed:** No.

### #87 — Sleep Priority Interlock doctrine classification

- **State:** OPEN, labels `documentation`, **docs-only**.
- **Doctrine check:** Already partially landed. The three candidate
  positions (α / β / γ) and the evidence required to pick are
  enumerated in `docs/5_runtime_layer.md` §7.8 SPI doctrine note and
  `docs/v9_v10_goals.md` §2.3 (canonical worked example). The #88
  provenance hook is live. Data is accumulating in
  `hvac_provenance_log` rows tagged
  `automation_candidate = v9_sleep_priority_interlock`.
- **Why agent must not pick:** `docs/3_regression_appendix.md` §4.18
  (arbitration before telemetry proves the need) and `docs/v9_v10_goals.md`
  §2.3 require operator doctrine clarification before any
  runtime change to SPI's override authority. Picking a position
  without evidence reintroduces the failure mode the retired pattern
  warns against.
- **Recommendation:** **VALID — DOCS/DOCTRINE DECISION NEEDED
  (operator)**. Defer until: (a) ≥3 SPI fires logged via #88, (b)
  operator picks α/β/γ. The docs-only PR that *records* the choice can
  be agent-implemented once the choice is made, but the choice itself
  must be operator.
- **Agent-safe:** No (operator decision).
- **Operator decision needed:** **Yes** (α / β / γ).

### #89 — Ghost Assassin vs Samsung Auto Guardrail consistency

- **State:** OPEN, labels `documentation`, **docs-only**.
- **Doctrine check:** Already named as classification-pending in
  `docs/5_runtime_layer.md` §7.8 (Ambiguity status note + doctrine
  notes paragraph) and `docs/v9_v10_goals.md` §8 (Integration-anomaly
  paragraph).
- **Two defensible rules:**
  - Rule α (both yield to manual override). Rationale: human intent is
    authoritative; if the operator manually set Lincoln to `heat` at
    01:20 during non-heating season, the ghost suppression must yield.
    Aligns with `docs/3_regression_appendix.md` §4.15.
  - Rule β (integration-anomaly always wins). Rationale: a 01:20
    phantom heat is, by construction, not a deliberate human action,
    so override gating provides false reassurance.
- **Why agent must not pick:** Both rules are doctrinally defensible.
  Picking either silently rewrites runtime authority over manual
  intent. This is exactly the class of arbitration that
  `docs/3_regression_appendix.md` §4.18 retires when agent-driven.
- **Recommendation:** **VALID — DOCS/DOCTRINE DECISION NEEDED
  (operator)**. After the operator picks, a docs-only PR updates
  `docs/5_runtime_layer.md` §7.8 and `docs/v9_v10_goals.md` §8. The
  loser-side runtime alignment is then **deferred to the
  Deferred-Until-Telemetry Register** (#92) and opened as its own
  scoped PR — not in #89's docs PR.
- **Agent-safe:** No (operator decision).
- **Operator decision needed:** **Yes** (rule α / rule β).

### #90 — Season / outdoor branch forensic signature documentation

- **State:** OPEN, label `documentation`, **docs-only**.
- **Doctrine check:** Fully consistent with V9/V10 and with
  `docs/comfort_failure_forensics.md`. The §8.6 anchor section exists
  but doesn't yet enumerate per-branch expected values, so analysts
  rederive them from `automations.yaml` Section 2 each investigation.
- **Why it's safe for an agent:** The work is "read the live YAML,
  transcribe expected ON/OFF/setpoint into a table." No new numeric
  truth is introduced. The doc's maintenance rule (update this
  subsection when Section 2 changes) is consistent with the existing
  doc cadence.
- **Recommendation:** **VALID — TACKLE NOW**. Highest-value docs work
  in the open set. One small markdown PR.
- **Acceptance criteria** *(verbatim from #90)*: per-branch table read
  from `automations.yaml` Section 2; cross-link from
  `docs/comfort_failure_forensics.md` §7 step 3; maintenance note that
  the subsection must update when Section 2 changes.
- **Hard constraints reaffirmed:** No threshold or setpoint change. No
  new branches. No `away_mode` / `lr_night_primary` / bedtime-window
  semantic changes. No Targeted Pre-Chill re-proposal.
- **Agent-safe:** Yes.
- **Operator decision needed:** No.

### #91 — Section 14 supervisor / boost collision quantifier

- **State:** OPEN, labels `observability`, `diagnostic`, **outside-HA
  analytic**.
- **Doctrine check:** Fully consistent with V10 §4.2 ("Provenance
  Collision Detector"). Output must live outside HA per `docs/v9_v10_goals.md`
  §9 Provenance Doctrine. Acceptance criteria explicitly require ≥4
  weeks of joined `hvac_provenance_log` + v5.5 data.
- **Task-specific question:** "Check whether #91 must remain outside-HA
  analytics only." **Yes**, explicitly. The issue body, V10 doctrine,
  and the forbidden-path discipline all require it. No HA automation
  may consume the quantifier's output. The HA-write-only / HA-read-never
  discipline on `hvac_provenance_log` extends to anything that joins it.
- **Why deferred:** v5.5 has been live for a short time; the
  `hvac_provenance_log` has been live for slightly longer (Section 15
  was added in PR for #66) but bedroom fan-out (#85) and SPI hook
  (#88) only landed within the past day. Insufficient data for
  ≥4-week analysis.
- **Recommendation:** **VALID — DEFER UNTIL TELEMETRY (outside-HA)**.
  Defer until ≥4 weeks of joined data accumulate. Then file as an
  outside-HA analytic PR (notebook, Apps Script, pandas, or similar),
  read-only against the Sheets tabs.
- **Hard constraint reaffirmed:** Output never feeds an HA automation.
- **Agent-safe:** Partial (analytic is outside HA, so the implementation
  surface is non-runtime; but the precondition is operator/time).
- **Operator decision needed:** Not for filing; for picking the
  analytic surface (notebook vs. Apps Script vs. Sheets formula).

### #92 — Deferred-Until-Telemetry Register

- **State:** OPEN, label `documentation`, **docs-only tracking**.
- **Doctrine check:** Fully consistent with `docs/v9_v10_goals.md`
  §11.2 (Later PRs deferred) and `docs/3_regression_appendix.md` §6
  (Reopen conditions).
- **Task-specific question:** "Check whether #92 should become a real
  docs file or remain issue-body tracking." Both are doctrinally
  defensible. The issue body explicitly invites the operator to pick.
- **Initial register content** *(enumerated in #92's body, all
  doctrinally consistent with current docs)*:
  - Targeted Pre-Chill (deferred per §4.12).
  - Multi-head capacity arbitration (deferred per §4.5).
  - New manual-vs-policy / cross-mode arbitration (deferred per §4.18).
  - Apollo MSR promotion (deferred per `apollo_msr_observability_checklist.md`).
  - Comfort survey / autonomous AI / predictive setpoint / ML season
    (retired per §4.13 / §4.19).
  - Event-driven decoupled control loops (deferred per V6 roadmap).
  - Section 2 latch consult against Section 14 (blocked on #91).
  - Ghost Assassin / Samsung Auto Guardrail runtime alignment (blocked
    on #89 doctrine pick).
  - SPI runtime change (blocked on #87 doctrine pick + ≥3 SPI fires
    via #88).
- **Recommendation:** **VALID — TACKLE NOW (operator picks surface)**.
  If a docs file is preferred, file as `docs/deferred_until_telemetry.md`
  and cross-link from `docs/v9_v10_goals.md` §11.2,
  `docs/3_regression_appendix.md` §6, and `docs/6_proposals.md`. If
  issue-body tracking is preferred, the issue itself is the artifact;
  edit it over time.
- **Hard constraint reaffirmed:** No item in the register may move to
  implementation without its named gating condition being met.
- **Agent-safe:** Yes for content (already enumerated). Operator picks
  surface only.
- **Operator decision needed:** Yes (surface), not (content).

## 8. Recommended Close List (Consolidated)

- **Close as completed:** #50.
- **Close with operator pick on path:** #33 (rewrite-or-close), #49
  (reopen-or-archive), #86 (close now, with optional later extension
  via #87 / #89).
- **Confirm existing closures:** #52, #62, #66, #69, #85, #88.

## 9. Recommended Deferred List (Consolidated)

- **#49** — until ≥3 clean Section 14 cycles per #49 close criteria.
- **#53** — until operator confirms v5.5 MSR field coverage.
- **#54** — until V9 simplification + forensic evidence justifies V6.
- **#63** — until v5.5 surfaces a second stale-setpoint=77 example.
- **#91** — until ≥4 weeks of joined `hvac_provenance_log` + v5.5
  data.

## 10. Suggested Next 3 PRs (Safest Order)

Each PR is docs- or tests-only. Each preserves all V9/V10 hard
constraints (no runtime YAML change, no threshold change, no safety
gate weakened, no Apollo MSR control promotion, no autonomous /
predictive setpoint behavior, no event-journal revival, no
`hvac_provenance_log` read-back).

### PR 1 — Tackle #90 (docs-only): Season/outdoor branch forensic signature table

**Scope:**
- Add a new subsection to `docs/comfort_failure_forensics.md` §8.6 (or
  a small companion file cross-linked from §8.6) listing per-branch
  expected ON/OFF/setpoint values, **transcribed from
  `automations.yaml` Section 2**.
- Cross-link from `docs/comfort_failure_forensics.md` §7 step 3.
- Maintenance note: when Section 2 changes, this subsection updates in
  the same PR.

**Why this is safest first:**
- Pure markdown. Reads live YAML; introduces no new numeric truth.
- No doctrine decision required.
- Highest immediate forensic value: removes the slowest manual step
  from every comfort complaint investigation going forward.

**Acceptance:** verbatim from #90's acceptance criteria.

### PR 2 — Tackle #92 (docs-only): Deferred-Until-Telemetry Register

**Scope (operator picks one):**
- **Option A:** New file `docs/deferred_until_telemetry.md` with the
  enumerated entries from #92's body. Cross-link from
  `docs/v9_v10_goals.md` §11.2, `docs/3_regression_appendix.md` §6,
  and `docs/6_proposals.md`.
- **Option B:** Maintain the register in #92's issue body; add a small
  pointer in `docs/v9_v10_goals.md` §11.2 noting where the live
  register lives.

**Why this is safe second:**
- Pure markdown. The content is already enumerated and is consistent
  with the existing doctrine docs.
- No doctrine decision required (operator picks surface only).
- Tripwire effect: future agents reading the register will not silently
  re-propose retired or evidence-gated items.

**Acceptance:** verbatim from #92's acceptance criteria.

### PR 3 — Tackle #51 part B (tests-only): Remaining safety invariants

**Scope:**
- Extend `tests/test_safety_invariants.py` (or add a companion file
  using the same `MooseSafetyLoader` pattern) with:
  - `test_ceiling_gate_76` (Section 3 ceiling gates, `above: 76`).
  - `test_v84_engage_below_64` (Section 14 engage trigger `below: 64`).
  - `test_v84_release_cap_67` (Section 14 release `above: 66.99`,
    with a comment explaining 66.99 ≈ 67 per the issue body §A note).
  - `test_v84_setpoint_77` (`temperature: 77` + `hvac_mode: heat`).
  - `test_v84_max_runtime_90min` (`timer.start` `duration:
    "01:30:00"`).
  - `test_no_event_journal_sink_resurfaces` (structural anti-regression
    per the issue's §A row 10).
  - `test_lincoln_lilly_slug_positive_and_negative` (extend the
    existing slug check to `configuration.yaml` positively and
    negatively).
- Each failure message cites the doctrinal source (Doc 1, Doc 5, or
  `docs/telemetry_confounders.md` §7).

**Why this is safe third:**
- Pure pytest against parsed YAML. Pattern already established by the
  existing file.
- No doctrine decision required.
- No runtime touch.
- The new tests should pass against current `automations.yaml`
  immediately; any future drift in those numeric values would surface
  as a red CI signal.

**Acceptance:** verbatim from #51's "Smallest useful first PR
proposal," covering rows 4, 5, 6, 7, 8, 10, 12 of §A. Row 9 (helper
existence) and §B / §C are explicitly out of scope.

## 11. Additional Observations (Not on the Listed Issue Set)

These are flagged for operator visibility but require no agent action.

- **Compressor cooldown timers are orphaned helpers.**
  `configuration.yaml` defines `lr_compressor_cooldown`,
  `master_compressor_cooldown`, `lincoln_compressor_cooldown`,
  `lilly_compressor_cooldown` (lines 84–100). A `grep` of
  `automations.yaml` shows **no** automation references any of these
  timers. The `docs/ha_nuisance_export.md` script exports them as
  candidate signal, and `docs/7_day_nuisance_evidence_plan.md` §M7
  flags them as a coverage candidate. Under V9 simplification doctrine
  (`docs/5_runtime_layer.md` §7.1–§7.4 known runtime constraints) this
  is exactly the "orphaned / transitional runtime pieces" class that
  V9 simplification work targets. **Not a new issue to file now;**
  the 7-day nuisance plan §M7 already covers it. Just noting for
  cross-reference.

- **`docs/4_operations_sheet.md` was referenced by #49's close
  conditions** (V8.4 effectiveness verdict must be recorded into Doc 4
  + Doc 5 §7.4). The on-disk Doc 4 should not yet mention V8.4
  effectiveness either positively or negatively under current
  evidence.

- **Recent commits suggest the codebase is actively maintained against
  V9/V10 doctrine.** PR #84 (V9/V10 direction docs), PR #98 (#88 SPI
  observer), PR #93/#99/#103 (#86 manual-override contract test
  tightening), PR #94 (#85 bedroom fan-out), PR #96 (#88 / 7-day
  nuisance plan), and the cooling-setpoint tuning PR #82 are all
  consistent with the V9/V10 direction. No regression flags.

## 12. Hard Constraints Honored by This Report

- Docs-only. No `automations.yaml` change.
- No `configuration.yaml` change.
- No ESPHome change.
- No helper added, removed, or repurposed.
- No threshold change (60°F LR runaway, 58°F Master floor, 76°F
  ceiling, 64°F Section 14 engage, 67°F Section 14 truth_cap, 77°F
  Section 14 demand setpoint, 90-min Section 14 timer, 68/72 cooling
  deadband, 64/68 heating deadband all unchanged).
- No Section 3 safety gate weakened.
- No Apollo MSR data promoted into HVAC control beyond the documented
  Lincoln fan-only exception.
- No AI / autonomous / predictive setpoint behavior introduced.
- No event-journal architecture reintroduced.
- `hvac_provenance_log` and `supervisor_state_log` remain
  HA-write-only / HA-read-never. This report does not propose
  consuming either tab from any HA automation.
- No SPI doctrinal position selected.
- No Ghost Assassin / Samsung Auto Guardrail rule selected.
- No deadband change proposed.
- No issue closed, opened, reopened, edited, or commented on the
  GitHub side by this report. Recommendations are advisory; operator
  acts.

## 13. Cross-references

- `docs/v9_v10_goals.md` (V9/V10 direction; the authoritative scope
  document).
- `docs/3_regression_appendix.md` (retired approaches and reopen
  conditions; especially §4.5, §4.12, §4.13, §4.15, §4.16, §4.17,
  §4.18, §4.19).
- `docs/5_runtime_layer.md` (live runtime, Manual Override Contract
  §7.8, Section 14 status §7.4, Apollo MSR boundary §7.7).
- `docs/comfort_failure_forensics.md` (workflow for comfort complaint
  investigations; #90 attaches to §8.6).
- `docs/telemetry_confounders.md` (window classification; operator
  annotation surface §6).
- `docs/hvac_provenance_logger_design.md` (#66 design + acceptance
  record; locked by `tests/test_provenance_observability.py`).
- `docs/v6_observability_roadmap.md` (V6 phase order; gating for #54).
- `docs/apollo_msr_observability_checklist.md` (MSR observability-only
  doctrine; locked by `tests/test_msr_observability_boundary.py`).
- `docs/6_proposals.md` (V9 proposals; Targeted Pre-Chill deferred).
- `docs/operator_annotation_design.md` (#50 adoption record).
- `docs/analysis/v8_4_lr_boost_v5_evidence_review.md` (#49
  evidence-pending state; §10 + §13 explicitly state "#49 remains
  open" / "#49 close criteria not met").
- `docs/postmortems/2026-05-02_event_journal_containment.md`
  (event-journal sink failure; informs anti-regression test in #51
  part B).
- `automations.yaml` Section 15 (`v8_5_hvac_provenance_logger`;
  current LR + bedroom + override timer + boost latch + SPI fire
  coverage).
- `tests/test_manual_override_contract.py` (the contract tests #86
  asked for; already passing).
- `tests/test_provenance_observability.py` (the provenance contract
  tests; already passing).
- `tests/test_safety_invariants.py` (partial coverage of #51 §A; to
  be extended in PR 3 above).
- `tests/test_msr_observability_boundary.py` (Apollo MSR boundary;
  already passing).

---

_End of Open Issue V9/V10 Validation Report._
