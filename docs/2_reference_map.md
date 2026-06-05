# Doc 2 / Moose House Climate Reference Map

**Canon Date:** 2026-06-05
**Document Role:** Reference Map — canonical routing entry point.
**Status:** Index. Update when topology, sensor naming, source precedence, or entity routing materially changes.

> **2026-06-05 live-sync:** §7 (Physical-device / source-path inventory) added,
> capturing the per-room Bluetooth / SmartThings / Matter transport map and the
> repo↔live truth-source sync (Master + Lilly Matter routes restored to truth;
> the disabled Living Room secondary route excluded). Entity-source sync only —
> the statistical truth model is unchanged.

---

## 1. Purpose

This is the canonical Doc 2 entry point referenced from `1_startup_canon.md`
(§9 Document Routing, §6 hardware-debt notes, §10 Startup Handoff Rule).

Doc 2 is the **routing and topology layer** of the Moose House documentation
hierarchy:

- **Doc 1 / Startup Canon** — `1_startup_canon.md` — what to believe.
- **Doc 2 / Reference Map** — *this document* — where to look.
- **Doc 3 / Regression Appendix** — `3_regression_appendix.md` — what not to reinvent.
- **Doc 4 / Operations Sheet** — `4_operations_sheet.md` — whether current doctrine is working.
- **Doc 5 / Runtime Layer** — `5_runtime_layer.md` — what is actually live now.
- **Doc 6 / Proposals** — `6_proposals.md` — V9 architectural proposals.
- **Telemetry Confounders** — `telemetry_confounders.md` — analysis guardrail.
- **Apollo MSR Observability Checklist** — `apollo_msr_observability_checklist.md` — observability-only doctrine and validation checklist for Apollo MSR sensors. Includes the single documented narrow exception (`§Explicit Exception: Lincoln Fan-Only Destratification`) for `climate.lincoln_air` `fan_only`/`off` gating, locked by `tests/test_msr_observability_boundary.py`.
- **Operator Annotation Design** — `operator_annotation_design.md` — out-of-band forensic annotation workflow. Status: sheet-side practice **adopted** (worksheet `supervisor_state_log` in the Home Assistant Google Sheet); Form / Apps Script ingest remains proposed.
- **V6 Telemetry Schema Proposal** — `v6_telemetry_schema_proposal.md` — proposed `VTherm_Launch_Data_v6` schema (planning only; V5 remains active).
- **V6 Observability Roadmap** — `v6_observability_roadmap.md` — phase order and guardrails for V5 → V6 observability work.
- **V8.4 LR Boost V5 Evidence Review** — `analysis/v8_4_lr_boost_v5_evidence_review.md` — tab-by-tab forensic review of Section 14 (V8.4) boost cycles in `VTherm_Launch_Data_v5` and prior versioned tabs. Verdict: effectiveness remains unmeasured; #49 close criteria not met.
- **Comfort Band & Truth-Confidence Plan** — `comfort_band_and_truth_confidence_plan.md` — planned comfort-profile model (`eric_cold` / `family_normal` / `sleep_cold` / `away_relaxed` / `safety_only`) and graded truth-confidence ladder (`healthy` / `degraded` / `fallback` / `failed`). Planning + doctrine only; runtime deferred. Doctrine integrated into Doc 1 §5.1/§6 and Doc 5 §7.9; guardrails in `tests/test_comfort_band_safety_separation.py` and `tests/test_truth_confidence_model_contract.py`.
- **Postmortems** — `postmortems/` — historical incidents.

If a new session needs to know **which sensor feeds which truth calculation,
which entity is downstream of which, or where a given concept's source-of-truth
lives**, Doc 2 is the routing layer that answers that.

## 2. What belongs in Doc 2

- Static topology (rooms, sensors, mini-split heads, Nest dining/boiler).
- Sensor naming truth and aliases.
- Source precedence per room (BT primary / ST + Matter fallbacks / Samsung internal low-weight / MSR-2 DPS310 excluded).
- Entity-id routing (truth → smoothed → control wrapper → supervisor consumer).
- Helper inventory and what writes/reads each helper.
- Worksheet and column-name mapping for `VTherm_Launch_Data_v5`.

What does **not** belong in Doc 2:
- Doctrine and active control posture (Doc 1).
- Runtime-layer implementation boundaries (Doc 5).
- Deferred/retired approaches (Doc 3).
- Performance verdicts (Doc 4).
- Architectural proposals (Doc 6).
- Telemetry classification rules (`telemetry_confounders.md`).

## 3. Current detailed truth-sensor architecture

The detailed truth-sensor architecture currently lives at the repository root in
[`../truth_sensor_architecture.md`](../truth_sensor_architecture.md). That
document covers:

- The truth-sensor pipeline: physical sensors → truth → smoothed → control wrappers → supervisor → telemetry.
- Sensor-freshness policy (2-hour staleness rejection).
- Weighting philosophy (human-space sensors prioritized; Samsung internal kept low-weight).
- Lincoln pilot architecture (outlier rejection, contributor diagnostics).
- Smoothed-sensor lowpass filter parameters (`time_constant=10`, `precision=2`).
- Control-wrapper rationale.
- Critical consumers of truth sensors.

That file is the authoritative source for the truth-sensor part of Doc 2 until
or unless it is migrated into `docs/`. **This PR does not move it.** A future
PR may relocate it as `docs/2a_truth_sensor_architecture.md` (or fold its
content directly into this file) — the move is deferred to keep this PR narrow.

## 4. Pointers (interim, until topology content lands here)

For the topology and routing slices Doc 2 is meant to cover, current sources are:

| Topic | Authoritative source today | Notes |
|---|---|---|
| Truth-sensor pipeline / weighting / freshness | [`../truth_sensor_architecture.md`](../truth_sensor_architecture.md) | Detailed architecture. |
| Live truth/control/telemetry versions | [`5_runtime_layer.md`](5_runtime_layer.md) §5, §6 | V8.3 control, V3.1 truth, V5 telemetry. |
| Helper inventory (live) | [`5_runtime_layer.md`](5_runtime_layer.md) §6.5 + `automations.yaml` header | Helpers required for runtime. |
| Sensor exclusions (MSR-2 DPS310 etc.) | `configuration.yaml` Sections 3–9 (live source); summarized in [`5_runtime_layer.md`](5_runtime_layer.md) §7.5 | Live config wins. |
| Physical-device / source-path (transport) inventory | §7 below; live HA registry authoritative for transport identity; `configuration.yaml` Sections 3–6 for truth membership; `automations.yaml` Section 1 for historical telemetry column names | Per-room BT/ST/Matter transports of one physical probe. |
| Telemetry worksheet / column names | `automations.yaml` Section 1 (`vtherm_mega_tracker_v5`) | Worksheet `VTherm_Launch_Data_v5`. |
| Operator-suppressed window classification | [`telemetry_confounders.md`](telemetry_confounders.md) | Read before joining columns to behavior. |
| Apollo MSR observability validation (proposed) | [`apollo_msr_observability_checklist.md`](apollo_msr_observability_checklist.md) | Observability-only; not a control authority. The single documented narrow exception is the legacy Lincoln fan-only destratification path (`climate.lincoln_air` `fan_only`/`off` only); locked by `tests/test_msr_observability_boundary.py`. |
| Operator annotation workflow (sheet-side adopted) | [`operator_annotation_design.md`](operator_annotation_design.md) and [`telemetry_confounders.md`](telemetry_confounders.md) §6 | Live worksheet `supervisor_state_log` in the Home Assistant workbook. Forensic-only; not read by HA. Form / Apps Script ingest still proposed. Adoption / first-row gate tracked in #50. |
| V6 telemetry schema (proposed) | [`v6_telemetry_schema_proposal.md`](v6_telemetry_schema_proposal.md) | Planning only. V5 remains active. |
| V6 observability roadmap (proposed) | [`v6_observability_roadmap.md`](v6_observability_roadmap.md) | Phase order and guardrails. |
| V8.4 LR boost V5 evidence review | [`analysis/v8_4_lr_boost_v5_evidence_review.md`](analysis/v8_4_lr_boost_v5_evidence_review.md) | Forensic review of Section 14 boost cycles in `VTherm_Launch_Data_v5`. Verdict: effectiveness unmeasured; #49 not yet closeable. |
| Comfort-profile + truth-confidence model (planned) | [`comfort_band_and_truth_confidence_plan.md`](comfort_band_and_truth_confidence_plan.md) | Planning + doctrine only. Comfort profiles and the `healthy/degraded/fallback/failed` truth ladder. Runtime (supervisor rewire, live `_confidence`/`_status` sensors, `last_changed`→`last_reported`) deferred to later PRs. |

## 5. Conflict rule

If Doc 2 (this file) and the detailed source it routes to disagree, **the
detailed source wins** for routing accuracy and Doc 2 should be updated. If Doc
2 and live YAML disagree, **YAML wins** for runtime truth — re-route Doc 2.

## 6. Maintenance rule

Update Doc 2 when:

- A sensor is added to or removed from a room's truth calculation.
- An entity is renamed (e.g., the Lilly/Lincoln slug fix in PR #35/#39).
- A helper is added, removed, or repurposed.
- A worksheet column is added, removed, or renamed.
- The Reference Map's authoritative-source link list (§4) needs a new row.

Do not update Doc 2 merely to improve prose. Doc 2 is an index, not a narrative.

## 7. Physical-device / source-path inventory (per-room transports)

**Last synced:** 2026-06-05 (repo ↔ live truth-source sync).

### 7.1 The transport principle (read this first)

Each occupied room is monitored by **one physical SwitchBot room probe**. That
single probe reaches Home Assistant over **multiple transports**:

- **Bluetooth (BT)** — the SwitchBot cloud/BT integration.
- **SmartThings (ST)** — the same probe bridged through SmartThings.
- **Matter** — the same probe exposed over Matter.

> **BT, SmartThings, and Matter are alternate transports of the *same physical
> thermometer*, not independent sensors.** Two transport rows reading 71.2 °F is
> one probe reported twice — not two probes agreeing.

Genuinely separate hardware (NOT transports of the room probe), kept distinct in
this inventory:

- **Samsung internal** (`*_air_temperature` / `*_air_humidity`) — the mini-split
  return-air thermistor. Real but biased; intentionally low-weight
  (0.20 temp / 0.25 humidity). See `truth_sensor_architecture.md` → Weighting.
- **MSR / Apollo diagnostics** (`*_msr_*`, e.g. `lincoln_msr_dps310_*`) —
  observability only; the DPS310 units are hardware-failed and excluded.
- **Office anchor** = Netatmo; **Dining** = Nest. Different devices, not SwitchBot.

**Authority for transport identity:**

- **Live HA registry / platform metadata is authoritative** for a route's current
  integration / transport identity — whether a route is Matter, Bluetooth, or
  SmartThings, plus its `disabled_by` / availability state.
- **`automations.yaml` telemetry column names** (`*_RoomProbe_BT`, `*_RoomProbe_ST`,
  `*_RoomProbe_Matter`, `*_HVAC_Samsung`) document **historical / export naming**,
  not current platform identity.
- **Where a telemetry label disagrees with the live registry, preserve the
  telemetry field name** (it is a stable observability column) **but document the
  live registry identity.** The clearest example is the Living Room disabled route
  (§7.3): the live registry identifies it as **Matter**, while its historical
  telemetry column is named `LR_*_RoomProbe_BT_Secondary`. The column name does
  not make the route Bluetooth.

Some older inline `configuration.yaml` comments also use legacy hardware labels
("WonderLabs Hub", "Wyze cam sensor") that predate this taxonomy; treat them as
historical, not authoritative.

### 7.2 Current truth model (and the deferred question)

Per-room truth currently takes a **weighted average of every fresh transport**
(plus the low-weight Samsung internal). Adding a transport adds a contributor;
removing/disabling one drops a contributor. Freshness is report-time
(`last_reported`), 2 h window.

> **Deferred design question (NOT decided here):** because the transports are
> copies of one probe, averaging all of them double-counts that probe relative
> to a room with fewer working transports. Whether truth should instead **pick
> the single best available transport per physical probe** is an open V9 question
> for a follow-up PR. The 2026-06-05 sync is **entity-source only** and does not
> change this model or any weight.

### 7.3 Per-room transport map (mini-split rooms)

Weights: primary room probe `1.0`, secondary/legacy transport `0.9`, Matter
`1.0`, Samsung internal `0.20` temp / `0.25` humidity. "In truth?" = currently a
weighted contributor.

**Living Room** — physical probe: SwitchBot Hub 2. Active temp contributors: **3**.

| Transport | Temperature entity | Humidity entity | In truth? | Weight |
|---|---|---|---|---|
| Bluetooth (BT, primary) | `sensor.hub_temperature` | `sensor.hub_humidity` | ✅ | 1.0 |
| SmartThings (ST) | `sensor.hub_temperature_2` | `sensor.hub_humidity_2` | ✅ | 0.9 |
| Matter (disabled, per live registry) | `sensor.hub_2_tempsensor_temperature` | `sensor.hub_2_humisensor_humidity` | ❌ excluded 2026-06-05 | — |
| Samsung internal | `sensor.living_room_air_temperature` | `sensor.living_room_air_humidity` | ✅ | 0.20 / 0.25 |

`sensor.hub_2_tempsensor_temperature` / `sensor.hub_2_humisensor_humidity` are the
Living Room **Matter route in the live HA entity registry**. They are historically
logged under the telemetry column name `LR_*_RoomProbe_BT_Secondary` — a historical
label that does **not** redefine the route as Bluetooth. The route is
`disabled_by:user`, has no live state, and is excluded from truth and from
`sensor.living_room_temperature_truth_active_count`. The telemetry column name is
preserved as a stable observability field.

**Master Bedroom** — physical probe: SwitchBot I/O Meter (7C3F). Active temp contributors: **4**.

| Transport | Temperature entity | Humidity entity | In truth? | Weight |
|---|---|---|---|---|
| Bluetooth (BT) | `sensor.master_bedroom_temp_temperature_2` | `sensor.master_bedroom_temp_humidity_2` | ✅ | 1.0 |
| SmartThings (ST) | `sensor.master_bedroom_temperature_temperature_2` | `sensor.master_bedroom_temperature_humidity_2` | ✅ | 0.9 |
| Matter | `sensor.master_bedroom_temp_temperature_3` | `sensor.master_bedroom_temp_humidity_3` | ✅ added 2026-06-05 | 1.0 |
| Samsung internal | `sensor.master_bedroom_air_temperature` | `sensor.master_bedroom_air_humidity` | ✅ | 0.20 / 0.25 |

Legacy/removed: `sensor.master_bedroom_temp_temperature` (Outdoor Meter 3F) — not wired.

**Lincoln's Room** — physical probe: SwitchBot I/O Meter (3618). Active temp contributors: **4** (reference room — already fully wired; outlier-rejection pilot, 3 °F limit on the three room-probe transports). Unchanged by the 2026-06-05 sync.

| Transport | Temperature entity | Humidity entity | In truth? | Weight |
|---|---|---|---|---|
| Bluetooth (BT) | `sensor.lincoln_s_temp_temperature` | `sensor.lincoln_s_temp_humidity` | ✅ | 1.0 |
| SmartThings (ST) | `sensor.lincoln_s_room_temperature_temperature` | `sensor.lincoln_s_room_temperature_humidity` | ✅ | 1.0 |
| Matter | `sensor.lincoln_temp_temperature` | `sensor.lincoln_temp_humidity` | ✅ | 1.0 |
| Samsung internal | `sensor.lincoln_air_temperature` | `sensor.lincoln_air_humidity` | ✅ | 0.20 / 0.25 |

Diagnostics (observability only, excluded from truth): `sensor.lincoln_msr_dps310_temperature` (hardware-failed), `sensor.lincoln_msr_dps310_pressure`, `sensor.lincoln_msr_esp_temperature`.

**Lilly's Room** — physical probe: SwitchBot Outdoor Meter (58). Active temp contributors: **4**.

| Transport | Temperature entity | Humidity entity | In truth? | Weight |
|---|---|---|---|---|
| Bluetooth (BT) | `sensor.lilly_temperature` | `sensor.lilly_humidity` | ✅ | 1.0 |
| SmartThings (ST) | `sensor.lilly_room_temperature_temperature` | `sensor.lilly_room_temperature_humidity` | ✅ | 0.9 |
| Matter | `sensor.lilly_temp_temperature_2` | `sensor.lilly_temp_humidity_2` | ✅ added 2026-06-05 | 1.0 |
| Samsung internal | `sensor.lilly_air_temperature` | `sensor.lilly_air_humidity` | ✅ | 0.20 / 0.25 |

> **Lilly contradiction resolved (2026-06-05):** `sensor.lilly_temp_temperature_2`
> is the **active Matter transport** of the Outdoor Meter 58 probe (telemetry
> `Lilly_Temp_RoomProbe_Matter`). It was previously *also* listed in
> `configuration.yaml` as a removed "Outdoor Meter 58 fallback" — listing one
> entity as both active and removed. The Matter copy is active; only the legacy
> non-`_2` transport `sensor.lilly_temp_temperature` remains removed/unwired.

### 7.4 Other room probes (supplemental / not mini-split truth)

These follow the same BT/ST/Matter transport pattern but are not first-class
supervisor inputs; authoritative entities are the `automations.yaml` Section 1
telemetry columns:

- **Deck / Outdoor** — `Deck_*_RoomProbe_BT` (`sensor.deck_temp_temperature`),
  `_ST` (`…_2`), `_Matter` (`…_3`).
- **Laundry** — `Laundry_*_RoomProbe_BT` (`sensor.laundry_temperature`),
  `_ST` (`sensor.bathroom_downstairs_*`), `_Matter` (`sensor.laundry_room_*_2`).
- **Office** — Netatmo anchor (`sensor.indoor_*`) plus
  `Office_*_RoomProbe_BT` (`sensor.office_temp_*`), `_ST` (`sensor.office_*_2`),
  `_Matter` (`sensor.office_temperature` / `sensor.office_humidity`).

### 7.5 Maintenance log

- **2026-06-05** — Repo ↔ live truth-source sync. Added Master Matter
  (`master_bedroom_temp_temperature_3`, `master_bedroom_temp_humidity_3`) and
  Lilly Matter (`lilly_temp_temperature_2`, `lilly_temp_humidity_2`) to weighted
  truth (w=1.0). Excluded the disabled Living Room Matter route — per the live HA
  registry — (`hub_2_tempsensor_temperature`, `hub_2_humisensor_humidity`,
  `disabled_by:user`, no live state) from truth + active count. Counts after
  sync: Living Room 3 · Master 4 · Lincoln 4 · Lilly 4.
  Locked by `tests/test_truth_source_transport_sync.py`.
