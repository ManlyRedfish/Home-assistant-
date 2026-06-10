# V8.3 Four-Zone Cooling Supervisor — Architecture Audit

**Audit date:** 2026-06-09
**Scope:** Read-only audit pass (no runtime change). Evidence packet: Hermes
"Opus Handoff" Blocks 1–5.
**Primary subject:** `automation.v7_5_main_supervisor` — alias
*"V8.3: Main Supervisor (Deadband Cooling + Heating)"* (`automations.yaml:358`).
**Verdict:** **No runtime changes required.** The YAML correctly implements the
verified cooling design. Two known, intentionally-deferred gaps are reconfirmed
and one documentation/implementation mismatch is newly surfaced — all advisory.

---

## a) Design explanation — does the YAML implement the verified design?

**Yes, for everything the supervisor actually owns.** The cooling branch matches
the doctrine that `tests/test_section2_cooling_setpoint_doctrine.py` pins
verbatim.

### Cooling deadband + setpoint (Branch 1, `automations.yaml:401-492`)
Per-zone logic, evaluated every run:

```
hvac_mode = cool      if  truth_temp >  on_at
          = off       if  truth_temp <= off_at
          = <hold>    otherwise   (keep prior cool/off state)
temperature = 61      (always commanded)
```

- **61 °F stored target — CONFIRMED.** `m_setpoint = l_setpoint = ly_setpoint =
  lr_setpoint = {{ 61 }}` (`automations.yaml:419,439,459,480`). The 61 °F command
  is *actuator demand*, intentionally below the off threshold so the unit pulls
  down decisively and shuts off on truth, not on a weak near-setpoint crawl
  (design note `automations.yaml:393-397`).
- **68 / 72 deadband — CONFIRMED for the normal (home) case**, but the handoff's
  "uniform 68–72 across all four zones" is a **simplification**. The real,
  test-locked thresholds are mode-dependent:

  | Zone | off_at | on_at | Source |
  |---|---|---|---|
  | Living Room | `74 if away else 68` | `76 if away else 72` | `automations.yaml:481-482` |
  | Lincoln | `74 if away else 68` | `76 if away else 72` | `automations.yaml:440-441` |
  | Lilly | `74 if away else 68` | `76 if away else 72` | `automations.yaml:460-461` |
  | Master | `74 if away else (62 if is_master_sleep else 68)` | `76 if away else (66 if is_master_sleep else 72)` | `automations.yaml:420-421` |

  `is_master_sleep = now().hour >= 18 or now().hour < 6` (`automations.yaml:418`).
  So Master runs a tighter **62/66 sleep band 18:00–06:00** and the standard
  **68/72** during the day. This is intentional doctrine, not a defect
  (test asserts these exact templates).

- **Hysteresis / hold — CONFIRMED.** Between thresholds the zone holds its prior
  state via `{% elif <x>_current == 'cool' %}cool {% else %}off`, reading the
  live `climate.*_air` state. State-retention is genuine, not a universal
  on/off.

### Household-mode behavior
- **Season gate — CONFIRMED.** Cooling commands live only inside the
  `season == 'cooling'` branch (`automations.yaml:401-403`). `shoulder` and
  `heating` are separate branches.
- **Away — CONFIRMED as setback (not hard-off).** Away relaxes thresholds to
  74/76 and keeps the 61 command; a zone still cools if truth > 76. (Handoff
  Block 4 Test 7 allows "or setback per design" — this is the setback path.)
- **Nest / Dining Room — CONFIRMED forced off.** First action of the cooling
  branch is `climate.set_hvac_mode → climate.dining_room: off`
  (`automations.yaml:406-408`). Dining Room is never sent a cool command
  anywhere.

### Items the handoff expected but the supervisor does *not* implement
- **Night mode (LR):** `lr_night_primary` is computed (`automations.yaml:379`)
  but in the **cooling** branch it is **unused**. It only changes behavior in
  the **heating-season night** branch (`automations.yaml:625`). Handoff Test 9
  ("night_mode_lr_primary modifies LR thresholds") therefore **does not apply to
  cooling season** — no effect there.
- **15-min compressor cooldown:** **Not implemented in the control path** — see
  Finding 1 below.

---

## b) Entity dependency map

### Supervisor reads (inputs)
| Variable | Entity read | Default if unavailable |
|---|---|---|
| `outdoor` | `sensor.deck_temperature_truth` | `50` |
| `lr_temp` | `sensor.living_room_temperature_truth` | `70` |
| `master_temp` | `sensor.master_bedroom_temperature_truth` | `70` |
| `lincoln_temp` | `sensor.lincoln_s_room_temperature_truth` | `70` |
| `lilly_temp` | `sensor.lilly_s_room_temperature_truth` | `70` |
| `season` | `input_select.hvac_season_mode` | — |
| `away` | `input_boolean.away_mode` | — |
| `lr_night_primary` | `input_boolean.night_mode_lr_primary` | — |
| `*_current` | live `climate.*_air` state | — |
| gate | `timer.manual_hvac_override` (must be `idle`) | condition fails ⇒ no run |

### Supervisor writes (outputs)
`climate.living_room_air`, `climate.master_bedroom_air`, `climate.lincoln_air`,
`climate.lilly_air`, `climate.dining_room` (off-only in cooling).

### Intermediate template entities (definitions in `configuration.yaml`)
```
Physical sensors
  → sensor.*_temperature_truth        (weighted fusion, 7200 s staleness)   :243-270, etc.
      → sensor.*_temperature_smoothed  (lowpass, time_constant=10, prec 2)   :1089-1143
          → sensor.*_temperature_control (UI/"supervisor" wrapper)           :938-1006
binary_sensor.*_heat_pump_firing       (template; state ≠ off/unavail)       :175-189
timer.*_compressor_cooldown            (15 min helpers — defined, unused)    :123-138
```
**Critical routing fact:** the supervisor (and every Section 3 safety gate)
reads **`sensor.*_temperature_truth` (raw truth)**. The `_smoothed` and
`_control` layers are **not** in any automation's read path — they feed only the
HA UI. (See Finding 3.)

---

## c) Failure modes that could affect equipment safety

| # | Failure mode | Behavior | Severity | Likelihood |
|---|---|---|---|---|
| C1 | **Truth sensor `unavailable`/all-stale (>2 h) while a unit is cooling** | `float(70)` default ⇒ temp treated as 70 °F ⇒ supervisor **holds** current state (70 is inside the deadband). Simultaneously the runaway-60 °F and Master-floor-58 °F gates are `numeric_state` triggers that **cannot fire** on a non-numeric truth. Net: a cooling unit can keep running to its 61 °F demand with no truth-based shutoff until the sensor recovers. | Moderate | Low |
| C2 | **No compressor anti-short-cycle interlock** (Finding 1) | Each 15-min tick may flip a zone off→cool→off if truth dances across a threshold; nothing enforces a minimum off-time at the supervisor. The 15-min tick cadence and lowpass smoothing on the *display* sensors are the only damping; the *control* sensor is raw truth (Finding 3), so the intended smoothing is not applied to control. | Low–Moderate | Low |
| C3 | **Supervisor disabled / crashed** | Climate entities retain last commanded state (Samsung holds). Comfort updates stop, but the three independent Section 3 gates (runaway 60, Master floor 58, ceiling 76) and Ghost Assassin remain armed. No new unsafe command is issued. | Low | Low |
| C4 | **Firing sensor unavailable** | No safety logic depends on `binary_sensor.*_heat_pump_firing`; they only feed runtime history_stats/telemetry. Control unaffected. | Negligible | Low |
| C5 | **Manual-override helper missing/never idle** | Supervisor condition `timer.manual_hvac_override == idle` would be false ⇒ supervisor never acts. Helper is UI-defined (not in repo YAML — see Unknowns). | Moderate | Very low |

None of C1–C5 is a *new* regression introduced by the current YAML; C1 and C2
are inherent to the truth-default + no-cooldown design and are the most worth
operator attention.

---

## d) Acceptance / failure-test results (Handoff Block 4)

### Acceptance tests
| # | Test | Result | Evidence |
|---|---|---|---|
| 1 | Deadband state-retention, all 4 zones | **PASS** | hold via `*_current` (`:429,449,469,490`) |
| 2 | Off→Cool only when on-threshold satisfied | **PASS** | `temp > on_at` (`:427,447,467,488`) |
| 3 | Cool→Off only when off-threshold satisfied | **PASS** | `temp <= off_at` |
| 4 | Equality-boundary inspection | **PASS (documented)** | `> on_at` (strict) and `<= off_at` (inclusive). At **exactly off_at ⇒ OFF**; at **exactly on_at ⇒ HOLD**. Hold band is `(off_at, on_at]`. |
| 5 | Dining Room forced off in cooling | **PASS** | `:406-408` |
| 6 | Season gate (≠cooling ⇒ no cool) | **PASS** | branch guard `:402-403` |
| 7 | Away mode | **PASS (setback, per design)** | 74/76 thresholds, not hard-off |
| 8 | Compressor cooldown linkage | **FAIL — not implemented** | no automation references `timer.*_compressor_cooldown` (Finding 1) |
| 9 | Night mode (LR) modifies LR | **N/A in cooling** | `lr_night_primary` only used in heating-night `:625` |

### Failure-mode tests
| # | Test | Result |
|---|---|---|
| 1 | Supervisor crash ⇒ no stuck-unsafe | **PASS** (gates independent; see C3) |
| 2 | Firing sensor unavailable ⇒ still functions | **PASS** (C4) |
| 3 | Truth stale >2 h rejected | **PARTIAL** — staleness *availability* logic is correct (`:248-257`), but the supervisor's `float(70)` fallback means a fully-unavailable truth sensor yields a "hold at 70" rather than a fail-to-safe-off (C1) |
| 4 | Season toggled mid-cooling ⇒ cooling stops | **PASS** — `input_select` change is a trigger (`:364-365`); next evaluation leaves the cooling branch |
| 5 | Away during cooling ⇒ zones off within a cycle | **PARTIAL/PASS** — away is *setback to 74/76*, not forced-off; zones below 74 do go off next tick |
| 6 | Cooldown prevents forced restart | **FAIL — no cooldown enforcement** (Finding 1) |

---

## e) Findings & migration steps

### Finding 1 — Compressor cooldown timers are orphaned (KNOWN / intentional)
`timer.lr_/master_/lincoln_/lilly_compressor_cooldown` (15 min) are defined
(`configuration.yaml:123-138`) but **no automation starts or checks them**
(verified by repo-wide grep; only references are the definitions, the nuisance
export list, and comments). The supervisor has **no minimum-off-time enforcement**.

This is **already documented and intentionally deferred**, not a silent defect:
- `docs/analysis/open_issue_v9_v10_validation.md:817` — "Compressor cooldown
  timers are orphaned helpers … no automation references any of these timers."
- `docs/6_proposals.md:16` — isolated 15-min per-unit cooldown timers are
  **"design-only doctrine"** under V9, "does not weaken any existing Section 3
  safety gate."
- `docs/7_day_nuisance_evidence_plan.md` §M7 tracks reference-coverage.

**Migration:** **None in this pass.** Wiring cooldown enforcement is V9 scope
with its own design constraints (decoupled control loops, event-time accounting,
`docs/event_telemetry_plan.md:481`). Implementing it here would exceed the audit
objective and pre-empt the V9 decision. *Recommend:* leave as-is; let V9 own it.

### Finding 2 — Handoff "uniform 68/72" understates Master's sleep/away bands
Not a YAML defect — a packet simplification. The YAML's mode-dependent Master
band (62/66 sleep, 68/72 day, 74/76 away) is correct and test-locked.
**Migration:** None. (Operator doc note only: update the handoff's "verified
topology" to reflect the Master sleep band so future audits don't flag a false
discrepancy.)

### Finding 3 — Supervisor reads raw `_truth`, not the documented `_control` wrapper (NEW)
`configuration.yaml:36` and the Section 10 header (`:927-936`) state
*"Smoothed output → control wrapper → V8.3 supervisor"* and that the wrappers
exist *"so the V8.3 supervisor … can manage them."* In fact the supervisor reads
`sensor.*_temperature_truth` directly (`automations.yaml:373-376`); the
`_smoothed` (lowpass) and `_control` layers feed only the UI. The stated
short-cycling benefit of smoothing (`truth_sensor_architecture.md:106-121`) is
therefore **not applied to control decisions**.

This is a **documentation/implementation mismatch**, and it means the only
control-loop damping is the 15-min tick cadence (Finding 1 / C2).
**Migration options (DEFERRED — do not apply without operator decision):**
- *(Doc-only, low risk)* Correct the `configuration.yaml` comments to say the
  control/smoothed wrappers are **UI-only** and the supervisor consumes raw
  truth; or
- *(Behavioral, NOT this pass)* Repoint the supervisor reads to
  `sensor.*_temperature_control` to actually engage smoothing. This **changes
  control behavior** and regression comparability and must go through the
  evidence/telemetry process — out of scope for an audit pass.

---

## f) Rollback

No runtime files were modified by this audit (docs-only). If any of the deferred
migrations above are later applied:
1. Git backup confirmed present (clean tree at audit time; supervisor unchanged).
2. Pre-change supervisor logic captured above and in trace
   `run_id 2cc51682fc628808ecb3a00c6b499204` (Handoff Block 2).
3. Revert any change with `git checkout -- automations.yaml configuration.yaml`
   (or restore the corresponding lines) and re-run `python -m pytest tests/`.
4. Confirm `tests/test_section2_cooling_setpoint_doctrine.py` and
   `tests/test_safety_invariants.py` pass post-rollback.

---

## g) Codex implementation prompt

**No changes required — audit complete.**

The V8.3 supervisor accurately implements the verified cooling design (68/72
deadband with documented Master sleep/away bands, 61 °F stored target,
hysteresis state-retention, season/away gating, Dining Room forced-off). The
only non-conformances to the handoff's expectations are:
- the 15-min compressor cooldown (Finding 1) — **knowingly orphaned, V9-deferred
  by existing doctrine**; and
- the smoothing/control-wrapper read path (Finding 3) — a **documentation**
  mismatch.

Neither warrants a Codex change in an audit pass. If the operator later elects to
act on Finding 3's doc-only correction or any V9 cooldown work, that requires a
separate, explicitly-approved change request with before/after telemetry — not an
audit deliverable.

---

## Unknowns — NOT silently resolved
| Unknown | Why | What would resolve it |
|---|---|---|
| `input_select.hvac_season_mode` option list, `input_boolean.away_mode/night_mode_lr_primary`, `timer.manual_hvac_override` definitions | UI/storage helpers — not in repo YAML | Read live HA `.storage` / helper registry |
| Handoff `automation.v7_5_main_supervisor_rev_b` vs actual id `v7_5_main_supervisor` | "_rev_b" suffix not in repo | Confirm live entity_id in HA |
| Trace generic var names `_off_at/_on_at/_current` vs YAML `m_/l_/ly_/lr_` | Handoff likely normalized names; values (61/68/72) match | Compare raw trace JSON to YAML var names |
| Lincoln 0.35 °F gap (truth 71.77 vs trace 71.42) | Most likely temporal (truth updated between trace and read), **not** smoothed-vs-raw since control reads raw truth (Finding 3) | Time-aligned truth history at trace timestamp |
| Master/Lilly presence sensors, `is_master_sleep` "presence" | `is_master_sleep` is purely time-based (`hour>=18 or <6`), no presence entity involved | n/a — resolved: time-based |
