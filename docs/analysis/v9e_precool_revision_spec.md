# V9-E Master Pre-Cool — Revision Spec

**Doc Date:** 2026-06-13
**Author:** Fable (research/recommendation pass)
**Status:** Proposal. Recommendation-only. No runtime YAML, helper, threshold, or
safety-gate change is made by this document. Per `docs/v9_v10_goals.md` §10 and the
§2.6 experiment contract, any runtime change lands in a separate scoped PR after the
household ratifies the daytime-hold decision flagged in §1.
**Inputs:**
- `VTherm_Launch_Data_v5_5` (export May 7–Jun 5 2026, native 15-min rows) — thermal
  response evidence.
- PR #143 + `automations.yaml` Section 2, `configuration.yaml` Section 16,
  `docs/v9_v10_goals.md` §2.6 — current envelope.
- Operator-reported Jun 13 run (forecast 91°F, engaged 02:00, ran 165 min,
  78.14→73.08°F, aborted 05:00 "Excessive cooling slope exceeded", latched out).
- External research on pre-cooling / thermal lag (sources listed at end).

Evidence labels: **FACT** (directly observed), **OBSERVATION** (pattern),
**INFERENCE** (conclusion), **UNKNOWN** (needs more data).

---

## 0. TL;DR — Revised Parameter Spec

| Parameter | Current | Recommended | Confidence |
|---|---|---|---|
| Window start | 02:00 | **02:00** (keep) | high |
| Window end | 06:00 | **12:00** (14:00 as a monitored option) | high (12:00) / medium (14:00) |
| Target temp (room-truth cutoff) | 64°F | **64°F** (keep; 65°F if energy-conservative) | high |
| Thermal floor (hard stop) | 63.5°F | **63.5°F** (keep) | high |
| Drop-rate slope guard | 2.5°F/hr per 15-min tick | **Remove** (floor is the real net); if retained, 5°F/hr over a 30-min smoothed window, armed only >3°F above target | high |
| Max runtime | 180 min, latching abort | **Demote to a non-latching soft backstop; raise cap to 480 min** | medium |
| Shove setpoint (hardware) | 61°F | **61°F** (unchanged — doctrine) | n/a |
| Re-arm / latch | one-shot/night | **Keep one-shot**, but only floor-breach + config-invalid latch | high |

**One-line thesis:** the guards killed a run that was physically fine, and the window
cooled the house at the one time of day it least needed it. Fix the slope guard
(remove it), and move the *hold* into the morning so the cooling charge survives to the
evening peak instead of bleeding off by mid-afternoon.

---

## 1. Window timing — move the *end*, not the *start*

### Evidence

**FACT — the room peaks in the evening, not midday.** On the May 18 heatwave day (deck
truth peaked 92.84°F at 14:00), Master truth peaked **77.96°F at 18:00** — ~4 h after
the outdoor/solar peak. June 4 repeats it: deck peaked ~89.8°F at 13:00–15:00, Master
peaked 73.09°F at 19:00 (~5–6 h lag).

**FACT — external research agrees.** Indoor air temperature lags outdoor peak by ~2 h
(light construction) to 3–8 h (masonry/heavy thermal mass). This house's 4–6 h lag puts
it firmly in the heavy-mass regime. The daily comfort problem is an *evening* problem
driven by all-day envelope gain.

**FACT — the cooling charge bleeds at ~1°F/hr.** After the AC shut off at 06:00 (normal
daytime deadband reverts to off≤68/on>72):
- May 18: 64.69°F @06:00 → 70.76 @12:00 → 72.6 @15:00 (crosses the 72°F on-threshold) →
  77.96 @18:00. Passive reheat ≈ 0.88°F/hr (morning), steepening to ~1.3°F/hr into the
  afternoon.
- Jun 4: 61.92°F @06:00 → 68.94 @13:00 ≈ 1.0°F/hr.

**FACT — the current 02:00–06:00 window is nearly redundant with baseline.** On May 18,
with **no** pre-cool, the standard sleep deadband (set 61, off≤62) alone drove Master to
**63.78°F by 05:00**. The pre-cool window targets exactly the hours the baseline already
cools the room to ~63–64°F.

**FACT — pre-cooling literature favors a window ending a few hours *before* the peak,
at a moderate setpoint.** Best peak-shaving in most climates comes from a "short
pre-cooling window with a high pre-cooling setpoint"; a charged mass sustains comfort
through a ~3 h peak (e.g., 14:00–17:00).

### Inference

**INFERENCE — the small-hours shove does almost no work the baseline isn't already
doing; the pre-cool's only unique lever is *holding the low base past 06:00*.** A charge
delivered at 05:00 and released at 06:00 reheats at ~1°F/hr and crosses the comfort
threshold around 14:00–15:00 — hours before the 18:00 peak. To carry through the peak,
the active hold has to extend into the morning/early afternoon.

If Master is held at the 64°F cutoff until **12:00**, the ~1°F/hr reheat lands the 72°F
breach near **20:00** — comfortably past the 18:00 evening peak. Holding until **14:00**
pushes it later still and is closer to the literature's "charge right before the peak,"
but spends compressor time deeper into the high-rate afternoon.

### Recommendation

- **Keep window start at 02:00.** Marginal cost over the existing sleep deadband is near
  zero, and pre-dawn kWh is cheapest; harmless.
- **Move window end to 12:00** (`is_precool_window: 2 <= now().hour < 12`). This is the
  high-value change. 14:00 is a defensible option but should be gated on the energy
  measurement in §3/§6 first.

### ⚠️ Decision for the household (architecturally significant)

Holding 64°F until noon/14:00 is, mechanically, *daytime cooling*. It preserves the
sanctioned §2.6 envelope shape (overnight arming, forecast gate, 61°F setpoint
unchanged, no 17:00 trigger, no Turbo) but it brushes the boundary of the **retired
Targeted Pre-Chill** non-goal (`v9_v10_goals.md` §3). This is the one decision in this
spec that changes the *character* of the experiment, not just a threshold. It should be
ratified by Eric before it lands in YAML. The conservative fallback is end=12:00 (hold
through the morning only); the aggressive option is end=14:00.

---

## 2. Slope guard — remove it; the floor is the real safety net

### Evidence

**FACT — the guard is a per-tick check against a quantized sensor.** The code computes
`(precool_prev_master - master_temp) >= (precool_drop_limit / 4)` each tick — i.e., a
single 15-min drop ≥ **0.625°F** (2.5 ÷ 4) trips it.

**FACT — the fused truth sensor moves in lumps, so a normal pulldown trips this
repeatedly.** Native 15-min data from the May 17→18 pulldown (warm start ~76°F): the
sensor holds flat for several ticks then jumps 0.3–1.4°F. Individual 15-min drops crossed
the 0.625°F threshold on **7 ticks** in a single overnight pulldown — including
**+1.36°F (5.44°F/hr)**, +1.07, +1.17 at the initial shove, and several 0.65–0.82°F ticks
later. Meanwhile the *hourly-averaged* rate stayed ~1.3–2.0°F/hr.

**FACT — the Jun 13 abort fits this exactly.** The run's average rate was 1.84°F/hr
(78.14→73.08 over 165 min), well under the 2.5°F/hr limit — yet it aborted on a single
15-min tick. It is essentially luck the latch held off until 05:00; the May 18 native
data says a normal pulldown trips the per-tick guard within the first hour.

**FACT — the floor was never in danger.** Lowest Jun 13 truth was 73.08°F; the floor is
63.5°F. Historically, even a multi-hour 61°F shove asymptotes at ~63.4°F (see §4) — the
hardware physically cannot drive the room much below the floor, and the §3 emergency
floor (58°F) sits below that as the true equipment stop.

### Inference

**INFERENCE — the slope guard is solving a problem that the thermal floor + the 61°F
setpoint + the cutoff already prevent.** A "cooling runaway" cannot happen: the setpoint
is 61°F, the room asymptotes near 63°F, the cutoff turns it off at 64°F, and the floor
catches 63.5°F. The slope guard adds no protection the envelope lacks; it only adds a
high-probability false abort driven by sensor quantization.

### Recommendation

- **Remove the slope guard** from `precool_guard_tripped`. Let the thermal floor be the
  self-termination net.
- **If belt-and-suspenders is wanted:** keep it but (a) raise to **5°F/hr**, (b) evaluate
  it over a **30-min (2-tick) smoothed** delta rather than a single 15-min diff, and
  (c) arm it only once the room is within ~3°F of target (a *shaped* guard: steep drops
  allowed during the shove, tighter near target). A full shaped profile is, in my view,
  over-engineering given the floor already bounds the downside — but this is the minimum
  that would stop the false trips if the guard is retained.

---

## 3. Runtime budget — demote it; it shouldn't gate a long-window hold

### Evidence

**FACT — 165/180 min was already near the ceiling** on a 4-h window, so the cap was
about to become the binding constraint regardless of the slope abort.

**FACT — control is cutoff-gated.** `precool_engage` is true only when
`master_temp > precool_target_temp`. Once the room reaches 64°F the compressor idles and
only re-engages on reheat; runtime accrues only on engage ticks. Over a long window
holding 64°F against ~1°F/hr reheat, duty is modest, not continuous.

**FACT — the counter and helper are both hard-capped at 300.** The accounting line is
`[precool_runtime + 15, 300] | min` and the helpers (`precool_runtime_counter`,
`precool_max_runtime`) declare `max: 300`. A window longer than 5 h cannot even be
expressed today.

### Inference

**INFERENCE — a *latching* runtime cap is the wrong tool for a multi-hour hold.** If the
budget exhausts at, say, 09:00, the one-shot latch would lock out the very morning hold
we are trying to create. With cutoff-gated control the budget is not needed to prevent
over-running; it is only a backstop against a stuck-on compressor.

### Recommendation

- **Demote runtime from a latching abort to a non-latching soft backstop** (it may pause
  the session, but should not set the nightly latch).
- **Raise the cap to 480 min** and lift the `300` clamp in both the accounting template
  and the two helpers to ≥480 so a long window is representable.
- **UNKNOWN — total kWh / compressor duty for a morning–noon hold is unmeasured.** The
  literature notes pre-cooling *increases* total cooling energy even as it shifts peak.
  Instrument duty-cycle and daily kWh over 2–3 runs before extending end to 14:00.

---

## 4. Target temp — keep 64°F (diminishing returns below it)

### Evidence

**FACT — the 61°F shove has a hard diminishing-returns knee at ~65–66°F.** May 17→18
pulldown: 76→68°F took ~2.5 h (~3°F/hr), but 68→64°F took ~3 h (~1.3°F/hr), and the room
**asymptoted at ~63.4°F** — it could not be driven below ~63.4°F even running to 05:15.

**FACT — a 68°F cutoff would be nearly inert.** The room is already at/near 68°F during
the morning reheat path (May 18: 68°F by ~08:00–09:00), so a 68°F cutoff would command
little cooling.

**FACT — a 62°F target collides with the floor invariant.** PR #143 added
`is_config_valid` requiring target > floor. With the floor at 63.5°F, a 62°F target is
**invalid** and would itself trip the abort latch ("Invalid config: target must exceed
floor"). Reaching 62°F also requires fighting the ~63.4°F asymptote for very little gain.

### Recommendation

- **Keep target = 64°F.** It sits just above the envelope asymptote and just above the
  floor — the right cutoff for this hardware.
- **65°F is a reasonable energy-conservative bump** (cuts hold duty for ~1°F of comfort)
  and aligns with the literature's "higher pre-cool setpoint." Use 65°F if §3's energy
  measurement shows the morning hold is expensive; otherwise 64°F.
- **Do not go to 62°F** — unreachable in practice and invalid against the floor unless
  the floor is also lowered (not recommended — see §5).

---

## 5. Thermal floor — keep 63.5°F (it becomes the *primary* guard)

### Evidence

**FACT — the floor was never approached** (Jun 13 low 73.08°F) and historically the
envelope asymptotes ~63.4°F under the 61°F shove, i.e., right at the floor.

**OBSERVATION — the 0.5°F gap between target (64) and floor (63.5) is intentional
headroom**, and the §3 emergency floor (58°F) sits well below as the true equipment stop.

### Recommendation

- **Keep floor = 63.5°F.** Do not lower it. With the slope guard removed (§2), the floor
  becomes the *primary* self-termination guard, and 63.5°F is well-placed: just below the
  64°F cutoff, just above the achievable asymptote. The gap is correct as-is.

---

## 6. Re-arm logic — keep one-shot, because real aborts become rare and terminal

### Evidence

**FACT — the one-shot latch locked out the whole morning after a *false* slope trip** at
05:00. The lockout itself wasn't the root problem — the spurious abort was.

**INFERENCE — once the slope guard is removed (§2) and the runtime cap is demoted (§3),
the only remaining latching aborts are floor-breach and config-invalid — both genuinely
terminal/safety conditions** where "stop for the night" is the correct response.

### Recommendation

- **Keep the one-shot nightly latch**, but scope it so only **floor-breach** and
  **config-invalid** set it. A floor breach is a real safety event; a config-invalid pair
  is operator error — both should stay latched until the 22:00 reset.
- **No re-arm machinery needed** under this design — there is no longer a noisy guard to
  recover from. (If, later, the runtime backstop is ever made latching again, *then*
  add a forecast-refresh re-arm; not before.)

---

## 7. Implementation notes for the eventual scoped PR (not changed here)

`automations.yaml` Section 2:
- Window gate: `is_precool_window: "{{ 2 <= now().hour < 12 }}"` (or `< 14`).
- Drop `precool_slope_tripped` from `precool_guard_tripped` (or rewrite per §2 option).
- Move `precool_runtime_tripped` out of the latching path (non-latching session pause),
  or remove; keep `precool_floor_tripped` and the config-invalid check as the only
  latch sources.
- Runtime accounting clamp `[precool_runtime + 15, 300] | min` → `… , 480] | min`.

`configuration.yaml` Section 16:
- `precool_runtime_counter.max` and `precool_max_runtime.max`: 300 → 480 (and
  `precool_max_runtime.initial`: 180 → 480, or whatever §3's measurement supports).
- Leave `precool_target_temp` (64), `precool_thermal_floor` (63.5) initials as-is.

Doctrine / process:
- The window-end extension into daytime needs household ratification (§1 flag) and a
  `v9_v10_goals.md` §2.6 update before the YAML PR, per §10's docs-first rule.
- Section 1 `Precool_*` telemetry already exports the needed state; add duty/kWh
  observation for the §3/§6 energy UNKNOWN if not already derivable.

---

## 8. Sources

- LBNL — *Reducing Residential Peak Electricity Demand with Mechanical Pre-Cooling of
  Building Thermal Mass*: https://bies.lbl.gov/publications/reducing-residential-peak-electricity
- LBNL-55800 — *Peak Demand Reduction from Pre-Cooling with Zone Temperature Setup*:
  https://simulationresearch.lbl.gov/sites/all/files/55800.pdf
- *Demand response via pre-cooling and solar pre-cooling: A review* (ScienceDirect):
  https://www.sciencedirect.com/science/article/pii/S0378778822005114
- *Aggressive pre-cooling of a building to reduce peak power during extreme heat days*
  (ScienceDirect): https://www.sciencedirect.com/science/article/pii/S2352467724000420
- Thermal lag (overview): https://en.wikipedia.org/wiki/Thermal_lag
- *Why Your Home Overheats on Sunny Days* (United Air Temp): https://www.unitedairtemp.com/blog/why-home-is-warm-on-mild-days/
- Primary telemetry: `VTherm_Launch_Data_v5_5` (Google Sheet
  `1URlWLkBYHYzuRcTvB32jPs_Fvs2bdDFn2L-sW3y10w8`), May 17–20 and Jun 3–5 heatwave rows;
  Jun 13 run rows 3477–3536 (operator-reported).
</content>
</invoke>
