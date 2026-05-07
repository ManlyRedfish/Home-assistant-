# Telemetry Confounders — Operator-Suppressed Supervisor Windows

**Doc Date:** 2026-05-04
**Document Role:** Telemetry Analysis Guardrail
**Status:** Living. Update when a new confounder pattern is identified or when the
operator annotation practice changes.
**Scope:** Documentation only. Does not change runtime YAML, thresholds, safety gates,
or telemetry schema.

---

## 1. Purpose

This document warns analysts (human, Claude, Gemini, ChatGPT, future ops) that some
windows in `VTherm_Launch_Data_v5` reflect **operator-disabled supervisor state**, not
clean V8.3 Section 2 automation behavior. Drawing doctrine conclusions from those
windows is a category error: the supervisor was not running, so it cannot be blamed
for what happened.

Read this **before** citing any cold-drift, zero-runtime, or "Section 2 did/did not
do X" pattern from V5 as evidence.

## 2. Why this exists

On nights and days when sleep was disrupted, the operator has on occasion **manually
disabled** `automation.v7_5_main_supervisor` (the V8.3 Section 2 supervisor). When the
supervisor is disabled:

- Section 1 telemetry (`vtherm_mega_tracker_v5`) keeps writing rows every 15 minutes
  on its own time-pattern trigger. Sheets logging is unaffected.
- Section 2 stops issuing `set_temperature` / `set_hvac_mode` commands.
- Section 14 LR Heating Recovery Boost is independent — it can still engage off the
  truth-sensor numeric_state trigger if its conditions are met.
- Section 3 Safety Gates (LR runaway 60°F, Master floor 58°F, ceiling 76°F, SPI, WAF
  watcher) remain independent and active.

The operator did not historically annotate these disable windows. The V5 schema has
**no `Supervisor_Enabled` column**. Therefore the cleanest forensic signal that a
window was operator-suppressed is _behavioral_, derived from rows that V5 already
records.

## 3. The contaminated window: 2026-04-28 → 2026-05-01

This is the canonical operator-suppressed window in current telemetry.

| Day        | LR_HP_Runtime_Today_Hrs (max) | LR pattern across day                                                                                                      |
| ---------- | ----------------------------: | -------------------------------------------------------------------------------------------------------------------------- |
| 2026-04-29 |                      **0.00** | LR pinned `off@68` for 95/95 ticks; truth drifted 64.0 → 63.7°F                                                            |
| 2026-04-30 |                      **0.00** | LR pinned `off@68` for 96/96 ticks; truth drifted to 60.3°F                                                                |
| 2026-05-01 |                      **0.00** | LR pinned `off@68` for 96/96 ticks; truth held in low 60s; 56-tick stretch min 59.05°F (0.95°F above the LR runaway floor) |

Three consecutive days of zero LR heat-pump runtime in heating/shoulder season with
truth dropping into the low 60s **cannot be reconciled with V8.3 doctrine**:

- V8.3 heating doctrine commands `heat@68` when `LR_Temp_Truth < 64°F`
  (`automations.yaml` Section 2; Doc 1 §5.1).
- The supervisor would have issued `heat@68` on every 15-minute tick across these
  three days had it been running.
- It did not. Therefore the supervisor was not running.

**Apr 28–May 1 must be classified `operator_suppressed_likely` and excluded from any
analysis claiming Section 2 produced or failed to produce a behavior.**

## 4. Behavioral classification rules

Apply these rules row-by-row when analyzing a flagged window. Each rule depends only
on columns already in V5.

### 4.1 Strong proxy: zero daily LR HP runtime in heating/shoulder

If `LR_HP_Runtime_Today_Hrs` is **0.00** for an entire day during heating or shoulder
season, the supervisor was almost certainly disabled. V8.3 cannot produce zero LR
runtime if LR truth ever dipped below 64°F in that day, which it almost always does
in heating season.

### 4.2 Frozen-pattern proxy: LR mode `off`, SP `68`, no movement

If LR shows `(mode=off, setpoint=68)` across many consecutive ticks while LR truth
crosses below 64°F **without any single tick of `mode=heat`**, classify as
`operator_suppressed_likely`. Section 2 V8.3 with truth < 64°F issues `heat@68` on
every supervisor tick; a frozen `off@68` pattern means Section 2 did not run.

### 4.3 Non-doctrinal setpoint signature

LR setpoints of 60, 65, 71, 75, 77, or 80°F are **not** in V8.3 doctrine. The
supervisor only commands SP=68 (heating/shoulder daytime) or SP=64 (LR bedtime
18:00–22:00). Non-doctrinal setpoints indicate either:

- Operator manual setting (`waf_or_manual_override_possible`), or
- Section 14 boost (`SP=77` only — confirm against engage trigger).

`SP=77` predating Section 14 deployment (PR #21, 2026-05-02 evening) is operator
manual emulation, not Section 14.

### 4.4 Non-doctrinal Master/Lincoln/Lilly state during heating/shoulder

If Master is in `cool@61` or `fan_only@75`, or Lilly is in `fan_only@75`, during
heating or shoulder season, those modes are not Section 2 commands. Treat the window
as operator-managed.

### 4.5 Decision tree

| Signature                                                                                  | Class                                                |
| ------------------------------------------------------------------------------------------ | ---------------------------------------------------- |
| `LR_HP_Runtime_Today_Hrs = 0.00` for full day in heating/shoulder                          | `operator_suppressed_likely`                         |
| Frozen `(off, 68)` across many ticks while truth < 64°F                                    | `operator_suppressed_likely`                         |
| Non-doctrinal SP (60/65/71/75/80) appearing on LR without Section 14 latch evidence        | `waf_or_manual_override_possible`                    |
| Section 14 boost confirmed (`SP=77` post-2026-05-02 with engage edge)                      | `boost_engaged` (separate analysis from §2 doctrine) |
| Doctrinal SP (68 daytime / 64 LR bedtime) with mode movement on `:00, :15, :30, :45` ticks | `clean_auto`                                         |
| None of the above                                                                          | `unknown`                                            |

## 5. What this means for forward analyses

1. **Do not promote `operator_suppressed_likely` rows to `clean_auto` without an
   operator annotation** explicitly confirming the supervisor was enabled across
   that window.
2. **Do not derive Section 2 doctrine conclusions** (e.g., "the 64°F engage threshold
   is too low," "Section 2 has a heating night-default defect") from contaminated
   windows. Doctrine claims require clean-window evidence.
3. **Section 14 boost evaluation is also affected.** Every Section 14 engage cycle
   observed through 2026-05-04 was terminated externally (within minutes of engage)
   by operator-side state — WAF, manual setpoint nudge, or truth_unavailable —
   rather than by `truth_cap` (67°F) or the 90-minute timeout. The boost mechanism's
   actual recovery effectiveness is therefore **still unmeasured**, and any verdict
   beyond "engage path fires correctly" is premature.
4. **Cross-doc drift risk.** If a future doc (Doc 4 / Operations Sheet, a postmortem,
   a regression entry) cites Apr 28–May 1 as evidence of Section 2 behavior, that
   doc is wrong and should be corrected against this confounder note.

## 6. Operator Annotation Practice

To prevent the same confounder from contaminating future analyses, the operator must utilize the out-of-band forensic workflow.

For the full design and schema of this out-of-band workflow, refer to the [Operator Annotation Design (`docs/operator_annotation_design.md`)](operator_annotation_design.md).

The event journal infrastructure was **retired and removed** after the sink failed
to register. Do not re-introduce observers or attempt a new event-journal write path
on the strength of this annotation need without a proven HA-compatible sink.

## 7. Hard constraints carried forward

This document does not change:

- Section 2 Main Supervisor.
- Section 3 Safety Gates.
- Section 14 LR Heating Recovery Boost.
- Truth-sensor weights or staleness rules.
- Telemetry schema (`VTherm_Launch_Data_v5`).
- Any threshold (64°F engage, 67°F truth_cap, 90-min timer, 60°F runaway,
  58°F floor, 76°F ceiling).
- The removal of EJ observers and the `script.log_event` no-op.

If a future proposal materially relaxes any of the above, that proposal must be
evaluated against `docs/3_regression_appendix.md` reopen conditions, not against this
doc.

## 8. Cross-references

- `docs/apollo_msr_observability_checklist.md` — Validation checklist outlining MSR observability constraints.
- `docs/1_startup_canon.md` §5.1 — V8.3 heating doctrine (the doctrine that
  contaminated windows must not be evaluated against).
- `docs/3_regression_appendix.md` §4.4 — "Preemptive Living Room Suppression Without
  Evidence" reopen rule. Apr 28–May 1 is **not** evidence for that reopen.
- `docs/5_runtime_layer.md` §7.4 — Section 14 V8.4 status (updated separately to
  reflect that engages have now occurred but every cycle was contaminated).
- `docs/v8_4_heating_recovery_boost_plan.md` §10.5, §11.1 — Section 2 latch-guard
  reopen criteria. The "Section 2 overwrite" hypothesis is **weakened**, not
  strengthened, by current evidence; the latch-guard PR remains deferred.
- `docs/postmortems/2026-05-02_event_journal_containment.md` §9 — evidence pipeline
  while the event journal is contained.
- GitHub Issue #31 — the originating context for this doc.

---

_End of Telemetry Confounders Doc._
