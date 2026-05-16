# 7-Day Nuisance Evidence Plan — Observability / Runtime Noise (Docs-Only)

**Date:** 2026-05-16  
**Status:** Planning artifact (no runtime changes)  
**Scope:** Evidence collection and interpretation only. No YAML edits, no threshold edits, no helper additions.

---

## 1) Purpose

Define a one-week measurement plan to determine whether specific observability/runtime surfaces are:

- **Noisy** (high volume with low operator value),
- **Stale** (rarely used, no current diagnostic utility), or
- **Worth keeping** (supports safety/forensics/integration diagnosis).

This plan is **not** a change request. It is an evidence gate before any modification proposals.

---

## 2) Hard Guardrails (Do Not Change Yet)

1. **Do not edit runtime YAML.**
2. **Do not change automations.**
3. **Do not change thresholds.**
4. **Do not add helpers.**
5. **Observability noise ≠ runtime failure.**
6. **Safety gates and integration-anomaly gates are not deletion candidates based on annoyance alone.**
7. **Any retirement requires all three:**
   - reference proof,
   - telemetry proof,
   - separate PR.

---

## 3) 7-Day Measurement Window

- **Window length:** 7 consecutive days.
- **Window start/end:** choose a clean midnight-to-midnight UTC or local window and record it explicitly in analysis notes.
- **Aggregation granularity:** daily + 7-day total.
- **Primary sinks:**
  - `hvac_provenance_log` tab,
  - Section 11 transition logger outputs (HA Logbook / corresponding telemetry),
  - HA notification/event traces for guardrail + anomaly automations,
  - existing sheet telemetry tabs already in production.

---

## 4) Metrics and Threshold Bands

> Bands are **nuisance triage bands**, not correctness bands. Crossing a nuisance band triggers review, not immediate runtime edits.

### M1 — Provenance Row Volume (Section 15, bedroom fan-out impact)

- **Metric name:** `m1_provenance_rows_per_day`
- **Data source:** `hvac_provenance_log` sheet rows/day.
- **How to calculate:**
  - Count rows written per day.
  - Also compute bedroom-share `%` for rows where source entity is Master/Lincoln/Lilly.
  - Track 7-day median and max.
- **Threshold bands (7-day):**
  - **Normal:** median ≤ 250 rows/day and max ≤ 400/day
  - **Watch:** median 251–450/day or any day 401–650
  - **Nuisance:** median > 450/day or any day > 650
- **Safe action if nuisance:**
  - Run attribution split (which trigger classes dominate: temperature attr changes vs hvac_mode changes vs season-mode writes).
  - Propose docs-only filtering candidates (future PR) without touching runtime.

### M2 — Transition Logger Volume (Section 11)

- **Metric name:** `m2_transition_events_per_day`
- **Data source:** Section 11 transition logger events/day.
- **How to calculate:**
  - Count transition events/day.
  - Compute ratio: `transition_events / total climate state changes observed`.
- **Threshold bands (7-day):**
  - **Normal:** 20–180/day and ratio 0.6–1.4
  - **Watch:** 181–300/day or ratio 1.41–1.8
  - **Nuisance:** >300/day or ratio >1.8
- **Safe action if nuisance:**
  - Identify duplicate logging patterns (same entity, same mode, short interval).
  - Draft dedupe hypotheses for later validation PR.

### M3 — Samsung Auto Guardrail Notification Count

- **Metric name:** `m3_auto_guardrail_notifications_per_day`
- **Data source:** HA notifications/logbook entries tagged to Samsung Auto Guardrail automation.
- **How to calculate:**
  - Count notifications/day.
  - Count distinct episodes (bursts within 10 minutes collapse to one episode).
- **Threshold bands (7-day):**
  - **Normal:** ≤ 2/day and ≤ 1 episode/day
  - **Watch:** 3–5/day or 2 episodes/day
  - **Nuisance:** > 5/day or > 2 episodes/day
- **Safe action if nuisance:**
  - Validate whether events correlate to real integration anomalies.
  - If mostly repetitive with no new operator decision value, open docs issue to evaluate notification hygiene in separate PR.

### M4 — Ghost Assassin Fire Count

- **Metric name:** `m4_ghost_assassin_fires_per_day`
- **Data source:** Ghost Assassin automation fire events from HA traces/logbook/provenance proxies.
- **How to calculate:**
  - Count fires/day.
  - Compute `% followed by meaningful state correction within 2 minutes`.
- **Threshold bands (7-day):**
  - **Normal:** 0–3/day with correction-rate ≥ 70%
  - **Watch:** 4–8/day or correction-rate 40–69%
  - **Nuisance:** >8/day or correction-rate < 40%
- **Safe action if nuisance:**
  - Classify fires into true anomaly recoveries vs repetitive no-value actions.
  - Keep safety/anomaly authority intact; only queue observability refinement discussion.

### M5 — Shade Command Frequency & No-op Prevention Quality

- **Metric name:** `m5_shade_command_efficiency`
- **Data source:** Shade automation command logs + resulting device state.
- **How to calculate:**
  - Count total shade commands/day.
  - Count no-op commands (`requested_state == current_state`).
  - Compute no-op rate = `no_op / total`.
- **Threshold bands (7-day):**
  - **Normal:** total ≤ 24/day and no-op rate < 15%
  - **Watch:** total 25–40/day or no-op rate 15–30%
  - **Nuisance:** total > 40/day or no-op rate > 30%
- **Safe action if nuisance:**
  - Produce command-path attribution (time windows, triggers, duplicate invocations).
  - Draft no-op suppression options as docs-only candidates for separate PR.

### M6 — Section 14 Boost Helper Usefulness

- **Metric name:** `m6_boost_helper_signal_value`
- **Data source:** Section 14 helper state changes + linked boost cycle outcomes in telemetry.
- **How to calculate:**
  - Count helper state transitions/day.
  - For each transition, classify whether it contributed to actionable interpretation of a boost cycle outcome (yes/no).
  - Compute signal-value rate = `actionable_transitions / total_transitions`.
- **Threshold bands (7-day):**
  - **Normal:** signal-value rate ≥ 60%
  - **Watch:** 35–59%
  - **Nuisance:** < 35%
- **Safe action if nuisance:**
  - Build reference map of who reads/writes each helper.
  - If low value persists, propose helper observability rationalization plan (docs-only) before any runtime edit.

### M7 — Compressor Cooldown Timer Usage References

- **Metric name:** `m7_cooldown_timer_reference_coverage`
- **Data source:** Existing telemetry/trace evidence where cooldown timers are referenced in logic and/or appear in event context.
- **How to calculate:**
  - Count cooldown timer start/active/finish observations/day.
  - Count linked control decisions where cooldown reference appears in context.
  - Compute linkage ratio = `linked_decisions / cooldown_observations`.
- **Threshold bands (7-day):**
  - **Normal:** linkage ratio ≥ 50% with at least 1 observation on ≥ 4 days
  - **Watch:** linkage ratio 25–49% or observations on only 2–3 days
  - **Nuisance:** linkage ratio < 25% or observations on ≤ 1 day
- **Safe action if nuisance:**
  - Treat as observability gap first (missing references/provenance), not control failure.
  - Open docs task for improved traceability evidence requirements in future PR.

---

## 5) Nuisance Triage Decision Rule (End of Day 7)

For each metric, classify final status:

- **Keep as-is:** stayed in Normal band.
- **Monitor:** entered Watch band but not Nuisance.
- **Investigate nuisance:** entered Nuisance band.

If **Investigate nuisance**:
1. Create a short evidence note with date-bounded counts and source links.
2. Confirm whether the surface is safety-related or integration-anomaly-related.
3. If yes, mark **non-retirement candidate** unless stronger proof exists.
4. Open a **separate docs/planning PR** for any proposed tuning or retirement criteria.

---

## 6) Explicit “Do Not Change Yet” Statement

During this 7-day plan:

- Do **not** remove automations.
- Do **not** disable safety gates.
- Do **not** disable Samsung Auto Guardrail.
- Do **not** disable Ghost Assassin.
- Do **not** alter shade thresholds/logic.
- Do **not** remove Section 14 helpers.
- Do **not** alter compressor cooldown timer behavior.

This period is strictly for evidence capture and nuisance classification.

---

## 7) Exit Criteria for Any Future Retirement Proposal

A surface can only be considered for retirement/tuning after this plan if all are present:

1. **Reference proof:** where it is used, who depends on it, and why dependency is safe to change.
2. **Telemetry proof:** 7-day (or longer) evidence showing persistent nuisance with low decision value.
3. **Separate PR:** dedicated change PR with regression risks and rollback path.

Absent all three, default action is **retain and continue observing**.
