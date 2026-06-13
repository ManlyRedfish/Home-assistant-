# V9-E Pre-Cool — Telemetry-Driven Release Trigger (research)

**Doc Date:** 2026-06-13
**Author:** Fable (research pass)
**Status:** Proposal / findings. Recommendation-only. No runtime YAML changed.
**Companion:** `docs/analysis/v9e_precool_revision_spec.md` (recommends replacing the
06:00 clock end; proposed 12:00 as a safe intermediate). This doc evaluates whether a
*telemetry-driven* release can replace the wall clock entirely.
**Inputs:** `VTherm_Launch_Data_v5_5` native 15-min rows, May 7–Jun 5 2026 (the local
export; covers the May 17–20, May 26–27, and Jun 3–5 heatwaves). Columns used:
`Deck_Temp_Truth`, `Master_Temp_Truth`, `Shade_1/2_Light`, `Master_Air_Mode`.

Labels: **FACT** (observed), **OBSERVATION** (pattern), **INFERENCE** (conclusion),
**UNKNOWN** (needs data).

---

## 0. Bottom line

**No outdoor-condition signal in the current telemetry can time the release better than a
clock.** The indoor thermal peak is solar/time-driven, not outdoor-air-temp-driven, and
every proposed outdoor trigger (temp threshold, rate-of-change, light, storm passage)
either fires hours too late or is damped out by the building mass. The single most
reliable, lowest-variance feature in the data is **the outdoor peak time (~13:00) and the
stable ~5 h indoor lag** — i.e., the clock.

**Recommended release rule:** a **forecast-conditioned time release**, not an
outdoor-sensor rule:

> Release the deep-hold (revert to the normal deadband) at:
> - **13:00** if `precool_tomorrow_high` ≥ 90°F
> - **11:00** if 85°F ≤ `precool_tomorrow_high` < 90°F
> Hard backstop: never hold past **14:00**.

This holds the charge until the outdoor heat-drive has peaked, scaled by severity, then
lets the room coast to its ~18:00 peak and down. It reuses the existing forecast cache,
needs no new sensor, and is robust against the failure modes documented below. The
companion spec's flat noon is a reasonable special case of this rule.

To eventually go *fully* telemetry-driven, see §6 (sensors to add + data budget).

---

## 1. Outdoor temp threshold (Q1) — REJECT

**FACT — at the indoor peak, it is still hot outside.** Deck temp at each day's Master
truth peak:

| Day | Master peak | Deck @ peak |
|---|---|---|
| May 18 | 78.1°F @18:15 | 84.6°F |
| May 19 | 75.7°F @17:45 | 80.6°F |
| May 20 | 75.2°F @17:30 | 85.5°F |
| May 26 | 72.1°F @16:30 | 83.8°F |
| May 27 | 72.8°F @17:30 | 84.9°F |
| Jun 03 | 68.7°F @17:45 | 84.0°F |
| Jun 04 | 73.4°F @19:30 | 79.7°F |

Median deck-at-indoor-peak ≈ **84°F**.

**FACT — the outdoor temp thresholds occur near midnight, long after the indoor coast
begins.** Deck falls to ≤70°F only ~23:00–00:30, ≤68°F after ~22:15, ≤65°F after ~23:45.
The deck-below-Master crossover (the true passive-coast point) lands at 21:00–23:45 when
it happens at all — on 4 of 9 hot days deck never dropped below Master before midnight.

**INFERENCE — Master starts coasting ~4–6 h *before* outdoor temp crosses any of the
candidate thresholds.** The relationship is backwards for a release trigger: the room
cools first (solar rolloff), the air cools later. There is **no consistent outdoor temp
threshold** that maps to the indoor coast point. A "release when deck ≤ 70/68/65°F" rule
would fire near midnight — useless for holding a charge to the 18:00 peak.

---

## 2. Rate-of-change of outdoor temp (Q2) — REJECT (too slow + mass-damped)

**FACT — the outdoor peak time is consistent (~13:00).** Across the 9 hot days the deck
peak fell at 12:00–14:30 (7 within 12:30–14:30).

**FACT — but a 2 h sustained negative trend confirms late.** First time deck was ≥2°F
below its value 2 h earlier: 13:45, 15:15, 16:00, 16:30, 16:45 (×2), 17:15, 18:15 —
median ≈ **16:30**, because outdoor temp plateaus near its peak for hours before falling.
By the time the trend confirms, the indoor peak (~18:00) is already underway.

**FACT — the indoor mass ignores short outdoor swings.** On May 19 and May 20 evenings the
deck dropped 6–9°F in 30 min; Master truth moved ~0°F (even ticked *up* slightly) over the
following hour.

**INFERENCE — outdoor rate-of-change is doubly unsuitable: it confirms too late, and the
heavy mass damps exactly the fast transients a rate trigger keys on.** Reject as a release
predictor.

---

## 3. Solar proxy: Shade_1/2_Light (Q3) — REJECT (saturated + late)

**FACT — `Shade_1_Light` is a coarse 0–10 scale that saturates.** It reaches 10 by
~07:30–08:45 every day and holds at 10 until dropping to 0 at ~20:00–20:30 (sunset). There
is no daytime gradient — it cannot resolve solar *intensity* or detect the afternoon
rolloff.

**FACT — its only transition (sunset, ~20:15) lags the Master peak (~18:00) by ~2 h.**

**INFERENCE — shade light cannot time the release.** It is a binary "is it daylight"
flag whose one usable edge fires ~2 h after the peak. (It would, at best, confirm
"daytime is over" — too late to be the trigger.)

---

## 4. Weather events (Q4) — not present / damped

**FACT — no genuine frontal passage in the May–Jun window.** A scan for deck drops ≥5°F
in ≤35 min returned 7 hits; the only extreme one (May 26, deck "53→14°F") is a sensor
dropout (14°F in May is impossible), and the rest are ordinary post-peak evening cooling
(May 19/20, ~17:00–18:00).

**FACT — even those real 6–9°F/30-min outdoor drops produced ~0 indoor response within
60–90 min** (same damping as §2).

**UNKNOWN — true storm-front behavior** (a real cold-front passage during a heat day) is
not in this dataset. Given the observed damping it is unlikely to warrant a dedicated
release path, but it cannot be ruled out without an event to observe.

---

## 5. Heavy-mass coast model — what actually balances 18:00 vs 22:00 (Q5)

**FACT — the lag is stable.** Master peaks ~17:30–19:30 (~5 h after the ~13:00 outdoor
peak), consistent with the companion spec's 4–6 h heavy-mass lag and external literature
(masonry indoor lag 3–8 h).

**INFERENCE — the only forward-looking predictor available in the morning is the forecast
high** (already the §2.6 arming gate). Outdoor *current* conditions at release time
(late morning/noon) don't yet encode the afternoon, and — per §1–§4 — outdoor conditions
that *do* encode it arrive too late.

**INFERENCE — release window from the reheat model.** With the held base at the 64°F
cutoff and the companion spec's ~1°F/hr coast: 64°F + (hours to 18:00) must stay under the
72°F comfort line ⇒ release no earlier than ~10:00 to carry cool through the 18:00 peak.
Releasing at 11:00–13:00 lands the 72°F breach at ~19:00–21:00 — past the peak — and the
18:00 evening sleep deadband (off≤62/on>66) then governs the night, so there is **no
"overcool past 22:00" risk** from the hold itself; that risk would only arise if the deep
hold were carried into the night, which this rule does not do.

**Severity scaling:** hotter days both peaked later and stayed hotter (May 18–20, deck
92–95°F, Master peak 17:30–20:30) than the milder hot days (May 26–27 / Jun 3, deck 86°F,
peak 16:30–17:45). So a hotter forecast warrants a later release — hence the
forecast-conditioned times in §0 (13:00 at ≥90°F, 11:00 at 85–90°F).

---

## 6. To replace the clock entirely — telemetry to collect (UNKNOWN resolution)

The clock wins today only because we are missing the two signals that actually drive the
indoor coast. To build a true `release = f(sensors)`:

1. **An unsaturated solar/irradiance sensor** (pyranometer W/m², or a lux sensor with a
   useful daytime range — the current 0–10 shade light is saturated). The afternoon solar
   rolloff is the real cause of the indoor coast; measuring it directly would let the
   release fire on "solar gain has dropped below X." **Data budget:** ~10–15 hot days to
   correlate irradiance-rolloff time against indoor-peak time and fit the offset.
2. **A measured passive-reheat rate from an *actual released hold*.** Every reheat number
   we have (~1°F/hr) is inferred from AC-off morning drift, not from a released afternoon
   hold under full solar load — the afternoon rate is likely higher and is the number the
   release model needs. **Data budget:** 5–10 instrumented pre-cool runs that log Master
   truth slope vs deck temp vs time after release.
3. **Per-tick compressor duty / kWh during the hold**, for the energy side of the trade
   (the companion spec's §3/§6 UNKNOWN).

With ~8–12 instrumented heatwave days carrying (1)–(3) you could fit
`release_time = f(forecast_high, current_truth, measured_reheat, solar_rolloff)` and
retire the clock. Until then, the forecast-conditioned time release in §0 is the
evidence-supported rule.

---

## 7. Sources

- Primary telemetry: `VTherm_Launch_Data_v5_5` (Google Sheet
  `1URlWLkBYHYzuRcTvB32jPs_Fvs2bdDFn2L-sW3y10w8`), heatwave rows May 17–20, May 26–27,
  Jun 3–5 2026.
- Companion: `docs/analysis/v9e_precool_revision_spec.md`; `automations.yaml` Section 2/16;
  `docs/v9_v10_goals.md` §2.6.
- Thermal-lag corroboration: see sources in the companion spec §8.
</content>
