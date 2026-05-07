# V8.4 LR Boost — V5 Evidence Review

**Review Date:** 2026-05-07
**Document Role:** Forensic evidence review of Section 14 (V8.4) boost cycles
against the live `VTherm_Launch_Data_v5` Google Sheets workbook and its prior
versioned tabs.
**Status:** Evidence-only. Docs-only. **No runtime change. #49 remains open.**

---

## 1. Purpose

This document preserves the evidence review performed against the live Moose
House telemetry workbook on 2026-05-07. It exists to answer the narrow
question: *given the data actually recorded in the Google Sheets workbook, can
Section 14 (V8.4) LR heating-recovery-boost effectiveness be measured today?*

The answer this review reaches is **no — effectiveness remains unmeasured.**
That verdict is consistent with `5_runtime_layer.md` §7.4 and
`telemetry_confounders.md` §5, which both already state the boost mechanism's
actual recovery effectiveness is unmeasured. This document supplies the
underlying tab-by-tab evidence.

This review is **not**:
- A claim that V8.4 boost is effective.
- A proposal to close #49.
- A modification to runtime behavior, automations, configuration, or ESPHome.

## 2. Workbook Located

The Google Drive / Sheets MCP found the live **"Home Assistant"** workbook in
the operator's Google Drive (last modified 2026-05-07). It is the active
telemetry sink referenced from `automations.yaml` Section 1
(`vtherm_mega_tracker_v5`) and `5_runtime_layer.md` §6.

The workbook is treated as **read-only evidence**. No values were written or
modified. Schema observations describe what already exists in the workbook;
they are not a proposal to change it.

## 3. Tabs Found

The workbook contains **five versioned VTherm telemetry tabs**:

| Tab | First Timestamp | Last Timestamp | Data Rows |
|---|---|---|---|
| `VTherm_Launch_Data` (original) | 2026-03-06 18:07 | 2026-03-10 17:15 | 376 |
| `VTherm_Launch_Data_v2` | 2026-03-10 17:27 | 2026-03-14 17:30 | 385 |
| `VTherm_Launch_Data_v3` | 2026-03-14 17:40 | 2026-04-03 20:15 | 2,325 |
| `VTherm_Launch_Data_v4` | 2026-04-04 11:24 | 2026-04-16 13:30 | 1,161 |
| `VTherm_Launch_Data_v5` | 2026-04-16 13:38 | 2026-05-07 09:15 | 2,550 |

- **Total span:** 2026-03-06 through 2026-05-07.
- **Total data rows analyzed:** **6,797**.
- **Live runtime tab:** `VTherm_Launch_Data_v5` (per `5_runtime_layer.md` §6).
- **All older tabs are archival.** They are not written to by live automations.

## 4. Cross-Version Schema Map (LR-relevant logical fields)

| Logical field | Original | v2 | v3 | v4 | v5 | Notes |
|---|---|---|---|---|---|---|
| Timestamp | `Timestamp` | `Timestamp` | `Timestamp` | `Timestamp` | `Timestamp` | Stable |
| LR truth temperature | `LR_Hub_Temp` (single-probe proxy) | `LR_Hub_Temp` (proxy) | `LR_Temp_Truth` | `LR_Temp_Truth` | `LR_Temp_Truth` | Fused truth output first appears in v3 |
| LR air setpoint | `LR_Air_Setpoint` | same | same | same | same | Stable across versions |
| LR HVAC mode | `LR_Air_Mode` | same | same | same | same | `heat`/`cool`/`off` |
| LR HVAC action | `LR_Air_Action` | same | same | same | same | Cloud-path field; `None` in nearly all rows |
| LR HP runtime today | `LR_HP_Runtime_Today_Hrs` | same | same | same | same | Day-cumulative; resets at midnight |
| LR truth sensor count | — | — | `LR_Truth_Count` | `LR_Truth_Count` | `LR_Truth_Count` | Added v3 |
| LR primary BT probe | `LR_Hub_Temp` | `LR_Hub_Temp` | `LR_Hub_Temp` | `LR_Hub_Temp` | `LR_Temp_RoomProbe_BT_Primary` | Renamed v5 (Semantic Heritage) |
| LR ST hub probe | — | — | — | — | `LR_Temp_RoomProbe_ST` | New v5 |
| LR Samsung internal | `LR_Air_Internal_Temp` | same | same | same | `LR_Temp_HVAC_Samsung` | Renamed v5 |
| Season mode | — | — | — | `Season_Mode` | `Season_Mode` | First appears v4 |
| Away mode | — | — | — | `Away_Mode` (often `None`) | `Away_Mode` | First appears v4; v4 values unreliable |
| Night mode | — | — | — | `Night_Mode_Toggle` | `Night_Mode_Toggle` | First appears v4 |
| **Section 14 boost latch** | **absent** | **absent** | **absent** | **absent** | **absent** | **No telemetry column for `input_boolean.lr_heating_recovery_boost_active`.** |
| **Section 14 boost timer** | **absent** | **absent** | **absent** | **absent** | **absent** | **No telemetry column for `timer.lr_heating_recovery_boost_max_runtime`.** |
| **Section 2 supervisor enabled** | **absent** | **absent** | **absent** | **absent** | **absent** | **Not exported.** |
| Manual override timer | absent | absent | absent | absent | absent | Not exported as a column |
| Operator/manual setpoint clue | setpoint value only | same | same | same | same | Inferred from non-doctrinal SP per `telemetry_confounders.md` |

Older tabs are useful for **baseline history** only. v5 is the only tab that
spans the known May Section 14 boost timestamps.

## 5. Known May Section 14 Boost Cycles (v5)

All four engage timestamps recorded in `5_runtime_layer.md` §7.4 were located in
the v5 tab. Setpoint, mode, runtime, season, and away values at each engage
tick:

| Known engage timestamp | LR_Temp_Truth | LR_Air_Setpoint | LR_Air_Mode | LR_HP_Runtime_Today_Hrs | Season_Mode | Away_Mode |
|---|---|---|---|---|---|---|
| 2026-05-03 04:45 | 64.83 °F | 77.0 | `heat` | 2.35 hrs | heating | off |
| 2026-05-03 11:45 | 64.91 °F | 77.0 | `heat` | 7.05 hrs | heating | off |
| 2026-05-04 10:00 | 64.03 °F | 77.0 | `heat` | 3.35 hrs | shoulder | off |
| 2026-05-04 13:30 | 63.88 °F | 77.0 | `heat` | 3.37 hrs | shoulder | off |

Each engage row is consistent with a Section 14 trigger condition (LR truth
sub-65 °F, setpoint at the 77 °F doctrinal boost value, mode commanded to
`heat`, away off). This matches the `5_runtime_layer.md` §7.4 statement that
the engage path fired four times.

### 5.1 May 3 cycles are single-row captures

Both 2026-05-03 04:45 and 2026-05-03 11:45 appear as a **single 15-minute row**
each at `LR_Air_Setpoint = 77`. The next captured 15-minute row in each case
already shows the setpoint reverted (back to 60 / 71 in surrounding context).
Within the recorded 15-minute telemetry resolution, there is **no observable
boost arc** — no captured pre-boost LR_Truth, no captured mid-boost
trajectory, no captured post-boost recovery to the 67 °F truth-cap target.

Both cycles are consistent with the postmortem note that observed cycles were
terminated externally within minutes (presumed WAF or `truth_unavailable`), not
by `truth_cap` or the 90-minute timeout.

### 5.2 May 4 is the best available candidate, and it is weak

The 2026-05-04 setpoint=77 window is the longest contiguous boost-coded
interval in v5: 22 rows from 10:00 through 15:15. The HP runtime counter
behavior across that window is the determinative signal:

| Time | LR_Temp_Truth | LR_Air_Setpoint | LR_Air_Mode | LR_HP_Runtime_Today_Hrs |
|---|---|---|---|---|
| 10:00 | 64.03 | 77 | heat | 3.35 |
| 10:15 | 63.68 | 77 | off | 3.36 |
| 11:00 | 63.17 | 77 | off | 3.36 |
| 12:00 | 63.17 | 77 | off | 3.36 |
| 13:00 | (None) | 77 | off | 3.36 |
| 13:30 | 63.88 | 77 | heat | 3.37 |
| 14:00 | 63.87 | 77 | off | 3.38 |
| 15:15 | 64.85 | 77 | off | 3.38 |

`LR_HP_Runtime_Today_Hrs` advanced from **3.35 → 3.38** across the entire
~5-hour boost-coded window — a delta of approximately **0.03 hours, or about
two minutes** of cumulative HP runtime. `LR_Air_Mode` was `off` for 20 of the
22 rows. LR_Truth was null at 13:00 and 13:15.

The boost setpoint was held, but the heat pump did not run for any sustained
period during the window. The recorded runtime-counter delta is too small to
constitute a heating cycle from which recovery effectiveness could be inferred.

## 6. No Dedicated Section 14 Boost Telemetry Exists

Across all five tabs, **no column exists** for any of the following Section 14
state variables:

- `input_boolean.lr_heating_recovery_boost_active` (the boost latch).
- `timer.lr_heating_recovery_boost_max_runtime` (the 90-minute boost timer).
- Section 2 supervisor enabled state.
- An explicit "boost engaged" / "boost released" edge marker.
- A `truth_cap` reach indicator.

Boost identification in the workbook therefore relies entirely on
`LR_Air_Setpoint = 77` as a proxy signal, plus the rules in
`telemetry_confounders.md` §3.4 (post-2026-05-02 SP=77 implies Section 14
candidate; pre-deployment SP=77 was operator manual emulation). This proxy is
sufficient to **locate** boost candidates but not sufficient to **confirm**
that the latch was set, when it released, or whether the release was via
`truth_cap`, the 90-minute timeout, or external/manual interruption.

This is a recording-coverage observation about the workbook's columns. It is
not a proposal to add columns now. Telemetry-schema work belongs to the V6
schema proposal (`docs/v6_telemetry_schema_proposal.md`) and the V6
observability roadmap (`docs/v6_observability_roadmap.md`); this review does
not advance either.

## 7. Baseline Windows (older tabs and v5)

Cold LR windows where `LR_Temp_Truth < 64 °F` and `LR_Air_Setpoint ≠ 77` were
located across all tabs that record `LR_Temp_Truth`:

| Tab | Baseline rows | Min LR_Truth | Guardrails available | Confidence |
|---|---|---|---|---|
| `VTherm_Launch_Data` (original) | 102 | 59.90 °F | None (no Season/Away; LR_Truth is single-probe proxy) | Low |
| `VTherm_Launch_Data_v2` | 124 | 58.46 °F | None (proxy LR_Truth) | Low |
| `VTherm_Launch_Data_v3` | 506 | 55.00 °F | None (no Season/Away) | Medium-low |
| `VTherm_Launch_Data_v4` | 71 | 60.42 °F | Season ✓; Away unreliable | Medium |
| `VTherm_Launch_Data_v5` | 245 | 59.05 °F | Season ✓; Away ✓; same schema epoch as boosts | High |

The strongest v5 baseline windows occur as overnight cold drifts on dates
**without** Section 14 engages — for example, the 2026-05-01 overnight window
where LR_Truth fell to 59.05 °F at 09:45 with `LR_Air_Setpoint = 68`,
`LR_Air_Mode = off`, `LR_HP_Runtime_Today_Hrs = 0`, `Season_Mode = heating`,
`Away_Mode = off`.

These baselines are clean as standalone overnight drifts. They are **not
clean pair-matched** to the May 3–4 boost engages: baseline cold troughs
occur in the early-morning hours (typically 02:00–10:00) at deeper cold
temperatures, while the May 4 boost engaged at 10:00 from a starting LR_Truth
of 64.03 °F that had already partially recovered from the morning low. There
is no day in v5 with matched time-of-day, matched starting LR_Truth, matched
Season_Mode, matched Away_Mode, and a Section 14 engage — and a corresponding
counterfactual day with the same conditions and **no** engage — from which a
causal recovery-time delta could be computed.

The schema gap described in §6 also limits baseline pairing: even where the
matching conditions exist, there is no recorded boost-state column to confirm
that a candidate "non-engage" baseline did not, in fact, briefly engage and
release within a 15-minute capture interval.

## 8. May 6 Setpoint=77 Window — Disqualified

A 32-row window on 2026-05-06 from 14:00 through 22:00 carries
`LR_Air_Setpoint = 77`. The window is **disqualified** as a Section 14
boost-effectiveness data point:

- `LR_HP_Runtime_Today_Hrs` is `0.0` for every row in the window.
- `LR_Air_Mode` is `off` for every row.
- `LR_Temp_Truth` (where present) ranges 68.41 °F to 69.44 °F — well above the
  Section 14 engage threshold and well above the 67 °F truth-cap target.
- LR_Truth is null for the first 13 rows of the window (14:00–17:00).

No heating occurred. The setpoint persisted at 77 °F without HP activity in a
warm room. The pattern is consistent with a stale or stuck setpoint artifact
(setpoint helper holding 77 °F after a prior engage cleared, or a setpoint
that was not reset by the release path), not with an active V8.4 boost cycle.
This window is mentioned here only to document its disqualification — not as
evidence for or against effectiveness.

A separate followup may be warranted to investigate why `LR_Air_Setpoint`
remained at 77 in this window. That followup is out of scope for this
docs-only review.

## 9. Verdict

**Effectiveness remains unmeasured.**

The V5 evidence does not permit a measurement of Section 14 boost
effectiveness. Specifically:

- Two of the four known engages (May 3 04:45 and May 3 11:45) are
  single-row captures with no observable arc.
- The best contiguous engage window (May 4 10:00–15:15) records only
  ~0.03 hours of cumulative HP runtime advancement across the entire
  ~5-hour boost-coded interval.
- No tab records the Section 14 boost latch, boost timer, supervisor enabled
  state, or release-cause edge. Boost detection in v5 relies on the
  `LR_Air_Setpoint = 77` proxy alone.
- Baseline windows of comparable depth exist but cannot be pair-matched on
  time-of-day, starting LR_Truth, Season_Mode, and Away_Mode against the
  observed engages.
- One additional setpoint=77 window on 2026-05-06 is disqualified as a
  stale-setpoint artifact (zero HP runtime, mode off, truth above target).

This review **does not contradict** the existing `5_runtime_layer.md` §7.4 and
`telemetry_confounders.md` §5 verdicts. It corroborates them with the
underlying row-level evidence.

## 10. #49 Close Criteria Not Met

For the same reasons in §9, the criteria required to close issue #49 are not
satisfied by current V5 evidence. In particular:

- Fewer than three clean uncontaminated boost cycles are observable.
- No pair-matched baseline comparison is possible from current columns.
- No confirmation of release-cause (truth_cap, timeout, or external
  interruption) is recorded.

Issue #49 remains open. This review does not propose to close it.

## 11. Hard Constraints Honored by This Review

- Docs-only.
- No modification of `automations.yaml`.
- No modification of `configuration.yaml`.
- No modification of any ESPHome YAML.
- No change to any runtime behavior or helper.
- No change to the workbook (read-only evidence access).
- No claim that V8.4 boost is effective.
- No closure of issue #49.

## 12. References

- `docs/5_runtime_layer.md` §7.4 — Section 14 V8.4 deploy status and the
  prior unmeasured-effectiveness statement.
- `docs/telemetry_confounders.md` §3.4, §5 — `SP=77` interpretation rules and
  the unmeasured-effectiveness verdict.
- `docs/v8_4_heating_recovery_boost_plan.md` — V8.4 design (status note at
  top supersedes the event-journal portions).
- `docs/postmortems/2026-05-02_event_journal_containment.md` — evidence
  pipeline guidance for Section 14 validation.
- `docs/v6_telemetry_schema_proposal.md`, `docs/v6_observability_roadmap.md` —
  where any future telemetry-column additions to support boost-state recording
  would be discussed (this review does not advance either).

## 13. Addendum (issue #62 / v5.5 schema)

This addendum was added after the issue #62 implementation PR. The body of
this review (§1 through §12) describes the state of evidence at the time
of the original 2026-05-07 analysis and is **left unchanged**. The §6
finding that no Section 14 boost-state columns existed in the workbook was
correct as of that date and applies to the historical `VTherm_Launch_Data_v5`
tab in perpetuity.

**What changed:**
- Issue #62 added Section 14 boost-state observability columns going
  forward, in a new wide-table interim schema `VTherm_Launch_Data_v5_5`.
  The original `VTherm_Launch_Data_v5` tab remains historical and is no
  longer written to.
- The new columns (`Section14_Boost_Active`, `Section14_Timer_State`,
  `Section14_Timer_Remaining`, `Section14_Last_Engage_Reason`,
  `Section14_Last_Release_Reason`, `Section14_Last_Engage_At`,
  `Section14_Last_Release_At`, `Section14_Engage_Eligible`,
  `Section14_WAF_Active`, `Section14_Truth_Available`) are populated by
  the same 15-minute export plus by Section 14 action-block writes to
  four new helpers (two `input_text`, two `input_datetime`).
- Section 14 control logic, triggers, conditions, thresholds (64 °F engage,
  67 °F truth_cap, 77 °F demand setpoint, 90-minute timer), and climate /
  timer / latch effects were **not** changed. The new helpers are written
  AFTER the existing control actions complete.

**What does not change:**
- Historical rows in `VTherm_Launch_Data_v5` (and prior tabs) remain
  inferential for Section 14 cycle classification — they still rely on
  the `LR_Air_Setpoint = 77` proxy described in §6.
- The four cycles enumerated in §5 (2026-05-03 04:45, 2026-05-03 11:45,
  2026-05-04 10:00, 2026-05-04 13:30) cannot be retroactively classified
  by release cause from current evidence.
- The verdict in §9 — **effectiveness remains unmeasured** — is unchanged
  by this addendum. v5.5 starts collecting the data needed for a future
  measurement; it does not retroactively supply that measurement.
- The verdict in §10 — **#49 close criteria not met** — is unchanged.
  Issue #49 remains open. v5.5 enables the future evidence pipeline that
  could eventually satisfy the #49 criteria; this addendum does not.

**Forward path:** with v5.5 active, future Section 14 cycles will record
their engage cause, release cause, and timestamps directly. Once ≥3 clean
cycles per the #49 criteria accumulate, an effectiveness verdict can be
written using direct boost-state telemetry rather than setpoint inference.
