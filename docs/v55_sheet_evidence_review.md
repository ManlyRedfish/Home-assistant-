# V5.5 Sheet Evidence Review (Operator Guide)

**Doc Date:** 2026-05-10
**Document Role:** Operator-facing guide for running the read-only V5.5
telemetry analysis script and interpreting its output.
**Status:** Documentation only. **No runtime change.** Companion script lives at
`tools/analyze_v55_telemetry.py`.

---

## 1. Purpose

This guide explains how to forensically review the live `Home Assistant` →
`5.5` (`VTherm_Launch_Data_v5_5`) telemetry tab without modifying anything.
It covers how to export the tab as CSV, how to run the analyzer, what the
verdict labels mean, and why this is strictly a sheet-side observation
exercise that **cannot** affect Home Assistant control.

It does **not** describe how to change automations, helpers, thresholds,
safety gates, the truth-sensor architecture, or the Section 14 boost layer.
For those, see `docs/v8_4_heating_recovery_boost_plan.md`,
`docs/5_runtime_layer.md`, and the YAML in `automations.yaml` /
`configuration.yaml`.

## 2. Scope Boundary

The analyzer and this guide:

- Only **read** a local CSV file you supply.
- Never connect to Home Assistant, ESPHome, or any device.
- Never authenticate to Google or write back to Google Sheets.
- Never require API keys, OAuth tokens, or other secrets.
- Cannot trigger automations, change helpers, or modify HVAC behavior.
- Cannot extend the Lincoln MSR fan-only exception (see
  `docs/apollo_msr_observability_checklist.md`).
- Cannot close issue #49.
- Cannot declare V8.4 boost effective on its own — only the strict verdict
  gate in §6 can produce a `VALIDATED_CANDIDATE`, and that gate is
  intentionally hard to clear.

This is the same observability-only doctrine carried forward from the V5
evidence review (`docs/analysis/v8_4_lr_boost_v5_evidence_review.md`).

## 3. Why Sheet-Side and Repo-Side Checks Are Different

Repo-side static tests (e.g. `tests/test_msr_observability_boundary.py`,
`tests/test_safety_invariants.py`) verify that the **YAML configuration**
respects doctrine: that automations do not promote MSR data into control,
that safety gates do not depend on observability sources, and that the
Lincoln fan-only exception is constrained.

Sheet-side analysis verifies that the **runtime data** the system has been
recording is consistent with what doctrine expects. Specifically, it asks
whether the V8.4 LR Heating Recovery Boost is producing measurable,
uncontaminated cycles in the live telemetry — a question that the YAML alone
cannot answer.

The two layers are complementary. A passing repo-side test does not imply a
clean runtime, and a clean runtime does not retroactively bless a YAML
change. Treat them as independent gates.

## 4. Exporting the Sheet Tab as CSV

The live workbook URL is:

`https://docs.google.com/spreadsheets/d/1URlWLkBYHYzuRcTvB32jPs_Fvs2bdDFn2L-sW3y10w8`

Tab to export: **`5.5`** (`VTherm_Launch_Data_v5_5`).

To export:

1. Open the workbook in your browser.
2. Click the `5.5` tab so it becomes the active worksheet.
3. **File → Download → Comma Separated Values (.csv)**.
4. Save the resulting file locally, for example as
   `Home_Assistant_5_5.csv`.

Notes:

- The CSV download includes only the active tab. If you accidentally
  download the `Home Assistant` workbook from a different active tab (e.g.
  `VTherm_Launch_Data_v5`), the analyzer will detect missing Section 14
  columns and gate the verdict to `NOT_VALIDATED_MISSING_COLUMNS`.
- Do not edit the CSV before running the analyzer. Header drift and inserted
  rows can break column synonym matching or split a boost cycle.
- The analyzer never uploads or transmits the CSV. It is a local file.

## 5. Running the Analyzer

The analyzer is a single Python script with no third-party dependencies. It
runs on any environment that already runs the repo's pytest suite.

```bash
python tools/analyze_v55_telemetry.py path/to/Home_Assistant_5_5.csv
```

By default the analyzer writes the markdown report to
`reports/v55_telemetry_evidence_review.md` and creates the `reports/`
directory if it does not already exist. Override with `--output`:

```bash
python tools/analyze_v55_telemetry.py Home_Assistant_5_5.csv \
    --output reports/2026-05-10_v55_review.md
```

To dry-run and print the report to stdout without writing a file:

```bash
python tools/analyze_v55_telemetry.py Home_Assistant_5_5.csv --no-write
```

The analyzer exits with status 0 on success and 2 if the CSV file is missing.

## 6. Verdict Labels

The analyzer emits exactly one of the following verdicts for V8.4 boost
effectiveness. Verdicts are intentionally conservative — `VALIDATED_CANDIDATE`
is the only optimistic label and it requires every condition below to hold.

| Label                              | Meaning                                                                                                                                                                                                                          |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `NOT_VALIDATED_NO_DATA`            | The CSV has no data rows.                                                                                                                                                                                                        |
| `NOT_VALIDATED_MISSING_COLUMNS`    | One or more required Section 14 columns are missing from the export. Likely cause: wrong tab exported, or the v5.5 schema header has not yet been deployed.                                                                      |
| `NOT_VALIDATED_CONTAMINATED`       | At least one detected boost cycle is contaminated by WAF, truth-unavailable, runaway floor breach, or ceiling breach.                                                                                                            |
| `NOT_VALIDATED_TOO_FEW_DAYS`       | Telemetry span is < 14 contiguous days. Even a clean dataset cannot validate boost effectiveness with too little history.                                                                                                        |
| `PARTIAL_EVIDENCE_NEEDS_REVIEW`    | No contamination found and span ≥ 14 days, but at least one cycle is indeterminate (truncated capture, `timeout`, `season_change`, missing fields), or LR truth did not stay within 68–72°F throughout the boost window.         |
| `VALIDATED_CANDIDATE`              | All boost cycles classified `clean`, span ≥ 14 days, and LR truth stayed within 68–72°F throughout each boost window. **This is a candidate, not a final verdict.** It still requires operator sign-off and #49 close criteria.  |

A note on the comfort-band check: doctrine sets the truth-cap at 67°F, so a
clean cycle releases LR truth around 67°F — below the 68–72°F band. The
analyzer therefore expects the band check to fail for most real cycles and
to gate the verdict to `PARTIAL_EVIDENCE_NEEDS_REVIEW`. This is the
intended conservative bias.

## 7. Cycle Classifications

For each detected boost cycle, the analyzer records a classification:

- `clean` — released by `truth_cap`, no WAF, no truth-unavailable, LR truth
  did not breach the runaway floor or ceiling, and the cycle was not
  truncated by the export window.
- `contaminated` — release reason is `waf` or `truth_unavailable`, or WAF
  was active during the cycle, or LR truth crossed below 60°F or above 76°F.
- `indeterminate` — release reason is `timeout`, `season_change`, blank, or
  unmapped, **or** the cycle is truncated at the start or end of the export
  window, **or** core fields are missing.

These classifications match the doctrine in
`docs/v8_4_heating_recovery_boost_plan.md` and the contamination rules in
`docs/telemetry_confounders.md`.

## 8. Lincoln MSR Fan-Only Exception (Observability Only)

The report includes a Lincoln MSR observability section that summarizes:

- `Lincoln_Presence_MSR` state distribution.
- `Lincoln_Temp_Diag_MSR`, `Lincoln_Pressure_Diag_MSR`, and
  `Lincoln_ESPTemp_Diag_MSR` min/max plus blank-row counts.

This section is **strictly observational**. It does not endorse extending
the Lincoln fan-only exception, promoting any MSR signal into VTherm truth,
or wiring MSR data into supervisor / Section 14 / safety / Section 2
control surfaces. Extending the exception requires:

1. A doctrine update in `docs/apollo_msr_observability_checklist.md`.
2. A matching allow-list change in
   `tests/test_msr_observability_boundary.py`.
3. Both landing in the same PR, per the existing PR Review Checklist.

This sheet-side report cannot grant any of those.

## 9. What This Report Cannot Do

- Cannot close issue #49.
- Cannot mark the V8.4 boost as effective on its own.
- Cannot compare cycles against a counterfactual baseline that the CSV does
  not contain.
- Cannot read `supervisor_state_log` (the operator narrative annotation
  tab); cycles overlapping `supervisor_disabled`, `manual_setpoint_nudge`,
  `waf_observed`, `truth_unavailable`, or `stale_setpoint_artifact`
  annotations should be re-classified manually before relying on this
  report.
- Cannot read `hvac_provenance_log` (machine provenance); `manual_user`
  origins overlapping a candidate cycle disqualify the cycle from a
  clean-window verdict.
- Cannot detect operator overrides that did not propagate through the
  manual-override timer.

If the operator wants any of those signals folded in, that is a future
followup for the V6 schema (`docs/v6_telemetry_schema_proposal.md` and
`docs/v6_observability_roadmap.md`), not for this docs-only PR.

## 10. Hard Constraints Honored

- Documentation and analysis only.
- No runtime YAML changes.
- No `automations.yaml` changes.
- No `configuration.yaml` changes.
- No Google Sheets write-back logic.
- No Home Assistant control changes.
- No MSR promotion.
- No declaration that V8.4 boost is effective unless the strict evidence
  gate passes.
- Conservative `not validated` is preferred over optimistic claims.

## 11. Cross-References

- `tools/analyze_v55_telemetry.py` — the script this guide describes.
- `docs/analysis/v8_4_lr_boost_v5_evidence_review.md` — V5 evidence review
  (with v5.5 addendum).
- `docs/v8_4_heating_recovery_boost_plan.md` — Section 14 design and
  thresholds.
- `docs/telemetry_confounders.md` — operator-suppressed-window classifier
  and `supervisor_state_log` annotation guidance.
- `docs/apollo_msr_observability_checklist.md` — MSR observability doctrine
  and Lincoln fan-only exception terms.
- `docs/5_runtime_layer.md` §7.4 — Section 14 V8.4 deploy status.
- `docs/v6_telemetry_schema_proposal.md`, `docs/v6_observability_roadmap.md`
  — where any future schema column work would live (this PR does not
  advance either).

---

_End of V5.5 Sheet Evidence Review (Operator Guide)._
