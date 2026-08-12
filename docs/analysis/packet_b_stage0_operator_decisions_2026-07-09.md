# Packet B — Design Work Handoff for Claude Code

## Context

PR #160 (sensor-chain fix) shipped. Packet B is the deferred follow-up:
rewrite Section 2 of `automations.yaml` (V8.3 Main Supervisor) to add
per-zone graceful degradation so that when one zone's room-truth sensor
is invalid, the supervisor skips only that zone rather than commanding
it on a `float(70)` fake fallback.

A Stage 0 replacement YAML exists at
`deploy/packet_b_stage0_section2_replacement.yaml` (Rev 4) but is stale.
This document records the design decisions and operator input needed
before a code-writing session can regenerate and land Stage 0.

## Canonical references

- `docs/analysis/packet_b_revision_4_control_contract.md` — Rev 4 doctrine
- `deploy/packet_b_stage0_section2_replacement.yaml` — stale Stage 0 artifact
- `deploy/packet_b_stage0_COPY_INSTRUCTIONS.md` — deploy checklist
- `automations.yaml` §Section 2 (lines ~401–977) — live supervisor

## Operator Decisions Recorded (2026-07-09)

### D3: CHANGE-5 shoulder-day bedroom deadband (68/72) — ✅ SETTLED

The data supports 68/72 with hold-through. The deadband + 61/turbo
combo is already proven as the energy-efficient approach. Eric confirmed.

**Locked input for Stage 0:** Use 68/72 with hold-through in shoulder
season for all three bedrooms (Master, Lincoln, Lilly).

### D1/V9-E Pre-cool — 🚫 DEFER (do not port)

V9-E Master Pre-cool was an experiment aimed at pre-cooling the Master
overnight with a thermal buffer for the next day's heat. It is **not
working in its current form** — it cannot achieve meaningful pre-cool
because the kids bedrooms are also cooling at night, splitting compressor
capacity. The supervisor cannot command "all zones off except Master" to
concentrate compressor power.

**Effect on Stage 0:** V9-E variables (`precool_*` input_numbers), window
guards, and template consults must be **removed** from the Stage 0
replacement. The feature was experimental and non-functional — removing
it is correct.

### D1/Lilly Heatwave Sleep Guard — ✅ SIMPLIFIED AND PORTED

**Old mechanism:** `lilly_heatwave_sleep_guard` input_boolean that
conditionally narrowed Lilly's bedtime deadband only during heat waves.

**New mechanism (operator decision):** Lilly should have a **permanent**
68/72 bedtime deadband from 19:00-07:00, not gated on heat wave
conditions. The heatwave sleep guard input_boolean is no longer needed
as a separate mechanism — just encode Lilly's bedtime band as a
permanent rule.

**Reasoning:** Lilly's room runs hotter than Lincoln's, but if it's
overcooled at night, the cold air falls from her room into the kitchen
below, wasting energy in a zone that doesn't need cooling. A permanent
68/72 band 19:00-07:00 ensures she's comfortable without overcooling
the kitchen.

**Effect on Stage 0:** Remove `lilly_heatwave_sleep_guard` references.
Add a simple `lilly_bedtime` band similar to the kids bedtime band but
with Lilly as the gating entity and slightly different thresholds
(68/72 at 19:00-07:00).

### D1/Master Fan-Sync Tie-In — ✅ PORT

Master's room is 10×22 ft. The mini-split head is on the far short wall
pointing at the door. The door is at the top of the stairs. Without the
ceiling fan and a closed door, cold air spills down the stairs and the
Master never cools properly. The ceiling fan pushes airflow across the
full 22ft length.

The fan-sync automation (`v10_master_bedroom_fan_sync`) handles the
sync independently, but Section 2 passes variables that tell it when
Master is actively cooling. These tie-ins must be preserved.

**Effect on Stage 0:** Keep the Master fan-sync variables in the action
list. This is likely one variable assignment or one extra action step.

### D1/Heat Wave Override Gate — ✅ PORT

`input_boolean.heat_wave_override == off` is already a condition in
live Section 2. In Stage 0, this becomes part of the precedence model
(P0: manual override, P1: away mode, P1.5: heat wave override).

**Effect on Stage 0:** Add the heat wave override condition to the
condition block (one line of YAML). Ensure the action template checks
it before commanding any zone.

## Design Items Still Needing Work

### D2: Turbo capability preflight (BLOCKING)

Stage 0 YAML hard-codes `cooling_fan_mode: turbo`. This must be verified
live before implementation. The preflight doc
(`docs/analysis/turbo_capability_preflight.md`) does not yet exist.

**What needs live verification:**
1. `fan_modes` inventory per Samsung head (LR, Master, Lincoln, Lilly)
2. The actual fan-mode token string (is it literally `"turbo"`?)
3. Correct service call — `climate.set_fan_mode` vs. `climate.set_preset_mode`
4. Persistence under subsequent `climate.set_temperature` or `climate.set_hvac_mode`
5. Non-interaction with `v8_samsung_auto_guardrail`
6. Fallback rule if turbo is unavailable on any head

**This should be run first** — before code writing — so the results
feed into the Stage 0 YAML generation. The operator can run this
manually in HA or have the AI gather it via HA API.

### D4: Precedence interaction matrix

The Rev 4 §1.3 precedence model (P0–P5) does not explicitly place
heat wave override or away mode. Even though D1 decided what to port,
their exact position in the gate order and how they interact with
truth-invalid off-biasing is not documented.

**What's needed:** A pseudocode section showing for each zone (Master,
Lincoln, Lilly, LR) the ordered list of gates that resolve
`cool` / `off` / hold, and where a truth-invalid check short-circuits
to `off`. This belongs in the drift reconciliation doc.

The resolved order is:
1. Manual override timer active → stand down entirely (P0)
2. Away mode → off all zones (P1)
3. Heat wave override active → cool/61/turbo all zones (P1.5)
4. Night conservation (LR night primary) → LR hold, bedrooms follow
   bedtime bands (P2)
5. Kids bedtime 18:00-07:00 → Lincoln + Lilly follow bedtime deadband
   (P3). Lilly's band is 68/72. Lincoln's band is X/X (confirm).
6. Lilly permanent 19:00-07:00 band → 68/72 (overlaps with kids bedtime
   but is Lilly-specific)
7. Master night band → P2 from Rev 4
8. Daytime → standard deadband (P5 from Rev 4)
9. Per-zone truth-invalid → short-circuit that zone to off at any
   precedence level

### D5: M1 HVAC-mode-as-memory sign-off

Stage 0 uses M1 (reads the thermostat's current hvac_mode to determine
whether we're in cooling or heating). Rev 4 called out `fan_only` / `auto`
edge cases where this could read stale. Needs operator sign-off.

**Open question to operator:** Accept M1 as-is (with the known edge
cases where a transient `fan_only` or `auto` mode could be misread),
or introduce per-path state latches now?

### D6: §1.4 framing clarification

Rev 4 §1.4 says LR cooling is ineligible in shoulder. In practice,
this is enforced by the season-mode branch selection (cooling branch
doesn't run in shoulder). Needs one doc line clarifying this is a
branch-level enforcement, not a within-branch guard.

### D7: Test coordination

Author a test-plan appendix in the drift reconciliation doc. Key changes:

- **Byte-hash re-pin:** `EXPECTED_SECTION_HASHES["section2_main_supervisor"]`
  in `tests/test_supervisor_manual_observability.py`. Section 3 / Section 14 /
  `EXPECTED_CONFIGURATION_HASH` must stay unchanged.
- **Break-and-update:** `test_section2_cooling_setpoint_doctrine.py`
  (hard-codes per-zone `*_setpoint` variables + Lilly terms — Stage 0
  replaces both). Re-verify `test_section2_kids_bedtime.py`,
  `test_section2_lr_night_profile.py`, `test_section2_shove_command_setpoints.py`,
  `test_supervisor_shoulder_night.py`.
- **New tests:** `test_section2_kids_bedtime_contract.py`,
  `test_section2_away_precedence.py`,
  `test_section2_turbo_on_cool_commands.py`,
  `test_section2_hysteresis_comparators.py`,
  `test_section2_bedroom_cooling_priority.py`.
- **Un-skip:** Two `@pytest.mark.skip` tests in
  `tests/test_packetA_truth_unavailable_failsafe.py` that are gated on
  Packet B landing.

## Execution Order

1. **D2 (turbo preflight)** — run live verification first
2. **D1 drift reconciliation doc** — produce
   `docs/analysis/packet_b_stage0_drift_reconciliation.md` incorporating
   the operator decisions above and resolving D4, D5, D6
3. **D7 test plan** — appendix in the same doc
4. **Implementation** — regenerate Stage 0 YAML from Rev 4 + drift
   reconciliation + preflight, update tests, re-pin Section 2 hash,
   open PR

## Settled Decisions (do NOT redesign)

- Precedence order P0–P5 and the §1.3 threshold matrix (Rev 4)
- Actuator shove doctrine: `hvac_mode: cool` → `61 °F` → `fan_mode: turbo`
- §1.5 Bedroom Cooling Priority (shoulder LR heat forced off when any
  bedroom cools AND `lr_truth > 60`); `v9_sleep_priority_interlock`
  stays as reactive backstop
- Per-zone `<zone>_truth_ok` variables with
  `float(none) is not none and x==x and -90≤x≤200`; invalid truth
  resolves the zone's call to `off`
- Stage 0 confined to Section 2 of `automations.yaml`; no helpers, no
  `configuration.yaml` change, Packet A `v8_6_*` automations preserved
  verbatim
- Rollback = `git revert` + reload (Rev 4 §9)
- Stage 1 (Shadow Evidence MVP) is a separate, later PR

---

## Appendix: follow-up operator decisions (recorded 2026-07-09, post-handoff)

Two items from §"Design Items Still Needing Work" above were resolved in a
follow-up session after this handoff was authored. Recorded here so the
next Packet B session finds them in one place.

### D-Lincoln: Lincoln's bedtime band — 66/70 (2026-06-07 decision preserved)

The handoff §D4 line read *"Lilly's band is 68/72. Lincoln's band is X/X
(confirm)."* Operator answer: **keep Lincoln at 66/70** per the 2026-06-07
operator decision in `AGENTS.md`. Asymmetry with Lilly (68/72 permanent
19:00–07:00) is intentional — Lincoln's room runs cooler and tolerates the
tighter band. `AGENTS.md` §"2026-06-07 — Lincoln & Lilly bedtime cooling"
stays valid for Lincoln; a new dated entry should record the Lilly
refinement when Stage 0 lands.

### D5: M1 (HVAC-mode-as-memory) — accepted, latches deferred to Stage 1

Stage 0 lands on **M1 as-is**. No new helpers in `configuration.yaml`.
Stage 0 remains a Section-2-only change.

Plain-language rationale (operator-facing): "M1" is the Rev 4 doctrine name
for the supervisor's memory of "am I currently in a cooling call?" — used
to hold state through the deadband (temp between engage and release, so
we neither turn ON nor turn OFF, we hold whatever we were doing). M1
answers that by reading the mini-split head's CURRENT `hvac_mode` back off
the head (e.g. `is climate.master_bedroom_air currently 'cool'?`). Free
— no extra helpers, no state to persist — but occasionally the head
reports a transient `fan_only` or `auto` mode for a few seconds (Samsung
auto-mode transitions, cloud latency). If the supervisor happens to fire
during that transient, its hold logic reads an unexpected mode string and
falls through to `off`. Consequence: a very short cooling call could be
released one 15-min tick early. Not a safety issue. Stage 1 alternative
would introduce per-zone `input_boolean` "cooling-call latches" that the
supervisor writes on ON/OFF transitions and reads back — bulletproof, but
adds helpers to `configuration.yaml`, breaking the "Stage 0 = Section 2
only" invariant. **Stage 1 may revisit if telemetry shows real misreads.**
