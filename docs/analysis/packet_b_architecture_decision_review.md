# Packet B — Architecture Decision Review (PR #138 §3.4)

```
═══════════════════════════════════════════════════════════════
PACKET B — ARCHITECTURE DECISION MEMO
Moose House HVAC — Temperature Input Path Selection
═══════════════════════════════════════════════════════════════

Role:       Independent architecture reviewer for the PR #138 §3.4
            decision gate.
Inputs:     PR #138 (docs/analysis/packet_b_filter_model_revision.md,
            head 434063b), the repository at main (06d0b69), the
            operator's Google Drive telemetry ("Home Assistant"
            spreadsheet, examined 2026-06-10), and the Hermes replay
            return packet — which was NOT delivered.
Decision:   REMAIN BLOCKED — EVIDENCE PACKET NOT RECEIVED
Status:     No architecture selected. No implementation authorized
            beyond decision-neutral documentation corrections
            (Section 6). No runtime change of any kind.
═══════════════════════════════════════════════════════════════
```

## 1. Evidence Integrity Finding

**The evidence package does not exist in any reviewable form.** The
tasking prompt states the complete Hermes return packet would be
supplied for review. It was not supplied in the review session, and an
exhaustive search found no copy anywhere reachable:

- PR #138 has zero comments and zero review threads;
- no file in the repository (any branch on `origin`) contains the
  packet, a replay script, a tick ledger, or any artifact matching it;
- no branch, issue, or PR references Hermes, the replay, or the
  evidence package;
- the only "replay" matches in the repo are unrelated documents
  (`docs/event_telemetry_plan.md`, `docs/hvac_provenance_logger_design.md`).

What was available for review is a **second-hand four-line summary of
reported conclusions**: 380 tick-by-tick decisions, 7.1 % decision
divergence, zero harmful divergences, per-zone ledgers "exist",
recommendation Option A. None of the machine-readable artifacts that
PR #138 §3.1–§3.3 require — event streams, cross-validation output,
tick ledger, exclusion log, per-zone mismatch classifications, harm
definitions — were present to be examined.

A summary of conclusions is not evidence. PR #138 §3.4 is an
evidence-gated decision rule; it cannot be exercised against hearsay.

### 1.1 Examination of the accessible telemetry (Google Drive)

The operator indicated the Drive connector has access to the house
telemetry. The only matching artifact is the Google Sheet **"Home
Assistant"** (last modified 2026-06-10 13:00 UTC). It was examined in
full. It contains seven tabs:

| Tab | Window (local) | Rows | Cadence | Season mode | Truth columns |
|---|---|---|---|---|---|
| 0 | 2026-05-07 13:37 → 17:30 | 18 | 15 min snapshots | shoulder | yes |
| 1 | 2026-04-16 13:38 → 18:15 | 20 | 15 min snapshots | **cooling** | yes |
| 2 | 2026-04-04 11:24 → 14:45 | 18 | 15 min snapshots | shoulder | yes |
| 3 | 2026-03-14 17:40 → 22:15 | 22 | 15 min snapshots | (heating-era schema) | partial |
| 4 | 2026-03-10 17:27 → 23:15 | 25 | 15 min snapshots | (heating-era schema) | no |
| 5 | 2026-03-06 18:07 → 03-07 06:45 | 54 | 15 min snapshots | (heating-era schema) | no |
| 6 | 2026-05-07 → 05-16 | 177 events | event journal | n/a | `climate.living_room_air` + LR boost boolean only |

Findings against the PR #138 §3.1 dataset requirements:

1. **No native-granularity truth event streams.** Tabs 0–5 are
   15-minute *snapshots* — exactly the resampling §3.1 prohibits
   ("Do not resample — the event-count dynamics are the object of
   study; resampling destroys them"). An event-based filter
   `y[n] = 0.9·y[n−1] + 0.1·x[n]` cannot be replayed from snapshot
   data: one sample per 15 minutes produces a radically laggier
   filtered series than the real per-event filter.
2. **No `*_temperature_smoothed` or `*_temperature_control` series
   anywhere** in the workbook. The §3.2(2) cross-validation halt gate
   is therefore impossible to run against this data.
3. **Cooling coverage is one tab of ~4.6 hours** (tab 1, 2026-04-16,
   20 ticks; zone truth ranges 69–73 °F). The §3.1 absolute minimum
   is 48 hours of active cooling. Maximum constructible cooling-tick
   decisions: 20 ticks × 4 zones = **80**, irreconcilable with the
   claimed denominator of 380.
4. The event journal (tab 6) covers a single entity pair related to
   the LR heating-recovery-boost work — unrelated to Packet B.

**Consequence:** either Hermes ran the replay on a dataset that has
not been delivered anywhere discoverable, or Hermes ran it on this
telemetry — in which case the replay is void under §3.1 (resampled,
wrong season, window 10× too short) and §3.2(2) (cross-validation
impossible). Both branches lead to the same place.

**Finding: the evidence is inadequate for decision-making — the
claimed evidence package is absent, and the only accessible telemetry
is affirmatively incapable of producing it.**

## 2. Verified Replay Findings

None. Zero replay findings could be verified. Against each of the
twelve mandated review questions:

| # | Question | Result |
|---|----------|--------|
| 1 | Replay implements `y[n] = 0.9·y[n−1] + 0.1·x[n]`? | **Unverifiable.** No replay code or cross-validation output supplied. PR #138 §3.2(2) makes smoothed-series cross-validation a halt gate; there is no evidence it was run, let alone passed. |
| 2 | Identical supervisor logic/inputs/timestamps/setpoints/modes/safety on both routes? | **Unverifiable.** No decision-function source, no tick ledger. |
| 3 | 380 ticks a valid denominator? | **Unverifiable and ambiguous.** If 380 = aggregate zone-decisions (95 ticks × 4 zones), the window is ≈ 23.75 h — **below the §3.1 hard minimum of 48 h of active cooling**. If 380 = per-zone ticks, the window is ≈ 4.0 days — above the minimum but below the 7–14-day target. The packet must state which; one reading invalidates the dataset outright. The accessible Drive telemetry (§1.1) supports at most 80 cooling-season zone-decisions, so 380 cannot have come from it. |
| 4 | Could excluded/missing/duplicated/unevaluable/initialization ticks change the result? | **Unknown.** No exclusion log, no reconstructed-tick flags (§3.1 row 3), no initialization-window handling reported. |
| 5 | Is 7.1 % numerically supported? | **Arithmetically plausible only**: 27/380 = 7.105 % is the unique integer fit. The count of 27 divergent decisions is itself unverified. |
| 6 | Do aggregates hide a zone-specific problem? | **Unknown.** Per-zone ledgers were claimed but not produced. 27 divergences concentrated in one zone (e.g., Master, with its three band regimes) would be a materially different result than 27 spread across four. |
| 7 | Defensible, consistently applied harm definition? | **Unknown.** No harm definition was supplied at all. §3.3 metrics 5–6 (chatter prevented vs. delayed OFF/ON, overcooling °F·min, comfort-excursion °F·min) were not reported. |
| 8 | What does "zero harm" mean? | At absolute best it could mean *zero divergences classified harmful, under an unstated rule, in this dataset*. It cannot mean zero proven harm. Note the statistical weight: with 27 divergent events and 0 classified harmful, the one-sided 95 % upper bound on the harmful-divergence fraction (rule of three) is ≈ 11 %. "Zero harm" over 27 events is weak evidence even if every artifact were verified. |
| 9 | Is replay evidence sufficient for §3.4? | Replay evidence of the §3.1–§3.3 form **would be** sufficient for the gate as written (the gate was designed around it). The summary supplied is not that evidence. |
| 10 | Coverage of relevant operating conditions? | **Unknown.** No coverage table for band-edge crossings per zone, transitions, stale/frozen-lag plateaus, startup/restart (§3.1 row 6), equipment firing, or override windows. §3.1 explicitly requires "a handful of band-edge crossings per controlled zone"; unreported. |
| 11 | Hidden risk of keeping filtered truth observational? | See Section 9. Real but manageable; primarily the documented-vs-actual routing contradictions (verified below) and the absence of routing-invariant tests. |
| 12 | Are doc corrections + routing tests sufficient under Option A? | Conditionally — see Sections 7–9. Not evaluable as a decision today. |

What **was** independently verified, directly against the repository
(main @ 06d0b69):

- The V8.3 supervisor consumes **raw truth**:
  `automations.yaml:372–376` and `automations.yaml:980–983` read
  `sensor.*_temperature_truth | float(70)` (deck uses `float(50)`).
- **No automation** references `*_temperature_smoothed` or
  `*_temperature_control`; every temperature reference in
  `automations.yaml` is a `*_truth` entity.
- Section 10 control wrappers (`configuration.yaml:927+`) are
  pass-throughs of the smoothed sensors with `| round(2)` and
  `float(none) is not none` availability, exactly as PR #138 §1 states.
- Section 12 filters (`configuration.yaml:1088–1144`): `lowpass`,
  `time_constant: 10`, `precision: 2`, one per truth sensor — i.e.
  `y[n] = 0.9·y[n−1] + 0.1·x[n]` per accepted event.
- All three §1 documentation contradictions exist verbatim:
  1. `configuration.yaml:1080–1082` (Section 12 header): "the V8.3
     supervisor ultimately acts on the smoothed values" — false.
  2. `configuration.yaml:927–933` (Section 10 header): wrappers feed
     the "supervisor" and without them "control stops working" —
     false for the supervisor.
  3. `truth_sensor_architecture.md:38–40`: pipeline diagram
     `… → Smoothed Sensors → Control Wrappers → HVAC Supervisor` —
     false.

### Classification of all material claims

- **Verified evidence:** current raw-truth routing; absence of any
  smoothed/control consumer in automations; filter configuration;
  the three documentation contradictions; PR #138's blocked status.
- **Reasonable inference:** if a divergence count exists, it is 27;
  the replay, if performed per §3.2, is the right instrument for this
  decision.
- **Unsupported claim:** that the replay was performed; that it
  cross-validated; that 380 ticks were evaluated; the 7.1 % rate; the
  per-zone ledgers; "zero harmful divergences"; the Option A
  recommendation's evidentiary basis.
- **Residual uncertainty:** everything in §3.3 (convergence-event
  counts, tick deltas, crossing delays, nuisance crossings, chatter
  suppressed vs. OFF/ON delayed); dataset window, season, coverage;
  cold-start behavior; per-zone distribution.
- **Architecture judgment:** Section 4 below.

## 3. Interpretation

What the available material demonstrates:

- The **current architecture is, as a matter of verified fact, Option
  A-shaped**: the supervisor and all safety automations run on raw
  truth; the filtered chain is consumed by nothing but the UI-facing
  wrappers. This is routing reality, not a decision.
- The repository's own documentation **actively misdescribes** that
  reality in three places, in the dangerous direction (it tells a
  future maintainer the filtered chain is load-bearing for control).

What it does **not** demonstrate:

- It does not demonstrate that raw routing is *better* than filtered
  routing for this house. That is precisely the empirical question
  PR #138 blocked on, and the data that would answer it was not
  delivered.
- Even taken entirely at face value, the reported summary would not
  demonstrate safety in any general sense. 380 decisions over (at
  most) ~4 days of one season, with zero-of-27 divergences classified
  harmful under an unstated rule, bounds the harmful-divergence rate
  no tighter than ~11 % at 95 % confidence and says nothing about
  startup, sensor faults, frozen-lag plateaus, or heating season.
  "Zero observed harmful divergences in this dataset" is the strongest
  statement the claimed numbers could ever support.
- Critically, **the reported summary does not even map onto the §3.4
  rule it is invoked under.** §3.4's first branch (→ Option A) requires
  "divergence ≈ 0 and small tick deltas". 7.1 % — one divergent
  decision in fourteen — is not ≈ 0 by any reading. The remaining
  branches require a net-harm/net-benefit classification of the
  divergences: net harmful → Option A strengthened; net beneficial →
  Option B/C becomes a live candidate. A result of "7.1 % divergence,
  zero harmful" therefore lands in the rule's *third* region or in an
  unclassified "all-neutral" gap — either of which makes Option A a
  conclusion that must be argued from the harm/benefit ledger, not
  read off the first branch. Hermes's recommendation may well be
  right, but as reported it skips the very branch logic the gate
  exists to enforce. This is an independent reason the underlying
  ledger is required, not optional.

## 4. Architecture Decision

**REMAIN BLOCKED.**

Neither Option A nor Option B is selected. No third architecture is
proposed. The PR #138 verdict — `DESIGN BLOCKED — OFFLINE REPLAY
EVIDENCE REQUIRED` — stands unchanged, with the qualifier that the
replay is now *claimed* to exist; what is required is its **delivery
in verifiable form**, not necessarily its re-execution.

## 5. Decision Rationale (PR #138 §3.4 applied explicitly)

The §3.4 rule has three branches keyed to the divergent-decision rate
and the harm/benefit character of the divergences:

1. *Divergence ≈ 0 and small tick deltas → Option A.*
   Cannot fire: the only reported rate is 7.1 %, which is not ≈ 0,
   and tick-delta statistics (§3.3 metric 2) were not reported at all.
2. *Divergence > 0, net harmful → Option A, strengthened.*
   Cannot fire: no harm ledger, no overcooling/excursion metrics, no
   harm definition. "Zero harmful" is asserted, which if true makes
   this branch inapplicable — but it is unproven.
3. *Divergence > 0, net beneficial → Option B/C becomes a live
   candidate (full migration protocol required).*
   Cannot fire or be excluded: whether the 27 claimed divergences
   were chatter-suppressing (beneficial), OFF/ON-delaying (harmful),
   or inconsequential is exactly the missing classification.

No branch of the decision rule can be evaluated. Under the gate's own
terms, and under the review instruction not to force a decision on
insufficient evidence, the only available outcome is Remain Blocked.

**To unblock, Hermes (or any re-runner) must deliver, as committed
machine-readable artifacts, not prose:**

1. The replay implementation (script/notebook) showing the per-event
   recurrence `round(0.9·y[n−1] + 0.1·x[n], 2)`, the event-acceptance
   rules, and initialization handling.
2. The §3.2(2) cross-validation result: replayed series vs. recorded
   `*_temperature_smoothed`, per zone, with max deviation. If this
   gate was not run or did not pass within precision rounding, the
   replay is void regardless of its other outputs.
3. The tick ledger: every supervisor execution instant in the window,
   per zone, with raw input, replayed filtered input, active band
   edges, mode/away/sleep/override state, both decisions, the command
   actually issued, and an evaluated/excluded/reconstructed flag with
   reason. The 380 (or corrected) denominator must be derivable from
   this ledger by counting.
4. Dataset provenance: export window (start/end timestamps), season
   mode, zones covered, band-edge-crossing counts per zone, and
   whether the §3.1 row-6 restart observation was captured. The window
   must satisfy §3.1's 48-hour active-cooling minimum unambiguously.
   The provenance must also explain its relationship to the Drive
   "Home Assistant" telemetry examined in §1.1: that workbook cannot
   produce the claimed result, so the packet must come from a recorder
   export at native event granularity that does not yet exist in any
   shared location. If no such export exists, the replay must be
   re-executed against a fresh §3.1-compliant recorder export — which,
   given the current date (June, early cooling season), may require a
   1–2 week collection window before the gate can clear.
5. The harm-classification rule, stated *before* its application, and
   the per-divergence classification ledger, including §3.3 metrics
   4–6 (nuisance crossings, chatter suppressed, OFF/ON delays with
   °F·min quantities).
6. Per-zone divergence counts, so concentration can be checked.

This is delivery of work already claimed to be done. It should cost
hours, not a new data-collection campaign — unless the artifacts do
not exist, which would itself be the finding.

## 6. Packet B Authorized Scope

**Authorized now (decision-neutral, severable):**

- Correcting the three verified documentation falsehoods (Section 8)
  *to accurately describe current routing*. These statements are false
  today under every candidate architecture, and PR #138 §1 already
  re-affirmed the underlying routing facts as model-independent.
  Correcting a false statement about present-tense code does not
  pre-commit the §3.4 decision.

**Explicitly NOT authorized until the decision gate clears:**

- Declaring raw truth the supervisor's *authoritative* input as
  normative doctrine (as opposed to documented current fact).
- Routing-invariant contract tests that freeze raw-truth routing
  (they encode Option A; adding them now is deciding by test suite).
- Any change to filter config, control wrappers (including the
  reclassified §5 availability enhancement), supervisor input
  expressions, or any runtime YAML.
- Anything in Packet A's territory (truth-validity guards,
  finite-value definitions, protective-OFF) — per PR #138 §4.2.
- Any Option B routing, shadowing, or staged rollout.

**Unchanged constraints (PR #138 §4, re-affirmed):** safety
automations remain on raw truth regardless of outcome; the
frozen-lag property of an event-count filter makes filtered inputs
categorically unsuitable for the runaway cutoff, emergency floor,
ceiling gates, and Ghost Assassin.

## 7. Required Contract Tests (specification for later implementation)

Defined now so the implementer can move immediately once the gate
clears; **contingent on the decision landing on Option A** (branch 1
or 2 of §3.4). Style: pytest over parsed YAML, consistent with the
existing `tests/test_truth_*` suites.

1. **Supervisor raw-routing invariant.** For each controlled zone
   (LR, Master, Lincoln, Lilly) plus deck/outdoor: every temperature
   variable in the supervisor automation(s) (both the variables block
   ~372–376 and the second block ~980–983, located structurally, not
   by line number) resolves to `sensor.<zone>_temperature_truth`, and
   to no `*_smoothed` or `*_control` entity.
2. **No-filtered-consumer invariant.** No automation, script, or
   template in `automations.yaml` references any `*_temperature_smoothed`
   or `*_temperature_control` entity. (Asserts the filtered chain is
   observational; fails loudly on any future silent promotion.)
3. **Safety-chain raw-routing invariant.** Runaway cutoff, emergency
   floor, ceiling gates, and Ghost Assassin trigger/condition entities
   are `*_temperature_truth` only.
4. **Filter-shape invariant.** Each Section 12 filter is exactly
   `lowpass, time_constant: 10, precision: 2` over its truth sensor —
   so any retuning of the observational chain is a deliberate,
   test-visible act.
5. **Wrapper passivity invariant.** Section 10 wrappers read only
   their corresponding `*_smoothed` sensor (availability and state),
   preserving the documented UI-only role.
6. **Documentation-consistency guard (optional but recommended).**
   The three corrected doc passages assert raw-truth supervisor
   routing; a test greps that the *false* phrasings ("supervisor
   ultimately acts on the smoothed values", wrapper-header
   "supervisor" claim, diagram arrow into the supervisor) do not
   reappear.

## 8. Documentation Corrections (the three PR #138 §1 contradictions)

1. **`configuration.yaml` Section 12 header (lines ~1078–1086).**
   Delete/replace "the V8.3 supervisor ultimately acts on the smoothed
   values. Removing these causes noisy truth spikes to propagate
   directly into setpoint decisions." Correct statement: the smoothed
   sensors feed the Section 10 control wrappers for UI/diagnostic
   display only; the V8.3 supervisor and all safety automations read
   raw `*_temperature_truth` directly; removing the filters affects
   dashboards, not control.
2. **`configuration.yaml` Section 10 header (lines ~927–937).**
   Remove "SUPERVISOR" from the title and the claim that without the
   wrappers "downstream consumers lose their temperature input and
   control stops working." Correct statement: wrappers expose
   smoothed values with stable unique_ids for the HA UI; no
   automation consumes them; control is unaffected by their removal
   (UI/dashboards are affected).
3. **`truth_sensor_architecture.md` pipeline diagram (lines 38–40)
   and the corresponding prose (§"Control Wrappers", line ~124+).**
   Re-draw so the supervisor consumes truth sensors directly:
   `Truth Sensors → HVAC Supervisor` on the control path, with
   `Truth Sensors → Smoothed Sensors → Control Wrappers → UI` as a
   parallel observational branch. Audit the "Main Supervisor"
   consumer listing (line ~161) for the same error.

Each correction states present-tense fact verified in this review and
is safe to apply before the architecture decision (Section 6).

## 9. Residual Risks and Validation

- **Primary risk: decision latency.** The house continues running the
  (verified, currently functioning) raw-truth architecture while
  blocked. No new runtime risk is introduced by remaining blocked.
- **Misdocumentation risk** persists until Section 8 lands: a
  maintainer following the current headers could "fix" the supervisor
  onto the filtered chain believing that was always the design — the
  exact silent promotion the eventual contract tests exist to prevent.
  This is the strongest argument for executing the authorized slice
  promptly.
- **Observational-chain drift risk:** with the filter consumed only by
  the UI, its behavior (frozen-lag plateaus after quiet periods,
  startup priming) can silently diverge from operator expectations —
  an operator-understanding hazard, not a control hazard. The Section
  8 corrections plus filter-shape test mitigate; no further action
  proposed now.
- **Evidence-existence risk:** the possibility that the Hermes
  artifacts cannot be produced must be treated as live until they
  appear. If they cannot, the replay must be re-executed per §3.1–§3.3
  before any decision; the reported 7.1 %/zero-harm figures must then
  be discarded entirely rather than "approximately trusted".
- **Even after a verified Option A decision**, replay evidence is
  retrospective and single-season. Post-implementation validation
  needs: the §3.1 row-6 restart observation if not in the packet, and
  one heating-season spot-check of tick-delta statistics before the
  decision is treated as season-independent doctrine. Live testing of
  control changes is not required under Option A (no runtime change).

## 10. Implementation Handoff

> **Directive to the implementation planner:** Packet B remains
> blocked at the PR #138 §3.4 gate; do not implement routing changes,
> contract tests, or normative "authoritative input" doctrine. Two
> work orders only: (1) *now* — apply the three decision-neutral
> documentation corrections specified in Section 8, docs-only, no
> functional YAML or test changes; (2) *to Hermes* — deliver the six
> verification artifacts enumerated in Section 5 (replay
> implementation, cross-validation result, tick ledger with
> exclusions, dataset provenance resolving the 380-tick denominator
> ambiguity against the 48-hour minimum, pre-stated harm rule with
> per-divergence ledger, per-zone counts) as committed
> machine-readable files — noting that the Drive "Home Assistant"
> workbook cannot be that dataset (§1.1), so a native-granularity
> recorder export per §3.1 must be produced or freshly collected,
> reusing the existing exporter tooling
> (tools/export_ha_nuisance_evidence.ps1). On receipt, this review
> re-convenes,
> evaluates §3.4 branch-by-branch against the actual ledgers, and —
> only then — selects Option A, Option B/C, or strengthens the block.
