# Kids' Bedroom Overnight Cooling Plan (Lincoln & Lilly)

**Doc Date:** 2026-06-06 (v2 — corrected control model)
**Document Role:** Planning + adversarial review. **No operational changes.**
**Scope:** Lincoln's Room and Lilly's Room overnight cooling comfort.
**Status:** Proposal. Repository analysis + operator correction (2026-06-06).
Live HAOS is the source of truth; Codex verifies and implements.

> **v2 note — what changed since v1.** v1 assumed the live system runs the
> repo's Section 2 *deadband + 61 °F shove* doctrine and recommended tightening
> that deadband. **The operator corrected this on 2026-06-06:** the intended/new
> control model is a **native Samsung-thermostat hold** — set a real comfort
> setpoint and let the head's inverter **scale back as it reaches temp** — and
> **"we never do the deadband."** This **supersedes**, for Lincoln & Lilly, the
> 2026-06-02 `comfort_control_actuator_arbitration_spec.md` (the "shove + off
> inside the band" doctrine) and the "deadband is the comfort contract" framing.
> The plan below is rebuilt around the new model.

> **Operating model honored:** analysis + plan only; nothing edited/reloaded/
> deployed on the live system. The "new" controller is **not in Git** (repo
> lags live). Git is the rollback/comparison/documentation layer.

---

## 0. Source data and how it was read

- **Authoritative overnight evidence:** Google Drive → Google Sheet **"Home
  Assistant"** (fileId `1URlWLkBYHYzuRcTvB32jPs_Fvs2bdDFn2L-sW3y10w8`, modified
  2026-06-06), tab **`VTherm_Launch_Data_v5_5`** — the live 15-min export from
  `vtherm_mega_tracker_v5` (Section 1) and the source of the supplied CSV.
- **The repo copy is stale:** `Home Assistant (9).xlsx` ends **2026-06-05 15:00**
  and lacks the `Supervisor_Enabled` / `Manual_Override_State` /
  `Manual_Override_Remaining_Sec` columns — it does **not** contain the overnight
  window. Those rows live only in the live Sheet.
- **"VTherm" is a telemetry brand, not the controller.** There is no Versatile
  Thermostat integration; the operator-confirmed live controller for the kids is
  the **native Samsung head thermostat** (HA holds a setpoint; the head
  modulates). The mini-split entities are `climate.lincoln_air` /
  `climate.lilly_air`.

---

## 1. Executive diagnosis

**The rooms overheat overnight because the legacy Section 2 supervisor is still
enabled and overwrites the new native-thermostat hold — Lincoln & Lilly have two
controllers fighting on the same heads, and the legacy one wins every tick.**

Operator-confirmed facts (2026-06-06):
- **Intended control:** hold a comfort setpoint on each head; let the inverter
  scale back near temp; **no deadband**; **room truth must stay ≤ 70 °F**.
- **Live reality:** `automation.v7_5_main_supervisor` (Section 2) is **still
  enabled** and runs every 15 min + on every `Season_Mode` change.

What Section 2 does to the kids' heads each time it runs (live YAML
`automations.yaml`), directly contradicting the hold:
1. **Re-commands `cool @ 61 °F`** (the test-locked "shove," `:439,:459`) instead
   of the comfort setpoint — so the head is told to run flat-out, not hold ~70.
2. **Cuts the head fully OFF at room-truth `≤ 68 °F`** (`:446–471`) — the
   bang-bang deadband the operator says they no longer want. The room then
   free-heats toward 72 before truth crosses `> 72` and 61-shove resumes.
3. **Force-OFFs the kids in shoulder-night** (`:533–535`) and on the shoulder/
   heating day+night paths — so when auto-season flipped `cooling → shoulder` at
   ~02:45 (Deck 64.4 °F), the kids were commanded off for the rest of the night.
4. Never sets the kids' **fan**, so a manually-left **`turbo`** sticks all night.

Two secondary writers can also fight the hold: **Section 8 Samsung Auto
Guardrail** (every 10 min) and **Section 6 destrat** (fan), and the **76 °F
ceiling gate** ends in a hard `off`. None caused last night, but all must be made
hands-off/safe for the kids.

**Net:** the head is yanked between a 61 °F shove and OFF (and force-off in
shoulder) and never allowed to hold ~70 and modulate → the 67↔72 sawtooth and the
hours-long warm plateau. The fix is **not** to tune a deadband; it is to **stop
the legacy stack from touching Lincoln & Lilly and let the head hold a tuned
comfort setpoint** — with room truth as a light ceiling guard, not a bang-bang.

`Night_Mode_Toggle`, `Away_Mode`, manual override, and the truth sensors were not
at fault (§4, §11).

---

## 2. Relevant files and entity IDs

### 2.1 Files (complete scope)
Only `automations.yaml` and `configuration.yaml` carry logic/helpers. Confirmed
absent (nothing missed): no `scripts.yaml`, `packages/`, `blueprints/`,
`custom_components/`, `appdaemon/`, `pyscript/`. **The new native-thermostat hold
is not represented in Git at all** — it is live config (head setpoint/mode set
by hand or by a live-only automation).

### 2.2 Entity IDs

| Concept | Entity ID | In repo? |
|---|---|---|
| Lincoln / Lilly heads | `climate.lincoln_air`, `climate.lilly_air` | device |
| Lincoln / Lilly room truth | `sensor.lincoln_s_room_temperature_truth`, `sensor.lilly_s_room_temperature_truth` | `configuration.yaml:451,643` |
| Samsung internal (biased, w=0.20) | `sensor.lincoln_air_temperature`, `sensor.lilly_air_temperature` | yes |
| Lincoln truth contributor count | `sensor.lincoln_temperature_truth_active_count` | yes |
| Lilly truth contributor count | **none exported** (gap) | — |
| Outdoor/Deck truth | `sensor.deck_temperature_truth` | yes |
| Season mode | `input_select.hvac_season_mode` | **NOT in repo — live UI helper** |
| "Night_Mode_Toggle" | `input_boolean.night_mode_lr_primary` | **NOT in repo — live UI helper** |
| Away mode | `input_boolean.away_mode` | **NOT in repo — live UI helper** |
| Manual override timer | `timer.manual_hvac_override` | **NOT in repo — live UI helper** |
| Lincoln / Lilly cooldown (orphaned, 15 min) | `timer.lincoln_compressor_cooldown`, `timer.lilly_compressor_cooldown` | `configuration.yaml:131,135` |
| Legacy supervisor (**still enabled**) | `automation.v7_5_main_supervisor` | `automations.yaml:358` |
| Lincoln presence | `binary_sensor.lincoln_presence_debounced_v3` | `configuration.yaml:203` |
| Lilly presence | **none** (Lilly has no presence sensor) | — |

> **Repo-lag flags:** season mode, away mode, night toggle, the override timer
> (and its **duration**), **and the new native-thermostat hold itself** are not in
> Git. Codex must read all of them live (§15).

---

## 3. Full control-flow map (intended vs. actual)

```
  INTENDED (operator's new model)                ACTUAL (live today)
  ───────────────────────────────                ───────────────────
  room truth + season decide IF cooling          legacy Section 2 (STILL ENABLED)
        │                                         runs every 15 min + on season change
        ▼                                               │
  set climate.<kid>_air = cool @ COMFORT           overwrites head every tick:
  setpoint (tuned so truth ≤ 70), quiet fan          cool@61 / off≤68 / shoulder-night off
        │                                               │
        ▼                                               ▼
  head inverter MODULATES / "scales back"          head yanked 61-shove ↔ OFF
  near setpoint — supervisor leaves it alone        (+ stuck turbo) → 67↔72 sawtooth
        │                                          + force-off after 02:45 season flip
        ▼
  truth used only as a light ≤70 ceiling guard
  + Section 3 safety; NOT as a bang-bang off
```

Both control paths currently write the **same** entities → this is a live
**conflicting-writers** condition (the exact failure the objective forbids), and
the legacy path wins because it reasserts on a schedule.

---

## 4. Exact likely cause of last night's behavior (transition by transition)

Legacy cooling band = `ON>72 / OFF≤68`, command `61 / turbo`. Times approximate.

| Time | Observed | Cause (legacy Section 2 overwriting the hold) |
|---|---|---|
| 21:00 | both off, ~68 °F rising | Truth had fallen `≤68` → Section 2 cut heads OFF; hold can't keep them at ~70 because Section 2 re-offs every tick. |
| 22:45 / 23:15 | Lincoln / Lilly → cool | truth crossed `>72` → Section 2 engages `cool@61/turbo` (overshooting past any ~70 hold). |
| 23:45 / 00:00 | → off | 61/turbo overshot to `≤68` → Section 2 cut OFF (bang-bang). |
| 00:00–02:00 | Lilly drifts 71–72, off | Section 2 holds OFF until `>72`; the head is never allowed to sit in `cool@~70` and modulate. |
| 02:00 | Lincoln → cool | crossed `>72` → 61-shove again. |
| **02:45** | Season → shoulder; Deck 64.4 °F | Section 5 auto-season (`:919–951`): Deck in 50–68/2h → `shoulder`; the season change re-triggers Section 2 immediately. |
| 02:45 → 08:30 | both off / warm to ~72 | shoulder-night force-offs the kids (`:533–535`); shoulder-day mild path also offs them unless `outdoor>70`/`LR>71`. Returning to `cooling` needs Deck `>72`/2h (daytime). The hold is overwritten with OFF the whole time → Lilly stewed 71–72 °F. |

**05:45 Lincoln boundary:** still `is_night` + `shoulder`, where Section 2 offs
the kids — a 05:45 re-engage would not come from Section 2. Verify in the live
trace (manual nudge / cloud push / ceiling gate). §15.

The `72.32 °F` maxima are the room at the legacy `>72` ON edge; under the new
hold the head should cap the room near the comfort setpoint long before 72.

---

## 5. Confirmed facts vs assumptions requiring live verification

### 5.1 Operator-confirmed (2026-06-06)
- New control = **native Samsung thermostat hold + inverter modulation; no
  deadband.**
- **Legacy Section 2 is still enabled live** (it is the overwriter).
- **Room-truth comfort ceiling = 70 °F** ("sweaty kids" above that).

### 5.2 Confirmed from the repo (YAML = legacy runtime)
- Section 2 commands the kids `cool@61` / `off≤68` / `on>72` and **force-offs**
  them in shoulder-night, shoulder-day(non-warm), heating-night(LR-primary), and
  heating-day (`comfort_failure_forensics.md` bulk-off table; `automations.yaml`
  Section 2). It never sets their fan.
- `61`/`79` shoves and `68/72` thresholds and the shoulder-night kids force-off
  are **test-locked** (`tests/test_section2_shove_command_setpoints.py`,
  `tests/test_supervisor_shoulder_night.py`).
- Auto-season: `>72/2h→cooling`, `<45/2h→heating`, `50–68/2h→shoulder`.
- `Night_Mode_Toggle` = `input_boolean.night_mode_lr_primary` (heating-only,
  `:625`); **no weekday gating anywhere** (window was Fri→Sat; irrelevant).
- Manual-override gate enforced on supervisor/ceiling/destrat/guardrail/boost.
- Supervisor truth fallback = `float(70)` when a room's truth is unavailable.
- Lilly has no presence sensor; cooldown timers exist but are orphaned.

### 5.3 Assumptions requiring live verification (Codex)
- **That Section 2 is actively overwriting the kids' heads at `:00/:15/:30/:45`
  with 61** (confirm via Logbook / `hvac_provenance_log` provenance =
  `automation_or_script` / `v7_5_main_supervisor`).
- **Samsung-internal vs room-truth bias** for each head during active cooling
  (config note: Lincoln Samsung ≈ +4.7 °F). This determines what number to
  command so the **room** (not the head's biased sensor) tops out at ≤70.
- **The heads run in `cool`, not Samsung `auto`** (auto would trip Section 8 and
  the bias/behavior differs).
- `turbo` origin (no automation sets it) and the **supported fan modes**.
- `timer.manual_hvac_override` **duration**; overnight `Manual_Override_State`.
- Why `Supervisor_Enabled` is **blank** in the export (entity_id / worksheet
  header issue — observability defect, not evidence of cause).

---

## 6. Overlapping automation / race-condition audit

**Every writer to `climate.lincoln_air` / `climate.lilly_air` today:**

| # | Automation (id) | Trigger | Action on kids | Override-gated? | Conflict with the new hold |
|---|---|---|---|---|---|
| 0 | **New native-thermostat hold** (live, not in Git) | operator/automation sets head setpoint | hold `cool @ ~70`, modulate | (must) | **Being overwritten by #1 every tick.** |
| 1 | `v7_5_main_supervisor` (S2) — **enabled** | /15 + season change | `cool@61` / `off` / force-off | ✅ idle | **Primary conflict.** Reasserts legacy policy over the hold every tick. |
| 2 | `v8_samsung_auto_guardrail` (S8) | hvac_action / →auto / /10 | force `off` on Samsung `auto` | ✅ idle | Only fires if head reports `auto`; harmless if head stays `cool`, but it is a second scheduled writer. |
| 3 | `v7_5_safety_ceiling_gates` (S3) | truth `>76` | cooling: `cool@68` 45 min → **off** | ✅ idle | Emergency only; its terminal `off` would drop the hold — make it hand back to the hold, not hard-off. |
| 4 | `v8_comfort_fan_destratification` (S6) | :07/:22/:37/:52 | heating/shoulder `fan_only`+fan | ✅ idle | Triggers only when head is `off`; if the hold keeps the head in `cool`, it won't fire — but should be scoped off the kids to be safe. |
| 5 | `v7_5_ghost_assassin` (S4) | 01:20 | Lincoln: `heat`&non-heating→off | ❌ (protection) | Harmless to a cool hold; keep. |
| — | WAF watcher (S3) | human change to a head | starts override timer | n/a | Correct — converts a parent's nudge into the override window. |

**Conclusion:** there are **already** conflicting writers (the new hold vs. the
still-enabled legacy stack). The fix is to make #1 (and #3/#4) **hands-off for the
kids**, leave #2/#5 as `auto`/ghost protection, and let #0 own the heads.
Implementing the hold **inside one place that owns the kids** (and removing the
kids from #1) prevents re-introducing a race.

---

## 7. Minimal recommended implementation

Design principle: **one owner per head.** Remove Lincoln & Lilly from the legacy
comfort stack and let the native thermostat hold a tuned comfort setpoint, with
truth as a ≤70 ceiling guard and Section 3 as safety. Keep rooms independent.
Preserve the manual-override contract. Abandon the 61 shove **for the kids**.

### Tier 1 — Stop the fight (highest value; do first)
**A. Carve Lincoln & Lilly out of `v7_5_main_supervisor` (Section 2).** Delete
their `set_temperature` blocks (cooling `:438–471`; shoulder-day warm
`:546–549`; heating-night `:610–614`, `:640–644`) and remove them from every
bulk-off target list (`:533–535`, `:577`, `:581`, `:633`, `:671`). After this,
Section 2 no longer touches the kids' heads in any branch — Master/LR/Nest
behavior is unchanged. This single change stops the 61-shove, the `≤68` bang-bang
**and** the shoulder-night force-off in one move.

**B. Scope the other legacy writers off the kids (or make them safe):** remove
Lincoln/Lilly from Section 6 destrat; change the Section 3 ceiling gate's cooling
branch so that after the 45-min emergency it **returns the head to the comfort
hold**, not a hard `off`; leave Section 8 (auto guard) and Section 4 (ghost) as
protection.

### Tier 2 — Hold the comfort setpoint (the new owner)
**C. Establish the held setpoint as a *room-truth* target, not a head number.**
The head regulates against its **biased internal sensor**, so commanding "70" does
**not** mean the room holds 70. Pick the commanded number so **room truth** tops
out at ≤70 (operator ceiling). Method: command `cool` at a starting setpoint
(begin ~68 °F), observe `sensor.<kid>_room_temperature_truth` for 1–2 nights, and
adjust the commanded number until truth plateaus at ~69 °F (never >70). Expose it
as a tunable `input_number` per room so it can be dialed without code edits.

**D. Add one small "kids comfort hold" automation that owns both heads**
(independent per room): on a 15-min reassert + a truth-over-ceiling trigger +
season change, while `timer.manual_hvac_override == idle`, ensure each head is
`cool @ comfort_setpoint` with a **quiet fan** (low/auto, never turbo) whenever
cooling is appropriate, and otherwise leave it alone — **no deadband off.** Let
the head modulate. A light guard: if room truth `> 70.5 °F` for ~5 min and the
head is not cooling, set it to `cool`. (Turn off only for genuine non-cooling
conditions, e.g. heating season with a cold room — see §12.)

**E. Reset the stuck fan.** The hold sets `fan_mode` to a quiet value while
`cool`; `turbo` is reserved for the ≥76 °F ceiling gate / a high-temp emergency.

### Tier 3 — Optional hardening
**F. Anti-short-cycle / min-on** using the existing orphaned
`timer.lincoln_compressor_cooldown` / `timer.lilly_compressor_cooldown` (only
relevant if the hold ever turns a head fully off). **G. Event-based ≤70 guard**
already covered by D's truth trigger (removes the 15-min polling dependency for
the ceiling). **H.** Migrate the per-room comfort setpoint into the planned
comfort-profile system later.

> **Doctrine update required:** §1/§5.1 of `1_startup_canon.md`, the
> `comfort_control_actuator_arbitration_spec.md` "off-inside-the-band / shove,"
> and the `comfort_failure_forensics.md` "deadband is the contract" framing must
> be amended to note that **Lincoln & Lilly are now native-thermostat-hold
> rooms** (setpoint + modulation), not deadband/shove rooms. Other rooms are
> unchanged unless the operator extends the model.

---

## 8. "From → To" change table

| # | Item | From (live today) | To (proposed) | Tests to update |
|---|---|---|---|---|
| A | Section 2 owns kids | `cool@61` / `off≤68` / `on>72` / shoulder force-off, all branches | Kids **removed** from Section 2 entirely | `test_section2_shove_command_setpoints.py` (cooling-cmd count drops; kids threshold asserts removed), `test_supervisor_shoulder_night.py` (kids no longer required in bulk-off), `test_section2_cooling_setpoint_doctrine.py` |
| B | Ceiling gate end-state | `cool@68` 45 min → **off** | → return head to comfort hold | adjust ceiling-gate test if any |
| B | Destrat on kids | fan_only on kids (heating/shoulder) | kids removed from destrat | destrat test scope |
| C | Held setpoint | `61` shove (legacy) | comfort setpoint tuned so **room truth ≤70** (start ~68, per-room `input_number`) | new helper test |
| D | Control style | 15-min bang-bang deadband | hold `cool@setpoint`, head modulates; truth used as ≤70 ceiling guard only | new "kids hold" automation + its tests (incl. override-idle gate) |
| E | Fan | unset → `turbo` sticks | quiet (low/auto) while cooling; turbo only ≥76 emergency | — |
| — | Manual override | gated (S2 etc.) | new hold automation **also** gates on `idle` | extend `test_manual_override_contract.py` |
| — | Independence | per-room already | preserved (separate per-room steps) | — |

---

## 9. Proposed YAML (illustrative — DO NOT APPLY HERE; Codex adapts vs. live)

### 9.A Remove kids from Section 2 (representative — applies to every kid reference)
```yaml
# COOLING branch: delete the Lincoln (:438–451) and Lilly (:458–471)
#   `- variables:` + `- action: climate.set_temperature` blocks entirely.
# SHOULDER-NIGHT bulk-off (:533–535): drop the kids, keep Nest:
- action: climate.set_hvac_mode
  target: { entity_id: climate.dining_room }   # was [lincoln_air, lilly_air, dining_room]
  data: { hvac_mode: "off" }
# Do the same for every other bulk-off list (:577, :581, :633, :671) and delete
# the heating-night kid set_temperature steps (:610–614, :640–644).
# RESULT: Section 2 issues NO command to climate.lincoln_air / climate.lilly_air.
```

### 9.B New owner: kids comfort hold (native-thermostat, no deadband)
```yaml
- id: kids_comfort_hold
  alias: "Kids Comfort Hold (native thermostat + modulation, no deadband)"
  mode: single
  trigger:
    - platform: time_pattern               # reassert intent (defends against drift)
      minutes: "/15"
    - platform: numeric_state              # ≤70 ceiling guard (event-based)
      entity_id: [sensor.lincoln_s_room_temperature_truth, sensor.lilly_s_room_temperature_truth]
      above: 70.5
      for: "00:05:00"
    - platform: state
      entity_id: input_select.hvac_season_mode
  condition:
    - condition: state
      entity_id: timer.manual_hvac_override
      state: "idle"
  action:
    - variables:
        season: "{{ states('input_select.hvac_season_mode') }}"
        # Per-room comfort setpoints are tunable helpers; tuned so ROOM TRUTH ≤70.
        l_sp:  "{{ states('input_number.lincoln_cool_setpoint') | int(68) }}"
        ly_sp: "{{ states('input_number.lilly_cool_setpoint')   | int(68) }}"
        l_truth:  "{{ states('sensor.lincoln_s_room_temperature_truth') | float(70) }}"
        ly_truth: "{{ states('sensor.lilly_s_room_temperature_truth')   | float(70) }}"
        # Cool is appropriate in cooling/shoulder, or any time the room is warm.
        cool_ok: "{{ season in ['cooling','shoulder'] }}"
    # --- Lincoln (independent) ---
    - choose:
        - conditions: "{{ cool_ok or l_truth > 70.5 }}"
          sequence:
            - action: climate.set_temperature
              target: { entity_id: climate.lincoln_air }
              data: { hvac_mode: "cool", temperature: "{{ l_sp }}" }
            - action: climate.set_fan_mode
              target: { entity_id: climate.lincoln_air }
              data: { fan_mode: "low" }          # quiet; verify supported names live
      # else: leave the head as-is (heating-season handling TBD; see §12).
    # --- Lilly (independent; identical, no presence dependency) ---
    - choose:
        - conditions: "{{ cool_ok or ly_truth > 70.5 }}"
          sequence:
            - action: climate.set_temperature
              target: { entity_id: climate.lilly_air }
              data: { hvac_mode: "cool", temperature: "{{ ly_sp }}" }
            - action: climate.set_fan_mode
              target: { entity_id: climate.lilly_air }
              data: { fan_mode: "low" }
```

### 9.C Tunable comfort-setpoint helpers (configuration.yaml)
```yaml
input_number:
  lincoln_cool_setpoint:        # tuned so Lincoln ROOM TRUTH tops out ≤70
    name: "Lincoln Cool Setpoint"
    min: 64
    max: 72
    step: 1
    unit_of_measurement: "°F"
  lilly_cool_setpoint:
    name: "Lilly Cool Setpoint"
    min: 64
    max: 72
    step: 1
    unit_of_measurement: "°F"
```

> **Why the commanded number is not "70":** the head regulates on its own
> internal thermistor, which is biased vs. room air during cooling (Lincoln
> noted ≈ +4.7 °F). Tune each `*_cool_setpoint` from `*_room_temperature_truth`
> so the *room* never exceeds 70 — that is the operator's actual ceiling.

---

## 10. Safety and anti-short-cycle behavior

- **Section 3 untouched:** LR runaway `<60` (`:737–762`), Master floor `<58`
  (`:778–801`) — never gated by override. The 76 °F ceiling gate stays as the
  emergency backstop for the kids; adjust only its *terminal* action to hand back
  to the comfort hold instead of a hard `off`.
- **No bang-bang to short-cycle:** the head holds `cool` and **modulates**;
  because the supervisor stops cutting it OFF at a band edge, the primary source
  of rapid cycling is removed. If the hold ever turns a head fully off, wire the
  existing `timer.<kid>_compressor_cooldown` (15 min) for min-off/min-on.
- **Ceiling guard is sustained** (`for: 5m`) so a transient spike doesn't act.
- **Turbo only for emergency** (≥76 °F ceiling gate); never the overnight default.

---

## 11. Manual override behavior (must remain authoritative)

- **Mechanism (confirmed):** `v7_5_waf_manual_override` (`:858–881`, restart)
  starts `timer.manual_hvac_override` on any non-automation change to a head.
- **Effect:** while `active`, Section 2, ceiling gates, destrat, guardrail, boost
  **and the new `kids_comfort_hold`** must stand down (all gate on `idle`). Add
  `kids_comfort_hold` to `test_manual_override_contract.py`.
- **Expiry (route to live):** the timer's duration is **not in Git** (~1 h
  documented); on expiry → `idle` → the hold reasserts on the next tick. The hold
  must **not** undo a parent's nudge during the window.

---

## 12. Seasonal shoulder-mode behavior

- **Today:** shoulder (and the 02:45 outdoor-driven flip) **force-offs the kids**
  — the root of the warm plateau. Outdoor Deck temp silently vetoes indoor
  comfort (Regression Appendix §4.16).
- **After the change:** the kids are out of Section 2, so a `→shoulder` flip no
  longer offs them. The `kids_comfort_hold` keeps `cool@setpoint` whenever cooling
  is appropriate **or** the room exceeds the 70 °F ceiling — **regardless of
  season**. Season becomes a *bias*, not a veto (matching the operator's intent
  and the actuator-spec's "season biases, does not hard-ban").
- **Heating season (scope note):** this plan targets overnight overheating. For
  winter, decide whether the kids' heating stays in Section 2 (then `kids_comfort_hold`
  should no-op in `heating` unless the room is over the cooling ceiling) or also
  migrates to a hold. Recommended: keep `cool_ok = season in ['cooling','shoulder']`
  plus the year-round `>70.5` guard, and leave heating to a follow-up so this
  change stays minimal.
- **Independence:** Lincoln and Lilly are handled in separate steps; one reaching
  its setpoint never disables the other.

---

## 13. Validation procedure (Codex, live)

1. **Static:** `python -m pytest tests/` green, with the updated Section 2 /
   shoulder-night / cooling-setpoint tests and the new hold + helper tests.
   Re-assert `58/60` floors and report-time freshness unchanged.
2. **Config check:** `ha core check` before reload.
3. **Provenance:** confirm Section 2 no longer writes `climate.lincoln_air` /
   `climate.lilly_air` (Logbook / `hvac_provenance_log` shows no
   `v7_5_main_supervisor` writes to the kids).
4. **Hold + modulation:** with override idle and a warm room, confirm the head
   sits in `cool @ comfort_setpoint` with a quiet fan and **modulates** (hvac_action
   cycles run→idle) instead of being cut OFF; confirm the other child is
   unaffected (independence) and Master/LR/Nest unchanged.
5. **Ceiling:** drive a room `>70.5` for 5 min and confirm the guard ensures
   cooling; confirm the room **truth** plateaus ≤70 after setpoint tuning.
6. **Season flip:** force `cooling→shoulder` overnight and confirm the kids keep
   cooling (no force-off).
7. **Override:** nudge a head; confirm the hold stands down for the window and
   reasserts on expiry.
8. **2–3 nights telemetry:** max kids truth ≤70, no `turbo` rows, far fewer
   off↔cool transitions than the June 5–6 baseline.

---

## 14. Rollback procedure

- Changes are confined to `automations.yaml` (Section 2 kid-removal + new
  `kids_comfort_hold` + ceiling-gate terminal tweak), `configuration.yaml` (two
  `input_number` helpers), and the test files. **Rollback = `git revert` + reload
  automations;** no entity renames, no truth-layer changes.
- Because Git lags live, Codex must **first commit the live Section 2 + the live
  native-thermostat hold setup** (so the repo matches reality), then apply changes
  on top — so rollback returns to the *actual* prior live state.
- Disabling the single `kids_comfort_hold` automation + re-enabling the kids in
  Section 2 is an instant full rollback. Safety gates are untouched throughout.

---

## 15. Specific live automation traces Codex must inspect

1. **Confirm the fight:** for `climate.lincoln_air` / `climate.lilly_air`, pull
   Logbook + `hvac_provenance_log` across the overnight window — expect
   `v7_5_main_supervisor` writes at `:00/:15/:30/:45` (and at 02:45) commanding
   `61`/`off`. This is the proof the legacy supervisor overwrote the hold.
2. **Bias characterization:** compare `sensor.<kid>_air_temperature` (Samsung
   internal) vs `sensor.<kid>_room_temperature_truth` during active cooling to
   pick the commanded setpoint that holds room truth ≤70.
3. **Mode check:** confirm the heads run in `cool` (not Samsung `auto`).
4. **02:45 flip:** trace `v7_5_auto_season_mode` + the supervisor re-run.
5. **05:45 Lincoln anomaly:** classify the re-engage origin (manual / cloud /
   ceiling gate).
6. **turbo provenance** + **supported fan modes** for both heads.
7. **Override timer** definition/duration + overnight `Manual_Override_State`.
8. **`Supervisor_Enabled` blank** root cause (entity_id / worksheet header).
9. **Helper existence:** `input_select.hvac_season_mode`, `input_boolean.away_mode`,
   `night_mode_lr_primary`, `timer.*` exist live as assumed.

---

## 16. Copy-paste Codex implementation prompt

```
ROLE: You are modifying the LIVE Moose House Home Assistant config inside HAOS.
Git lags live; LIVE YAML + live traces are source of truth. Read
docs/kids-bedroom-overnight-cooling-plan.md (v2) first.

CONTEXT (operator-confirmed 2026-06-06):
- Lincoln & Lilly should be controlled by the NATIVE Samsung thermostat: set a
  real comfort setpoint and let the head's inverter scale back as it reaches
  temp. NO bang-bang deadband. Room TRUTH must never exceed 70°F.
- The legacy Section 2 supervisor (automation.v7_5_main_supervisor) is STILL
  ENABLED and overwrites that hold every 15 min with cool@61 / off<=68 and
  force-offs the kids in shoulder-night. That fight is the bug.

STEP 0 — VERIFY LIVE (report before editing):
  1. Confirm Section 2 is enabled and is writing climate.lincoln_air /
     climate.lilly_air at :00/:15/:30/:45 with setpoint 61 (Logbook /
     hvac_provenance_log).
  2. Snapshot live automations.yaml Section 2, the live native-thermostat hold
     setup for the kids, and live helpers (input_select.hvac_season_mode,
     input_boolean.away_mode, night_mode_lr_primary, timer.manual_hvac_override,
     timer.{lincoln,lilly}_compressor_cooldown). COMMIT them so the repo matches
     live BEFORE changing anything.
  3. Characterize Samsung-internal vs room-truth bias during cooling for each
     head; confirm heads run in 'cool' (not 'auto'); list supported fan modes.

STEP 1 — STOP THE FIGHT:
  A. Remove Lincoln & Lilly from automation.v7_5_main_supervisor entirely:
     delete their set_temperature blocks in every season branch and remove them
     from every bulk-off target list. Section 2 must issue NO command to
     climate.lincoln_air / climate.lilly_air. Leave Master/LR/Nest unchanged.
  B. Remove the kids from Section 6 destrat; change the Section 3 76°F ceiling
     gate cooling branch to hand the head back to the comfort hold instead of a
     hard 'off'. Leave Section 8 (auto guard) and Section 4 (ghost) as protection.

STEP 2 — NEW OWNER (kids comfort hold; see plan §9.B/§9.C):
  C. Add input_number.lincoln_cool_setpoint / lilly_cool_setpoint (tunable),
     tuned from room truth so each room tops out <=70°F (start ~68, adjust).
  D. Add ONE automation 'kids_comfort_hold' (mode: single) that, while
     timer.manual_hvac_override == idle, ensures each head is cool @ its comfort
     setpoint with a quiet fan whenever cooling is appropriate (cooling/shoulder
     season) OR room truth > 70.5°F for 5 min, and otherwise leaves it alone.
     NO deadband off. Keep Lincoln and Lilly independent. Reserve turbo for the
     76°F ceiling gate only.
  E. Add kids_comfort_hold to tests/test_manual_override_contract.py (must gate
     on idle). Update tests/test_section2_shove_command_setpoints.py,
     tests/test_supervisor_shoulder_night.py, and
     tests/test_section2_cooling_setpoint_doctrine.py to reflect that the kids
     are no longer Section-2-controlled. Do NOT weaken the 58/60 safety asserts
     or report-time freshness.

STEP 3 — DOCTRINE: amend 1_startup_canon.md §5.1,
  comfort_control_actuator_arbitration_spec.md, and comfort_failure_forensics.md
  to record that Lincoln & Lilly are native-thermostat-hold rooms (setpoint +
  modulation), not deadband/shove rooms.

CONSTRAINTS:
  - One owner per head: after STEP 1, only kids_comfort_hold (+ Section 3 safety,
    Section 8 auto-guard, Section 4 ghost) may touch the kids' heads.
  - Every comfort automation keeps the timer.manual_hvac_override == idle gate;
    Section 3 floors (58/60) must NOT gate on override.
  - Do not rename entities, collapse sections, or remove telemetry/safety. Do not
    promote MSR/Apollo into control.
  - Make NO change without STEP 0. If live contradicts the plan, STOP and report.

VALIDATE: python -m pytest tests/ ; ha core check ; reload ; run plan §13 live
checks ; capture 2-3 nights and confirm room truth stays <=70 with no turbo and
far fewer off<->cool transitions than the June 5-6 baseline.

ROLLBACK: git revert the changes + reload; or disable kids_comfort_hold and
re-enable the kids in Section 2 (plan §14). No entity/truth migrations involved.
```

---

### Appendix — doctrine alignment notes
- This plan stops treating outdoor/season as an authority over an occupied
  child's bedroom (Doc 1 §7; Appendix §4.16) and resolves an existing
  conflicting-writers condition rather than adding one.
- It **supersedes**, for Lincoln & Lilly only, the 2026-06-02 actuator-shove /
  "off-inside-the-band" spec and the deadband-as-contract framing, per the
  operator's 2026-06-06 decision (native-thermostat hold + modulation, room ≤70).
- It keeps comfort and safety separate, preserves the manual-override contract,
  and keeps the two rooms independent. The held setpoint is tuned against room
  truth (not the head's biased thermistor), consistent with the truth-first
  philosophy.
