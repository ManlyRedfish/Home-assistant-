# Discovery: LR Night Cooling Steals Master Bedroom Capacity

**Date:** 2026-07-03
**Author:** Hermes (read-only investigation)
**Status:** Discovery — ready for Codex plan

---

## 1. Problem Statement

Eric reports: "my room [Master Bedroom] stays too hot at night because the living room keeps kicking on."

The Samsung mini-split system uses a **single shared outdoor compressor** across all four indoor heads. When the Living Room and Master Bedroom both call for cooling simultaneously, refrigerant capacity is divided. With the LR running on turbo and the Master on auto fan, the Master loses the contest.

## 2. Evidence: Current State (3:30 PM ET, July 3)

| Zone | HVAC Mode | Setpoint | Fan Mode | Current Temp | Firing |
|------|-----------|----------|----------|-------------|--------|
| **Living Room** | cool | 61°F | **turbo** | **~71°F** ✅ | **ON** |
| **Master Bedroom** | cool | 61°F | auto | **84-86°F** 🔴 | ON |
| Lincoln | cool | 61°F | auto | 77°F | ON |
| Lilly | cool | 61°F | turbo | 77°F | ON |

**Context:** Heat wave override expired ~09:50 ET. Section 2 supervisor resumed control. The Master has been running cool@61 since 11:45 (4+ hours) and the truth temp has **risen** from 77°F to 86°F despite continuous cooling. This is evidence of capacity starvation — the head is running but not moving enough heat.

## 3. Evidence: Historical Firing Correlation (Last 48h)

### LR Heat Pump Firing (July 1-3)
The LR fired **continuously through late evening and overnight** during the heat wave:

| Night | Time Window | LR Firing Pattern |
|-------|-------------|-------------------|
| Jul 1-2 | 18:00-05:00 | Frequent cycling on/off (~20-30 min intervals) |
| Jul 2-3 | 18:00-05:26 | Cycling continued under heat wave override |

### Master Heat Pump Firing
The Master fired intermittently during the same periods. After the override expired:

| Time | Event |
|------|-------|
| ~11:30 ET | Master firing goes OFF (truth still climbing) |
| ~11:45 ET | Master firing resumes (cool@61) |
| 11:45-16:13 ET | Master temp climbs from **77°F → 86°F** despite running |

The Master's truth temperature trajectory shows it's **unable to cool effectively** when competing with the LR.

## 4. Evidence: Temperature Trajectory Today

### Master Bedroom Truth (today, chronological from 11:45 AM)

| Time (EDT) | Temp |
|-----------|------|
| 11:45 | 77.2°F |
| 12:09 | 77.5°F |
| 12:32 | 77.9°F |
| 12:54 | 78.2°F |
| 13:14 | 78.0°F |
| 13:28 | 78.4°F |
| 13:58 | 78.5°F |
| 14:12 | 79.0°F |
| 14:27 | 79.3°F |
| 14:31 | 79.5°F |
| 14:38 | 79.8°F |
| 14:50 | 80.2°F |
| 15:04 | 80.5°F |
| 15:17 | 80.8°F |
| 15:27 | 81.0°F |
| 15:37 | 80.9°F |
| 16:10 | 81.0°F (and climbing) |

**Steady climb despite continuous cooling at 61°F.** Rate: ~0.5-1.0°F per hour rise.

### Living Room Truth (same period)

| Time (EDT) | Temp |
|-----------|------|
| 12:05 | 68.2°F |
| 12:47 | 69.2°F |
| 13:40 | 69.2°F |
| 14:30 | 69.5°F |
| 14:55 | 70.0°F |
| 15:35 | 70.3°F |
| 16:10 | 70.8°F |

**LR is well-controlled at 68-71°F** while running cool@61/turbo. The LR is holding its temperature comfortably while the Master cannot.

## 5. Root Cause: Architecture Gap

### Single compressor, shared capacity
The Samsung multi-split system uses one outdoor compressor for all four heads. Documented in `docs/5_runtime_layer.md` line 155:

> *"No explicit multi-head capacity arbitration. The automations file explicitly states that this is deferred until there is measured evidence of real starvation under load."*

**This discovery IS the measured evidence.** The Master climbing 9°F over 4+ hours while running cool@61 constitutes starvation under load.

### Section 2 Cooling Branch (automations.yaml lines 652-665)
The LR runs a **flat 68/72 deadband 24/7** in cooling:

```yaml
lr_off_at: "{{ 74 if away else 68 }}"
lr_on_at:  "{{ 76 if away else 72 }}"
```

No night-time relaxation. Every time LR temp drifts above 72°F at night, it kicks on at 61/turbo and competes for compressor capacity.

### Existing infrastructure, unused
- `input_boolean.night_mode_lr_primary` — **exists** (currently OFF), designed for LR night conservation
- `lr_night_primary` template variable — **read on line 429** but only consumed in heating/shoulder branch (line 805), NOT in the cooling branch.
- `packet_b_revision_4_control_contract.md` CHANGE-3 — **already designed** the LR night conservation profile

## 6. Existing Design (from packet_b_revision_4_control_contract.md)

CHANGE-3 — LR night conservation profile (line 438-444):

> In the cooling branch, when `night_mode_lr_primary` is on and not away: LR uses **76 engage / 74 release / hold-through / cool@61/turbo** instead of the daytime 72/68.

| Profile | Engage | Release | Setpoint | Fan |
|---------|--------|---------|----------|-----|
| Daytime (default) | >72°F | ≤68°F | 61°F | unchanged |
| LR Night (P4) | >76°F | ≤74°F | 61°F | turbo |
| Away (P1) | >76°F | ≤74°F | 61°F | turbo |

## 7. Implementation Boundary

**File to change:** `automations.yaml`, Section 2 cooling branch, LR command block (lines 652-665).

**Scope:** The LR `lr_off_at` / `lr_on_at` thresholds in the cooling season branch when `night_mode_lr_primary` is ON and not away mode.

**No new helpers, no new files.** The `input_boolean.night_mode_lr_primary` helper already exists and is editable from the HA UI.

**No other sections affected.** Section 3 safety gates, Section 4 ghost assassin, Section 5 auto season, Section 6 fan destrat, Sections 7-16 are all untouched.

## 8. Safety Gates (still active during night mode)

- **V7.5 Safety Ceiling Gates** — independent comfort upper bound (76°F rooms) — if LR hits ceiling, safety fires regardless of night mode
- **V8.2 Runaway Cooling Cutoff (LR)** — 60°F floor, independent
- **Manual Override Watcher** — any manual HVAC adjustment starts `timer.manual_hvac_override` which gates the whole supervisor
- **Section 19 Heat Wave Override** — if enabled, Section 2 is fully gated anyway

The 74/76 conservation profile keeps the LR above the safety ceiling (76°F engage, ceiling gates trip at 76°F with separate logic) — no conflict.

## 9. Turbo Fan on All Cooling Calls

CHANGE-2 from the control contract (already documented, not yet implemented) adds `fan_mode: turbo` on every cooling call. This would benefit the Master as well but is a separate concern — the LR night profile is the primary fix for the sleeping comfort complaint.

## 10. References for Codex

- `automations.yaml` lines 646-665 — current LR cooling command
- `automations.yaml` line 429 — `lr_night_primary` variable (already defined, unused in cooling)
- `automations.yaml` line 427 — `is_night` variable (22:00-06:00)
- `docs/analysis/packet_b_revision_4_control_contract.md` — CHANGE-3 design (LR night 76/74 profile)
- `input_boolean.night_mode_lr_primary` — existing helper, currently OFF
- `input_boolean.away_mode` — existing helper, currently OFF
