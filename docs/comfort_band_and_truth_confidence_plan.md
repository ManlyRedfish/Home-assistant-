# Comfort Bands & Sensor-Truth Confidence — Planning Proposal

**Doc Date:** 2026-06-02
**Document Role:** Analysis + first-PR planning proposal (comfort-band supervisor + truth-confidence model).
**Status:** Proposal. Planning only. Does **not** change runtime YAML, thresholds, safety gates, helpers, telemetry schema, or any control authority.
**Scope discipline:** This document is written to satisfy the Moose House docs-first / evidence-first doctrine ([`1_startup_canon.md`](1_startup_canon.md) §7, [`v9_v10_goals.md`](v9_v10_goals.md) §11). It proposes a future PR; it is not that PR.

---

## Executive Summary

Moose House already behaves like a deadband supervisor in principle — the live
doctrine explicitly says "deadbands are the comfort contract" and that "the
commanded Samsung setpoint is actuator-demand, not comfort truth." The gap is
**not** philosophy; it is **structure and graceful degradation**:

1. **Comfort bands are hardcoded numeric literals** scattered across ~12 inline
   Jinja templates in one giant `choose:` block in `automations.yaml` Section 2
   (`v7_5_main_supervisor`). There is no comfort-*profile* abstraction, no
   household-profile selector, and no single place that expresses "Eric Cold"
   vs "Family Normal." The numbers are also tuned warm relative to Eric's stated
   meat-locker preference (cooling OFF at 68, ON at 72; heating day target 68).

2. **Sensor truth degrades as a cliff, not a slope.** Freshness is computed with
   `last_changed` + a 2-hour `max_age`, which is the exact bug Eric flagged: a
   stable sensor that reports the same temperature for >2h is treated as stale
   even when its transport is perfectly healthy. When `fresh.count` hits 0 the
   truth entity goes `unavailable` and the supervisor silently substitutes
   `float(70)` — a single binary "healthy → 70°F fallback" with no `degraded` /
   `fallback` middle states and no confidence signal.

3. **Samsung internal thermistors can currently make truth "available."** The
   `living_room_air_temperature` (Samsung, weight 0.20) is counted in the
   `fresh.count > 0` availability test. So a Samsung-only room currently reports
   as healthy truth, contradicting Eric's "Samsung is low-confidence fallback,
   not comfort truth" intent.

4. **Telemetry/forensics is heavily overbuilt; the comfort-control layer is
   underbuilt.** Sections 1, 14, 15, plus ~10 analysis/telemetry docs exist for
   observability and provenance. There is no comfort-profile model and no truth
   *confidence/status* surface at all.

The recommended first PR is **docs + tests + helper-schema definition only**.
It adds a comfort-profile doctrine, a truth-confidence model
(`healthy/degraded/fallback/failed`), and regression tests that **assert the
intended invariants without changing any runtime behavior**. The freshness
`last_changed` → `last_reported` correction is identified as the single
candidate "low-risk correction," but it is still deferred to a second,
narrowly-scoped runtime PR because it touches live availability of every truth
sensor.

---

## Findings

### Where current comfort bands are defined

| Location | What it holds | Form |
|---|---|---|
| `automations.yaml` Section 2 `v7_5_main_supervisor` (id `v7_5_main_supervisor`, alias "V8.3") | Every comfort band for every room/season/time branch | **Hardcoded numeric literals** inside inline Jinja `variables:` blocks (e.g. `m_setpoint: "{{ 74 if away else (61 if is_master_sleep else 66) }}"`, `lr_off_at: "{{ 74 if away else 68 }}"`, heating `master_temp < 67`, bedtime LR `64`/`62-64`). |
| `docs/1_startup_canon.md` §5.1 | Comfort Contract doctrine: "setpoint 68, off ≤68, on >72"; Master sleep 62-66; away 74-76; V8.3 heating top-anchored 68/off≥68/on<64; bedtime LR 64. | Prose doctrine |
| `docs/5_runtime_layer.md` §6.1 | Same bands, restated as runtime snapshot. | Prose |
| `docs/comfort_failure_forensics.md` §8.6 "Section 2 branch expectation table" | A complete per-branch ON/OFF/setpoint transcription of the live YAML. | Reference table (descriptive, YAML wins) |

**Key fact:** there is no profile abstraction and no helper. Bands cannot be
changed without editing supervisor Jinja, and there is exactly one implicit
profile ("the house") with per-room/season/time special cases baked in.

### Where current truth sensors are defined

`configuration.yaml` (V3.1 truth layer), per-room template sensors:

- `sensor.<room>_temperature_truth` (weighted average, `availability:` gate)
- `sensor.<room>_humidity_truth`
- `sensor.living_room_co2_truth` (3h staleness, MSR CO2, observability)
- `sensor.<room>_temperature_truth_contributors` (LR, Lincoln — fresh source names)
- `sensor.<room>_temperature_truth_active_count` (LR, Lincoln)
- `sensor.lincoln_temperature_truth_rejected` (outlier diagnostics — Lincoln pilot)
- downstream: `..._smoothed` (lowpass) → `..._control` wrappers.

**There is NO `_truth_confidence` and NO `_truth_status` sensor anywhere**
(confirmed by grep). Contributors + active_count are the only existing
"how-healthy" surfaces, and they are diagnostics, not a graded status.

### Where freshness / staleness / failure logic exists

All in `configuration.yaml`, inside each truth sensor's `availability:` and
`state:` templates. The universal pattern:

```jinja
{% set max_age = 7200 %}                 {# 2 hours; CO2 uses 10800 #}
{% set hub = states('sensor.hub_temperature') | float(none) %}
{% if hub is not none
   and (now() - states.sensor.hub_temperature.last_changed).total_seconds() < max_age %}
  {% set fresh.count = fresh.count + 1 %}
{% endif %}
...
{{ fresh.count > 0 }}                     {# availability: 1+ fresh source #}
```

Findings:

- **`last_changed` is the freshness clock everywhere.** `last_reported` is used
  *nowhere* in the repo. `last_changed` only advances when the **value**
  changes, so a thermally stable room (sensor reporting the same value) ages out
  at 2h and is dropped — exactly the false-stale failure Eric described. The
  correct signal for "is this sensor still talking" is `last_reported` (or
  `last_updated`), not `last_changed`.
- **Failure is binary.** `availability` returns `fresh.count > 0`. When it is
  false the entity becomes `unavailable`; there is no `degraded`/`fallback`
  state. The Truth Sensor Architecture doc and Startup Canon §4 both *assert*
  graceful degradation, but the implementation expresses only "≥1 source" vs
  "no sources."
- **The supervisor's only degradation handling is `float(70)`.** Section 2 reads
  `states('sensor.living_room_temperature_truth') | float(70)`. A failed truth
  injects a silent 70°F, which (per the forensics doc) generally resolves
  branches to `off`. This is a hidden behavior with no confidence signal and no
  band-widening.

### Where Samsung / mini-split sensor values are used

- **In truth fusion:** `sensor.<room>_air_temperature` (Samsung internal) is a
  weighted contributor — temp weight `0.20`, humidity `0.25` — and **is counted
  in the `fresh.count` availability test**. Therefore a Samsung-only room
  currently produces *available* (effectively "healthy") truth. The weighting
  is correctly low, but availability does not distinguish "real sensors present"
  from "only the biased internal thermistor present."
- **As actuator command:** Section 2 issues `climate.set_temperature` setpoints
  that are explicitly documented as "actuator-demand, not comfort truth" (lines
  ~368-371). This part already matches Eric's intent.
- **Anomaly gates:** `v8_samsung_auto_guardrail` (Section 8) forces off rogue
  Samsung `auto`; `v7_5_ghost_assassin` (Section 4) suppresses phantom heat.

### Where safety gates are enforced

`automations.yaml` Section 3:

| id | Threshold | Class | Gates on override? |
|---|---|---|---|
| `v8_2_lr_runaway_cooling_cutoff` | LR truth `< 60°F` while cooling | **True safety** (equipment) | No |
| `v8_2_master_emergency_floor` | Master truth `< 58°F` while cooling | **True safety** (equipment) | No |
| `v7_5_safety_ceiling_gates` | room truth `> 76°F` | **Comfort** ceiling (per doctrine) | Yes (`idle`) |
| `v9_sleep_priority_interlock` | Master cool + LR heat, LR `> 60°F` | **Ambiguous** interlock | No |
| `v7_5_waf_manual_override` | climate change w/o parent context | Manual-intent ingest | n/a |

The 58°F/60°F floors are also depended on by the supervisor's heating branches
as "backstops live in Section 3" comments — comfort and safety are *documented*
as separate but the heating branch's LR `60` setpoint and the Section 3 `60`
runaway sit close together (see Risk Analysis).

### Where existing tests already cover these topics

| Test | Covers | Relevance |
|---|---|---|
| `tests/test_safety_invariants.py` | LR 60°F + Master 58°F triggers exist and force `off` | **Safety floor lock.** Must keep passing untouched. |
| `tests/test_section2_cooling_setpoint_doctrine.py` | Pins exact cooling Jinja strings (`m_setpoint == "{{ 74 if away else (61 if is_master_sleep else 66) }}"`, etc.) | **Literal-string lock** on current hardcoded bands — any profile refactor breaks this and must update it in the same PR. |
| `tests/test_supervisor_shoulder_night.py` | Shoulder-night Master cooling escape | Band regression guard. |
| `tests/test_truth_entity_registry_integrity.py` | Canonical truth/smoothed/control IDs not ghosted/`_2`/unavailable; fixtures `ha_states_truth_entity_{healthy,broken}.json` | **Reusable harness** for the new truth-status tests. |
| `tests/test_msr_observability_boundary.py` | MSR/Apollo entities cannot enter control (except Lincoln fan-only) | Locks goal #4. |
| `tests/test_manual_override_contract.py` | Override gating classification | Comfort-vs-safety separation. |
| `tests/test_provenance_observability.py` | `hvac_provenance_log` is HA-write-only | Observability discipline pattern. |

**No test currently asserts:** comfort bands ≠ safety floors as *values*;
Samsung-only ≠ healthy; degraded widens/blocks; ESP-down ≠ total failure; or
that a stable (unchanging) reading is not stale.

---

## Proposed Doctrine

A new doctrine layer that sits **above** the existing deadband contract without
replacing it. The existing deadband doctrine ([`1_startup_canon.md`](1_startup_canon.md)
§5.1) becomes the *per-profile* expression of bands rather than a single global
band set.

1. **A comfort profile is a named band-set, not a thermostat target.** The
   system does nothing while room truth is inside the active profile's band. It
   acts only on band exit. (This is already the deadband contract; the change is
   making the band-set a selectable named object.)
2. **Samsung setpoints are actuator commands, never comfort truth.** (Already
   doctrine; restated and test-locked.)
3. **One global profile selector first.** Start with a single house-wide
   `input_select` profile, not per-room profiles. Per-room/per-occupant profiles
   are explicitly deferred (consistent with the retired "room-isolation-first"
   and "over-architected arbitration before need" warnings in
   [`3_regression_appendix.md`](3_regression_appendix.md) / Startup Canon §7).
4. **Comfort bands are preferences; safety gates are physical protection.** They
   may never share a threshold definition. A test must assert numeric
   separation.
5. **Truth has a confidence/status, and control reacts to it.** Degraded truth
   should widen bands or block aggressive action rather than acting on a thin or
   biased source. Failed truth should hold/safe rather than inject a hidden
   sentinel.

### Proposed profiles (draft — numbers NOT final)

These are doctrine/test *shapes*, not implementation requirements. Eric's draft
numbers carried in as the starting point:

| Profile | heat_on_at | heat_off_at | cool_on_at | cool_off_at | Notes |
|---|---|---|---|---|---|
| `eric_cold` (Meat Locker) | 58–60 | 61–63 | 66 | 64–65 | Eric's default. Coldest comfort profile. |
| `family_normal` | 64 | 66 | 70 | 68 | Matches the *current* live cooling band (off 68 / on ~70-72). |
| `sleep_cold` | ~58–60 | ~61–63 | 66 | 64 | Mirrors `eric_cold`; room-specific (Master) deferred. |
| `away_relaxed` | 58 (protect) | 62 | 76 | 74 | House protection + energy, not comfort. Mirrors current `away` numbers. |
| `safety_only` | — | — | — | — | Comfort bands disabled; only Section 3 emergency cutoffs + structural protection remain. |

Invariant for every profile: `heat_on_at < heat_off_at ≤ cool_off_at <
cool_on_at`, and all comfort thresholds strictly **above** the Section 3 safety
floors (heat_on_at > 60°F LR runaway and > 58°F Master floor). `safety_only`
disables comfort action entirely.

---

## Sensor Truth Model

Add **two** new derived outputs per room alongside the existing
`contributors`/`active_count` diagnostics (which become inputs to status):

| Entity | Type | Meaning |
|---|---|---|
| `sensor.<room>_temperature_truth` | (exists) | The weighted value. Unchanged in PR1. |
| `sensor.<room>_temperature_truth_contributors` | (exists) | Fresh source names. Reused. |
| `sensor.<room>_temperature_truth_confidence` | **new** | Numeric 0.0–1.0 (or 0–100). Driven by count + class of fresh primary sources, agreement spread, and whether only fallback/biased sources remain. |
| `sensor.<room>_temperature_truth_status` | **new** | `healthy` / `degraded` / `fallback` / `failed`. |

### Status definitions (proposed)

| Status | Rule | Control reaction (deferred to a later PR) |
|---|---|---|
| `healthy` | ≥2 valid **primary** sources (Matter / BT / SmartThings) fresh and within tolerance of each other | Normal bands. |
| `degraded` | exactly 1 valid primary source, **or** primary + fallback only | Widen bands / block aggressive moves (e.g., suppress turbo pulldown). |
| `fallback` | only Samsung/mini-split internal **or** held-last-good value remains | No aggressive action; hold; surface alert. Samsung-only is **never** `healthy`. |
| `failed` | no usable source | No new comfort command; hold last safe; alert. (Safety gates still independent.) |

### Source classes

- **Primary:** Matter sensors, Bluetooth probes, SmartThings/SwitchBot hubs
  (the human-space sensors that already carry weight 0.9–1.0).
- **Fallback (low confidence):** Samsung/mini-split internal thermistor
  (weight 0.20). Always biased; useful only when nothing else is fresh.
- **Experimental / observability-only:** Apollo / MSR / ESP temperature,
  DPS310, CO2, radar, pressure. **Not** promoted to control (goal #4). May
  appear in `contributors` as clearly-marked experimental, or in a separate
  `sensor.<room>_temperature_truth_observers` listing, but never raise
  confidence into `healthy` and never feed the weighted value.

### Freshness correction (the core technical finding)

- Replace `last_changed` with `last_reported`/`last_updated` for the
  "is this sensor still reporting" test, so a stable unchanging reading is not
  mistaken for a dead sensor. Keep value-sanity (`float(none) is not none`) and
  source-specific availability (entity not `unavailable`/`unknown`) as separate
  checks.
- For ESP/Apollo sources, prefer source-specific availability (the integration's
  own `unavailable` state) over a generic age test, because they "need
  hand-holding."

**Why this is still deferred to its own runtime PR:** changing the freshness
clock changes the live `availability` of every truth sensor — a strict
behavior change — so it ships separately from the docs/tests PR, with its own
before/after telemetry comparison, per regression doctrine.

---

## Comfort Band Model

### Proposed band variable / helper names

Phase target is a **single global profile** plus per-profile band numbers in
helpers, leaving the supervisor's structure intact at first:

```
input_select.comfort_profile        # eric_cold | family_normal | sleep_cold |
                                     # away_relaxed | safety_only

# Per active-profile bands (global, not per-room yet):
input_number.comfort_heat_on_at
input_number.comfort_heat_off_at
input_number.comfort_cool_on_at
input_number.comfort_cool_off_at
```

Supervisor-internal Jinja variable names (when a later PR rewires Section 2)
stay consistent with the existing convention so diffs stay readable:
`*_on_at`, `*_off_at`, `*_setpoint` (e.g. `lr_cool_on_at`, `lr_heat_off_at`).

### Decision pipeline (Eric's architecture, mapped to entities)

```
Room Truth            sensor.<room>_temperature_truth (+ _confidence/_status)
   ↓
Comfort Profile       input_select.comfort_profile → band numbers
   ↓
Band Decision         hysteresis: act only on band exit; hold inside band;
/ Deadband            confidence/status may widen or block
   ↓
Actuator Command      climate.set_temperature/set_hvac_mode (Samsung = actuator)
```

### Degraded / fallback behavior (proposed, deferred)

- `healthy`: normal profile bands.
- `degraded`: widen bands by a fixed margin (e.g. +1–2°F hysteresis) and/or
  forbid aggressive pulldown setpoints; act conservatively.
- `fallback`: no comfort action beyond holding; rely on Section 3 only; alert.
  Replaces today's hidden `float(70)` with an explicit, observable posture.
- `failed`: issue no new comfort command; safety gates remain fully independent.

---

## Safety Invariants

These must not change in any comfort/truth PR:

1. `v8_2_lr_runaway_cooling_cutoff` — LR truth `< 60°F` → LR `off`. Threshold and
   action locked by `test_safety_invariants.py`. **Do not retune toward comfort.**
2. `v8_2_master_emergency_floor` — Master truth `< 58°F` → Master `off`. Locked.
3. Safety gates do **not** gate on `timer.manual_hvac_override`; comfort policy
   does. (Manual Override Contract, [`5_runtime_layer.md`](5_runtime_layer.md) §7.8.)
4. Apollo / MSR / ESP stay observability-only (except the locked Lincoln
   fan-only exception). Locked by `test_msr_observability_boundary.py`.
5. Comfort bands may never be defined with the same value/identity as a safety
   floor. New test will assert every comfort `heat_on_at` stays strictly above
   the 60°F/58°F floors.

### Where comfort and safety are currently entangled (flagged, not fixed)

- **76°F ceiling gate** (`v7_5_safety_ceiling_gates`) lives in Section 3 (the
  "safety" section) but is doctrinally a **comfort** ceiling and gates on
  override. It is mislocated by section, correctly classified by doctrine. The
  profile model should treat 76°F as a per-profile comfort ceiling, not a safety
  invariant — but moving it is out of scope for PR1.
- **Heating-night LR `60°F` setpoint** (supervisor) sits one degree from the
  Section 3 LR `60°F` runaway. They are different mechanisms (comfort target vs
  equipment cutoff) but share a number; the profile doctrine should keep comfort
  `heat_on_at` strictly above the runaway so they never alias.
- **`v9_sleep_priority_interlock`** remains the canonical ambiguous interlock —
  do not reclassify it in this work.

---

## Recommended First PR

**Title:** `Define Moose House comfort bands and sensor-truth confidence model`

**Type:** Docs + tests + helper-schema definition only. **No** change to
`automations.yaml` runtime logic, no change to live truth `availability`/`state`
templates, no threshold change, no safety change.

### Exact files likely to change

| File | Change | Kind |
|---|---|---|
| `docs/comfort_band_and_truth_confidence_plan.md` | This proposal (promote to accepted doctrine section). | docs |
| `docs/1_startup_canon.md` | §5.1 reframed: deadbands are the active expression of a *selected comfort profile*; add profile vocabulary + "Samsung = actuator" line. Add to §7 nothing (no retired reopen). | docs |
| `docs/5_runtime_layer.md` | New subsection documenting the planned `_truth_confidence`/`_truth_status` outputs and the `healthy/degraded/fallback/failed` ladder as **planned**, not live. | docs |
| `docs/2_reference_map.md` | Add a routing row for this plan. | docs |
| `tests/test_comfort_band_safety_separation.py` | New. Asserts comfort bands are separate from safety floors. | test |
| `tests/test_truth_confidence_model.py` | New. Fixture-driven assertions on the status ladder (see below). | test |
| `tests/fixtures/ha_states_truth_*.json` | New fixtures: samsung-only, esp-down-others-up, stable-unchanging. | test fixtures |
| (optional) `configuration.yaml` helper **schema stub** | Only if helper definitions are added as inert `input_select`/`input_number` with no consumer. **Recommend deferring even this** to keep PR1 reviewable. | borderline |

### What should be docs-only

Everything that describes the profile model, the band numbers, the truth-status
ladder, the degraded/fallback reactions, and the freshness rationale.

### What runtime YAML should wait for a later PR

- Rewiring Section 2 to read profile helpers instead of literals (breaks
  `test_section2_cooling_setpoint_doctrine.py` — must be updated together).
- Adding live `sensor.<room>_temperature_truth_confidence` / `_status` templates.
- The `last_changed` → `last_reported` freshness correction (its own PR + a
  before/after telemetry window, because it changes live availability).
- Any band-number change toward Eric Cold defaults (requires the deadband-change
  evidence gate in [`v9_v10_goals.md`](v9_v10_goals.md) §10).

---

## Tests to Add

All five map directly to Eric's goals and are written to pass against the
**intended doctrine** so they encode the contract before runtime exists.

1. **Comfort bands are separate from safety floors.**
   Parse Section 3 floor thresholds (60 / 58) and the proposed profile band
   numbers; assert every comfort `heat_on_at`/`cool_off_at` is strictly above
   60°F (LR) / 58°F (Master) and that no comfort band reuses a safety-gate
   threshold identity.

2. **Samsung-only truth cannot be `healthy`.**
   Fixture: only `*_air_temperature` (Samsung) fresh; all primary sources
   stale/absent. Assert computed status ∈ `{fallback}` (never `healthy`/`degraded`).

3. **Degraded truth widens bands or blocks aggressive control.**
   Fixture: exactly one primary fresh. Assert the documented degraded reaction
   (band-widen flag set OR aggressive-setpoint suppressed) — initially a pure
   model/unit test over the proposed status function.

4. **Unavailable ESP does not equal total truth failure.**
   Fixture: ESP/Apollo source `unavailable`, but Matter + BT (or ST) fresh.
   Assert status is `healthy`/`degraded`, **not** `failed`.

5. **Stable sensors are not marked stale because the value didn't change.**
   Fixture: a primary source whose `last_changed` is >2h old but
   `last_reported`/`last_updated` is recent. Assert it counts as fresh under the
   proposed freshness rule. (This test will *fail* against today's
   `last_changed` logic — which is the point: it documents the bug and gates the
   later freshness-correction PR.)

Reuse the loader + fixture harness from
`tests/test_truth_entity_registry_integrity.py`.

---

## Deferred Runtime Implementation

Explicitly **not** in the first PR:

- Section 2 supervisor refactor to consume `input_select.comfort_profile`.
- Live truth `_confidence` / `_status` template sensors in `configuration.yaml`.
- `last_changed` → `last_reported` freshness migration.
- Band retuning toward Eric Cold (deadband-change evidence gate applies).
- Per-room or per-occupant profiles.
- Any change to the 76°F ceiling gate location/classification.
- Any promotion of MSR/Apollo/ESP into control or truth weighting.

Each is an independent, telemetry-prefaced, regression-checked later PR per
[`v9_v10_goals.md`](v9_v10_goals.md) §11.2.

---

## Open Questions / Decisions for Eric

1. **Default profile:** Should `eric_cold` be the house default with
   `family_normal` as an explicit opt-in, or vice-versa? (Affects what the
   supervisor selects when no one has set a profile.)
2. **Profile granularity now:** Confirm single global `input_select.comfort_profile`
   first (recommended), with per-room (e.g. Master `sleep_cold`) deferred?
3. **Final band numbers:** The draft numbers above are placeholders. Do you want
   PR1 to *document* candidate numbers (non-binding) or leave them as TODO until
   a band-change evidence pass?
4. **Degraded reaction:** Prefer "widen bands by N°F" or "block aggressive
   pulldown/boost but keep bands"? (Affects test #3's assertion.)
5. **Confidence encoding:** 0.0–1.0 float or 0–100 integer for
   `_truth_confidence`? (Cosmetic but locks the test.)
6. **Freshness PR sequencing:** OK to land test #5 as an intentionally-failing
   (xfail) regression marker in PR1, or should it wait until the freshness-fix
   PR so CI stays green? (Recommend `xfail` with a reason string so the bug is
   tracked in CI.)

---

## Copy-paste PR title and body

**Title:**

```
Define Moose House comfort bands and sensor-truth confidence model
```

**Body:**

```
## What

Docs + tests only. No runtime YAML, threshold, safety-gate, helper, or
telemetry-schema change. Establishes the doctrine and regression contract for
a future comfort-band supervisor and a graded sensor-truth confidence model.

## Why

The system already treats deadbands as the comfort contract and Samsung
setpoints as actuator commands, but:
- Comfort bands are hardcoded literals in Section 2 with no profile abstraction
  and are tuned warm relative to the household's cold preference.
- Truth degrades as a cliff (last_changed + 2h -> unavailable -> hidden 70F
  fallback) with no confidence/status surface, and a stable unchanging sensor
  is falsely treated as stale.
- Samsung-only truth can currently read as "available," contradicting its
  low-confidence intent.

## Scope (this PR)

- Adds docs/comfort_band_and_truth_confidence_plan.md (accepted doctrine).
- Reframes 1_startup_canon.md and 5_runtime_layer.md to describe comfort
  profiles + the healthy/degraded/fallback/failed truth ladder as PLANNED.
- Adds regression tests asserting the intended invariants:
  * comfort bands are numerically separate from the 60F/58F safety floors
  * Samsung-only truth cannot be healthy
  * degraded truth widens bands / blocks aggressive control
  * an unavailable ESP/Apollo source != total truth failure
  * a stable (unchanging) sensor is not marked stale (xfail until the
    last_changed -> last_reported correction lands)

## Explicitly deferred (later, separate PRs)

- Section 2 refactor to read input_select.comfort_profile.
- Live _truth_confidence / _truth_status template sensors.
- last_changed -> last_reported freshness migration (changes live availability).
- Any band retuning toward "Eric Cold" (deadband-change evidence gate).
- Per-room / per-occupant profiles.

## Safety / doctrine guarantees

- Section 3 safety floors (LR 60F runaway, Master 58F floor) unchanged and
  still locked by test_safety_invariants.py.
- Apollo/MSR/ESP remain observability-only (Lincoln fan-only exception intact),
  locked by test_msr_observability_boundary.py.
- No active HVAC behavior changes in this PR.

## Open questions

See "Open Questions / Decisions for Eric" in the plan doc (default profile,
profile granularity, final band numbers, degraded reaction, confidence
encoding, freshness PR sequencing).
```
