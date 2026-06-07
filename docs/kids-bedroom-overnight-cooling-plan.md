# Kids' Bedroom Overnight Cooling Plan (Lincoln & Lilly)

**Doc Date:** 2026-06-06 (v4 — supervisor-first in-place correction, cooling+shoulder)
**Document Role:** Planning + adversarial review. **No operational changes.**
**Scope:** Lincoln's & Lilly's **cooling + shoulder** comfort (night *and* day).
Heating/winter is **out of scope.** Live HAOS is source of truth; Codex verifies.

> ## ⛔ The PR #134 / earlier-revision approach is ABANDONED
> A separate `kids_comfort_hold` automation, per-room `*_cool_setpoint`
> `input_number` helpers, and moving actuator ownership between Sections 2/3/6/8
> were proposed earlier and are **rejected and withdrawn.** They violated the
> **supervisor-first** architecture. This v4 creates **no** new controller,
> helper, or ownership transfer.

> ## Architecture (unchanged): SUPERVISOR-FIRST
> **The Section 2 supervisor decides; the Samsung heads execute and modulate.**
> The native Samsung thermostat/inverter is the *actuator mechanism*, not a
> second controller. Section 2 maintains the **intended cooling mode + the real,
> live-verified comfort target**, then lets the head **scale back (modulate)** as
> it nears that target. Section 2 remains the **sole** kids' comfort-policy writer.

This is the **smallest in-place Section 2 edit** that fixes the June 5–6 hot-day-
and-night failure for Lincoln & Lilly across **cooling and shoulder** seasons.
Planning only — no runtime YAML committed, nothing deployed.

> ## Two numbers, kept distinct (important)
> - **`70 °F` = the room-truth comfort ceiling** ("no warmer than 70 — that's when
>   I have sweaty kids"). Operator-given; used only for the **truth-based ENGAGE
>   decision** in shoulder. Safe to reference directly.
> - **`verified_target` = the Samsung *setpoint* the supervisor commands** — the
>   exact value **already tested live** that holds room truth ≤ 70 given the head's
>   biased internal sensor. **NOT assumed to be 70.** Git currently has `61`; the
>   real value is live-only and Codex must read it (§7). Never hard-code 70 as the
>   command.

---

## 1. Executive diagnosis

In cooling/shoulder hot weather, Section 2 drives Lincoln & Lilly with a
**`cool @ 61` shove + a bang-bang OFF at room-truth ≤ 68**, and **bulk-forces them
off** in every shoulder sub-branch (night, and day mild/cold). Because 61 °F is far
below the comfort target, the head runs flat-out and overshoots down; the
supervisor then cuts it OFF at 68; the room free-heats past 72; repeat — the
67↔72 sawtooth. At ~02:45 auto-season flipped `cooling → shoulder` (Deck 64.4 °F);
shoulder-night force-offed the kids, **and after 06:00 the shoulder-day mild/cold
branches kept force-offing them**, so the warm plateau ran to ~08:30. The
supervisor never sets the kids' fan, so `turbo` persisted.

**Correct supervisor-first behavior:** Section 2 maintains **`cool @
verified_target`** and lets the head **modulate** — no 61 shove, no bang-bang OFF,
and **no blind force-off** while a room still needs cooling. The change is
confined to the **Lincoln & Lilly cooling and shoulder blocks of Section 2.**

---

## 2. Relevant entities + live-vs-Git status

Only `automations.yaml` (Section 2) and its three locking tests change. No new
files, automations, or helpers.

| Concept | Entity / location | Status |
|---|---|---|
| Kids' heads | `climate.lincoln_air`, `climate.lilly_air` | live device |
| Kids' room truth | `sensor.lincoln_s_room_temperature_truth`, `sensor.lilly_s_room_temperature_truth` | `configuration.yaml:451,643` |
| Supervisor (sole comfort writer) | `automation.v7_5_main_supervisor` | `automations.yaml:358` |
| Season mode / auto-switch | `input_select.hvac_season_mode` / `automation.v7_5_auto_season_mode` | live helper / `:919` |
| Manual-override timer | `timer.manual_hvac_override` | live UI helper (preserve) |

**Distinct sources:**
- **In Git (test-locked) = legacy:** kids `cool@61 / off≤68 / on>72` + shoulder
  bulk-offs.
- **Live-only / verify:** the **comfort target "we were already testing"**
  (`verified_target`) and its **away** variant — **not in Git** (Git has 61).
- **Stale doctrine (do not follow for the kids):** `cool@66` in
  `comfort_failure_forensics.md` §8.6; the `comfort_control_actuator_arbitration_spec.md`
  "61 shove / off-inside-the-band"; "deadband is the comfort contract." Valid for
  other rooms; superseded for Lincoln & Lilly cooling/shoulder.
- **Codex must verify in HAOS:** the live Section 2 may already hold partial
  comfort-target edits from the testing — **diff live vs Git before patching** (§7).

---

## 3. Exact current failure chain (cooling + shoulder, June 5–6)

1. Cooling tick → kids `cool @ 61` (`:439,:459`) → head runs flat-out, overshoots
   toward ~67.
2. Next tick room-truth ≤ 68 → supervisor `off` (`:446–450,:466–470`).
3. Head off → room free-heats toward 72.
4. Room > 72 → re-`cool @ 61`. → **67↔72 sawtooth** (1–4 repeat).
5. ~02:45 Deck 64.4 °F/2h → `shoulder`; season change re-triggers the supervisor
   (`:364–365`).
6. Shoulder-**night** → bulk-off `[lincoln,lilly,dining]` (`:533–535`) regardless
   of room temp.
7. After 06:00 shoulder-**day mild/cold** → bulk-off keeps the kids off (`:576–578,
   :580–582`) → warm plateau to ~08:30.
8. No kids' fan write → `turbo` sticks.

---

## 4. Every live Section 2 write to the kids' heads — and scope

(Per the source-of-truth requirement; Git line refs. **Codex re-confirms live**, §7.)

| # | Write | Lines | Current | Scope |
|---|---|---|---|---|
| A | Cooling-season Lincoln `set_temperature` | 438–451 | `cool@61 / off≤68 / on>72` | **IN — change to hold** |
| B | Cooling-season Lilly `set_temperature` | 458–471 | same | **IN — change to hold** |
| C | Shoulder-**night** bulk-off | 533–535 | `[lincoln,lilly,dining]→off` | **IN — escape + no-op** |
| D | Shoulder-day **warm** Lincoln | 545–547 | `cool if >70 else off, 61` | **IN — escape + no-op** |
| E | Shoulder-day **warm** Lilly | 548–550 | same | **IN — escape + no-op** |
| F | Shoulder-day **cold** bulk-off | 576–578 | `[master,lincoln,lilly,dining]→off` | **IN — escape + no-op** |
| G | Shoulder-day **mild** bulk-off | 580–582 | `[lr,master,lincoln,lilly,dining]→off` | **IN — escape + no-op** |
| H–K | Heating-season kid writes/bulk-offs | 609–614, 632–634, 639–644, 670–672 | heat / off | **OUT — winter (untouched)** |
| — | Season-change retrigger | 364–365 | re-runs on `hvac_season_mode` change | fixed implicitly by C–G |
| — | Manual-override gate | 366–369 | `timer.manual_hvac_override == idle` | **PRESERVE exactly** |
| — | Kids' fan writes | — | **none** → `turbo` sticks | Optional quiet-fan (confirm live) |

---

## 5. The in-place correction (supervisor-first)

Two policies, per the operator's spec. **No new automation, no helpers. Master/LR/
Dining/Nest unchanged.**

### 5.1 Cooling season (A, B) — **active hold, no OFF, no `else off`**
Replace each kid block with a single unconditional command: **maintain `cool @
verified_target`** and let the head modulate. **Remove** the truth-based lower OFF
*and* the `l_on_at`/`ly_on_at` engage thresholds *and* the `else off` mode
decision (the v3 artifact). The supervisor no longer decides cool-vs-off for the
kids in cooling season — it just holds the target; the inverter does the rest.
Preserve the prior **away** relaxation via a relaxed live-verified away target.

### 5.2 Shoulder season (C, D, E, F, G) — **truth-gated escape, no-op default**
Remove `climate.lincoln_air` / `climate.lilly_air` from **every** shoulder bulk-off
(keep the non-kid entities), and remove the warm-path kid `cool@61/else off`
blocks. Add **one independent per-room escape** that applies across all shoulder
sub-branches (night/warm/cold/mild):
- **Truth decides engagement:** if `room_truth > 70` (the comfort ceiling) →
  command `cool @ verified_target` (head modulates).
- **Non-engaged = NO-OP:** issue **no** command — **do not OFF** a kid's head
  merely because the shoulder branch is mild/cold. Leave the head unchanged unless
  an intentional policy or a Section 3 safety condition requires OFF. (Once
  engaged, the no-op naturally *maintains* the last `cool @ verified_target`, so
  the head keeps modulating until the room is clearly fine.)

Master keeps its existing shoulder-night cooling escape; LR keeps its heat/off;
Nest stays in the bulk-offs. Lincoln & Lilly remain **independent**.

### 5.3 Optional, confirm-live (fan)
If the tested behavior set a quiet fan, add one `climate.set_fan_mode` (`low`/
`auto`) on the kids' cool path so `turbo` no longer sticks; reserve `turbo` for the
76 °F ceiling gate. Confirm supported fan-mode names live.

### 5.4 Representative YAML (illustrative — DO NOT APPLY; Codex adapts vs. live)
```yaml
# ── COOLING SEASON ── Lincoln (Lilly identical). Replaces :438–451 / :458–471.
# Active hold: maintain cool at the live-verified target; head modulates.
# No on_at, no off_at, NO `else off`.
- action: climate.set_temperature
  target: { entity_id: climate.lincoln_air }
  data:
    hvac_mode: "cool"
    temperature: >-
      {{ verified_away_target if away else verified_target }}
      {# verified_* = exact Samsung setpoints already tested live to hold room
         truth <=70. NOT assumed to be 70. Confirm both from live history. #}

# ── SHOULDER SEASON ── per-kid truth-gated escape, applied across ALL shoulder
# sub-branches (recommended: hoist to the top of the `season == 'shoulder'`
# sequence, then remove lincoln/lilly from every sub-branch bulk-off and the
# warm-path kid blocks). Independent per room. NO default → no-op (never OFF).
- choose:
    - conditions: "{{ lincoln_temp > 70 }}"          # ROOM-TRUTH ceiling (engage)
      sequence:
        - action: climate.set_temperature
          target: { entity_id: climate.lincoln_air }
          data: { hvac_mode: "cool", temperature: "{{ verified_target }}" }
- choose:
    - conditions: "{{ lilly_temp > 70 }}"
      sequence:
        - action: climate.set_temperature
          target: { entity_id: climate.lilly_air }
          data: { hvac_mode: "cool", temperature: "{{ verified_target }}" }

# Shoulder bulk-offs, kids removed (keep non-kid entities):
#   night : [climate.dining_room]
#   cold  : [climate.master_bedroom_air, climate.dining_room]
#   mild  : [climate.living_room_air, climate.master_bedroom_air, climate.dining_room]
# Shoulder-day WARM: delete the Lincoln/Lilly cool@61 blocks (escape covers them).
```

> **Why no OFF for the kids now:** at `61` the head froze the room, so the
> supervisor *had* to cut it off; at `verified_target` the head **modulates to idle
> on its own**, so "maintain cool" (cooling season) or "engage-then-no-op"
> (shoulder) is correct and the supervisor OFF is removed. The only OFFs that may
> still reach the kids' heads are **intentional policy or Section 3 safety** — not
> a mild-shoulder bulk-off.

---

## 6. From → To behavior table

| Aspect | From (Git/legacy, test-locked) | To (in-place Section 2) |
|---|---|---|
| Cooling-season kids | `cool@61`, `off` if truth ≤ 68, engage if truth > 72, else off | **maintain `cool @ verified_target`** (no OFF, no on_at, no `else off`); head modulates |
| Cooling-season setpoint | `61` (assumed) | **`verified_target`** (live-confirmed; NOT 70-by-assumption) |
| Cooling-season away | relaxed via thresholds | relaxed via `verified_away_target` (confirm live) |
| Shoulder-night kids | bulk-forced `off` | engage `cool @ verified_target` if truth > 70; **else no-op** |
| Shoulder-day warm kids | `cool@61` if > 70 else `off` | engage `cool @ verified_target` if truth > 70; **else no-op** |
| Shoulder-day mild/cold kids | bulk-forced `off` | engage `cool @ verified_target` if truth > 70; **else no-op** |
| Shoulder bulk-off lists | include kids | **kids removed** (non-kid entities kept) |
| Kids fan (opt, confirm live) | unset → `turbo` sticks | quiet (`low`/`auto`) while cooling |
| Master / LR / Dining / Nest | `61` shove + deadband / heat / off | **UNCHANGED** |
| Manual-override gate | `idle` | **UNCHANGED** |
| Section 3 floors / 76° ceiling | 58 / 60 / 76 | **UNCHANGED** |
| Heating-season kid branches | heat / off | **UNCHANGED (out of scope)** |

---

## 7. Live verification checklist (Codex, before patching)

1. **Diff live vs Git** for `automation.v7_5_main_supervisor` Section 2; record any
   comfort-target edits already present from testing, and **commit the live
   Section 2 first** so the repo matches reality.
2. **Confirm the failure source:** Logbook / `hvac_provenance_log` for the kids'
   heads over 2026-06-05 21:00 → 06-06 08:30 — expect `v7_5_main_supervisor`
   `cool@61`/`off` at `:00/:15/:30/:45`, the 02:45 shoulder-night force-off, **and
   the post-06:00 shoulder-day force-offs**.
3. **`verified_target` (and away variant):** read the exact Samsung setpoint(s) you
   were testing; confirm from history they hold **room truth ≤ 70** (account for
   Samsung-internal vs room-truth bias). This value goes into the patch — **do not
   substitute 70.**
4. **Head mode:** confirm heads run in `cool` (not Samsung `auto`).
5. **Fan:** confirm `turbo` origin and supported fan-mode names before adding any
   quiet-fan command.
6. **Helpers exist live:** `input_select.hvac_season_mode`,
   `timer.manual_hvac_override` (+ duration), `input_boolean.away_mode`.
7. **05:45 Lincoln anomaly:** classify the re-engage origin from the live trace.

---

## 8. Tests that genuinely need updating

Only the three Section-2 cooling/shoulder locks; safety/invariant tests stay green.

- **`tests/test_section2_cooling_setpoint_doctrine.py`** — the kids no longer use
  `l_*`/`ly_*` variables at all (cooling is now a plain `cool @ verified_target`
  command). **Remove `l_setpoint/l_off_at/l_on_at/ly_setpoint/ly_off_at/ly_on_at`
  from the required-variable set (lines 59–60, 69–70) and their asserts (87–90).**
  Add an assert that the kids' cooling command is `hvac_mode: cool` with a
  setpoint that is **not 61** and **has no truth-based OFF / `else off`**. **Leave
  `m_*` and `lr_*` (Master/LR = 61) unchanged.**
- **`tests/test_section2_shove_command_setpoints.py`** — the cooling scan (`== 61`,
  count at 144–146) must **exclude the kids** (assert Master/LR still `61`; assert
  Lincoln/Lilly use `verified_target`, not 61) and the count is updated for the new
  cooling+shoulder kid commands; **remove the kids threshold-string asserts
  (153–156).** Keep the `58/60` and no-arbitration/MSR/freshness asserts.
- **`tests/test_supervisor_shoulder_night.py`** —
  `test_shoulder_night_bulk_off_still_covers_lincoln_lilly_dining` → require **only
  `climate.dining_room`**; add asserts that the per-kid shoulder cooling escape
  exists (`cool` + `lincoln_temp`/`lilly_temp` + `verified_target`) and that the
  non-engaged path is a **no-op** (no kid `set_hvac_mode: off`). Keep the Master/LR
  shoulder-night asserts. (If the escape is hoisted to the shoulder-branch top,
  point the test at that level.)

---

## 9. Untouched invariants (must NOT change)

- **Section 2 remains the sole kids' comfort-policy writer.** No new automation,
  no `kids_comfort_hold`, no helpers, no ownership moved among Sections 2/3/6/8.
- **`timer.manual_hvac_override` behavior preserved exactly** (supervisor still
  gates on `idle`; WAF watcher + window unchanged).
- **Section 3 unchanged** — LR runaway `<60`, Master floor `<58`, 76 °F ceiling,
  WAF (locked by `test_safety_invariants.py`, `test_comfort_band_safety_separation.py`).
- **Master, LR, Dining, Nest unchanged** (still `61` shove + deadband / heat / off).
- **Heating-season kid branches unchanged** (separate future decision).
- **Telemetry, truth sensors, MSR/Apollo boundary, report-time freshness,
  auto-season thresholds** unchanged.
- **Lincoln & Lilly independent** — separate per-room steps; one reaching target
  never disables the other.

---

## 10. Rollback plan

- Change set = `automations.yaml` Section 2 (kids cooling + all shoulder blocks)
  + the three test files. **Rollback = `git revert` + reload automations.** No
  entity/truth/helper/telemetry migration.
- Git may lag live → Codex **commits the live Section 2 first**, then patches, so
  rollback returns to the actual prior live state.
- Master/LR/Dining/Nest and Section 3 untouched → rollback never affects other
  rooms or equipment protection.

---

## 11. Codex prompt — smallest live patch

```
ROLE: Modify the LIVE Moose House Home Assistant config inside HAOS. Git lags
live; LIVE YAML + live traces are source of truth. Read
docs/kids-bedroom-overnight-cooling-plan.md (v4) first.

ARCHITECTURE: SUPERVISOR-FIRST. automation.v7_5_main_supervisor (Section 2)
decides; the Samsung heads execute and modulate. Do NOT create a separate
controller. The PR #134 kids_comfort_hold approach is ABANDONED — no separate
automation, no *_cool_setpoint helpers, no ownership transfer among Sections
2/3/6/8.

GOAL: Smallest in-place Section 2 edit so Lincoln & Lilly hold cool at the
live-verified Samsung comfort target and let the head modulate — across COOLING
and SHOULDER seasons (night AND day). Heating/winter is OUT OF SCOPE.

TWO NUMBERS: 70°F is the ROOM-TRUTH ceiling (engage decision only). verified_target
is the Samsung SETPOINT already tested live to hold room truth <=70 — read it from
live history; DO NOT hard-code 70 as the command. Git has 61 (legacy).

STEP 0 — VERIFY LIVE (report before editing):
  1. Diff live Section 2 vs Git; commit the live Section 2 first so the repo
     matches reality. Note any comfort-target edits already present from testing.
  2. Confirm via Logbook/hvac_provenance_log that Section 2 writes the kids
     cool@61/off at :00/:15/:30/:45, the 02:45 shoulder-night force-off, and the
     post-06:00 shoulder-day force-offs.
  3. Read verified_target (and away variant); confirm from history it holds room
     truth <=70. Confirm heads run 'cool' (not 'auto'); list supported fan modes.

STEP 1 — PATCH SECTION 2 (Lincoln & Lilly only):
  COOLING (A/B): replace each kid block with a single unconditional
    climate.set_temperature: hvac_mode 'cool', temperature verified_target
    (away -> verified_away_target). REMOVE the truth-based off, the on_at engage
    threshold, AND the `else off` mode decision. No on/off logic for the kids in
    cooling season — just maintain cool@target; the inverter modulates.
  SHOULDER (C/D/E/F/G): remove climate.lincoln_air & climate.lilly_air from EVERY
    shoulder bulk-off (night/cold/mild) and delete the warm-path kid cool@61
    blocks. Add ONE independent per-room truth-gated escape (recommend hoisting to
    the top of the season=='shoulder' sequence): if <room>_temp > 70 ->
    climate.set_temperature cool@verified_target; NO default branch -> no-op (never
    issue OFF to a kid just because shoulder is mild/cold). Keep Lincoln & Lilly
    independent. Master keeps its shoulder-night escape; LR/Nest unchanged.
  (Optional) quiet kids fan (low/auto) on the cool path if it matches what you
    tested; reserve turbo for the 76F ceiling gate.

  DO NOT touch Master, LR, Dining, Nest, the manual-override gate, Section 3, the
  heating-season kid branches, telemetry, truth sensors, or any other automation.

STEP 2 — UPDATE ONLY THESE TESTS:
  - test_section2_cooling_setpoint_doctrine.py: drop the l_*/ly_* variable
    requirements + asserts; assert kids cooling = cool @ (not 61) with no off;
    leave Master/LR (61) asserts.
  - test_section2_shove_command_setpoints.py: exclude kids from the ==61 cooling
    scan (Master/LR stay 61; kids = verified_target); fix the command count;
    remove kid threshold strings; keep 58/60 + no-arbitration asserts.
  - test_supervisor_shoulder_night.py: kids no longer required in bulk-off (Nest
    only); assert the per-kid escape exists and the non-engaged path is a no-op.

VALIDATE: python -m pytest tests/ ; ha core check ; reload ; confirm Section 2 now
holds the kids cool@verified_target and the head MODULATES (hvac_action run->idle)
instead of cycling 61<->off; confirm NO supervisor OFF reaches the kids in mild
shoulder; capture 2-3 days/nights and confirm room truth stays <=70 across the
night->day boundary with far fewer transitions than the June 5-6 baseline.
Master/LR/Section 3 unchanged.

ROLLBACK: git revert the Section 2 + test changes and reload. No migrations.
If live contradicts this plan, STOP and report instead of inventing behavior.
```

---

### Appendix — what this plan deliberately does NOT do
- No `kids_comfort_hold`, no `*_cool_setpoint` helpers, no ownership transfer
  between sections (PR #134 approach abandoned).
- No hard-coded `70` as the Samsung command (uses the live-verified target).
- No supervisor OFF for the kids except intentional policy / Section 3 safety.
- No change to Master/LR/Dining/Nest, Section 3, the override contract,
  heating-season kid branches, telemetry, truth sensors, or MSR boundaries.
- No live implementation — planning only.
