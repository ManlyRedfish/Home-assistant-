# Kids' Bedroom Overnight Cooling Plan (Lincoln & Lilly)

**Doc Date:** 2026-06-06 (v3 — supervisor-first in-place correction)
**Document Role:** Planning + adversarial review. **No operational changes.**
**Scope:** Lincoln's & Lilly's **cooling / shoulder hot-night** comfort only.
**Status:** Proposal. Live HAOS is source of truth; Codex verifies + implements.

> ## ⛔ The PR #134 / v2 approach is ABANDONED
> The previous revision proposed a **separate `kids_comfort_hold` automation**,
> per-room `input_number` setpoint helpers, and moving actuator ownership between
> Sections 2/3/6/8. **That design is rejected and withdrawn.** It violated the
> Moose House **supervisor-first** architecture (the Section 2 supervisor decides;
> the Samsung heads execute). This v3 plan does **not** create any new controller,
> helper, or ownership transfer.

> ## Architecture (unchanged): SUPERVISOR-FIRST
> **The Section 2 supervisor decides; the Samsung heads execute.** The native
> Samsung thermostat / inverter is the *actuator mechanism*, not a second
> controller. The supervisor maintains the **intended cooling mode + a real
> comfort target**, then lets the head **scale back (modulate)** as it approaches
> that target. Section 2 remains the **sole** kids' comfort-policy writer.

This task is the **smallest in-place Section 2 edit** that fixes the June 5–6
hot-night failure for Lincoln & Lilly. Planning only — no runtime YAML committed,
nothing deployed to live HAOS.

---

## 1. Executive diagnosis

In cooling/shoulder hot-nights, Section 2 controls Lincoln & Lilly with a
**`cool @ 61 °F` "shove" plus a bang-bang OFF at room-truth ≤ 68 °F**, and
**force-offs them in shoulder-night**. Because 61 °F is far below the comfort
target, the head runs flat-out and overshoots downward; the supervisor then cuts
it fully OFF at 68; the room free-heats to >72; the cycle repeats — the 67↔72
sawtooth. When auto-season flips `cooling → shoulder` at ~02:45 (outdoor Deck
64.4 °F), the shoulder-night branch **bulk-forces the kids off** for the rest of
the night, so the rooms sit at ~72 °F for hours. Section 2 also never sets the
kids' fan, so a manually-left **turbo** persists.

**The correct supervisor-first behavior** (what we were already testing) is to
have the supervisor command **`cool` at a real comfort target (~70 °F)** and
**leave the head in cool to modulate** — instead of shoving to 61 and bang-banging
to OFF — and to **not blind-force the kids off** in shoulder-night while their
rooms still need cooling. This is an **in-place change to the Section 2 Lincoln &
Lilly cooling/shoulder blocks only.**

---

## 2. Relevant files, entities, and live-vs-Git status

Only `automations.yaml` (Section 2) and its three locking tests change. No new
files, automations, or helpers.

| Concept | Entity / location | Status |
|---|---|---|
| Kids' heads | `climate.lincoln_air`, `climate.lilly_air` | live device |
| Kids' room truth | `sensor.lincoln_s_room_temperature_truth`, `sensor.lilly_s_room_temperature_truth` | `configuration.yaml:451,643` |
| Supervisor (sole comfort writer) | `automation.v7_5_main_supervisor` | `automations.yaml:358` |
| Season mode | `input_select.hvac_season_mode` | **live UI helper, not in Git** |
| Manual-override timer | `timer.manual_hvac_override` | **live UI helper, not in Git** (preserve behavior) |
| Auto-season switch | `automation.v7_5_auto_season_mode` | `automations.yaml:919` (unchanged) |

**Live vs Git vs stale doctrine — must be kept distinct:**

- **Exists in Git (and is what the locking tests pin):** kids `cool @ 61` +
  `off ≤ 68` + `on > 72` + shoulder-night bulk-off. This is the *legacy* behavior.
- **Exists only live / being verified:** the operator reports the **real
  comfort-target behavior "we were already testing"** — i.e., commanding a real
  target (~70) and letting the head modulate. **The exact tested target value is
  not in Git** (Git has 61). Codex must read it from the live supervisor and
  confirm it holds **room truth ≤ 70 °F** given the Samsung internal-sensor bias
  (Lincoln Samsung ≈ +4.7 °F vs truth).
- **Stale doctrine (describes the abandoned approaches, do not follow for the
  kids):** the `cool@66` values in `comfort_failure_forensics.md` §8.6 / the
  `comfort_control_actuator_arbitration_spec.md` "off-inside-the-band / 61 shove"
  doctrine / "deadband is the comfort contract." These remain valid for *other*
  rooms but are superseded for Lincoln & Lilly cooling.
- **Codex must verify in HAOS:** the live Section 2 may already contain partial
  comfort-target edits from the testing — **diff live `automations.yaml` Section 2
  against Git before patching** (§7).

---

## 3. Exact current failure chain (cooling/shoulder hot-night)

1. **T+0 (any cooling tick):** supervisor runs (every 15 min) → cooling branch →
   commands kids **`cool @ 61`** (`automations.yaml:439,459`). Head runs flat-out.
2. **Overshoot:** 61 °F demand + (stuck) turbo pulls the room well below the ~70
   target, toward ~67 °F.
3. **Bang-bang OFF:** next tick sees room-truth **≤ 68** → supervisor commands
   **`off`** (`:446–450`, `:466–470`). Compressor stops entirely.
4. **Free-heat:** with the head off, the room climbs back toward 72 °F.
5. **Re-shove:** room-truth crosses **> 72** → supervisor re-commands `cool @ 61`.
   → **67↔72 sawtooth** (steps 1–5 repeat).
6. **02:45 season flip:** Deck 64.4 °F sustained 2 h → `v7_5_auto_season_mode`
   sets `shoulder`; the season change is also a **supervisor trigger**
   (`:364–365`) → Section 2 re-runs immediately.
7. **Shoulder-night force-off:** now `shoulder` + `is_night` → branch bulk-commands
   **`[lincoln_air, lilly_air, dining_room] → off`** (`:533–535`) regardless of
   room temp. Kids stay off for the rest of the night → **~72 °F for hours**
   (Lilly to 08:30).
8. **Fan:** Section 2 issues **no** kids' fan command, so `turbo` persists all night.

---

## 4. Every live Section 2 write to `climate.lincoln_air` / `climate.lilly_air`

(Identified per the source-of-truth requirement; line numbers are Git `main`-class
`automations.yaml`. **Codex must re-confirm against live** — see §2/§7.)

| # | Write | Lines | Current behavior | Scope |
|---|---|---|---|---|
| A | Cooling-season `set_temperature` Lincoln | 438–451 | `cool@61 / off≤68 / on>72 / hold` | **IN SCOPE — change** |
| B | Cooling-season `set_temperature` Lilly | 458–471 | same | **IN SCOPE — change** |
| C | Shoulder-**night** bulk-off | 533–535 | `[lincoln,lilly,dining] → off` | **IN SCOPE — change** |
| D | Shoulder-**day warm** `set_temperature` Lincoln | 545–547 | `cool if >70 else off, temp 61` | Adjacent — optional `61→70` |
| E | Shoulder-**day warm** `set_temperature` Lilly | 548–550 | same | Adjacent — optional |
| F | Shoulder-**day cold** bulk-off | 576–578 | `[master,lincoln,lilly,dining] → off` | Out of scope (note) |
| G | Shoulder-**day mild** bulk-off | 580–582 | `[lr,master,lincoln,lilly,dining] → off` | Out of scope (note: contributes to post-06:00 morning warmth) |
| H–K | Heating-season kid writes / bulk-offs | 609–614, 632–634, 639–644, 670–672 | heat / off | **Out of scope — winter (untouched)** |
| — | Season-change retrigger | 364–365 | re-runs supervisor on `hvac_season_mode` change | Fixed implicitly by C |
| — | Manual-override gate | 366–369 | `timer.manual_hvac_override == idle` | **PRESERVE exactly** |
| — | Kids' **fan-mode** writes | — | **none exist** → `turbo` sticks | Optional quiet-fan (confirm live) |

**Core minimal change = A, B, C.** D/E are a one-token consistency tweak;
F/G/H–K are explicitly out of scope.

---

## 5. The in-place correction (supervisor-first)

Keep the existing per-room variables/blocks; change only the kids' **values and
the mode template** so the supervisor maintains `cool @ target` and lets the head
modulate. **No new automation. No helpers. Master/LR/Dining/Nest unchanged.**

### 5.1 Cooling-season (A, B) — replace shove+bang-bang with comfort-target hold
- `l_setpoint` / `ly_setpoint`: **`61` → real comfort target (representative `70`;
  away `74`)** — confirm exact tested value live.
- **Engage at the target**, not 72: `l_on_at` / `ly_on_at`: `72 → 70` (away `76`).
- **Remove the lower bang-bang OFF**: delete the `elif <room>_temp <= *_off_at →
  off` line so the head, once cooling, **stays in cool and modulates** near 70.
  `l_off_at` / `ly_off_at` are no longer used and are removed.

### 5.2 Shoulder-night (C) — stop blind force-off; keep cooling when warm
- Remove `climate.lincoln_air` and `climate.lilly_air` from the bulk-off list
  (Nest stays off); give each kid the **same** corrected cool-target decision as
  §5.1. This mirrors the existing **Master shoulder-night cooling escape**
  (`:519–532`) — a known, test-backed pattern — so the kids keep cooling/modulating
  when their rooms are still warm and idle (head-modulated) when not.

### 5.3 Optional consistency (D, E)
- Shoulder-day **warm path** kid setpoints `61 → 70` so a daytime warm room is
  held at the same comfort target. (Does not change its existing `>70` engage.)

### 5.4 Optional, confirm-live (fan)
- If the tested behavior included a quiet fan, add a single `climate.set_fan_mode`
  (e.g. `low`/`auto`) to the kids' cool path so `turbo` no longer sticks; reserve
  `turbo` for the 76 °F ceiling gate. Confirm supported fan-mode names live.

### 5.5 Representative YAML (illustrative — DO NOT APPLY; Codex adapts vs. live)
```yaml
# COOLING branch — Lincoln (Lilly identical with ly_*). Replaces :438–451.
- variables:
    l_setpoint: "{{ 74 if away else 70 }}"   # real comfort target (was 61 shove)
    l_on_at:    "{{ 76 if away else 70 }}"    # engage AT the target (was 72)
    l_current:  "{{ states('climate.lincoln_air') }}"
- action: climate.set_temperature
  target: { entity_id: climate.lincoln_air }
  data:
    hvac_mode: >-
      {% if lincoln_temp > l_on_at %}cool
      {% elif l_current == 'cool' %}cool   {# stay in cool; head modulates near target #}
      {% else %}off{% endif %}             {# no bang-bang off at the old ≤68 edge #}
    temperature: "{{ l_setpoint }}"

# SHOULDER-NIGHT — replaces the kids portion of the :533–535 bulk-off.
# Keep Nest in the bulk-off; give each kid the SAME corrected decision as above.
- action: climate.set_hvac_mode
  target: { entity_id: climate.dining_room }   # was [lincoln_air, lilly_air, dining_room]
  data: { hvac_mode: "off" }
# + per-kid `climate.set_temperature` cool@70 blocks (independent), mirroring
#   the Master shoulder-night escape directly above them.
```

> **Why the head no longer needs a supervisor OFF:** at `61` the head would freeze
> the room, so the supervisor *had* to cut it off at 68. At a real `70` target the
> head **modulates to idle on its own** when the room reaches ~70 — so "stay in
> cool" is correct and the bang-bang OFF is removed. The exact commanded number is
> whatever holds **room truth ≤ 70** given the head's biased internal sensor;
> confirm the live tested value (§7).

---

## 6. From → To behavior table

| Aspect | From (Git/legacy, test-locked) | To (in-place Section 2) |
|---|---|---|
| Kids cooling setpoint | `cool @ 61` shove | `cool @ ~70` comfort target (away 74) |
| Kids lower OFF | `off` when truth ≤ 68 (bang-bang) | **removed** — stay `cool`, head modulates |
| Kids cooling engage | truth `> 72` | truth `> 70` (at the target) |
| Shoulder-night kids | bulk-forced `off` | same cool-target decision; only Nest force-off |
| Shoulder-day warm kids (opt) | `cool @ 61` if `>70` | `cool @ 70` if `>70` |
| Kids fan (opt, confirm live) | unset → `turbo` sticks | quiet (`low`/`auto`) while cooling |
| Master / LR / Dining / Nest | `61` shove + deadband | **UNCHANGED** |
| Manual-override gate | `idle` | **UNCHANGED** |
| Section 3 floors / 76° ceiling | 58 / 60 / 76 | **UNCHANGED** |
| Winter/heating kid branches | heat / off | **UNCHANGED (out of scope)** |

---

## 7. Live verification checklist (Codex, before patching)

1. **Diff live vs Git:** dump live `automation.v7_5_main_supervisor` Section 2 and
   compare to Git. Record any live comfort-target edits already present from the
   testing (so the patch matches, not reverts, live intent).
2. **Confirm the failure source:** Logbook / `hvac_provenance_log` for
   `climate.lincoln_air` / `climate.lilly_air` over 2026-06-05 21:00 →
   06-06 08:30 — expect `v7_5_main_supervisor` writes at `:00/:15/:30/:45` (and
   02:45) commanding `cool@61` / `off`, and the shoulder-night force-off.
3. **Exact comfort target:** read the value the operator was testing; confirm it
   holds **room truth ≤ 70 °F**. Characterize Samsung-internal vs room-truth bias
   per head during active cooling so the commanded number is right.
4. **Head mode:** confirm heads run in `cool` (not Samsung `auto`, which would trip
   Section 8 and behave differently).
5. **Fan:** confirm `turbo` origin (no Section 2 write sets it) and the supported
   fan-mode names before adding any quiet-fan command.
6. **Helpers exist live:** `input_select.hvac_season_mode`,
   `timer.manual_hvac_override` (and its duration), `input_boolean.away_mode`.
7. **05:45 Lincoln anomaly:** classify the re-engage origin (manual / cloud /
   ceiling gate) from the live trace.

---

## 8. Tests that genuinely need updating

Only the three Section-2 cooling/shoulder locks. Safety/invariant tests stay green.

- **`tests/test_section2_cooling_setpoint_doctrine.py`** — update the **kids only**:
  `l_setpoint`/`ly_setpoint` `"{{ 61 }}"` → `"{{ 74 if away else 70 }}"`;
  `l_on_at`/`ly_on_at` → `"{{ 76 if away else 70 }}"`; **remove** the
  `l_off_at`/`ly_off_at` asserts and their entries in the required-variable set
  (lines 59–60, 69, 87–90). **Leave `m_*` and `lr_*` (Master/LR = 61) unchanged.**
- **`tests/test_section2_shove_command_setpoints.py`** — the cooling-command
  scan (`== 61`, count check at line 144–146) and the kids threshold-string
  asserts (153–156) must reflect kids `= 70` (Master/LR remain `61`); adjust the
  expected cooling-command count for the new kids cool@70 paths (cooling + the
  shoulder-night kids cool blocks). Keep the `58/60` safety asserts and the
  "no arbitration/comfort_profiles" asserts intact.
- **`tests/test_supervisor_shoulder_night.py`** — change
  `test_shoulder_night_bulk_off_still_covers_lincoln_lilly_dining` to require only
  `climate.dining_room`, and add kids "cooling-escape step exists" + "excluded from
  bulk-off" asserts mirroring the existing Master-escape tests (101–123). Keep the
  Master/LR shoulder-night asserts unchanged.

---

## 9. Untouched invariants (must NOT change)

- **Section 2 remains the sole kids' comfort-policy writer.** No new automation,
  no `kids_comfort_hold`, no helpers, no ownership moved among Sections 2/3/6/8.
- **`timer.manual_hvac_override` behavior preserved exactly** — supervisor still
  gates on `idle`; the WAF watcher and override window are unchanged.
- **Section 3 unchanged** — LR runaway `<60`, Master floor `<58`, 76 °F ceiling
  gate, WAF watcher (locked by `test_safety_invariants.py`,
  `test_comfort_band_safety_separation.py`).
- **Master, LR, Dining, Nest unchanged** — they keep `61` shove + deadband.
- **Winter / heating-season kid branches unchanged** (separate future decision).
- **Telemetry, truth sensors, MSR/Apollo boundary, report-time freshness,
  auto-season thresholds** unchanged.
- **Lincoln & Lilly stay independent** — separate per-room `set_temperature`
  steps; one reaching its target never disables the other.

---

## 10. Rollback plan

- Change set = `automations.yaml` Section 2 (kids cooling + shoulder-night blocks)
  + the three test files above. **Rollback = `git revert` the patch + reload
  automations.** No entities renamed, no truth/helper/telemetry migration.
- Because Git may lag live, Codex should **first commit the live Section 2** (so
  the repo matches reality), then apply the patch on top — so rollback returns to
  the actual prior live state.
- Master/LR/Dining/Nest and all Section 3 safety remain untouched, so rollback
  never affects other rooms or equipment protection.

---

## 11. Codex prompt — smallest live patch

```
ROLE: Modify the LIVE Moose House Home Assistant config inside HAOS. Git lags
live; LIVE YAML + live traces are source of truth. Read
docs/kids-bedroom-overnight-cooling-plan.md (v3) first.

ARCHITECTURE: SUPERVISOR-FIRST. automation.v7_5_main_supervisor (Section 2)
decides; the Samsung heads execute and modulate. Do NOT create a separate
controller. The PR #134 kids_comfort_hold approach is ABANDONED — do not
re-introduce it, its input_number setpoint helpers, or any ownership transfer
among Sections 2/3/6/8.

GOAL: Smallest in-place Section 2 edit so Lincoln & Lilly hold a real comfort
target (~70°F, room truth <=70) and let the head modulate, instead of cool@61
+ bang-bang off<=68 + shoulder-night force-off. Cooling/shoulder hot-night only.

STEP 0 — VERIFY LIVE (report before editing):
  1. Diff live Section 2 vs Git; record any comfort-target edits already present
     from testing. COMMIT the live Section 2 so the repo matches reality first.
  2. Confirm via Logbook/hvac_provenance_log that Section 2 writes the kids' heads
     cool@61/off at :00/:15/:30/:45 (and the 02:45 shoulder force-off).
  3. Read the exact comfort target you were testing; confirm it holds room truth
     <=70 given Samsung internal-sensor bias. Confirm heads run 'cool' (not
     'auto') and list supported fan modes.

STEP 1 — PATCH SECTION 2 (Lincoln & Lilly only):
  A/B. Cooling branch: set kids setpoint to the comfort target ("{{ 74 if away
       else 70 }}"); engage at the target (l_on_at/ly_on_at "{{ 76 if away else
       70 }}"); REMOVE the lower "off when temp<=off_at" branch so the head stays
       in cool and modulates. Remove the now-unused l_off_at/ly_off_at vars.
  C.   Shoulder-night: remove climate.lincoln_air & climate.lilly_air from the
       bulk-off (keep climate.dining_room) and give each kid the SAME cool-target
       decision, mirroring the existing Master shoulder-night escape directly
       above it. Keep Lincoln & Lilly independent.
  (Optional) D/E: shoulder-day warm path kid setpoints 61 -> 70.
  (Optional, if it matches what you tested) add a quiet kids fan (low/auto) on the
       cool path so turbo stops sticking; reserve turbo for the 76F ceiling gate.

  DO NOT touch Master, LR, Dining, Nest, the manual-override gate, Section 3, the
  heating-season kid branches, telemetry, truth sensors, or any other automation.

STEP 2 — UPDATE ONLY THESE TESTS:
  - test_section2_cooling_setpoint_doctrine.py: kids setpoint/on_at -> 70 set,
    remove l_off_at/ly_off_at asserts; leave Master/LR (61) asserts unchanged.
  - test_section2_shove_command_setpoints.py: kids cooling commands now 70 (Master/
    LR stay 61); fix the cooling-command count + kids threshold strings; keep the
    58/60 + no-arbitration asserts.
  - test_supervisor_shoulder_night.py: kids no longer required in bulk-off (Nest
    only); add kids cooling-escape asserts mirroring the Master-escape tests.

VALIDATE: python -m pytest tests/ ; ha core check ; reload ; confirm Section 2 now
commands kids cool@~70 and the head MODULATES (hvac_action run->idle) instead of
cycling 61<->off; confirm shoulder flip no longer force-offs the kids; capture
2-3 nights and confirm room truth stays <=70 with far fewer off<->cool transitions
than the June 5-6 baseline. Master/LR/Section 3 unchanged.

ROLLBACK: git revert the Section 2 + test changes and reload. No migrations.

If live contradicts this plan, STOP and report instead of inventing behavior.
```

---

### Appendix — what this plan deliberately does NOT do
- Does **not** remove Lincoln/Lilly from Section 2, create `kids_comfort_hold`,
  add `*_cool_setpoint` helpers, or move actuator ownership between sections
  (all explicitly rejected; PR #134 approach abandoned).
- Does **not** redesign winter heating or rewrite Moose House doctrine.
- Does **not** change Master/LR/Dining/Nest, Section 3 safety, the override
  contract, telemetry, truth sensors, or MSR boundaries.
- Does **not** implement anything in live HAOS — planning only.
