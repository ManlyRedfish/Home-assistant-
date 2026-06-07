# Kids' Bedroom Overnight Cooling Plan (Lincoln & Lilly)

**Doc Date:** 2026-06-06 (v5 — supervisor-first, state-aware cooling+shoulder hold)
**Document Role:** Planning + adversarial review. **No operational changes.**
**Scope:** Lincoln's & Lilly's **cooling + shoulder** comfort (night *and* day).
Heating/winter is **out of scope.** Live HAOS is source of truth; Codex verifies.

> ## ⛔ The PR #134 / earlier-revision approaches are ABANDONED
> A separate `kids_comfort_hold` automation, per-room `*_cool_setpoint`
> `input_number` helpers, and moving actuator ownership between Sections 2/3/6/8
> are **rejected and withdrawn**, as is the original deadband-retune/cooldown-timer
> idea. This v5 creates **no** new controller, helper, or ownership transfer.

> ## Architecture (unchanged): SUPERVISOR-FIRST
> **The Section 2 supervisor decides; the Samsung heads execute and modulate.**
> The native Samsung thermostat/inverter is the *actuator mechanism*, not a second
> controller. Section 2 maintains the intended cooling **mode + the real,
> live-verified comfort target**, then lets the head **scale back (modulate)** as it
> nears that target. Section 2 stays the **sole** kids' comfort-policy writer.

This is the **smallest in-place Section 2 edit** that fixes the June 5–6 hot
day-and-night failure for Lincoln & Lilly across **cooling and shoulder**. Planning
only — no runtime YAML committed, nothing deployed.

> ## Two numbers, kept distinct (important)
> - **`70 °F` = the room-truth comfort ceiling** ("no warmer than 70 — that's when
>   I have sweaty kids"). Operator-given; used only for the **truth-based ENGAGE
>   decision**. Safe to reference directly.
> - **`verified_target` = the Samsung *setpoint* the supervisor commands** — the
>   **current verified policy cooling target** already tested live, which holds room
>   truth ≤ 70 given the head's biased internal sensor. **NOT assumed to be 70**
>   (Git has the legacy `61`); Codex reads it from live history. It is **policy-aware**
>   — if the **live Away Mode contract** changes the kids' cooling target, that value
>   reflects it. **Do not invent a separate `verified_away_target`; honor whatever
>   the live Away contract already does.**

---

## 1. Executive diagnosis

In cooling/shoulder hot weather, Section 2 drives Lincoln & Lilly with a
**`cool @ 61` shove + bang-bang `off` at room-truth ≤ 68**, and **bulk-forces them
off** in every shoulder sub-branch (night, and day mild/cold). 61 °F is far below
the comfort target, so the head runs flat-out, overshoots down to ~67; the
supervisor cuts it OFF at 68; the room free-heats past 72; repeat — the 67↔72
sawtooth. At ~02:45 auto-season flipped `cooling → shoulder` (Deck 64.4 °F);
shoulder-night force-offed the kids, **and after 06:00 the shoulder-day mild/cold
branches kept force-offing them**, so the warm plateau ran to ~08:30. `turbo`
persisted because no automation sets the kids' fan.

**Correct supervisor-first behavior:** Section 2 maintains **`cool @
verified_target`** and lets the head **modulate** — no 61 shove, no bang-bang OFF,
and **no blind force-off** while a room still needs cooling — with a **state-aware**
shoulder hold that also clears a stale `heat` mode and reasserts policy after an
override/away change. Confined to the **Lincoln & Lilly cooling and shoulder
blocks of Section 2.**

---

## 2. Relevant entities + live-vs-Git status

Only `automations.yaml` (Section 2) and its Section-2 locking tests change. No new
files, automations, or helpers.

| Concept | Entity / location | Status |
|---|---|---|
| Kids' heads | `climate.lincoln_air`, `climate.lilly_air` | live device |
| Kids' room truth | `sensor.lincoln_s_room_temperature_truth`, `sensor.lilly_s_room_temperature_truth` | `configuration.yaml:451,643` |
| Supervisor (sole comfort writer) | `automation.v7_5_main_supervisor` | `automations.yaml:358` |
| Season mode / auto-switch | `input_select.hvac_season_mode` / `automation.v7_5_auto_season_mode` | live helper / `:919` |
| Manual-override timer | `timer.manual_hvac_override` | live UI helper (preserve) |
| Away mode | `input_boolean.away_mode` | live UI helper (honor existing contract) |

**Distinct sources:**
- **In Git (test-locked) = legacy:** kids `cool@61 / off≤68 / on>72` + shoulder
  bulk-offs.
- **Live-only / verify:** the **comfort target "we were already testing"**
  (`verified_target`) and the **live Away contract** — not in Git (Git has 61).
- **Stale doctrine (do not follow for the kids):** `cool@66` in
  `comfort_failure_forensics.md` §8.6; the actuator-shove "off-inside-the-band";
  "deadband is the comfort contract." Valid for other rooms; superseded for the kids.
- **Codex must verify in HAOS:** the live Section 2 may already hold partial
  comfort-target edits — **diff live vs Git before patching** (§7).

---

## 3. Exact current failure chain (cooling + shoulder, June 5–6)

1. Cooling tick → kids `cool @ 61` (`:439,:459`) → head overshoots toward ~67.
2. Next tick room-truth ≤ 68 → supervisor `off` (`:446–450,:466–470`).
3. Head off → room free-heats toward 72.
4. Room > 72 → re-`cool @ 61`. → **67↔72 sawtooth** (1–4 repeat).
5. ~02:45 Deck 64.4 °F/2h → `shoulder`; season change re-triggers the supervisor
   (`:364–365`).
6. Shoulder-**night** → bulk-off `[lincoln,lilly,dining]` (`:533–535`) regardless of
   room temp.
7. After 06:00 shoulder-**day mild/cold** → bulk-off keeps the kids off (`:576–578,
   :580–582`) → warm plateau to ~08:30.
8. No kids' fan write → `turbo` sticks.

---

## 4. Every live Section 2 write to the kids' heads — and scope

(Per the source-of-truth requirement; Git line refs. **Codex re-confirms live**, §7.)

| # | Write | Lines | Current | Scope |
|---|---|---|---|---|
| A | Cooling-season Lincoln `set_temperature` | 438–451 | `cool@61 / off≤68 / on>72` | **IN — active hold** |
| B | Cooling-season Lilly `set_temperature` | 458–471 | same | **IN — active hold** |
| C | Shoulder-**night** bulk-off | 533–535 | `[lincoln,lilly,dining]→off` | **IN — state-aware hold** |
| D | Shoulder-day **warm** Lincoln | 545–547 | `cool if >70 else off, 61` | **IN — state-aware hold** |
| E | Shoulder-day **warm** Lilly | 548–550 | same | **IN — state-aware hold** |
| F | Shoulder-day **cold** bulk-off | 576–578 | `[master,lincoln,lilly,dining]→off` | **IN — state-aware hold** |
| G | Shoulder-day **mild** bulk-off | 580–582 | `[lr,master,lincoln,lilly,dining]→off` | **IN — state-aware hold** |
| H–K | Heating-season kid writes/bulk-offs | 609–614, 632–634, 639–644, 670–672 | heat / off | **OUT — winter (untouched)** |
| — | Season-change retrigger | 364–365 | re-runs on `hvac_season_mode` change | drives the shoulder cleanup |
| — | Manual-override gate | 366–369 | `timer.manual_hvac_override == idle` | **PRESERVE exactly** |
| — | Kids' fan writes | — | **none** → `turbo` sticks | Optional quiet-fan (confirm live) |

---

## 5. The in-place correction (supervisor-first)

**No new automation, no helpers. Master/LR/Dining/Nest unchanged.**

### 5.1 Cooling season (A, B) — **active hold, no OFF, no `else off`**
Replace each kid block with a single unconditional command: **maintain `cool @
verified_target`** and let the head modulate. **Remove** the truth-based lower OFF,
the `on_at`/`off_at` thresholds, and the `else off` decision. Because cooling-season
commands `cool` unconditionally, it also cleans any stale `heat`/`off`. The
`verified_target` is policy-aware (honors the live Away contract; no invented away
setpoint).

### 5.2 Shoulder season (C, D, E, F, G) — **state-aware hold (per room, independent)**
Remove `climate.lincoln_air` / `climate.lilly_air` from **every** shoulder bulk-off
(keep non-kid entities) and remove the warm-path kid `cool@61/else off` blocks.
Apply one independent per-room decision **across all shoulder sub-branches**
(recommend hoisting to the top of the `season == 'shoulder'` sequence):

| Condition (per kid) | Action | Why |
|---|---|---|
| `room_truth > 70` | `cool @ verified_target` | engage cooling at the ceiling |
| else, head **already `cool`** | **reassert** `cool @ verified_target` | maintain the native hold; **restore policy after manual-override expiry or an Away/normal policy change** |
| else, head **in `heat`** | `off` | **intentional season-transition cleanup** of an incompatible stale heating mode when shoulder policy takes ownership — *not* a temperature-deadband OFF |
| else (head `off`/`fan_only`, room ≤ 70) | **no-op** | nothing to do; never force OFF just because shoulder is mild/cold |

This fixes the v4 gap: a passive no-op could leave a kid in `heat` after a
`heating→shoulder` flip, and would not re-apply policy after override/away changes.

### 5.3 Optional, confirm-live (fan)
If the tested behavior set a quiet fan, add one `climate.set_fan_mode`
(`low`/`auto`) on the kids' cool path so `turbo` no longer sticks; reserve `turbo`
for the 76 °F ceiling gate. Confirm supported fan-mode names live.

### 5.4 Representative YAML (illustrative — DO NOT APPLY; Codex adapts vs. live)
```yaml
# ── COOLING SEASON ── Lincoln (Lilly identical). Replaces :438–451 / :458–471.
# Active hold: maintain cool at the current verified policy target; head modulates.
# No on_at, no off_at, NO `else off`. verified_target is policy-aware (honors the
# live Away contract; do NOT invent a separate away setpoint).
- action: climate.set_temperature
  target: { entity_id: climate.lincoln_air }
  data:
    hvac_mode: "cool"
    temperature: "{{ verified_target }}"   # live-tested setpoint that holds truth ≤70; NOT assumed 70

# ── SHOULDER SEASON ── per-kid STATE-AWARE hold, applied across ALL shoulder
# sub-branches (recommended: hoist to the top of the season=='shoulder' sequence,
# then remove lincoln/lilly from every sub-branch bulk-off and the warm-path kid
# blocks). Independent per room.
- choose:
    # warm OR already cooling -> hold/reassert the policy target (head modulates)
    - conditions: "{{ lincoln_temp > 70 or is_state('climate.lincoln_air','cool') }}"
      sequence:
        - action: climate.set_temperature
          target: { entity_id: climate.lincoln_air }
          data: { hvac_mode: "cool", temperature: "{{ verified_target }}" }
    # stale heat on a not-warm room -> season-transition cleanup (NOT a deadband off)
    - conditions: "{{ is_state('climate.lincoln_air','heat') }}"
      sequence:
        - action: climate.set_hvac_mode
          target: { entity_id: climate.lincoln_air }
          data: { hvac_mode: "off" }
  # no default -> NO-OP (head off/fan_only and room ≤70: leave unchanged)
# … identical choose for climate.lilly_air using lilly_temp …

# Shoulder bulk-offs, kids removed (keep non-kid entities):
#   night : [climate.dining_room]
#   cold  : [climate.master_bedroom_air, climate.dining_room]
#   mild  : [climate.living_room_air, climate.master_bedroom_air, climate.dining_room]
# Shoulder-day WARM: delete the Lincoln/Lilly cool@61/else-off blocks (escape covers them).
```

> **Why no temperature-deadband OFF for the kids:** at `61` the head froze the
> room, so the supervisor *had* to cut it off; at `verified_target` the head
> **modulates to idle on its own**. The only OFFs that reach the kids' heads now are
> **(a) the intentional `heat`-mode season-transition cleanup** and **(b) Section 3
> safety** — never a mild-shoulder bulk-off.

---

## 6. From → To behavior table

| Aspect | From (Git/legacy, test-locked) | To (in-place Section 2) |
|---|---|---|
| Cooling-season kids | `cool@61`, `off` if truth ≤ 68, engage if > 72, else off | **maintain `cool @ verified_target`** (no OFF, no on_at, no `else off`); head modulates |
| Cooling-season setpoint | `61` (assumed) | **`verified_target`** (live-confirmed, policy-aware; NOT 70-by-assumption) |
| Away handling | relaxed via thresholds | **honor existing live Away contract** via `verified_target`; no invented away setpoint |
| Shoulder kids, room > 70 | bulk-off / `cool@61` | `cool @ verified_target` |
| Shoulder kids, head already `cool` | bulk-off | **reassert `cool @ verified_target`** (restores policy after override/away change) |
| Shoulder kids, head in `heat` | bulk-off | **`off`** (intentional season-transition cleanup) |
| Shoulder kids, head `off`/`fan_only` & ≤ 70 | bulk-off | **no-op** (never a mild-shoulder OFF) |
| Shoulder bulk-off lists | include kids | **kids removed** (non-kid entities kept) |
| Kids fan (opt, confirm live) | unset → `turbo` sticks | quiet (`low`/`auto`) while cooling |
| Master / LR / Dining / Nest | `61` shove + deadband / heat / off | **UNCHANGED** |
| Manual-override gate | `idle` | **UNCHANGED** (reassert path restores policy on expiry) |
| Section 3 floors / 76° ceiling | 58 / 60 / 76 | **UNCHANGED** |
| Heating-season kid branches | heat / off | **UNCHANGED (out of scope)** |

---

## 7. Live verification checklist (Codex, before patching)

1. **Diff live vs Git** for `automation.v7_5_main_supervisor` Section 2; record any
   comfort-target edits already present from testing, and **commit the live Section
   2 first** so the repo matches reality.
2. **Confirm the failure source:** Logbook / `hvac_provenance_log` for the kids'
   heads over 2026-06-05 21:00 → 06-06 08:30 — expect `v7_5_main_supervisor`
   `cool@61`/`off` at `:00/:15/:30/:45`, the 02:45 shoulder-night force-off, **and
   the post-06:00 shoulder-day force-offs**.
3. **`verified_target`:** read the exact Samsung setpoint you were testing; confirm
   from history it holds **room truth ≤ 70**. **Do not substitute 70.**
4. **Away contract:** confirm what Away Mode does to the kids' cooling target live,
   and preserve it through `verified_target` — **do not invent an away setpoint.**
5. **State-aware shoulder paths:** verify on a real `heating→shoulder` transition
   that a kid head left in `heat` is taken to `off` (cleanup), and that a `cool`
   head is reasserted to `verified_target` after `timer.manual_hvac_override`
   expires.
6. **Head mode:** confirm heads run in `cool` (not Samsung `auto`).
7. **Fan:** confirm `turbo` origin and supported fan-mode names before any
   quiet-fan command.
8. **05:45 Lincoln anomaly:** classify the re-engage origin from the live trace.

---

## 8. Tests that genuinely need updating

Only the Section-2 cooling/shoulder locks; safety/invariant tests stay green.

- **`tests/test_section2_cooling_setpoint_doctrine.py`** — the kids no longer use
  `l_*`/`ly_*` variables (cooling is a plain `cool @ verified_target` command).
  **Remove `l_setpoint/l_off_at/l_on_at/ly_setpoint/ly_off_at/ly_on_at` from the
  required set (lines 59–60, 69–70) and their asserts (87–90)**; assert the kids'
  cooling command is `hvac_mode: cool` with a setpoint **not equal to 61** and **no
  truth-based OFF / `else off`**. **Leave `m_*`/`lr_*` (Master/LR = 61) unchanged.**
- **`tests/test_section2_shove_command_setpoints.py`** — the cooling `== 61` scan
  (144–146) must **exclude the kids** (Master/LR stay `61`; kids use
  `verified_target`), update the command count, and **remove the kid threshold-string
  asserts (153–156).** Keep `58/60` + no-arbitration/MSR/freshness asserts.
- **`tests/test_supervisor_shoulder_night.py` → expand to the WHOLE shoulder branch**
  (rename to `test_supervisor_shoulder_branch.py` or add a sibling). Traverse the
  entire `season == 'shoulder'` branch (night **and** day sub-branches) and assert:
  1. **no** unconditional/bulk `set_hvac_mode: off` target list anywhere in shoulder
     includes `climate.lincoln_air` or `climate.lilly_air`;
  2. the old shoulder-day **warm** `cool@61`/`else off` kid blocks are **removed**;
  3. Lincoln and Lilly each have **independent** state-aware hold logic;
  4. `room_truth > 70` engages `cool @ verified_target`;
  5. **head already `cool` → reassert** `cool @ verified_target`;
  6. **head `heat` → explicit `set_hvac_mode: off`** (season-transition cleanup);
  7. **off, non-warm room → no command** (the choose has no default and no other kid
     write);
  8. **Master/LR/Dining/Nest behavior unchanged** (their existing steps remain,
     incl. the Master shoulder-night cooling escape and LR heat/off).

(Because `verified_target` is live-determined, the tests assert structure/conditions
and "setpoint ≠ 61", not a specific number.)

---

## 9. Untouched invariants (must NOT change)

- **Section 2 remains the sole kids' comfort-policy writer.** No new automation, no
  `kids_comfort_hold`, no helpers, no ownership moved among Sections 2/3/6/8.
- **`timer.manual_hvac_override` behavior preserved exactly** — supervisor still
  gates on `idle`; the shoulder **reassert-when-cool** path is how policy is
  restored *after* the override window expires (not by bypassing it). WAF watcher +
  window unchanged.
- **Section 3 unchanged** — LR runaway `<60`, Master floor `<58`, 76 °F ceiling, WAF
  (locked by `test_safety_invariants.py`, `test_comfort_band_safety_separation.py`).
- **Master, LR, Dining, Nest unchanged** (still `61` shove + deadband / heat / off).
- **Heating-season kid branches unchanged** (separate future decision).
- **Telemetry, truth sensors, MSR/Apollo boundary, report-time freshness,
  auto-season thresholds** unchanged.
- **Lincoln & Lilly independent** — separate per-room steps; one reaching target
  never affects the other.

---

## 10. Rollback plan

- Change set = `automations.yaml` Section 2 (kids cooling + all shoulder blocks) +
  the Section-2 test files. **Rollback = `git revert` + reload automations.** No
  entity/truth/helper/telemetry migration.
- Git may lag live → Codex **commits the live Section 2 first**, then patches, so
  rollback returns to the actual prior live state.
- Master/LR/Dining/Nest and Section 3 untouched → rollback never affects other rooms
  or equipment protection.

---

## 11. Codex prompt — smallest live patch

```
ROLE: Modify the LIVE Moose House Home Assistant config inside HAOS. Git lags live;
LIVE YAML + live traces are source of truth. Read
docs/kids-bedroom-overnight-cooling-plan.md (v5) first.

ARCHITECTURE: SUPERVISOR-FIRST. automation.v7_5_main_supervisor (Section 2) decides;
the Samsung heads execute and modulate. Do NOT create a separate controller. The
PR #134 kids_comfort_hold approach is ABANDONED — no separate automation, no
*_cool_setpoint helpers, no ownership transfer among Sections 2/3/6/8.

GOAL: Smallest in-place Section 2 edit so Lincoln & Lilly hold cool at the
live-verified Samsung comfort target and let the head modulate — across COOLING and
SHOULDER (night AND day). Heating/winter is OUT OF SCOPE.

TWO NUMBERS: 70°F is the ROOM-TRUTH ceiling (engage decision only). verified_target
is the Samsung SETPOINT already tested live to hold room truth <=70; read it from
live history; DO NOT hard-code 70 as the command (Git has 61). verified_target is
policy-aware — honor the existing live Away contract; do NOT invent an away setpoint.

STEP 0 — VERIFY LIVE (report before editing):
  1. Diff live Section 2 vs Git; commit the live Section 2 first. Note any
     comfort-target edits already present from testing.
  2. Confirm via Logbook/hvac_provenance_log that Section 2 writes the kids
     cool@61/off at :00/:15/:30/:45, the 02:45 shoulder-night force-off, and the
     post-06:00 shoulder-day force-offs.
  3. Read verified_target; confirm from history it holds room truth <=70. Confirm
     the live Away behavior for the kids; confirm heads run 'cool' (not 'auto');
     list supported fan modes.

STEP 1 — PATCH SECTION 2 (Lincoln & Lilly only):
  COOLING (A/B): replace each kid block with a single unconditional
    climate.set_temperature: hvac_mode 'cool', temperature verified_target. REMOVE
    the truth-based off, the on_at/off_at thresholds, AND the `else off`. No on/off
    logic for the kids in cooling — just maintain cool@target; the inverter modulates.
  SHOULDER (C/D/E/F/G): remove climate.lincoln_air & climate.lilly_air from EVERY
    shoulder bulk-off (night/cold/mild) and delete the warm-path kid cool@61/else-off
    blocks. Add ONE independent per-room STATE-AWARE hold (recommend hoisting to the
    top of season=='shoulder'):
      - <room>_temp > 70 OR head already 'cool'  -> cool @ verified_target
      - head 'heat'                              -> set_hvac_mode off (season cleanup)
      - else (off/fan_only and <=70)             -> NO default -> no-op
    Keep Lincoln & Lilly independent. Master keeps its shoulder-night escape;
    LR/Nest/Dining unchanged.
  (Optional) quiet kids fan (low/auto) on the cool path if it matches what you
    tested; reserve turbo for the 76F ceiling gate.

  DO NOT touch Master, LR, Dining, Nest, the manual-override gate, Section 3, the
  heating-season kid branches, telemetry, truth sensors, or any other automation.

STEP 2 — UPDATE ONLY THESE TESTS:
  - test_section2_cooling_setpoint_doctrine.py: drop l_*/ly_* requirements+asserts;
    assert kids cooling = cool @ (not 61) with no off; leave Master/LR (61) asserts.
  - test_section2_shove_command_setpoints.py: exclude kids from the ==61 cooling scan
    (Master/LR stay 61; kids = verified_target); fix the count; remove kid threshold
    strings; keep 58/60 + no-arbitration asserts.
  - Expand the shoulder test to the WHOLE shoulder branch (night AND day): no bulk
    off includes the kids; warm cool@61/else-off blocks gone; per-kid independent
    state-aware logic; >70 -> cool@target; already-cool -> reassert; heat -> off;
    off-&-not-warm -> no command; Master/LR/Dining/Nest unchanged.

VALIDATE: python -m pytest tests/ ; ha core check ; reload ; confirm Section 2 holds
the kids cool@verified_target and the head MODULATES instead of cycling 61<->off; a
heating->shoulder flip takes a stale-heat kid head to off (not left heating); a cool
head is reasserted after override expiry; an off, <=70 kid head gets NO command;
capture 2-3 days/nights with room truth <=70 across the night->day boundary.
Master/LR/Section 3 unchanged.

ROLLBACK: git revert the Section 2 + test changes and reload. No migrations.
If live contradicts this plan, STOP and report instead of inventing behavior.
```

---

### Appendix — what this plan deliberately does NOT do
- No `kids_comfort_hold`, no `*_cool_setpoint` helpers, no ownership transfer between
  sections (PR #134 approach abandoned).
- No hard-coded `70` as the Samsung command (uses the live-verified, policy-aware
  target); no invented away setpoint.
- No supervisor temperature-deadband OFF for the kids — only the intentional
  `heat`-mode season-transition cleanup and Section 3 safety.
- No change to Master/LR/Dining/Nest, Section 3, the override contract,
  heating-season kid branches, telemetry, truth sensors, or MSR boundaries.
- No live implementation — planning only.
