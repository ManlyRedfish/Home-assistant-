# Packet B Stage 0 — Copy Instructions

Design authority: PR #141, Packet B Revision 4, including the §1.5 Bedroom Cooling Priority amendment.

## What to copy

Copy the complete contents of:

`deploy/packet_b_stage0_section2_replacement.yaml`

In Home Assistant File Editor, replace only the existing block beginning with:

`# SECTION 2: MAIN SUPERVISOR`

and ending immediately before:

`# SECTION 3: SAFETY GATES & WATCHDOGS`

Do not replace the rest of `automations.yaml`.

## Why this is a section-only artifact

The live Home Assistant file supplied by Eric contains deployed Packet A logic that may not be present in repository `main`, including:

- the four `*_truth_ok` supervisor guards;
- `v8_6_truth_unavailable_cooling_failsafe`;
- `v8_6b_truth_unavailable_cooling_reconciliation`.

The replacement preserves the supervisor guards. The separate Packet A automations remain outside Section 2 and must remain untouched.

## Pre-apply

1. Download or copy the current complete live `automations.yaml` as a timestamped backup.
2. Confirm these anchors exist before editing:
   - `- id: v7_5_main_supervisor`
   - `# SECTION 3: SAFETY GATES & WATCHDOGS`
   - `- id: v8_6_truth_unavailable_cooling_failsafe`
   - `- id: v8_6b_truth_unavailable_cooling_reconciliation`
3. Replace only Section 2.
4. Do not edit `configuration.yaml` for Stage 0.

## Validation before reload

Run Home Assistant **Check configuration**.

Do not reload or restart if validation fails. Restore the backup or correct the Section 2 paste first.

After validation passes, reload automations using the supported Home Assistant UI action.

## Immediate checks

Confirm:

- `automation.v7_5_main_supervisor` exists and is enabled;
- the Packet A failsafe and reconciliation automations still exist and are enabled;
- no other automation IDs disappeared;
- all four Samsung heads retain valid states;
- current setpoints and modes changed only as the supervisor policy requires;
- the supervisor trace shows no template or service errors.

## Stage 0 behavior to verify

- Global away: all cooling-eligible heads use room-truth 74–76 hysteresis.
- Master 18:00–06:00: 62–66 hysteresis.
- Lincoln and Lilly 18:00–07:00: independent 66–70 hysteresis in cooling and shoulder.
- LR night helper: 74–76 conservation hysteresis in cooling season without changing `away_mode`.
- Daytime: 68–72 hysteresis, including shoulder warm-path bedrooms.
- Every active Samsung cooling call sends `cool`, 61°F, then `fan_mode: turbo`.
- During shoulder, any bedroom cooling call suppresses LR heat while LR truth is above 60°F.
- Heating-season behavior and every Section 3 safety automation remain unchanged.

## Rollback

Restore the timestamped pre-apply `automations.yaml`, run Check configuration, and reload automations.

Stage 0 adds no helpers, entities, migrations, or recorder changes.
