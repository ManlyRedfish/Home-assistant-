# Kids' Bedroom Overnight Cooling Plan (Lincoln & Lilly)

**Doc Date:** 2026-06-06
**Document Role:** Planning + adversarial review. **No operational changes.**
**Scope:** Lincoln's Room and Lilly's Room overnight cooling comfort.
**Status:** Proposal. Repository analysis only. The live HAOS configuration,
live entity states, and live automation traces are the ultimate source of
truth and must be confirmed by Codex before any change ships.

> **Operating-model reminders honored by this document**
> - Claude Code produced analysis + a plan only. Nothing was edited, reloaded,
>   restarted, or deployed.
> - Codex (inside HAOS) will inspect and modify the live system later.
> - The Git repo may lag the live HAOS config. Where the repo cannot prove a
>   fact, this plan says so explicitly and routes it to live verification.
> - Git is the rollback / comparison / documentation layer; **live HAOS wins**.

---

## 0. Source data and how it was read

- **Authoritative overnight evidence:** Google Drive → Google Sheet **"Home
  Assistant"** (native Sheet, fileId `1URlWLkBYHYzuRcTvB32jPs_Fvs2bdDFn2L-sW3y10w8`,
  modified 2026-06-06), tab **`VTherm_Launch_Data_v5_5`**. This is the live
  15-minute telemetry export written by automation `vtherm_mega_tracker_v5`
  (Section 1). It is the file the supplied
  `Home Assistant - VTherm_Launch_Data_v5_5 (1).csv` was exported from.
- **The repo copy is stale.** `Home Assistant (9).xlsx` in the repo root
  contains the same tab but its `VTherm_Launch_Data_v5_5` rows **end at
  2026-06-05 15:00:00** and the workbook is missing the three sub-block-15
  columns (`Supervisor_Enabled`, `Manual_Override_State`,
  `Manual_Override_Remaining_Sec`). It therefore **does not contain the
  June 5 21:00 → June 6 08:30 overnight window**. The overnight rows and the
  override-state columns live only in the live Sheet.
- **"VTherm" is a telemetry name, not an integration.** There is **no
  Versatile Thermostat / `generic_thermostat` / custom `vtherm` climate
  entity** anywhere in the repo. "VTherm" is the worksheet/launch-data brand
  (`VTherm_Launch_Data_v*`). The real controller is the **custom Section 2
  supervisor** (`automation.v7_5_main_supervisor`) issuing raw
  `climate.set_*` calls to the Samsung heads. **"Don't fight VTherm" therefore
  means "don't fight the Section 2 supervisor / its manual-override contract /
  its season branches."** (Live-verify: confirm no Versatile Thermostat
  integration exists in the live HAOS add-on/integration list.)

This plan's behavioral claims are derived from the live YAML (`automations.yaml`,
`configuration.yaml`) cross-referenced with the operator-supplied overnight
observations. Items that depend on the exact overnight rows are flagged for
Codex in §15.

---

## 1. Executive diagnosis

Both children's rooms drifted to ~72 °F and held warm for hours overnight
because of **four compounding causes**, none of which is a sensor fault and
none of which is "VTherm." Ranked by comfort impact:

1. **Shoulder-night force-off with no kids' cooling escape (root cause of the
   hours-long warm period).** When `Season_Mode` auto-switched
   `cooling → shoulder` at ~02:45 (driven purely by outdoor Deck temperature),
   the Section 2 *shoulder-night* branch began issuing an unconditional
   `climate.set_hvac_mode: off` to `climate.lincoln_air` **and**
   `climate.lilly_air` every tick (`automations.yaml:533–535`). The **Master**
   bedroom has a documented shoulder-night cooling escape
   (`automations.yaml:519–532`); **the kids do not.** This is why Lilly stayed
   off from ~midnight to 08:30 and Lincoln went off at ~02:45 — the supervisor
   was *commanding* them off regardless of how warm the rooms were. This is the
   regression the project itself names "Treating Outdoor / Season Logic as
   Stronger Than Manual/Comfort Intent" (Doc 1 §7; Regression Appendix §4.16).

2. **A wide, high cooling deadband (cause of the 67 → 72 sawtooth ceiling).**
   In cooling season the kids' band is **ON when truth `> 72` °F, OFF when truth
   `≤ 68` °F** (`automations.yaml:438–471`). A 70 °F target cannot be held by a
   band whose top edge is 72 °F: the room is *allowed* to climb to 72 before any
   cooling starts. Max truth 72.32 °F is the room sitting right at/just over the
   72 ON edge.

3. **A "shove" actuator command (61 °F) with a stuck `turbo` fan (cause of the
   undershoot to ~67 °F and the noise).** The commanded setpoint is a
   deliberate, **test-locked** 61 °F "shove" (`automations.yaml:439,459`;
   `tests/test_section2_shove_command_setpoints.py`) so the unit pulls hard and
   the *supervisor's* `≤68` truth rule stops it — not the Samsung thermostat.
   Combined with a `turbo` fan that **no automation ever sets or resets**, the
   unit overshoots down toward ~67 °F before the next 15-minute tick catches
   `≤68` and shuts it fully off. The room then free-heats back to 72. Result:
   the large 67↔72 sawtooth.

4. **No anti-short-cycle / minimum-runtime protection.** Per-room
   `timer.*_compressor_cooldown` helpers exist in `configuration.yaml:131–138`
   but are **referenced by no automation** — they are orphaned. Nothing damps
   re-engagement, and control is **15-minute tick-based**, so both overshoot
   directions are coarse.

**Net effect:** a sawtooth bounded by a too-high ceiling during cooling season,
then a hard outdoor-driven shut-off for the rest of the night during shoulder
season. `Night_Mode_Toggle`, `Away_Mode`, manual override, and the truth
sensors were **not** at fault (see §4, §5, §11).

---

## 2. Relevant files and entity IDs

### 2.1 Files (complete scope)
The only places control logic, templates, and helpers live:

| File | Role |
|---|---|
| `automations.yaml` | All 21 automations (Sections 1–15). |
| `configuration.yaml` | Template truth sensors, `timer:`, `input_boolean:`/`input_text:`/`input_datetime:`, `recorder`, `template`, `sensor`. |
| `Home Assistant (9).xlsx` | **Stale** local telemetry snapshot (ends 2026-06-05 15:00). |

Confirmed **absent** (so nothing was missed): no `scripts.yaml`, `packages/`,
`blueprints/`, `custom_components/`, `appdaemon/`, `pyscript/`. The Samsung
heads, SmartThings, `google_sheets`, Netatmo, Nest, and `default_config` are
config-entry / UI integrations (not in YAML).

### 2.2 Entity IDs

| Concept | Entity ID | Defined in repo? |
|---|---|---|
| Lincoln mini-split | `climate.lincoln_air` | device (integration) |
| Lilly mini-split | `climate.lilly_air` | device (integration) |
| Lincoln room truth | `sensor.lincoln_s_room_temperature_truth` | `configuration.yaml:451` |
| Lilly room truth | `sensor.lilly_s_room_temperature_truth` | `configuration.yaml:~643` |
| Lincoln truth contributor count | `sensor.lincoln_temperature_truth_active_count` | yes (exported) |
| Lilly truth contributor count | **none exported** (telemetry gap) | — |
| Outdoor/Deck truth | `sensor.deck_temperature_truth` | yes |
| Season mode | `input_select.hvac_season_mode` | **NOT in repo — live UI helper** |
| "Night_Mode_Toggle" | `input_boolean.night_mode_lr_primary` | **NOT in repo — live UI helper** |
| Away mode | `input_boolean.away_mode` | **NOT in repo — live UI helper** |
| Manual override timer | `timer.manual_hvac_override` | **NOT in repo — live UI helper** |
| Lincoln cooldown (orphaned) | `timer.lincoln_compressor_cooldown` (15 min) | `configuration.yaml:131` |
| Lilly cooldown (orphaned) | `timer.lilly_compressor_cooldown` (15 min) | `configuration.yaml:135` |
| Lincoln presence (debounced) | `binary_sensor.lincoln_presence_debounced_v3` | `configuration.yaml:203` |
| Lilly presence | **none** (Lilly has no presence sensor) | — |
| Supervisor automation | `automation.v7_5_main_supervisor` | `automations.yaml:358` |

> **Repo-lag flag:** `input_select.hvac_season_mode`, `input_boolean.away_mode`,
> `input_boolean.night_mode_lr_primary`, and `timer.manual_hvac_override` are
> **referenced by automations but not defined in the repo.** They are live UI
> helpers. In particular, **the manual-override window *duration* is not in Git**
> — it is whatever `timer.manual_hvac_override` is configured to in HAOS
> (documented elsewhere as ~1 hour). Codex must read these live (§15).

---

## 3. Full control-flow map (per room, identical for Lincoln & Lilly)

```
 3 room-probe transports (BT + ST + Matter, w=1.0 each)        Samsung internal
 + 3°F outlier rejection vs base-mean of the three            (low weight 0.20)
        │                                                              │
        └──────────────► sensor.<room>_room_temperature_truth ◄────────┘
                 (weighted avg; availability = ≥1 fresh source <2h;
                  if UNAVAILABLE → supervisor reads float(70) sentinel)
                                    │
                                    ▼
        ┌───────────────────────────────────────────────────────────────┐
        │ GATE 0: timer.manual_hvac_override == idle ?  (else: stand down)│
        └───────────────────────────────────────────────────────────────┘
                                    │ idle
                                    ▼
   Section 2 supervisor (automation.v7_5_main_supervisor)
   triggers: every 15 min  +  on input_select.hvac_season_mode change
                                    │
            ┌───────────────────────┼────────────────────────┐
        season=cooling          season=shoulder           season=heating
            │                       │                          │
   on>72 / off≤68 / hold      is_night(22–06)?            (kids force-off
   setpoint 61 (shove)         ├─ yes → KIDS FORCED OFF     in most paths)
   fan: (unset → turbo         │        (533–535) ✗no escape
        sticks)                └─ no  → warm path cools kids
            │                          only if outdoor>70 or LR>71
            ▼                          else kids OFF
        climate.set_temperature / climate.set_hvac_mode
                                    │
                                    ▼
                       Samsung mini-split head (climate.<room>_air)
```

**Independent safety / side-effect writers layered on top** (see §6):
Section 3 ceiling gate (>76 °F), Section 4 ghost assassin (Lincoln 01:20),
Section 6 destrat fan, Section 8 Samsung auto guardrail.

The **seasonal eligibility** step is the decisive fork: it is evaluated *before*
any per-room comfort decision, and in shoulder/heating it can veto the kids'
rooms entirely regardless of room truth.

---

## 4. Exact likely cause of last night's behavior (transition by transition)

All times approximate; cooling-season band = `ON>72 / OFF≤68 / cmd 61`.

| Time | Observed | Repo-derived cause |
|---|---|---|
| 21:00 | Both rooms **off**, temps low (~68 °F) and rising | Cooling season; both had cooled `≤68` earlier in the evening → deadband holds **off** until truth `>72`. |
| 22:45 | Lincoln → **cool** | `lincoln_temp` crossed `>72` → engage `cool @ 61 / turbo`. |
| 23:15 | Lilly → **cool** | `lilly_temp` crossed `>72` → engage. |
| 23:45 | Lincoln → **off** | 61/turbo shove overshot down to `≤68` → off. |
| 00:00 | Lilly → **off** | `lilly_temp ≤ 68` → off. |
| 00:00–02:00 | Lilly creeps to ~71–72, stays **off** | In cooling season OFF holds until truth `>72`. Lilly hovered just under the strict `>72` ON edge → never re-triggered. |
| 02:00 | Lincoln → **cool** | `lincoln_temp` crossed `>72` again → engage. |
| **02:45** | `Season_Mode`: **cooling → shoulder**; Deck ≈ 64.4 °F | Section 5 auto-season (`automations.yaml:919–951`): Deck in the `50–68 °F` band sustained 2 h → `shoulder`. The season change is **also a supervisor trigger**, so Section 2 re-runs immediately. |
| 02:45 → morning | Lincoln **off**; Lilly **off** to 08:30 | Now `shoulder` + `is_night` → shoulder-night branch **forces Lincoln & Lilly off** (`533–535`). No kids escape (Master has one). After 06:00, shoulder-**day** mild path also forces kids off unless `outdoor>70` or `LR>71` (Deck/LR stayed cool). Returning to `cooling` needs Deck `>72 °F` for 2 h (a daytime event) → kids stewed at 71–72 °F. |

**The 72.32 °F maxima** are the rooms sitting at/just over the `>72` ON edge.
For Lilly especially, the warm plateau is dominated by the post-02:45
shoulder-night force-off, **not** by a slow cool-down.

**One anomaly to verify (not explainable from the repo alone):** the operator
notes "Lincoln off 02:45–05:45," implying a Lincoln re-engagement near 05:45.
05:45 is still `is_night` in `shoulder`, where Section 2 force-offs Lincoln —
so a 05:45 cooling start should not come from Section 2. Candidates: a manual
override (parent intervention → WAF timer), a Samsung/SmartThings cloud push,
or the Section 3 ceiling gate (only if truth briefly `>76`). **Codex must pull
the 05:30–06:15 rows + Logbook to classify this** (§15).

---

## 5. Confirmed facts vs assumptions requiring live HAOS verification

### 5.1 Confirmed from the repo (YAML is runtime truth)
- Kids' cooling band is `ON>72 / OFF≤68`, command `61 °F`, **fan never set by
  Section 2** (`automations.yaml:438–471`).
- Shoulder-night **force-offs Lincoln & Lilly**; Master has an escape; this is
  **locked by tests** (`tests/test_supervisor_shoulder_night.py:126–136` requires
  Lincoln+Lilly in the bulk-off; `:101–123` give Master its escape).
- `61` shove and the `68/72` thresholds are **locked**
  (`tests/test_section2_shove_command_setpoints.py:136–164`).
- Auto-season thresholds: `>72/2h → cooling`, `<45/2h → heating`,
  `50–68/2h → shoulder` (`automations.yaml:919–938`).
- `Night_Mode_Toggle` = `input_boolean.night_mode_lr_primary`, used **only** in
  the heating-night branch (`automations.yaml:625`); **no weekday gating exists
  anywhere** (`is_night` is pure clock `hour>=22 or hour<6`).
- Manual-override gate is enforced on supervisor, ceiling gates, destrat, Samsung
  guardrail, boost-engage (`tests/test_manual_override_contract.py`).
- Truth sensor falls back to **`float(70)`** in the supervisor when unavailable
  (`automations.yaml:375–376`; documented in `comfort_failure_forensics.md`).
- Lilly has **no** presence sensor; Lincoln does
  (`binary_sensor.lincoln_presence_debounced_v3`).

### 5.2 Assumptions requiring live verification (Codex)
- **`turbo` origin.** No automation sets it. Assumed: a sticky manual/SmartThings
  fan setting that Section 2 never resets during cooling. **Verify** the live
  fan-mode history for both heads overnight and the **list of supported fan
  modes** (e.g., `turbo / high / auto / low / quiet`) before specifying a quiet
  value.
- **`timer.manual_hvac_override` duration** (override-window length) — not in Git.
- **`Supervisor_Enabled` blank.** The column maps to
  `automation.v7_5_main_supervisor` on/off → `true/false`, returning blank only
  when the entity is `unknown/unavailable` (`automations.yaml:314–316`). Blank in
  every row implies either the sub-block-15 columns were added to the export
  *after* this window, the worksheet header was misaligned at write time (the
  deployment warning at `automations.yaml:101–106`), or the entity_id diverged.
  **This is an observability defect to confirm/fix, not proof of anything about
  the cause.**
- **`Manual_Override_State`** overnight (task says "idle where recorded") and
  the exact **Lincoln/Lilly setpoint=61 / fan=turbo** rows — confirm directly in
  the live tab.
- That the live Section 2 matches the repo (no out-of-band live edits).

---

## 6. Overlapping automation / race-condition audit

**Every automation that can command `climate.lincoln_air` / `climate.lilly_air`:**

| # | Automation (id) | Trigger | Action on kids | Override-gated? | Race / loop notes |
|---|---|---|---|---|---|
| 1 | `v7_5_main_supervisor` (S2) | 15-min + season change | cool/off/heat + setpoint 61/79 | ✅ idle | Primary writer; command-on-every-tick (noisy but `mode: single`). |
| 2 | `v7_5_safety_ceiling_gates` (S3) | truth `>76 °F` | cooling: `cool@68` 45 min→off; else `fan_only` 45 min→off | ✅ idle | `mode: parallel`; its 45-min `delay` can **collide with the next S2 tick** — S2 may re-off or re-cool mid-delay. Only fires `>76` (didn't fire last night). |
| 3 | `v7_5_ghost_assassin` (S4) | 01:20 daily | Lincoln only: if `heat` & season≠heating → off | ❌ (not a comfort gate) | Narrow; harmless to cooling. Still an independent writer to Lincoln. |
| 4 | `v8_comfort_fan_destratification` (S6) | :07/:22/:37/:52 | heating/shoulder: `fan_only`+`fan auto`, or off | ✅ idle | Can set `fan_only` on a kid the supervisor wants `off`; releases on delta/time. Lincoln gated on **presence**; Lilly on **daytime** (no presence sensor) → mostly dormant overnight. |
| 5 | `v8_samsung_auto_guardrail` (S8) | hvac_action / `→auto` / every 10 min | force `off` on Samsung `auto`-mode misbehavior | ✅ idle | Only acts when head reports `auto`; another every-10-min writer; can off a head between S2 ticks. |
| — | WAF watcher `v7_5_waf_manual_override` (S3) | any non-automation change to a head | starts `timer.manual_hvac_override` | n/a | Does not command climate; **converts human edits into the override window** that gates #1,2,4,5. |

**Key race conclusions**
- **No duplicate comfort controller exists today** — Section 2 is the sole
  comfort writer. **Therefore the fix must stay *inside* Section 2** (or a new
  automation that is season/time-exclusive with it) to avoid creating the very
  "two automations issuing conflicting climate commands" failure the objective
  forbids. A second always-on cooling automation would race S2 every tick.
- The realistic overlap window is the **ceiling-gate 45-min `delay` vs. S2/S8
  ticks** (`>76 °F` only) and **S6 fan_only vs S2 off** in shoulder. Neither
  drove last night, but both must be respected by any change.
- The **season-change edge trigger** means a `Season_Mode` flip can re-mode a
  room *immediately*, even mid-cooling (exactly what happened at 02:45).

---

## 7. Minimal recommended implementation

Design principle: **smallest change, inside Section 2, that (a) stops the
outdoor-driven warm plateau and (b) stops leaving `turbo` running, then
optionally (c) tightens the band toward 70 °F.** Keep the 61 shove. Keep rooms
independent. Reuse existing helpers. Update the locked tests deliberately.

### Tier 1 — Contract-failure fixes (do first; low risk; precedented)

**A. Add a kids' shoulder-night cooling escape** (mirror the existing Master
escape at `automations.yaml:519–532`). Remove `climate.lincoln_air` and
`climate.lilly_air` from the shoulder-night bulk-off (`533–535`); give each a
per-room `cool/off/hold` decision. This is the single highest-value fix — it
directly ends Lilly's all-night warm period and Lincoln's post-02:45 warm
period, and it removes "outdoor temperature silently vetoes an occupied
bedroom." Independence preserved (separate per-room steps).

**B. Stop `turbo` from sticking.** In the kids' cooling engage path, explicitly
command a quiet fan (overnight) / auto (day) **whenever the room is commanding
`cool`**. Section 2 cooling currently sets `hvac_mode`+`temperature` but never
`fan_mode`; this is the missing half of the V8.3 "prevent turbo sticking" fix
that was only ever applied to Section 6 (`automations.yaml:72–73`). Reserve
`turbo` for the high-temp emergency path / existing `>76 °F` ceiling gate.

Tier 1 alone keeps the rooms from stewing and silences the all-night turbo,
**without touching the locked `68/72` cooling thresholds** (the escape uses new
variable names). It changes only the shoulder-night bulk-off test and the
cooling-command *count* (8 → 10), both at 61.

### Tier 2 — Overnight comfort-band retune (operator-requested; test- & evidence-gated)

**C. Tighten the kids' *overnight* band toward 70 °F** — `ON>71 / OFF≤69.5`
during a sleep window (e.g., 21:00–07:00), leaving the daytime `68/72` band
unchanged. This is what actually holds "near 70" instead of floating to 72. It
**edits the test-locked threshold strings** and is, per project doctrine, a
**deadband change** (`comfort_failure_forensics.md` §10; `v9_v10_goals.md` §10)
— a single night is a forensic input, not yet repeated evidence. Recommend
shipping Tier 1 immediately and Tier 2 as a clearly-labeled deadband PR
(validated over a few nights, or accepted explicitly as an operator preference
override of the "needs repeated evidence" rule).

**D. Anti-short-cycle via the *existing* orphaned cooldown timers.** Wire
`timer.lincoln_compressor_cooldown` / `timer.lilly_compressor_cooldown` (already
defined, 15 min) so that after an OFF the room cannot re-engage `cool` until the
timer is `idle` (minimum-off), and enforce a minimum-on before an OFF. This
damps the extra cycling a tighter band would otherwise add. Reuses existing
helpers (observability requirement) instead of inventing new ones.

### Tier 3 — Optional structural (only if Tier 1+2 prove insufficient)

**E. Event-based crossings.** Add `numeric_state` triggers on
`sensor.<room>_room_temperature_truth` (`above: on_at, for: 5m` /
`below: off_at, for: 5m`) so crossings are acted on promptly between 15-min
ticks, with the cooldown timers (D) providing hysteresis. This removes the
"15-minute polling dependency" the objective calls out. Larger blast radius;
defer until evidence shows the tick latency still matters after A–D.

---

## 8. "From → To" change table

| # | Item | From (live/repo today) | To (proposed) | Touches locked test? |
|---|---|---|---|---|
| A | Shoulder-night kids | `lincoln_air`,`lilly_air` in unconditional bulk-off (`533–535`) | Per-room `cool/off/hold` escape; only `dining_room` stays in bulk-off | **Yes** — `test_supervisor_shoulder_night.py` (mirror Master change) + cooling-command count 8→10 in `test_section2_shove_command_setpoints.py` |
| B | Kids cooling fan | never set → `turbo` sticks | `fan_mode` quiet/`low` overnight, `auto` daytime, set only while `cool`; `turbo` reserved for ≥ emergency | No (adds `set_fan_mode`, not `set_temperature`) — confirm fan-mode names live |
| C | Kids overnight band | `ON>72 / OFF≤68` all hours | `ON>71 / OFF≤69.5` during 21:00–07:00; day unchanged | **Yes** — update `l_off_at/l_on_at/ly_off_at/ly_on_at` asserts |
| C | Kids setpoint cmd | `61` (shove) | `61` (unchanged) | No |
| D | Anti-short-cycle | cooldown timers defined but unused | min-off (timer idle) + min-on gate on engage/disengage | New tests recommended (none locks this today) |
| E | Control cadence | 15-min tick + season edge | + event-based truth crossings (`for: 5m`) | New tests recommended |
| — | Season authority | outdoor Deck temp can veto kids overnight | unchanged thresholds; A restores indoor comfort escape | No |
| — | Observability | `Supervisor_Enabled`/`Manual_Override_State` blank | confirm worksheet header / entity_id; add kids escape engage/release reason helpers | telemetry only |

---

## 9. Proposed YAML / template changes (illustrative — DO NOT APPLY HERE)

> These are reference shapes for Codex to adapt against the **live** Section 2.
> Exact fan-mode strings, the sleep-window hours, and band numbers are
> live-tunable. Codex must re-derive line numbers from the live file.

### 9.A Shoulder-night kids cooling escape (replaces `automations.yaml:533–535`)

```yaml
                    # --- Kids shoulder-night cooling escape -------------------
                    # Mirrors the Master escape above (commit e00013d shape).
                    # Outdoor/season must not leave an occupied child's bedroom
                    # above the overnight comfort limit. Rooms stay independent.
                    # Safety ceiling (>76°F, Section 3) is unchanged & separate.
                    - variables:
                        kids_on_at:  "{{ 76 if away else 71 }}"
                        kids_off_at: "{{ 74 if away else 69.5 }}"
                        kids_setpoint: "{{ 61 }}"           # locked shove command
                        l_current:  "{{ states('climate.lincoln_air') }}"
                        ly_current: "{{ states('climate.lilly_air') }}"
                    - action: climate.set_temperature
                      target: { entity_id: climate.lincoln_air }
                      data:
                        hvac_mode: >-
                          {% if lincoln_temp > kids_on_at %}cool
                          {% elif lincoln_temp <= kids_off_at %}off
                          {% elif l_current == 'cool' %}cool
                          {% else %}off{% endif %}
                        temperature: "{{ kids_setpoint }}"
                    - action: climate.set_temperature
                      target: { entity_id: climate.lilly_air }
                      data:
                        hvac_mode: >-
                          {% if lilly_temp > kids_on_at %}cool
                          {% elif lilly_temp <= kids_off_at %}off
                          {% elif ly_current == 'cool' %}cool
                          {% else %}off{% endif %}
                        temperature: "{{ kids_setpoint }}"
                    # Nest stays unconditionally off in shoulder-night.
                    - action: climate.set_hvac_mode
                      target: { entity_id: climate.dining_room }
                      data: { hvac_mode: "off" }
```

### 9.B Quiet-fan command in the cooling engage path (kids; Section 2 cooling branch and 9.A)

```yaml
            # Never leave turbo running all night. Set a quiet fan only while the
            # head is actually cooling. Verify supported fan_mode names live.
            - choose:
                - conditions: "{{ is_state('climate.lincoln_air', 'cool') }}"
                  sequence:
                    - action: climate.set_fan_mode
                      target: { entity_id: climate.lincoln_air }
                      data: { fan_mode: "{{ 'low' if is_night else 'auto' }}" }
            - choose:
                - conditions: "{{ is_state('climate.lilly_air', 'cool') }}"
                  sequence:
                    - action: climate.set_fan_mode
                      target: { entity_id: climate.lilly_air }
                      data: { fan_mode: "{{ 'low' if is_night else 'auto' }}" }
```

### 9.C Overnight band (kids cooling-season variables; replaces `automations.yaml:439–441,459–461`)

```yaml
            # Lincoln (Lilly identical with ly_*). Day band unchanged (68/72);
            # overnight band centers on the 70°F sleep target.
            - variables:
                l_setpoint: "{{ 61 }}"
                l_off_at: "{{ 74 if away else (69.5 if is_night else 68) }}"
                l_on_at:  "{{ 76 if away else (71   if is_night else 72) }}"
                l_current: "{{ states('climate.lincoln_air') }}"
```

### 9.D Anti-short-cycle latch (reusing existing cooldown timers)

```yaml
            # Engage only if min-off satisfied; start cooldown on disengage.
            # Add to the cool/off decision:  ... and is_state(
            #   'timer.lincoln_compressor_cooldown', 'idle')  for re-engage.
            # On transition cool->off:  timer.start lincoln_compressor_cooldown.
            # (Implement as a small choose around the existing set_temperature
            #  so deadband "hold" is preserved. Mirror for Lilly.)
```

### 9.E Observability (reuse existing patterns)
- Add `input_text` + `input_datetime` engage/release-reason helpers for the kids
  escape, mirroring the Section 14 boost helpers (`configuration.yaml:1166–1188`),
  and extend the Section 15 provenance logger (`automations.yaml:1754+`) or the
  v5.5 export so every kids engage/release records **temperature, season,
  manual-override state, and triggering rule**.
- Fix the blank `Supervisor_Enabled` / `Manual_Override_State` columns (verify the
  live worksheet header includes sub-block-15 and the entity_id resolves).
- Add a `Lilly_Truth_Count` export column to match `Lincoln_Truth_Count`.

---

## 10. Safety and anti-short-cycle behavior

- **Independent safety stays untouched.** LR runaway `<60 °F` (`737–762`), Master
  floor `<58 °F` (`778–801`), and the `>76 °F` ceiling gates (`810–856`) are not
  modified and must **not** gate on manual override (locked by
  `test_manual_override_contract.py`). The kids' comfort band must never alias a
  safety floor (Doc 1 §5.1).
- **Anti-short-cycle = reuse the orphaned per-room cooldown timers** (15 min):
  minimum-off before re-engage, minimum-on before disengage. This is the
  project-blessed way to "reduce compressor short-cycling" (AGENTS.md goals)
  without new helpers.
- **Sustained crossing:** Tier 3 uses `for: 5m` on truth crossings so a transient
  spike does not engage. Until then, the 15-min tick is itself a coarse debounce.
- **Emergency fan path only:** `turbo` allowed only at/above an emergency
  threshold (or via the existing `>76 °F` ceiling gate), never as the default
  overnight fan.

---

## 11. Manual override behavior (must remain authoritative)

- **Mechanism (confirmed):** `v7_5_waf_manual_override` (`858–881`,
  `mode: restart`) fires on any change to a head's `state` or `temperature`
  attribute **whose `trigger.context.parent_id is none`** (i.e., a human / app /
  cloud change, not an automation). It starts `timer.manual_hvac_override`.
- **Effect (confirmed, test-locked):** while that timer is `active`, Section 2,
  the ceiling gates, destrat, the Samsung guardrail, and boost-engage all
  **stand down** (they require `state: idle`). True safety gates ignore it.
- **Expiration (route to live):** the timer runs for its configured duration
  (**not in Git**; documented as ~1 h). On expiry → `idle` → the next 15-min
  supervisor tick re-applies policy (the `comfort_failure_forensics.md` §8.1
  "supervisor overwrite" signature). This is *by design*: the supervisor does
  not undo a parent's change *during* the window, only after it lapses.
- **Plan compliance:** because all proposed changes live **inside Section 2**
  (or, for E, a new automation that must also carry `state: idle`), the override
  contract is inherited automatically. **Do not add any kids automation that
  omits the `timer.manual_hvac_override == idle` gate** (Regression Appendix
  §4.15). If E is implemented as a new automation, extend
  `test_manual_override_contract.py` to assert it gates on idle.

---

## 12. Seasonal shoulder-mode behavior

- **Does shoulder block/delay bedroom cooling?** Yes — today it **forces the
  kids off** at night and on the mild/cold day paths (`comfort_failure_forensics.md`
  bulk-off table). Only the warm day path (`outdoor>70 or LR>71`) cools kids.
- **Does outdoor temp override indoor comfort?** Yes — `Season_Mode` is driven
  purely by Deck truth (Section 5), and the season then vetoes the kids. The plan
  treats this as the regression named in Doc 1 §7 / Appendix §4.16: outdoor is an
  input, not a meta-authority. **Fix A restores an indoor over-temperature escape**
  without changing the season thresholds (so seasonal control for LR/Master/Nest
  is untouched).
- **Special rule for occupied/sleeping bedrooms?** Master already has one
  (shoulder-night escape). The kids do not — A adds it. (Lilly has no presence
  sensor, so the escape is time-of-night based, not presence-based; Lincoln may
  optionally add presence later, but presence must not be a *new fragile
  dependency* — default to cooling the room when presence is unknown.)
- **Can `Season_Mode` change while a room is actively cooling?** Yes — the season
  change is a supervisor trigger; that is exactly the 02:45 force-off. With A in
  place, a `→shoulder` flip at night hands the kids to the escape (cool/off/hold)
  rather than an unconditional off.
- **Does `→shoulder` force `climate.turn_off`?** Today: yes (`set_hvac_mode off`).
  After A: only when the room is at/below `kids_off_at`.

---

## 13. Validation procedure (for Codex, post-change, live)

1. **Static:** `python -m pytest tests/` — all green, including the updated
   `test_supervisor_shoulder_night.py` and `test_section2_shove_command_setpoints.py`.
   Confirm `61` shove and `58/60` safety floors still asserted.
2. **Config check:** `ha core check` (or Developer Tools → YAML check) before reload.
3. **Dry trace:** Developer Tools → Template, paste the new hvac_mode templates with
   representative `lincoln_temp/lilly_temp/away/is_night` values; confirm
   cool/off/hold transitions at 71 / 69.5.
4. **Forced shoulder-night test:** with override idle, set `input_select.hvac_season_mode`
   to `shoulder` during 22:00–06:00 with a kid's truth >71 °F; confirm the head
   goes/stays `cool @ 61` with the quiet fan, and that the **other** child is
   unaffected (independence). Confirm Master + LR + Nest behavior unchanged.
5. **Override test:** manually nudge a kid's setpoint; confirm
   `timer.manual_hvac_override` goes `active` and the supervisor stands down for
   the window, then reasserts on expiry.
6. **Overnight telemetry:** capture 2–3 nights in `VTherm_Launch_Data_v5_5`; verify
   max kids truth ≤ ~71.5 °F, no `turbo` rows overnight, cycle count per room is
   not higher than baseline (cooldown timers working), and no ceiling-gate fires.
7. **Compare to baseline:** the June 5–6 window is the "before"; quantify
   reduction in time-above-71 and in off↔cool transitions.

---

## 14. Rollback procedure

- All changes are confined to `automations.yaml` Section 2 (+ optional
  `configuration.yaml` helper wiring for D/E and the test files). **Rollback =
  `git revert`/restore the prior `automations.yaml` (+ tests)** and reload
  automations; no entity renames, no truth-layer changes, so no migration.
- Because Git may lag live, Codex should **snapshot the live `automations.yaml`
  Section 2 and the live helper definitions before editing** (commit them first
  so the repo matches live), then apply changes on top — so rollback returns to
  the *actual* prior live state, not a stale repo state.
- The orphaned cooldown timers (D) and any new reason-helpers (E) are additive;
  removing their references restores prior behavior. If a new automation is used
  for E, disabling that single automation is an instant partial rollback.
- Safety gates are untouched, so rollback never affects equipment protection.

---

## 15. Specific live automation traces Codex must inspect

1. **02:45 season flip:** trace `automation.v7_5_auto_season_mode` and
   `automation.v7_5_main_supervisor` around 02:30–03:00 June 6. Confirm the
   `cooling→shoulder` `select_option` and the supervisor re-run that issued the
   kids `off`. Confirm Deck truth value at the flip.
2. **05:45 Lincoln anomaly:** pull `VTherm_Launch_Data_v5_5` rows 05:15–06:30 +
   HA Logbook + (if present) `hvac_provenance_log`/`supervisor_state_log` for
   `climate.lincoln_air`. Classify the re-engage origin (manual / cloud / ceiling
   gate / supervisor). This decides whether the 05:45 event is in scope.
3. **`turbo` provenance:** Logbook/history for `climate.lincoln_air` and
   `climate.lilly_air` `fan_mode` for the whole night — when/by whom was `turbo`
   last set, and did any automation touch it. Confirm supported fan-mode names.
4. **Manual-override timer:** read the live `timer.manual_hvac_override`
   definition (duration, `restore`) and any `active` windows overnight
   (`Manual_Override_State` / `_Remaining_Sec` columns).
5. **`Supervisor_Enabled` blank:** verify `automation.v7_5_main_supervisor`
   exists/`on`, and that the live worksheet header row includes the sub-block-15
   columns in order (deployment warning `automations.yaml:101–106`).
6. **Ceiling-gate non-fire:** confirm neither kid's truth hit `>76 °F` (so the
   45-min ceiling delay did not interact with S2).
7. **Live helper existence:** confirm `input_select.hvac_season_mode`,
   `input_boolean.away_mode`, `input_boolean.night_mode_lr_primary`, and
   `timer.*_compressor_cooldown` exist live and match this plan's assumptions.
8. **Section 2 parity:** diff live Section 2 against repo `automations.yaml` to
   ensure no out-of-band live edits before applying changes.

---

## 16. Copy-paste Codex implementation prompt

> Paste the block below to Codex inside HAOS. It is scoped to the **minimal
> Tier-1 fix first**, with Tier-2/3 gated behind explicit confirmation.

```
ROLE: You are modifying the LIVE Moose House Home Assistant config inside HAOS.
The Git repo may lag live. LIVE YAML + live traces are source of truth. Read
docs/kids-bedroom-overnight-cooling-plan.md before doing anything.

GOAL: Keep Lincoln's and Lilly's rooms near 70°F overnight without the 67→72
sawtooth, hours-long warm periods, turbo-all-night, rapid cycling, fighting the
Section 2 supervisor, breaking seasonal control, ignoring manual override, or
adding a second conflicting climate writer.

STEP 0 — VERIFY LIVE (do not skip; report findings before editing):
  1. Confirm there is NO Versatile Thermostat integration; the controller is
     automation.v7_5_main_supervisor (Section 2).
  2. Snapshot live automations.yaml Section 2 + live helper defs
     (input_select.hvac_season_mode, input_boolean.away_mode,
     input_boolean.night_mode_lr_primary, timer.manual_hvac_override,
     timer.lincoln_compressor_cooldown, timer.lilly_compressor_cooldown). Commit
     them so the repo matches live BEFORE changing anything.
  3. List supported fan_mode values for climate.lincoln_air and climate.lilly_air.
  4. Pull VTherm_Launch_Data_v5_5 rows 2026-06-05 21:00 → 2026-06-06 08:30 and
     classify the 05:45 Lincoln event and the turbo fan origin (see plan §15).

STEP 1 — TIER 1 (implement, then run pytest, then ha core check, then reload):
  A. In Section 2 shoulder-night sub-branch, REMOVE climate.lincoln_air and
     climate.lilly_air from the unconditional bulk-off and ADD a per-room
     cool/off/hold cooling escape mirroring the existing Master escape
     (plan §9.A). Keep setpoint 61. Keep dining_room in the bulk-off. Keep the
     two rooms independent (separate steps).
  B. In the kids' cooling engage paths (cooling-season branch AND the new
     shoulder-night escape), set a quiet fan while the head is 'cool'
     (low overnight / auto by day; turbo only for emergency). Never leave turbo
     as the overnight default (plan §9.B).
  C. Update the locked tests to match: in tests/test_supervisor_shoulder_night.py
     change the "bulk-off still covers lincoln/lilly" expectation to dining-only
     and add kids-escape-exists + kids-excluded-from-bulk-off tests (mirror the
     Master tests). In tests/test_section2_shove_command_setpoints.py update the
     cooling-command count (8 -> 10) and assert the two new kids escape commands
     are at 61. Do NOT weaken the 61 shove or the 58/60 safety asserts.

STEP 2 — TIER 2 (only after I confirm Tier 1 looks good for 2-3 nights):
  D. Tighten the kids OVERNIGHT band to ON>71 / OFF<=69.5 for 21:00-07:00,
     leaving the daytime 68/72 band unchanged (plan §9.C); update the locked
     threshold asserts. Frame as a deadband change.
  E. Wire timer.lincoln_compressor_cooldown / timer.lilly_compressor_cooldown for
     minimum-off (block re-engage until idle) and minimum-on (plan §9.D); add tests.

STEP 3 — OBSERVABILITY: add kids escape engage/release reason helpers (mirror
  Section 14), record temperature+season+override-state+rule on every engage/
  release, add a Lilly_Truth_Count export column, and fix the blank
  Supervisor_Enabled / Manual_Override_State columns (plan §9.E).

CONSTRAINTS:
  - Every comfort/destrat/guardrail automation MUST keep the
    timer.manual_hvac_override == idle gate. Safety floors (58/60) MUST NOT gate
    on override. Do not introduce arbitration/comfort_profiles/MSR into the
    supervisor (locked by tests).
  - Do not rename entities, collapse sections, or remove telemetry/safety.
  - Make NO change without STEP 0 verification. If anything live contradicts the
    plan, STOP and report instead of inventing behavior.

VALIDATE: python -m pytest tests/ ; ha core check ; reload automations ; run the
plan §13 live checks ; capture 2-3 nights of telemetry and compare to the
June 5-6 baseline (time-above-71 and off<->cool transition count per room).

ROLLBACK: git revert the Section 2 + test changes and reload (plan §14). No
entity/truth migrations are involved.
```

---

### Appendix — doctrine alignment notes
- This plan follows `comfort_failure_forensics.md`: it reconstructs the window,
  names the failure modes (§8.5/§8.6-adjacent: season branch overruled comfort;
  plus the deadband-ceiling and stuck-actuator-fan modes), and recommends the
  **smallest targeted fix** rather than a redesign.
- It does **not** re-propose any retired approach (Doc 1 §7): no presence-as-master
  governor, no premature arbitration, no isolation-first rewrite, no offset
  stacking. The shoulder-night escape is the already-blessed Master shape applied
  to the kids.
- It keeps comfort logic and safety logic separate, keeps the 61 shove doctrine,
  and treats outdoor/season as an input — not an authority over an occupied
  child's bedroom.
