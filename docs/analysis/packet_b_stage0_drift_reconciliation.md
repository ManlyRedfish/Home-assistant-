# Packet B Stage 0 — Drift Reconciliation

## Purpose

Records how the four features that drifted onto `main` since the Stage 0
artifact was written are handled in the Stage 0 replacement, plus the
resolved precedence order, framing clarifications, and test plan.

## Handoff decisions (from 2026-07-09 operator session)

All decisions recorded in `session-context/packet-b-handoff-for-claude.md`
and the `packet_b_stage0_operator_decisions_2026-07-09.md` document.
Treated as inputs — not re-litigated here.

| Feature | Decision | Rationale |
|---------|:--------:|:----------|
| V9-E Pre-cool | DEFER — remove from Stage 0 | Non-functional — can't concentrate compressor with kids running |
| Lilly Heatwave Guard | SIMPLIFY — permanent 68/72 19-07 band | Cold air falls from her room into kitchen |
| Master fan-sync | PORT — variables preserved | Room geometry requires fan for effective cooling |
| Heat Wave Override gate | PORT at condition level | Already exists as condition; no within-branch changes needed |
| D3 shoulder deadband | 68/72 with hold-through | Operator confirmed; proven energy-efficient |

## D6 framing: LR shoulder ineligibility

Rev 4 §1.4 states LR cooling is ineligible in shoulder. This is enforced
by the **season-mode branch selection** — the cooling branch (Branch 1)
does not run when `season != 'cooling'`. No within-branch guard is needed.
The shoulder branch (Branch 2) does not offer LR cooling commands under
any path in Stage 0, consistent with §1.4.

## Precedence pseudocode (per zone)

The following gate order applies to each zone's cooling decision. Lower
number = higher precedence. At any level, if `truth_ok` is false, the
zone short-circuits to `off`.

```
For each zone (Master, Lincoln, Lilly, LR):

  1. manual_hvac_override != idle → stand down entire automation
     (gated at the condition level, not per-zone)

  2. heat_wave_override == on → automation condition blocks firing
     (gated at the condition level, not per-zone)

  3. P1 — away mode
     - All zones: off (relaxed thresholds in cooling branch, but
       effectively off for bedrooms)

  4. P2 — LR night conservation (when lr_night_primary == on)
     - LR: hold at 74/76 deadband (relaxed, conserve runtime)
     - Bedrooms: follow their respective bedtime/night bands

  5. P3 — kids bedtime (18:00-07:00, cooling + shoulder)
     - Lincoln: 66/70 deadband, independent
     - Lilly: 68/72 deadband, independent (permanent, all nights)
     - Master: unaffected by P3; follows P2 or P5
     - LR: unaffected by P3; follows P4 or P5

  6. P4 — Lilly permanent bedtime (19:00-07:00)
     - Lilly: 68/72 deadband (overlaps with P3; consistent band)

  7. P5 — daytime standard deadband
     - Master: 68/72 (night: 62/66)
     - Lincoln: 68/72 (bedtime: owned by P3)
     - Lilly: 68/72 (bedtime: owned by P3/P4)
     - LR: 68/72 (night conservation: 74/76)

  8. truth_ok == false → short-circuit THAT ZONE to off
     Applied at ANY level — if truth is invalid when the zone's
     deadband decision is evaluated, the zone goes to off regardless.
```

## Test coordination (D7)

### Hash re-pin

`EXPECTED_SECTION_HASHES["section2_main_supervisor"]` in
`tests/test_supervisor_manual_observability.py` — new hash computed
from the Stage 0 replacement. Follow the existing re-pin history
convention with an explanatory comment.

### Must stay unchanged

- Section 3 hash (safety gates — `"section3_safety_gates"`)
- Section 14 hash (LR heating recovery boost)
- `EXPECTED_CONFIGURATION_HASH` (configuration.yaml untouched)

### Break-and-update tests

| Test file | What changed |
|-----------|-------------|
| `test_section2_cooling_setpoint_doctrine.py` | Per-zone `*_setpoint` variables + Lilly guard terms replaced by Stage 0 |
| `test_section2_kids_bedtime.py` | Re-verify with new Lilly 68/72 band |
| `test_section2_lr_night_profile.py` | Re-verify |
| `test_section2_shove_command_setpoints.py` | Re-verify |
| `test_supervisor_shoulder_night.py` | Re-verify (V9-E references removed) |

### New tests (Rev 4 §5.2)

| Test file | Purpose |
|-----------|---------|
| `test_section2_kids_bedtime_contract.py` | Verify Lincoln 66/70 and Lilly 68/72 bands |
| `test_section2_away_precedence.py` | Verify away overrides all other bands |
| `test_section2_turbo_on_cool_commands.py` | Assert fan-mode == `turbo` on every cool command |
| `test_section2_hysteresis_comparators.py` | Verify hold-through behavior |
| `test_section2_bedroom_cooling_priority.py` | Verify §1.5 bedroom priority |

### Un-skip

Two tests in `tests/test_packetA_truth_unavailable_failsafe.py`:
- `test_supervisor_declares_truth_validity_before_float_70_fallbacks`
- `..._invalid_truth_off_biased`

Both gated on Packet B landing.
