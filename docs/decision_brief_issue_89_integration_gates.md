# Decision Brief — Issue #89: Integration-Anomaly Gate Consistency (Ghost Assassin vs. Samsung Auto Guardrail)

**Doc Date:** 2026-08-07
**Issue:** #89 — *Ghost Assassin (Section 4) vs. Samsung Auto Guardrail
(Section 8) override-consistency doctrine (docs-only).*
**Class:** Docs-only. No `automations.yaml` change, no helper, no threshold.
**Runtime risk:** None.
**Decision status:** **OPEN — awaiting Eric.** This brief lays out the two
candidate rules and the evidence each needs. **It does not pick a rule.** Rule
selection is an owner-level decision over runtime authority against manual
intent.

---

## 1. What is being decided

Whether the two **integration-anomaly gates** — automations that suppress known
device misbehavior rather than steer comfort — should follow a **single,
consistent rule** for whether they yield to manual human intent, and if so,
which rule. The two gates are:

- **Section 4 — Ghost Assassin** (`v7_5_ghost_assassin`): a scheduled watcher
  that kills a phantom Lincoln `heat` activation.
- **Section 8 — Samsung Auto Guardrail** (`v8_samsung_auto_guardrail`): a
  reactive watcher that forces `off` any head that enters Samsung `auto`
  heating out of season (or auto-heats a room already ≥ 68°F).

The corpus flags them as inconsistent-by-construction: both protect against
device misbehavior, but the doctrine of *whether an integration-anomaly gate may
be overridden by a human* has never been pinned to one rule. See
[`5_runtime_layer.md`](5_runtime_layer.md) §7.8 (doctrine-notes paragraph) and
[`v9_v10_goals.md`](v9_v10_goals.md) §8 (integration-anomaly discussion).

## 2. Current runtime behavior (verbatim, read-only)

### 2.1 Ghost Assassin (Section 4, `automations.yaml:1197-1216`)

- **Trigger:** `platform: time, at: "01:20:00"` (once nightly).
- **Conditions:** `climate.lincoln_air == heat` **and**
  `input_select.hvac_season_mode != 'heating'`.
- **Action:** `climate.lincoln_air → off`, then a "Ghost Blocked" notify.
- **Gate on manual override:** **none.** No manual-intent surface is consulted.

### 2.2 Samsung Auto Guardrail (Section 8, `automations.yaml:1598+`)

- **Triggers:** `hvac_action` state change on the four climate entities; any
  entity going `to: "auto"`; and `time_pattern minutes:"/10"`.
- **Per-head conditions (first branch):** `mode == 'auto'` **and**
  `action_now == 'heating'` **and** `season != 'heating'`.
- **Per-head conditions (second branch):** `mode == 'auto'` **and**
  `action_now == 'heating'` **and** `room_temp >= 68`.
- **Action:** `climate.<head> → off`, then a "Samsung Auto Heat Blocked" notify.
- **Gate on manual override:** **none.** No manual-intent surface is consulted.

**Observed consistency today:** *neither* gate consults manual intent. In the
current runtime they are already consistent in behavior — both suppress
unconditionally. The inconsistency the corpus records is **doctrinal**: the docs
still frame the two as *disagreeing on whether they should gate on override*,
because #89 was written while a manual-override surface existed to gate on. See
§3.

## 3. Reconciliation caveat that reshapes #89 (read before deciding)

Issue #89 and the §7.8 doctrine note were written assuming a **live**
`timer.manual_hvac_override` that a gate *could* be made to yield to (Rule α =
"integration-anomaly gates yield to manual override"). **That timer, and the WAF
watcher that fed it, were removed in `cc720ab`** — see
[`manual_override_and_v9e_reconciliation.md`](manual_override_and_v9e_reconciliation.md)
and its §5 stale-reference index (the `deferred_until_telemetry.md` #89 row).

Consequence for this decision:

- **Rule α as literally written is currently unbuildable** — there is no
  `timer.manual_hvac_override` (nor any other manual-intent surface) for a gate
  to yield to. Choosing α therefore *also* requires Eric to first decide whether
  to restore a manual-intent surface (out of scope here; this brief does **not**
  invent one).
- **Rule β is unaffected** by the removal — "integration-anomaly always wins"
  needs no override surface and matches current runtime exactly.
- This does **not** resolve #89; it means the ballot must be read against
  current runtime (both gates un-gated), not the pre-`cc720ab` corpus.

## 4. The two candidate rules (no selection)

| | Rule | What the gates become | Requires (if chosen) | Reopen condition |
|---|---|---|---|---|
| **α** | **Both yield to manual override** | If the operator deliberately set the head, the anomaly suppression stands down; human intent is authoritative | A manual-intent surface must first exist to gate on (removed in `cc720ab`); until then α is aspirational. Aligns with [`3_regression_appendix.md`](3_regression_appendix.md) §4.15 | §4.18 conditions |
| **β** | **Integration-anomaly always wins** | Both gates stay authoritative over manual intent; a 01:20 phantom heat / out-of-season auto-heat is by construction not a deliberate action, so override-gating would give false reassurance | Nothing new — matches current runtime. Record that a manually-set out-of-season head *will* be forced off | §4.18 conditions |

Both rules are doctrinally defensible; the corpus deliberately does not favor one
([`5_runtime_layer.md`](5_runtime_layer.md) §7.8;
[`analysis/open_issue_v9_v10_validation.md`](analysis/open_issue_v9_v10_validation.md)
§#89). Picking either silently rewrites runtime authority over manual intent,
which is exactly the arbitration class
[`3_regression_appendix.md`](3_regression_appendix.md) §4.18 retires when
agent-driven — hence this is an owner decision.

**The consistency requirement is separable from the rule.** Eric may also decide
that the two gates need **not** share a rule — e.g. Ghost Assassin (a scheduled,
unambiguous 01:20 phantom) stays β while Samsung Auto Guardrail (reactive, could
in principle fire on a deliberate operator action) becomes α. The default the
corpus leans toward is *one consistent rule*, but splitting them is a defensible
third outcome and is recorded here so it is not treated as out of bounds.

## 5. Evidence that would inform the rule (not required to record it)

Unlike #87, #89 is primarily a **doctrine** pick, not a telemetry-gated one:
both current runtime behaviors are already known and neither gate has an
ambiguity that ≥N fires would resolve. Eric can record α/β today. The following
telemetry would only *inform* the choice or size the loser-side runtime work:

1. **Ghost Assassin fire frequency** — how often the 01:20 phantom actually
   occurs (is this suppressing a real recurring device fault or a one-off?).
2. **Samsung Auto Guardrail fire frequency and per-head split** — how often each
   head trips the out-of-season / ≥68°F auto-heat branch.
3. **Any instance of a fire coinciding with a deliberate operator action** — the
   only scenario in which α and β produce a different comfort outcome. If this
   has never been observed, β costs the operator nothing today.
4. Provenance is available via the Section 15 `hvac_provenance_log`
   (`origin_kind`, `automation_candidate`) for both automations, per
   [`hvac_provenance_logger_design.md`](hvac_provenance_logger_design.md).

## 6. What this brief does / does not do

- **Does:** state the current runtime facts for both gates (verbatim), enumerate
  the two rules (plus the split-rule outcome) with what each needs, and flag the
  `cc720ab` removal that makes Rule α aspirational.
- **Does not:** pick α/β (or split); modify Section 4 `v7_5_ghost_assassin` or
  Section 8 `v8_samsung_auto_guardrail`; weaken any safety gate; add an
  arbitration helper or `input_boolean`; retire either gate; invent a
  replacement manual-override mechanism; change the 01:20 schedule, the `/10`
  cadence, the 68°F threshold, or the season conditions.

## 7. Recommended decision surface for Eric

Record the chosen rule (and, if α, the separate decision about restoring a
manual-intent surface; or, if split, which gate takes which rule) in
[`5_runtime_layer.md`](5_runtime_layer.md) §7.8 (doctrine-notes paragraph) and
mirror the one-line result into [`v9_v10_goals.md`](v9_v10_goals.md) §8. Any
loser-side runtime change (aligning the gate that does not match the chosen rule)
is **deferred to the Deferred-Until-Telemetry Register** and opened as its own
separately-scoped runtime issue/PR via
[`deferred_until_telemetry.md`](deferred_until_telemetry.md) (the "Ghost Assassin
/ Samsung Auto Guardrail runtime alignment" row, `BLOCKED — DOCTRINE` on #89) —
it does **not** happen in the docs PR that records the decision.

## 8. Cross-references

- [`5_runtime_layer.md`](5_runtime_layer.md) §7.8
- [`v9_v10_goals.md`](v9_v10_goals.md) §8 (integration-anomaly / Safety Gate Doctrine)
- [`3_regression_appendix.md`](3_regression_appendix.md) §4.15, §4.18
- [`deferred_until_telemetry.md`](deferred_until_telemetry.md) (Ghost Assassin / Samsung Auto Guardrail runtime-alignment row)
- [`analysis/open_issue_v9_v10_validation.md`](analysis/open_issue_v9_v10_validation.md) §#89
- [`hvac_provenance_logger_design.md`](hvac_provenance_logger_design.md)
- [`decision_brief_issue_87_spi.md`](decision_brief_issue_87_spi.md) (sibling doctrine brief; same α-unbuildable caveat)
- [`manual_override_and_v9e_reconciliation.md`](manual_override_and_v9e_reconciliation.md) (WAF/timer removal — governs the Rule α caveat)
