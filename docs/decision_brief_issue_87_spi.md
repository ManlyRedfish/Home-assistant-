# Decision Brief — Issue #87: Sleep Priority Interlock (SPI) Doctrine Classification

**Doc Date:** 2026-08-07
**Issue:** #87 — *Sleep Priority Interlock doctrine classification (docs-only).*
**Class:** Docs-only. No `automations.yaml` change, no helper, no threshold.
**Runtime risk:** None.
**Decision status:** **OPEN — awaiting Eric.** This brief lays out the choices
and the evidence each needs. **It does not pick a position.** Position selection
is an owner-level decision and additionally depends on telemetry (below).

---

## 1. What is being decided

Whether `v9_sleep_priority_interlock` (Section 3) — which forces
`climate.living_room_air → off` whenever Master enters `cool` with LR in `heat`
and LR truth > 60°F — should be classified as **comfort policy**, a
**compressor/cross-mode protection gate**, or **observability-only**. The
classification governs whether SPI is *allowed* to override manual human intent.
See [`5_runtime_layer.md`](5_runtime_layer.md) §7.8 (canonical ambiguous
interlock) and [`v9_v10_goals.md`](v9_v10_goals.md) §2.3.

## 2. Current runtime behavior (verbatim, read-only)

- **Triggers:** state transitions `climate.master_bedroom_air → cool` and
  `climate.living_room_air → heat`.
- **Conditions:** Master `== cool`, LR `== heat`, `sensor.living_room_temperature_truth
  > 60°F`.
- **Action:** `climate.living_room_air → off`.
- **Gate:** **none on manual override.** SPI does not consult any manual-intent
  surface.
- **Observability:** SPI fire provenance is written via Section 15
  `spi_last_triggered` (PR #98, closing #88) — each fire adds a
  `hvac_provenance_log` row tagged `automation_candidate =
  v9_sleep_priority_interlock`. **No dedicated logbook tag yet.**

## 3. Reconciliation caveat that reshapes #87 (read before deciding)

Issue #87 and §7.8 were written assuming a **live** `timer.manual_hvac_override`
that SPI could be made to gate on (Position α = "gate on `== idle`"). **That
timer, and the WAF watcher that fed it, were removed in `cc720ab`** — see
[`manual_override_and_v9e_reconciliation.md`](manual_override_and_v9e_reconciliation.md).

Consequence for this decision:

- **Position α as literally written is currently unbuildable** — there is no
  `timer.manual_hvac_override` to gate on. Choosing α therefore *also* requires
  Eric to first decide whether to restore a manual-intent surface (out of scope
  here, and this brief does **not** invent one).
- Positions β and γ are **unaffected** by the removal — neither depends on the
  timer.
- This does **not** resolve #87; it means the ballot must be read against current
  runtime, not the pre-`cc720ab` corpus.

## 4. The three candidate positions (no selection)

| | Position | What SPI becomes | Requires (if chosen) | Reopen condition |
|---|---|---|---|---|
| **α** | **Comfort policy** | SPI must yield to manual intent | A manual-intent surface must first exist to gate on (removed in `cc720ab`); until then α is aspirational | §4.15 conditions |
| **β** | **Compressor / cross-mode protection gate** | SPI stays authoritative over manual intent (outdoor-unit cross-mode contention is an equipment concern) | Evidence that the LR-off it produces correlates with measured compressor distress | §4.18 conditions |
| **γ** | **Observability-only candidate** | SPI stops writing climate state; cross-mode contention is observed, not intervened on | Evidence that the contention is rare / low-value enough to not need intervention | §4.18 conditions |

All three are defensible. The corpus deliberately does not favor one
([`6_proposals.md`](6_proposals.md) "classification pending";
[`3_regression_appendix.md`](3_regression_appendix.md) §4.18).

## 5. Evidence required before a position can be picked

Per §4.18 (arbitration follows telemetry), position selection needs, from the
Section 15 `spi_last_triggered` observer:

1. **SPI fire frequency** (fires/week).
2. **LR mode source at fire time** — was LR `heat` set manually or by the
   supervisor? (Post-`cc720ab` there is no override timer to disambiguate this,
   so provenance on the LR `heat` write is the only signal — a reason β/γ may be
   easier to evidence than α.)
3. **Master mode source at fire time** — manual `cool/61` vs. supervisor.
4. **Correlation of the resulting LR-off with measured compressor distress**
   (the β discriminator).
5. **≥ 3 logged SPI fires** before any verdict.

## 6. What this brief does / does not do

- **Does:** state the runtime facts, enumerate the three positions with the
  evidence each needs, and flag the `cc720ab` removal that reshapes Position α.
- **Does not:** pick α/β/γ; modify Section 3 `v9_sleep_priority_interlock`;
  weaken any safety gate; add an arbitration helper or input_boolean; retire SPI;
  invent a replacement manual-override mechanism; propose deadband changes.

## 7. Recommended decision surface for Eric

When the ≥ 3-fire threshold and §5 evidence are in hand, record the chosen
position (and, if α, the separate decision about restoring a manual-intent
surface) in [`5_runtime_layer.md`](5_runtime_layer.md) §7.8 "Ambiguity status"
and mirror the one-line result into [`v9_v10_goals.md`](v9_v10_goals.md) §7. Any
loser-side runtime change goes through a separately-scoped issue via
[`deferred_until_telemetry.md`](deferred_until_telemetry.md); it does not happen
in the docs PR that records the decision.

## 8. Cross-references

- [`5_runtime_layer.md`](5_runtime_layer.md) §7.8
- [`v9_v10_goals.md`](v9_v10_goals.md) §2.3, §7
- [`3_regression_appendix.md`](3_regression_appendix.md) §4.15, §4.18
- [`comfort_failure_forensics.md`](comfort_failure_forensics.md) §8.9
- [`6_proposals.md`](6_proposals.md) "Sleep Priority Interlock — classification pending"
- [`manual_override_and_v9e_reconciliation.md`](manual_override_and_v9e_reconciliation.md)
</content>
