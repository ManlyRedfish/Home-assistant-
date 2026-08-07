# Manual Override & V9-E Pre-Cool — Runtime/Doctrine Reconciliation

**Doc Date:** 2026-08-07
**Document Role:** Canonical reconciliation note. It aligns the documentation
corpus with the observed `automations.yaml` commit history for two facts that
several canon docs still describe as live: the `timer.manual_hvac_override`
gate and the V9-E Master Pre-Cool runtime experiment.
**Status:** Living documentation. Docs-only. This note changes **no** runtime,
YAML, helper, threshold, setpoint, truth weight, telemetry schema, or safety
gate. It does **not** propose a replacement manual-override mechanism.
**Scope discipline:** Where an older doc still reads as if the timer or the
V9-E experiment is live, that doc's wording is *historical* as of the commits
named below. This note is the single place that records the delta; it does not
rewrite each downstream doc's body.

---

## 1. Why this note exists

The `docs/` corpus was written while two mechanisms were live. Both were later
removed in `automations.yaml`, but the prose was not fully reconciled. An agent
reading only the canon docs would conclude that (a) comfort-policy automations
still stand down on a manual setpoint nudge via `timer.manual_hvac_override`,
and (b) the Master Pre-Cool experiment is still running. Neither is true in the
current runtime. This note draws the line between five distinct states so no
future agent treats stale prose as runtime truth (per
[`3_regression_appendix.md`](3_regression_appendix.md) §5 "Live YAML outranks
prose for runtime truth").

The five states this note separates:

1. **Current runtime** — what `automations.yaml` at `main` actually does.
2. **Historical behavior** — what used to run, now removed, preserved for lineage.
3. **Deferred doctrine** — open owner decisions (Issues #87, #89) framed around
   a mechanism that no longer exists; they are *not* resolved by this note.
4. **Removed experiment** — V9-E Master Pre-Cool control, deleted from Section 2.
5. **Telemetry / helper remnants** — inert helpers, export columns, and stale
   in-line comments that survive the removals and must not be mistaken for live
   control.

---

## 2. The two reconciled commits

| Commit | Date | What it did (verified from `git show --stat` + body) |
|---|---|---|
| `cc720ab` | 2026-07-11 | *"remove manual_hvac_override timer + switch to smoothed truth."* Deleted the WAF automation `v7_5_waf_manual_override` and **all 11** `timer.manual_hvac_override` references from `automations.yaml`: the supervisor top-level gate, Section 6, Section 16, GSPI, and the Section 14 LR boost release. `configuration.yaml` byte-for-byte unchanged. Removed WAF tests. |
| `f1724e9` | 2026-07-09 | *"Packet B Stage 0 …"* Removed the **entire V9-E Master Pre-Cool block** (variables, state writes, template consults) from Section 2 and from the shoulder-night Master block. Deferred per operator decision — non-functional (cannot concentrate compressor with kids' heads running). Also removed `lilly_heatwave_sleep_guard` / `is_lilly_sleep`; added per-zone `*_truth_ok` guards. |

Both are the operator's own commits (`ericmanly@gmail.com`). This note records
the consequences; it does not re-open either decision.

---

## 3. Manual override — current runtime vs. historical

### 3.1 Current runtime (authoritative)

- **No live automation references `timer.manual_hvac_override`.** A repo-wide
  grep of `automations.yaml` returns only one match, a stale *comment* at
  `automations.yaml:447` (Section 3 header text). No trigger, condition, or
  action reads or writes the timer.
- The **Section 2 supervisor gates only on `input_boolean.heat_wave_override`
  being `off`** (`automations.yaml:399-401`). That is a comfort-vs-operator-
  override gate for the Section 19 Heat Wave Override — a *different*
  mechanism with a different helper (`timer.heat_wave_override_96h`), not a
  reinstated WAF timer.
- Consequently, **the manual-override contract as previously documented is not
  enforced by any live control path.** A parent-less setpoint nudge no longer
  starts a timer and no comfort-policy automation stands down because of one.
- The Section 14 boost **release** no longer triggers on the timer going
  `active` (that trigger was among the 11 removed); its release path is now
  driven by its own boost-latch/timeout logic only.

### 3.2 Historical behavior (removed, retained for lineage)

Before `cc720ab`, the contract was: the WAF watcher
`v7_5_waf_manual_override` detected a parent-less context setpoint change on
any of the four climate entities and started a 1-hour
`timer.manual_hvac_override`; comfort-policy automations (Section 2 supervisor,
76°F ceiling gate, Section 6 destratification, Section 8 Samsung Auto
Guardrail, Section 14 boost engage) gated on `== idle`; true safety gates (60°F
LR runaway, 58°F Master floor) did not. This is the behavior described in
[`5_runtime_layer.md`](5_runtime_layer.md) §7.8, [`v9_v10_goals.md`](v9_v10_goals.md)
§2.3 / §7, [`1_startup_canon.md`](1_startup_canon.md), and
[`3_regression_appendix.md`](3_regression_appendix.md) §4.14–§4.16. **Read those
passages as historical unless independently re-verified against current YAML.**

### 3.3 Owner decision this surfaces (not resolved here)

The removal leaves a **doctrine gap**: the corpus still treats a manual-override
contract as governing doctrine (e.g. §4.15 forbids comfort policy from
overriding manual intent), but the runtime that enforced it is gone. This note
**does not invent a replacement**. Whether to (a) formally retire the contract,
(b) restore a WAF-style ingest, or (c) adopt a different manual-intent surface
is an **owner-level decision** left to Eric. It is flagged here and cross-linked
from the Issue #87 and #89 decision briefs because both issues were written
around the now-absent timer.

---

## 4. V9-E Master Pre-Cool — removed experiment vs. remnants

### 4.1 Removed (authoritative)

`f1724e9` deleted the entire V9-E Master Pre-Cool control block from Section 2
and its references from the shoulder-night Master block. **No pre-cool control
runs today.** [`v9_v10_goals.md`](v9_v10_goals.md) §2.6 still reads
*"Status: LIVE (runtime exception)"* — that status line is **stale**; the
experiment is removed. Its inherited *"supervisor's
`timer.manual_hvac_override == idle` gate"* clause is doubly stale (the timer is
also gone).

### 4.2 Helper / automation remnants (inert)

- `automations.yaml` Section 16 `v9e_precool_nightly_reset` (`automations.yaml:2236`)
  **still fires daily at 22:00**, writing `input_boolean.precool_aborted_tonight`,
  `input_number.precool_runtime_counter`, `input_number.precool_previous_master_temp`,
  and `input_text.precool_abort_reason`. These are **helper writes with no live
  reader** — the control block that consumed them is gone. The automation is an
  inert remnant: it re-arms an envelope that no longer opens.
- The corresponding `configuration.yaml` Section 16 `precool_*` helpers and the
  six `Precool_*` Section 1 export columns persist as telemetry/helper remnants.

These remnants are **documented, not modified** (YAML is out of scope for this
docs-only lane). Their cleanup is a separate, out-of-scope runtime decision.

---

## 5. Stale-reference index

Each row is a place where the corpus still describes a removed mechanism as
live. Category legend: **H** = historical (pre-`cc720ab` contract), **X** =
removed V9-E experiment, **R** = inert remnant, **C** = stale in-line comment.
This index is the reconciliation surface; downstream doc bodies are not
individually rewritten.

| Location | Category | Stale claim | Reconciled reading |
|---|---|---|---|
| `5_runtime_layer.md` §7.8 table (`v7_5_main_supervisor`, ceiling, Section 6, Section 8, Section 14 rows) | H | "Gates on `timer.manual_hvac_override`? → Yes" | Historical. No such gate exists post-`cc720ab`. See §3.1. |
| `5_runtime_layer.md` §7.8 `v7_5_waf_manual_override` row | H | "Starts `timer.manual_hvac_override`" | Automation deleted in `cc720ab`. |
| `5_runtime_layer.md` §7.4 (Section 14 status) | H | Boost cycles "terminated externally … presumed WAF" | WAF ingest removed; external-termination cause is now unattributable to WAF. Governs Issue #91 exclusion rules. |
| `v9_v10_goals.md` §2.3, §7 | H | Enumerated paths "gate on `timer.manual_hvac_override == idle`" | Historical contract. |
| `v9_v10_goals.md` §2.6 | X | "Status: LIVE (runtime exception)" for V9-E | Removed in `f1724e9`. |
| `v9_v10_goals.md` §8 | H | "Suppressed by override timers" as a safety-gate prohibition | Timer no longer exists; prohibition is moot but retained as doctrine intent. |
| `1_startup_canon.md` | H | "Manual override contract: `timer.manual_hvac_override` …" | Historical. |
| `3_regression_appendix.md` §4.14, §4.15, §4.16 | H | Contract framed on the timer being live | Doctrine intent preserved; enforcement mechanism removed. |
| `deferred_until_telemetry.md` (#89 row) | H | "yield to `timer.manual_hvac_override`" | Reframe per Issue #89 brief — gate no longer exists. |
| `event_telemetry_plan.md` (`waf_state`, `waf_started`, `waf_expired`) | H/R | Proposed rows sourced from timer state | Source entity removed; proposal unbuildable as written. |
| `hvac_provenance_logger_design.md` (WAF / timer observers) | H | Observes `v7_5_waf_manual_override` + timer flips | Both removed; those observers have nothing to observe. |
| `automations.yaml:447` | C | Comment: "manual_hvac_override … gates on the supervisor above are all preserved" | Stale comment; no gate remains. (Not edited — YAML out of scope.) |
| `configuration.yaml:153` | C | Comment contrasts 96h timer with "`timer.manual_hvac_override` (which is a 1-hour WAF timer)" | References a removed timer for contrast only; harmless but stale. |
| `automations.yaml:2236` (Section 16) | R | Nightly re-arm of V9-E envelope | Inert remnant; envelope removed. See §4.2. |

---

## 6. What this note deliberately does NOT do

- Does **not** propose or invent a replacement manual-override mechanism.
- Does **not** pick doctrine for Issue #87 (SPI) or Issue #89 (integration-anomaly
  gates). Those remain owner decisions; see the decision briefs.
- Does **not** modify `automations.yaml`, `configuration.yaml`, helpers,
  thresholds, or tests.
- Does **not** delete the V9-E remnants; that is a separate runtime decision.
- Does **not** rewrite the body of each stale doc; §5 is the reconciliation of
  record.

## 7. Cross-references

- [`issue_91_collision_measurement_plan.md`](issue_91_collision_measurement_plan.md)
  — four-week Section 2 ↔ Section 14 collision quantifier (uses the §3.3 WAF
  removal to constrain exclusion rules).
- [`decision_brief_issue_87_spi.md`](decision_brief_issue_87_spi.md)
- [`decision_brief_issue_89_integration_gates.md`](decision_brief_issue_89_integration_gates.md)
- [`5_runtime_layer.md`](5_runtime_layer.md) §7.4, §7.8
- [`v9_v10_goals.md`](v9_v10_goals.md) §2.3, §2.6, §7, §8
- [`3_regression_appendix.md`](3_regression_appendix.md) §4.15–§4.18
- [`deferred_until_telemetry.md`](deferred_until_telemetry.md)
</content>
</invoke>
