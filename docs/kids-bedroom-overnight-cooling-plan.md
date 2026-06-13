# Kids' Bedroom Bedtime Cooling Plan (Lincoln & Lilly)

**Doc Date:** 2026-06-07 (v6 — 66–70 / 61-turbo bedtime deadband, per operator decision)
**Document Role:** Planning + adversarial review. **No operational changes.**
**Scope:** Lincoln's & Lilly's **bedtime cooling** (18:00–07:00) in **cooling and
shoulder** seasons. Daytime and heating are unchanged. Live HAOS is source of truth.

> ## Authoritative operator decision — 2026-06-07 (this plan implements exactly this)
> **Lincoln & Lilly bedtime cooling contract** (`climate.lincoln_air`,
> `climate.lilly_air`; independent):
> - **Room-truth deadband:** engage cooling at room truth **≥ 70 °F**; release
>   **≤ 66 °F**; while off between 66–70, remain off.
> - **Actuator during an active pull-down:** `hvac_mode: cool`, `temperature: 61 °F`,
>   `fan_mode: turbo`. **61/turbo is intentional and required** — moderate Samsung
>   setpoints scale back prematurely and can run ~18 h without pulling the room down.
> - **Bedtime logic (per room):**
>   `if truth ≥ 70: cool@61/turbo · elif truth ≤ 66: off · elif current==cool:
>   continue cool@61/turbo · else: off`.
> - **Season rule:** the same 66–70 pull-down works in **cooling and shoulder**; a
>   `cooling→shoulder` flip must **not** interrupt an active pull-down before 66 °F;
>   shoulder bulk-off must not override this contract.
> - **Scope:** bedtime only (18:00–07:00). Daytime kids behavior unchanged (legacy
>   68–72). Heating unchanged except shoulder must not break an active bedtime cycle.
>   Section 2 stays the sole comfort writer; manual override + Section 3 unchanged;
>   **no new controller, helpers, or native-thermostat continuous hold.**

> ## ⛔ Superseded by the decision above
> - The **native-thermostat "modulate, no deadband / `verified_target`"** model
>   (v2–v5) is **wrong** and withdrawn — 61/turbo + a real deadband is the contract.
> - The standalone `kids_comfort_hold` automation, `*_cool_setpoint` helpers, and
>   cross-section ownership transfer remain abandoned.
> - The original "tighten-the-68/72-deadband-and-reuse-cooldown-timers" idea is
>   replaced by this explicit, scoped operator contract.

> ## Canonical docs already updated (this PR)
> AGENTS.md ("Current Operator Decisions"), `docs/1_startup_canon.md` §5.1,
> `docs/5_runtime_layer.md` §6.1 + new §7.10 (APPROVED — PENDING IMPLEMENTATION),
> `docs/comfort_failure_forensics.md` (operator-approved revision note), and
> `docs/comfort_control_actuator_arbitration_spec.md` (scoped 61/turbo application).
> Doctrine and this plan now agree before any implementation.

---

## 1. Executive diagnosis

The live Section 2 supervisor runs the legacy **all-hours** kids cooling deadband
(`cool@61 / off≤68 / on>72`) and **bulk-forces the kids off** in shoulder (night,
and day mild/cold). Overnight that produced the 67↔72 sawtooth, and after the
~02:45 `cooling→shoulder` flip the kids were force-offed through to ~08:30.

**The operator-approved fix is a tighter, scoped *bedtime* deadband, not a new
control style:** during **18:00–07:00** in **cooling and shoulder**, Lincoln &
Lilly engage at **≥70 °F**, run **cool@61/turbo**, release at **≤66 °F**, and hold
off in 66–70 — independent per room, uninterrupted by a season flip, and never
overridden by a shoulder bulk-off. Daytime stays 68–72; heating is untouched.

---

## 2. Relevant entities + live-vs-Git status

Only `automations.yaml` (Section 2) and its Section-2 locking tests change. No new
files, automations, or helpers (`kids_bedtime` is a supervisor template variable,
like the existing `is_night`/`is_bedtime`/`is_master_sleep`).

| Concept | Entity / location | Status |
|---|---|---|
| Kids' heads | `climate.lincoln_air`, `climate.lilly_air` | live device |
| Kids' room truth | `sensor.lincoln_s_room_temperature_truth`, `sensor.lilly_s_room_temperature_truth` | `configuration.yaml:451,643` |
| Supervisor (sole comfort writer) | `automation.v7_5_main_supervisor` | `automations.yaml:358` |
| Season mode | `input_select.hvac_season_mode` | live UI helper |
| Manual-override timer | `timer.manual_hvac_override` | live UI helper (preserve) |

- **In Git (test-locked) = legacy:** kids `cool@61 / off≤68 / on>72` (all hours) +
  shoulder bulk-offs. **This is what's live.**
- **The 66–70 bedtime contract is operator-approved but NOT yet live** (Doc 5 §7.10).
- **Codex must diff live vs Git** before patching (the live Section 2 may already
  carry edits from testing).

---

## 3. Exact current failure chain (June 5–6)

1. Cooling tick → kids `cool @ 61` → overshoot toward ~67.
2. Next tick truth ≤ 68 → `off` (legacy lower edge).
3. Head off → room free-heats toward 72.
4. truth > 72 → re-`cool @ 61`. → **67↔72 sawtooth**.
5. ~02:45 Deck 64.4 °F/2h → `shoulder`; season change re-triggers the supervisor.
6. Shoulder-night → bulk-off `[lincoln,lilly,dining]` regardless of temp.
7. After 06:00 shoulder-day mild/cold → bulk-off keeps the kids off → warm to ~08:30.

Under the bedtime contract: step 2's release moves to **≤66** (so the head keeps
pulling down to 66 before stopping), the engage moves to **≥70** (so the room never
sits at 72), and steps 5–7 can no longer force the kids off during bedtime.

---

## 4. Every live Section 2 write to the kids' heads — and how the contract changes it

(Git line refs; **Codex re-confirms live**.)

| # | Write | Lines | Today | Under contract |
|---|---|---|---|---|
| A | Cooling Lincoln `set_temperature` | 438–451 | `cool@61 / off≤68 / on>72` | bedtime → 66–70 block owns it; **daytime unchanged** |
| B | Cooling Lilly `set_temperature` | 458–471 | same | same |
| C | Shoulder-night bulk-off | 533–535 | `[lincoln,lilly,dining]→off` | kids removed (is_night ⊂ bedtime → 66–70 block owns them); Nest stays |
| D/E | Shoulder-day warm kid blocks | 545–550 | `cool@61 if >70 else off` | gated to `not kids_bedtime` (daytime unchanged); bedtime → 66–70 block |
| F/G | Shoulder-day cold/mild bulk-offs | 576–578, 580–582 | kids in bulk-off | kids' off gated to `not kids_bedtime`; bedtime → 66–70 block |
| H–K | Heating-season kid writes | 609–614, 632–644, 670–672 | heat / off | **UNCHANGED (out of scope)** |
| — | Manual-override gate | 366–369 | `idle` | **PRESERVE exactly** |
| — | Kids' fan writes | — | none → turbo sticks | bedtime block sets `turbo` **explicitly** while cooling |

---

## 5. The in-place design (Section 2, supervisor-first)

**One new per-room block owns the kids during bedtime; the legacy branches keep
the daytime behavior, gated off during bedtime.** No new automation/helpers.

### 5.1 Add a `kids_bedtime` variable (top-level `variables`)
`kids_bedtime: "{{ now().hour >= 18 or now().hour < 7 }}"`  (18:00–07:00).

### 5.2 Add a "Kids Bedtime Cooling" block at the top of the supervisor action
(after `variables`, before the season `choose`). It runs **only** when
`kids_bedtime and season in ['cooling','shoulder']`, handles Lincoln and Lilly
**independently**, and is the single place that encodes the operator's logic:

```
per room:
  mode = cool   if truth >= 70
       = off    if truth <= 66
       = cool   if (66 < truth < 70) and current_mode == cool   # continue pull-down
       = off    otherwise
  if mode == cool: command cool @ 61, fan turbo
  else:            command off
```
Because this block is **season-independent** (covers both cooling and shoulder), a
`cooling→shoulder` flip mid-pull-down re-enters the same block with `current==cool`
→ continues to 66. The `set_fan_mode: turbo` is issued only on the cool command.

### 5.3 Gate the legacy branches so they don't double-command the kids during bedtime
- **Cooling branch (A/B):** wrap the existing Lincoln & Lilly `set_temperature`
  blocks so they run only when `not kids_bedtime`. Daytime keeps `cool@61 / off≤68 /
  on>72` exactly (test-locked values unchanged).
- **Shoulder branch:**
  - **is_night sub-branch** (22:00–06:00 ⊂ bedtime): remove `lincoln_air`/`lilly_air`
    from the bulk-off (→ `[dining]`); the bedtime block always owns them here.
  - **Shoulder-day sub-branch** (warm/cold/mild): gate the kid writes on
    `not kids_bedtime` (the warm-path kid `set_temperature` blocks, and the kids'
    membership in the cold/mild bulk-offs). Daytime behavior is preserved; the
    bedtime portion (18:00–22:00, 06:00–07:00) is owned by the bedtime block.

Master, LR, Dining, Nest steps are untouched throughout.

### 5.4 Representative YAML (illustrative — DO NOT APPLY; Codex adapts vs. live)
```yaml
# top-level variables: add
kids_bedtime: "{{ now().hour >= 18 or now().hour < 7 }}"

# ── KIDS BEDTIME COOLING (new block, top of action, before the season choose) ──
- choose:
    - conditions: "{{ kids_bedtime and season in ['cooling','shoulder'] }}"
      sequence:
        # Lincoln (independent)
        - variables:
            l_current: "{{ states('climate.lincoln_air') }}"
            l_mode: >-
              {% if lincoln_temp >= 70 %}cool
              {% elif lincoln_temp <= 66 %}off
              {% elif l_current == 'cool' %}cool
              {% else %}off{% endif %}
        - choose:
            - conditions: "{{ l_mode == 'cool' }}"
              sequence:
                - action: climate.set_temperature
                  target: { entity_id: climate.lincoln_air }
                  data: { hvac_mode: "cool", temperature: 61 }
                - action: climate.set_fan_mode
                  target: { entity_id: climate.lincoln_air }
                  data: { fan_mode: "turbo" }
          default:
            - action: climate.set_hvac_mode
              target: { entity_id: climate.lincoln_air }
              data: { hvac_mode: "off" }
        # Lilly (identical, using lilly_temp / climate.lilly_air) …
  # no default — outside bedtime/season the legacy branches handle the kids
```
Gating example (cooling branch kids blocks) and shoulder edits:
```yaml
# Cooling branch: guard the existing Lincoln/Lilly set_temperature blocks
- choose:
    - conditions: "{{ not kids_bedtime }}"
      sequence:
        - <existing Lincoln cool@61 / off≤68 / on>72 block>
        - <existing Lilly   cool@61 / off≤68 / on>72 block>
# Shoulder is_night bulk-off: [climate.lincoln_air, climate.lilly_air, climate.dining_room]
#   -> [climate.dining_room]
# Shoulder-day warm kid blocks and cold/mild kid-offs: wrap in `not kids_bedtime`.
```

> **61/turbo is intentional.** This plan does **not** reset the fan to quiet or
> raise the setpoint — the operator requires `cool@61/turbo` for the pull-down
> (moderate setpoints stall ~18 h). Turbo runs only while actively pulling down
> (70→66); between 66 and 70 the head is off.

---

## 6. From → To behavior table

| Aspect | From (live/legacy) | To (operator contract) |
|---|---|---|
| Kids cooling, **bedtime 18:00–07:00** | `cool@61 / off≤68 / on>72` (cooling) or bulk-off (shoulder) | **66–70 deadband:** engage ≥70 → `cool@61/turbo`; release ≤66 → off; hold in 66–70 |
| Kids actuator (pull-down) | `cool@61`, fan = stuck `turbo` | `cool@61` + **explicit `fan_mode: turbo`** |
| Shoulder-night kids | bulk-forced off | 66–70 bedtime block owns them (is_night ⊂ bedtime) |
| Shoulder-day kids, bedtime hours | bulk-off / warm-escape@61 | 66–70 bedtime block |
| Shoulder-day kids, **daytime** | warm-escape@61 / off | **unchanged** (gated `not kids_bedtime`) |
| Kids cooling, **daytime 07:00–18:00** | `cool@61 / off≤68 / on>72` | **unchanged** |
| Season flip mid-pull-down | shoulder force-off interrupts | bedtime block continues `cool@61/turbo` to ≤66 |
| Master / LR / Dining / Nest | as today | **UNCHANGED** |
| Manual-override gate | `idle` | **UNCHANGED** |
| Section 3 floors / 76° ceiling | 58 / 60 / 76 | **UNCHANGED** |
| Heating-season kid branches | heat / off | **UNCHANGED** |

---

## 7. Tests that genuinely need updating

Setpoint **61** is preserved everywhere, so the shove doctrine is intact.

- **`tests/test_section2_shove_command_setpoints.py`** — the new bedtime block adds
  two kid `cool@61` `set_temperature` commands; update the expected cooling-command
  **count** (still all `== 61`). Master/LR and the `58/60` safety + no-arbitration
  asserts unchanged.
- **`tests/test_section2_cooling_setpoint_doctrine.py`** — the daytime cooling kids
  block is unchanged (`l_setpoint=61`, `l_off_at="{{ 74 if away else 68 }}"`,
  `l_on_at="{{ 76 if away else 72 }}"`), now guarded by `not kids_bedtime`; confirm
  the test still locates these (adjust the traversal if the guard nests them).
- **`tests/test_supervisor_shoulder_night.py` → expand to the whole shoulder branch**
  (night + day): assert the kids are **removed from every shoulder bulk-off**; assert
  a **bedtime block** exists encoding `≥70→cool@61/turbo`, `≤66→off`,
  `current==cool→cool`, else `off`, **independently per room**; assert the
  shoulder-day legacy kid handling is **gated on `not kids_bedtime`**; assert
  **Master/LR/Dining/Nest unchanged** (Master shoulder-night escape, LR heat/off).
- **New (recommended):** a small test that the bedtime block gates on
  `kids_bedtime and season in ['cooling','shoulder']` and issues `fan_mode: turbo`
  only on the cool path.

---

## 8. Untouched invariants

- **Section 2 = sole kids' comfort writer.** No new automation/helpers; no ownership
  moved among Sections 2/3/6/8.
- **Setpoint 61 shove preserved** (operator-reaffirmed); turbo is explicit, intended.
- **`timer.manual_hvac_override`** behavior preserved exactly (supervisor still gates
  on `idle`; the bedtime block is inside the supervisor so it inherits the gate).
- **Section 3 unchanged** — LR runaway `<60`, Master floor `<58`, 76 °F ceiling, WAF.
- **Master, LR, Dining, Nest unchanged.** **Daytime kids (07:00–18:00) unchanged.**
- **Heating-season kid branches unchanged** (shoulder simply must not break an active
  bedtime cycle, which the season-independent bedtime block guarantees).
- **Telemetry, truth sensors, MSR/Apollo boundary, report-time freshness** unchanged.
- **Lincoln & Lilly independent** — separate per-room steps.

---

## 9. Validation procedure (Codex, live)

1. `python -m pytest tests/` green with the updated Section-2 tests; `58/60` floors
   and the `61` setpoint still asserted.
2. `ha core check`; reload.
3. **Bedtime engage/release:** with override idle and bedtime, drive a kid room above
   70 → confirm `cool@61/turbo`; let it fall to ≤66 → confirm `off`; between 66–70
   confirm it **holds** (cool stays cool, off stays off).
4. **No interruption on season flip:** force `cooling→shoulder` mid-pull-down →
   confirm the kid stays `cool@61/turbo` until ≤66 (no force-off).
5. **Shoulder bulk-off respect:** in shoulder mild/cold during bedtime, confirm no
   `off` is issued to a kid that is still pulling down.
6. **Daytime unchanged:** at 12:00 confirm the kids run the legacy `68–72` cooling /
   shoulder-day behavior; **independence** (one room's state never moves the other).
7. **Scope:** Master/LR/Dining/Nest and heating unchanged.
8. **2–3 nights telemetry:** kids' room truth cycles ~66–70 overnight (never parked
   at 72), turbo only during pull-downs.

---

## 10. Rollback plan

- Change set = `automations.yaml` Section 2 (new bedtime block + `kids_bedtime` var +
  the `not kids_bedtime` guards + shoulder-night bulk-off edit) + the Section-2 tests.
  **Rollback = `git revert` + reload.** No entity/truth/helper/telemetry migration.
- Git may lag live → Codex **commits the live Section 2 first**, then patches.
- Removing the bedtime block + guards restores the exact legacy behavior. Section 3
  and other rooms are untouched.

---

## 11. Live verification checklist (Codex, before patching)

1. **Diff live vs Git** for Section 2; commit live first; note any test-era edits.
2. **Confirm the failure source:** Logbook / `hvac_provenance_log` shows
   `v7_5_main_supervisor` `cool@61`/`off` at `:00/:15/:30/:45`, the 02:45 force-off,
   and the post-06:00 shoulder-day force-offs over 2026-06-05 21:00 → 06-06 08:30.
3. **Confirm `turbo` is acceptable to leave running during pull-downs** (operator
   says yes) and that the heads accept an explicit `fan_mode: turbo` (supported name).
4. **Heads run `cool`** (not Samsung `auto`).
5. **`timer.manual_hvac_override` duration**; overnight override state.
6. **05:45 Lincoln anomaly:** classify the re-engage origin.

---

## 12. Codex prompt — smallest live patch

```
ROLE: Modify the LIVE Moose House Home Assistant config inside HAOS. Git lags live;
LIVE YAML + live traces are source of truth. Read
docs/kids-bedroom-overnight-cooling-plan.md (v6) and AGENTS.md "Current Operator
Decisions" first.

ARCHITECTURE: SUPERVISOR-FIRST. automation.v7_5_main_supervisor (Section 2) is the
sole kids' comfort writer. Do NOT create a separate controller/helpers. 61/turbo is
intentional and required (moderate setpoints stall ~18h). This is a DEADBAND, not a
native-thermostat hold.

CONTRACT (Lincoln & Lilly, BEDTIME 18:00-07:00, cooling AND shoulder; independent):
  truth >= 70 -> cool @ 61, fan turbo
  truth <= 66 -> off
  66 < truth < 70 and current_mode == cool -> continue cool @ 61, turbo
  else -> off
Daytime (07:00-18:00) kids behavior unchanged (legacy 68-72). Heating unchanged.

STEP 0 — VERIFY LIVE: diff live Section 2 vs Git and COMMIT the live Section 2 first.
Confirm Section 2 writes the kids cool@61/off at :00/:15/:30/:45 and force-offs them
in shoulder. Confirm heads run 'cool' and accept fan_mode 'turbo'.

STEP 1 — PATCH SECTION 2 (kids only):
  - Add variable kids_bedtime = "{{ now().hour >= 18 or now().hour < 7 }}".
  - Add a "Kids Bedtime Cooling" block at the TOP of the action (before the season
    choose), gated on `kids_bedtime and season in ['cooling','shoulder']`, handling
    Lincoln and Lilly INDEPENDENTLY with the contract above; issue fan_mode turbo
    ONLY on the cool command.
  - Cooling branch: guard the existing Lincoln/Lilly set_temperature blocks on
    `not kids_bedtime` (daytime 68-72 unchanged).
  - Shoulder branch: remove climate.lincoln_air & climate.lilly_air from the
    is_night bulk-off (-> dining only); guard the shoulder-day warm kid blocks and
    the kids' membership in the cold/mild bulk-offs on `not kids_bedtime`.
  - Do NOT touch Master, LR, Dining, Nest, heating-season kid branches, the
    manual-override gate, Section 3, telemetry, truth sensors, or any other automation.

STEP 2 — TESTS:
  - test_section2_shove_command_setpoints.py: update the cooling-command count for
    the new bedtime kid cool@61 commands (still all 61); keep 58/60 + no-arbitration.
  - test_section2_cooling_setpoint_doctrine.py: daytime kids vars unchanged
    (61/68/72) now under a `not kids_bedtime` guard; fix traversal if nesting changed.
  - Expand the shoulder test to the whole branch: kids absent from every bulk-off;
    bedtime block exists with the exact per-room logic and turbo-on-cool; shoulder-day
    legacy kid handling gated on `not kids_bedtime`; Master/LR/Dining/Nest unchanged.

VALIDATE: pytest ; ha core check ; reload ; confirm bedtime engage>=70 -> cool@61/turbo,
release<=66 -> off, hold 66-70; a cooling->shoulder flip does NOT interrupt an active
pull-down; daytime unchanged; capture 2-3 nights with kids truth cycling ~66-70.

ROLLBACK: git revert + reload. No migrations. If live contradicts this plan, STOP and
report instead of inventing behavior.
```

---

### Appendix — what this plan does NOT do
- No native-thermostat continuous hold, no `verified_target`, no `kids_comfort_hold`,
  no `*_cool_setpoint` helpers, no ownership transfer (all withdrawn).
- No change to the 61 shove (reaffirmed), Master/LR/Dining/Nest, Section 3, the
  override contract, daytime kids, heating-season kids, telemetry, truth sensors, or
  MSR boundaries.
- No live implementation — planning only.
