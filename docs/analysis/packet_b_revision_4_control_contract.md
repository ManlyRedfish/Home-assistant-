# Packet B — Revision 4: Control Contract Reconciliation

```
═══════════════════════════════════════════════════════════════
PACKET B — REVISION 4
Moose House HVAC — Cooling Control Contract + Shadow Evidence MVP
═══════════════════════════════════════════════════════════════

Status:   CANONICAL Packet B design. Supersedes:
          - PR #140 (docs/analysis/packet_b_rev3_shadow_evidence_mvp.md)
            → SUPERSEDED in full.
          - PR #139 Document 2 (docs/analysis/packet_b_shadow_evidence_mvp.md)
            → decision model (§4) and schema (§5) REVISED by this document;
              isolation guarantees (§6–§7), recorder rules (§5.5), and
              documentation corrections (§8) are CARRIED FORWARD unchanged.
Bundle:   The Hermes air-gapped Codex implementation bundle generated from
          the PR #139/#140 design is REVOKED. See §10.
Routing:  The final raw-versus-filtered routing decision REMAINS BLOCKED
          (PR #138 §3.4 gate; PR #139 Document 1 review stands).
Date:     2026-06-10
Operator: Cooling-contract matrix dictated 2026-06-10 (this document
          encodes it; see AGENTS.md "Current Operator Decisions" doctrine
          introduced in PR #134).
═══════════════════════════════════════════════════════════════
```

---

## 0. Why the implementation bundle was paused

Packet B's purpose is unchanged and narrow: **determine whether the supervisor
should evaluate the same cooling policy using raw room truth or filtered room
truth.** Packet B does not own the comfort policy. But a shadow evaluator can
only produce meaningful raw-versus-filtered evidence if the policy it mirrors
is the *actual* operator-approved policy, evaluated with the *actual* state
semantics. The PR #139/#140 Shadow Evidence design fails that bar in five
specific ways:

1. **Omits the approved Lincoln/Lilly bedtime contract.** PR #134 (operator
   decision 2026-06-07) defines a 66–70 °F bedtime deadband with `cool/61/turbo`
   for the kids' rooms, 18:00–07:00, in cooling and shoulder seasons. The
   Rev 3 decision function (§4.1) evaluates the kids on the legacy 68/72 band
   at all hours. Any divergence statistics collected against the wrong kids'
   policy are unusable for the rooms where divergence matters most.
2. **Invents a Living Room night band that exists nowhere.** Rev 3 §4.1
   contains `elif zone == lr and night_mode_lr: on_at = 72, off_at = 64`.
   No such cooling band exists in `automations.yaml`, in any merged PR, or in
   any operator decision. The live `input_boolean.night_mode_lr_primary`
   helper currently affects only the heating-season night branch. The
   operator-approved LR night cooling profile is the 74–76 conservation
   deadband (§1, profile P4) — not 64/72.
3. **No independent controller-call memory per input path.** Rev 3 computes
   "hold" for *both* the raw and filtered hypothetical paths from the live
   head's reported HVAC mode. The live head reflects raw-path actuation
   history, so the filtered hypothetical is contaminated by the raw path:
   the two paths can never accumulate persistent state divergence, which is
   precisely the phenomenon the §3.4 gate needs to observe. The head's
   reported state was silently treated as reliable controller memory.
4. **Conflates or omits the four distinct actuator facts.** The schema records
   no commanded setpoint, no requested fan mode, no head-reported fan mode,
   and no `hvac_action` (firing) state. It cannot distinguish controller call
   → head mode → fan mode → compressor firing, so it cannot attribute
   divergence to decision logic versus actuation behavior.
5. **Away-mode precedence is incomplete.** Rev 3 models away only as a
   threshold substitution in the cooling branch. The live shoulder-season
   daytime cooling path ignores `input_boolean.away_mode` entirely (a live
   gap, see §5 CHANGE-4), and Rev 3 neither models nor flags this.

Consequence: the air-gapped Codex bundle generated from that design **must not
be deployed**. It is revoked (§10). Implementation is re-staged: Stage 0 lands
the correct cooling contract in the live supervisor; Stage 1 lands the shadow
evaluator that mirrors it exactly.

**This document modifies no runtime YAML.** It is the corrected architecture
and implementation handoff.

---

## 1. Final profile / precedence matrix

### 1.1 Authoritative inputs

| Source | Authority |
|---|---|
| PR #126 (merged) | Actuator shove doctrine: cooling command setpoint **61 °F**, heating command setpoint **79 °F**. Comfort thresholds are separate from actuator setpoints. |
| PR #134 (open, authoritative decision record) | Lincoln/Lilly bedtime contract: 18:00–07:00, cooling + shoulder, engage ≥ 70 °F, release ≤ 66 °F, hold through deadband, `cool/61/turbo`, rooms independent, season flip must not interrupt an active pull-down. |
| Live `automations.yaml` Section 2 | Master sleep band 18:00–06:00 (> 66 engage / ≤ 62 release); daytime > 72 / ≤ 68; away > 76 / ≤ 74; HVAC-mode-as-memory hysteresis; 61 °F shove on all cooling commands. |
| Operator matrix 2026-06-10 (this document) | Global away precedence; LR night conservation profile (74–76 via `night_mode_lr_primary`, **without** setting the away helper); **turbo on every cooling call**; explicit deadband/state-machine semantics; capability preflight requirement. |

### 1.2 Precedence (evaluated top to bottom, per zone, per tick)

```
P-1  Section 3 safety gates            — independent automations; always win;
                                          never modeled as comfort policy.
P0   Manual override                   — timer.manual_hvac_override != idle
                                          → supervisor abstains entirely
                                          (existing condition gate; unchanged).
P1   Global away                       — input_boolean.away_mode == on
                                          → overrides every occupied/night
                                          profile for all controlled zones.
P2   Master night                      — Master only, 18:00–06:00, not away.
P3   Kids bedtime                      — Lincoln & Lilly independently,
                                          18:00–07:00, not away,
                                          season ∈ {cooling, shoulder}.
P4   LR night conservation             — Living Room only, not away,
                                          input_boolean.night_mode_lr_primary == on.
P5   Daytime default                   — any controlled zone with no active
                                          night profile, not away.
```

A zone selects exactly one profile per evaluation. "Controlled zones" for the
cooling contract = the four Samsung heads (`climate.living_room_air`,
`climate.master_bedroom_air`, `climate.lincoln_air`, `climate.lilly_air`).
The Nest (`climate.dining_room`) is not a cooling actuator: it remains
forced off during cooling season and is outside the 61/turbo contract.

### 1.3 Profile matrix (room-truth switching thresholds — NOT head setpoints)

| # | Profile | Zone(s) | Window / trigger | Engage (call ON) | Release (call OFF) | Between thresholds | Command while called |
|---|---|---|---|---|---|---|---|
| P1 | Away | all 4 heads | `away_mode` on | truth **> 76** | truth **≤ 74** | preserve prior call | `cool` / **61 °F** / **turbo** |
| P2 | Master night | Master | 18:00–06:00 | truth **> 66** | truth **≤ 62** | preserve prior call | `cool` / 61 / turbo |
| P3 | Kids bedtime | Lincoln, Lilly (independent) | 18:00–07:00, cooling + shoulder | truth **≥ 70** | truth **≤ 66** | preserve prior call | `cool` / 61 / turbo |
| P4 | LR night | Living Room | `night_mode_lr_primary` on | truth **> 76** | truth **≤ 74** | preserve prior call | `cool` / 61 / turbo |
| P5 | Daytime | any without night profile | default | truth **> 72** | truth **≤ 68** | preserve prior call | `cool` / 61 / turbo |

Comparator notes (exact, intentional):

- P3 uses **≥ 70 / ≤ 66** per the PR #134 operator wording ("at 70 °F or
  above" / "at 66 °F or below"). All other profiles use strict `>` engage and
  `≤` release, matching the live Section 2 templates.
- The numbers 74/76 (P1, P4), 62/66 (P2), 66/70 (P3), 68/72 (P5) are
  **room-truth switching thresholds**. The head is never commanded to these
  values. The only cooling temperature ever sent to a head is **61 °F**
  (PR #126 shove doctrine).
- P4 vs P1: identical numbers, distinct profiles. P4 is an **occupied
  nighttime conservation profile** — it must NOT turn on, depend on, or be
  recorded as the global away helper. The shadow schema records them as
  distinct `profile_selected` values.
- P4 has no clock window: the helper itself is the night signal,
  operator-managed. No new schedule, helper, or automation is introduced.

### 1.4 Season eligibility layer

The profile matrix defines *what the deadband is* when a zone is evaluated
for cooling. Season (plus, in shoulder, outdoor conditions) defines *whether
a zone is evaluated for cooling at all*:

| Season | Cooling evaluation |
|---|---|
| `cooling` | All zones, all profiles, every tick. |
| `shoulder` | **P3 always** (the kids' bedtime block is season-independent across cooling/shoulder — this is what makes a `cooling→shoulder` flip unable to interrupt an active pull-down). Master night escape (P2/P1) during the night sub-branch (existing). Daytime bedroom cooling only under the existing warm-eligibility gate (`outdoor > 70 or lr_temp > 71`), using P5/P1 (see §5 CHANGE-3/4). LR cooling remains ineligible in shoulder (existing structure: LR is heat-or-off in shoulder). |
| `heating` | No cooling calls. P3 is inactive in heating season (PR #134 scope). The LR night helper retains its existing heating-season meaning, untouched by this contract. |

Heating-season behavior, Nest behavior, Section 6 destratification, Sections
7/7B solar logic, and Section 14 are entirely outside this contract and are
unchanged.

---

## 2. Exact hysteresis state-machine semantics

### 2.1 The state machine

Do not describe the upper/lower values as setpoints. Each zone carries one
bit of controller state:

```
controller_call ∈ { off, cool }          (per zone)

At each supervisor evaluation (15-min tick, season-mode change, or HA start):

  profile  = select_profile(zone, away, clock, helpers, season)   # §1
  if zone not cooling-eligible this tick (§1.4): no cooling transition.
  T        = room truth (raw today; the input path is Packet B's question)

  if controller_call == off:
      controller_call' = cool   if T ⟨engage-compare⟩ on_at(profile)
                       = off    otherwise
  else:  # controller_call == cool
      controller_call' = off    if T ⟨release-compare⟩ off_at(profile)
                       = cool   otherwise

Outputs (every evaluation, idempotent):
  controller_call' == cool → command hvac_mode: cool,
                                     temperature: 61,
                                     fan: turbo            (§4)
  controller_call' == off  → command hvac_mode: off
```

Equivalent formulation (what the live Jinja templates implement):
`engage-check first, release-check second, else preserve prior call`. Because
`on_at > off_at` in every profile, the two formulations are identical. The
upper threshold is only consulted when the call is off; the lower threshold
only when the call is cool; between them the prior call is preserved.

### 2.2 The four distinct facts (never to be conflated again)

| # | Fact | Where it lives | Semantics |
|---|---|---|---|
| 1 | **Controller cooling call** | Decision state of the supervisor (today: proxied by head mode; see §3) | What the policy decided. The hysteresis memory. |
| 2 | **Head-reported HVAC mode** | `states('climate.<zone>')` | What the head claims it was told (`cool`/`off`/`fan_only`/`auto`…). Subject to cloud lag, manual input, Samsung internal behavior. |
| 3 | **Head-reported fan mode** | `state_attr('climate.<zone>', 'fan_mode')` | Whether turbo/powerful is actually engaged. Never assumed; verified by preflight (§4). |
| 4 | **Actual compressor firing** | `state_attr('climate.<zone>', 'hvac_action')` (`cooling`/`idle`/`off`) | Telemetry. **Not** automatically the deadband-memory source — a satisfied head idles while the call is still active. |

Known errata recorded here (observability fix, not Stage 0 scope): the
`binary_sensor.*_heat_pump_firing` sensors in `configuration.yaml` Section 2
are head-**mode**-based (`not in ['off','unavailable','unknown']`), not
`hvac_action`-based. They measure "head engaged," not "compressor firing."
Stage 1 records `hvac_action` directly and does not rely on them; renaming or
correcting them is a separate observability task.

### 2.3 Threshold/command separation invariant

`on_at`/`off_at` decide ON/OFF against room truth. The Samsung head receives
**61 °F** so it pulls decisively (PR #126: moderate setpoints scale back
prematurely and can run ~18 h without pulling the room down). The room is
never supposed to reach 61 °F — the unit runs only from band-exit until
band-return, and Section 3 floors (58/60 °F) backstop equipment runaway
independently.

---

## 3. Controller-call memory recommendation

### 3.1 Options evaluated

**Option M1 — HVAC-mode-as-memory (current).** `controller_call` is read back
from `states('climate.<zone>')`. No new entities.

- Failure modes: cloud/SmartThings command lag makes the read-back stale for
  up to one tick (self-heals, because the command is reasserted every tick);
  a `fan_only` state from Section 6 reads as "not cool" (correct: those heads
  were off, eligible for destratification); after a manual-override window
  expires, the head's manually-set state *becomes* the memory (acceptable —
  it preserves the human's last intent until a threshold crossing); Samsung
  `auto` mode reads as "not cool" (Section 8 guardrail polices auto
  independently).
- Property worth keeping: degraded reads fail toward `off`, which is the safe
  direction, and every tick's full reassertion bounds any divergence between
  intent and device to one 15-minute tick.

**Option M2 — Controller-owned call latch.** Per-zone helper
(`input_boolean.<zone>_cooling_call` or equivalent) written by Section 2 and
read back as memory.

- Honest controller state, immune to head lag and manual contamination.
- Costs: new helpers + new writes from Section 2 (violates the "no new
  controller/helpers" boundary the operator set in PR #134); a second state
  that can desync from the device (latch says cool, head off) and therefore
  needs reconciliation logic and its own failure analysis; rollback now has
  state migration (orphaned helpers); every existing Section 2 test and the
  manual-override contract analysis must be redone.

### 3.2 Recommendation

**Stage 0 keeps Option M1 for the live controller. Stage 1 gives each shadow
path its own latch (M2-style) as read-only template state. Promotion of a
controller-owned latch for the live path is deferred to V9 and gated on
Stage 1 evidence.**

Rationale:

- The 61 °F shove plus per-tick reassertion makes M1's error bounded and
  self-healing; no live failure attributable to M1 memory loss is in
  evidence. Changing live state semantics *while also changing profiles*
  (Stage 0) would confound the Packet B measurement.
- The shadow evaluator **cannot** use M1 for its hypothetical paths at all
  (§0 defect 3). It gets latched call state per path by construction (§6).
- Stage 1's schema records, per tick, whether the M1 proxy
  (head-reported mode) agrees with the raw-path latch when the supervisor is
  ungated. That **measures the actual M1 error rate** — the exact evidence a
  V9 "explicit controller-state latches" decision (already an AGENTS.md
  known future goal) needs. Decision rule: if M1-proxy disagreement with the
  raw latch exceeds 1% of ungated ticks over the evidence window, propose the
  controller-owned latch as its own PR with its own rollback; otherwise M1
  stands.

Rollback / failure behavior:

- Stage 0 (M1): no new state → rollback is `git revert` + reload (§9.1).
  Failure behavior unchanged from today: unavailable head state reads as
  not-cool → call falls to off → reasserted off command (safe direction).
- Stage 1 latches: template entities only; removing Section 16 removes them.
  On restart, trigger-based template sensors restore their last state; if a
  latch is `unknown`/`unavailable` (first boot, new install), the evaluator
  seeds it from the engage/release comparison alone (stateless evaluation for
  that tick) and flags the record `memory_warmup: true` so those ticks are
  excluded from divergence statistics.

---

## 4. Turbo capability preflight (blocking gate for Stage 0)

The actuator-command contract: whenever `controller_call == cool`, issue
`hvac_mode: cool`, `temperature: 61`, and **explicitly request
turbo/powerful fan operation**, reasserting all three at the supervisor
cadence (15 min). Reassertion-at-cadence is endorsed: it is the existing
doctrine ("commands issued every tick rather than on transitions — harmless
but noisy"), it self-heals cloud lag and M1 staleness, and the idempotent
`set_fan_mode` adds no new failure surface. Transition-only commanding stays
a V9 goal; it is **not** safer today because nothing else re-establishes a
dropped command.

**No implementation may invent a fan-mode string.** The exact Home Assistant
fan-mode token and service for "turbo" on these Samsung heads is **unknown
until verified live**. Before any Stage 0 YAML is written, run this preflight
against each of the four `climate.*` Samsung entities and commit the results
as `docs/analysis/turbo_capability_preflight.md`:

| # | Check | How | Record |
|---|---|---|---|
| 1 | Supported fan modes | Read `fan_modes` attribute from each entity (Developer Tools → States) | Full list, exact case, per entity |
| 2 | Turbo token | Identify the turbo/powerful option in that list (e.g. `turbo`, `Turbo`, `high`…) | Exact case-sensitive string; if absent → check 5 |
| 3 | Correct service | Confirm `climate.set_fan_mode` accepts the token; if the integration exposes a different action (e.g. a SmartThings-specific service or a `preset_mode`), record the working call | Service + payload that verifiably engages turbo |
| 4 | Persistence | With turbo engaged: issue `climate.set_temperature` (61), re-read `fan_mode`; then issue `climate.set_hvac_mode: cool`, re-read again | Whether turbo survives each command type — this decides whether per-tick fan reassertion is mandatory or belt-and-suspenders |
| 5 | Turbo unavailable | If no turbo/powerful token exists on a head | Fallback = highest supported fan mode for that head, recorded as a capability deviation; the contract degrades to `cool/61/<max fan>` for that head only. Never send an unlisted string. |
| 6 | Guardrail interaction | Confirm engaging turbo does not flip the head to `auto` HVAC mode | Section 8 polices `auto`; fan mode must be orthogonal |

Stage 0 YAML must reference the recorded token (one constant, used
everywhere), and a Stage 0 contract test must assert the YAML's fan-mode
string equals the preflight-recorded token — so a guessed string cannot pass
review. If preflight check 4 shows turbo is cleared by `set_temperature` or
`set_hvac_mode`, the cool-path command order is fixed as: set_temperature
(with hvac_mode) **then** set_fan_mode, every tick.

Known-safe interactions, verified against current YAML: Section 6
destratification only touches heads that are `off` (engage) or `fan_only`
(release) — it cannot fight an active cool/turbo pull-down. Section 8 only
acts on heads in `auto` mode. Section 11/15 logging is observational.

---

## 5. Stage 0 — Cooling-contract implementation (scope and tests)

Stage 0 makes the live supervisor match §1–§2. **All changes confined to
`automations.yaml` Section 2 plus tests** (plus the preflight artifact).
Section 2 remains the sole comfort writer; no new helpers or automations.

### 5.1 Changes

**CHANGE-1 — Kids bedtime block (adopts PR #134 plan v6, with one
correction).** Implement exactly the season-independent per-room block from
`docs/kids-bedroom-overnight-cooling-plan.md` §5: `kids_bedtime`
variable (`hour >= 18 or hour < 7`); block at the top of the action gated on
`kids_bedtime and season in ['cooling','shoulder']`; per-room ≥70 engage /
≤66 release / hold-through; `cool@61` + explicit turbo on the cool path only;
legacy kid handling gated on `not kids_bedtime`; kids removed from the
shoulder-night bulk-off. **Correction per the 2026-06-10 precedence matrix:**
the block's gate must also require `not away` — global away (P1) outranks the
kids' bedtime profile, so when `away_mode` is on the kids fall through to
away handling (74/76, hold, 61/turbo). PR #134's pseudocode did not state an
away check; the precedence matrix resolves it.

**CHANGE-2 — Turbo on every cooling call.** Every Section 2 path that
commands `cool` to a Samsung head adds the explicit fan command using the
preflight token: cooling-branch Master/Lincoln/Lilly/LR (away and non-away),
shoulder-night Master escape, shoulder-day warm-path bedrooms, and the new
kids bedtime and LR night paths. Turbo is requested only while the call is
cool; the off path issues no fan command. This **extends** PR #134's
kids-only turbo to all cooling calls — operator-directed 2026-06-10.

**CHANGE-3 — LR night conservation profile (new behavior).** In the cooling
branch, when `night_mode_lr_primary` is on and not away: LR uses 76 engage /
74 release / hold-through / `cool@61/turbo` instead of the daytime 72/68.
Does not read or write `input_boolean.away_mode`. Heating/shoulder LR
behavior tied to this helper is unchanged. Shoulder LR cooling remains
ineligible (§1.4) — the profile takes effect where LR cooling is evaluated,
i.e. the cooling season branch.

**CHANGE-4 — Away parity in shoulder (live gap fix).** The shoulder-day warm
path currently cools bedrooms with no away handling, and the shoulder paths
generally ignore `away_mode` for cooling. Stage 0 applies P1 (76/74, hold,
61/turbo) wherever a zone is cooling-eligible in shoulder, consistent with
"away overrides every occupied/night profile."

**CHANGE-5 (operator-visible; recommended default) — Shoulder-day bedroom
deadband alignment.** The live shoulder-day warm path cools Master/Lincoln/
Lilly at `> 70 → cool, else off` — a zero-width band with no hold, which
contradicts both the operator's stated daytime doctrine (72/68) and the
hysteresis contract. Recommended: within the existing warm-eligibility gate
(`outdoor > 70 or lr_temp > 71`, unchanged), evaluate those zones with the
P5 daytime profile (72/68, hold-through, 61/turbo). This touches the path PR
#134's plan listed as "daytime unchanged," so it is called out here for
explicit operator approval at design review; the fallback (keep legacy 70/70
no-hold, mirrored as-is by the shadow) is inferior but acceptable. **The
shadow evaluator mirrors whichever variant Stage 0 lands** — the policy and
its mirror cannot diverge.

Untouched: heating-season logic, Nest/Dining, Section 1/3/4/5/6/7/7B/8/9/11/
14/15, manual-override gate, all Section 3 thresholds, truth sensors,
telemetry, MSR boundaries, `configuration.yaml`.

### 5.2 Stage 0 tests

Existing tests updated: `test_section2_shove_command_setpoints.py` (command
count grows; all cooling commands still resolve to 61; heating still 79),
`test_section2_cooling_setpoint_doctrine.py` (daytime kid variables unchanged
under the new `not kids_bedtime` guard; traversal fix if nesting changed),
`test_supervisor_shoulder_night.py` (kids absent from shoulder bulk-offs;
Master escape preserved).

New tests (pytest over parsed YAML, repo pattern):

1. `test_section2_kids_bedtime_contract.py` — bedtime block exists; gated on
   `not away`, `kids_bedtime`, `season in ['cooling','shoulder']`; per-room
   ≥70/≤66/hold logic; turbo issued only on the cool path; rooms independent.
2. `test_section2_away_precedence.py` — every cooling-eligible path resolves
   74/76 under away, including shoulder paths; away outranks Master night,
   kids bedtime, and LR night.
3. `test_section2_lr_night_profile.py` — LR cooling thresholds are 76/74 with
   hold when `night_mode_lr_primary` on (not away); the helper is never
   written; `away_mode` is never written by Section 2.
4. `test_section2_turbo_on_cool_commands.py` — every Samsung cool command is
   paired with the fan command; the fan-mode string equals the
   preflight-recorded token (read from one place); no fan command on off
   paths; Nest receives no fan command.
5. `test_section2_hysteresis_comparators.py` — locks the exact comparators
   per profile (`>`/`≤` for P1/P2/P4/P5; `≥`/`≤` for P3) and that every
   cooling profile preserves prior call between thresholds.

Stage 0 ships only when the full suite is green, `ha core check` passes, and
the PR #134 plan's live validation steps (§9 of that plan) plus: away-flip
mid-pull-down behaves per P1; LR night engage/release at 76/74; turbo
observed on the head (`fan_mode` attribute) during a real pull-down.

---

## 6. Stage 1 — Corrected Shadow Evidence MVP (schema and tests)

Stage 1 begins **only after Stage 0 is merged, deployed, and live-verified.**
It carries forward unchanged from PR #139 Document 2: the observational-only
verdict, zero-`climate.*`-call guarantee (§6 there), failure containment
(§7), the recorder rules — no `include:`/`exclude:`, `purge_keep_days: 30`,
`commit_interval: 5` preserved (§5.5) — the three documentation corrections
(§8), and the event-level export specification with its schema-dependent
warnings (§5.4). Those sections are not restated; they remain binding.

What changes: the decision model and the schema.

### 6.1 Shadow decision model

The shadow evaluator mirrors the **Stage 0 policy exactly**: same profile
selection (§1.2–§1.4), same thresholds and comparators (§1.3), same
hysteresis semantics (§2.1) — evaluated twice per zone per tick:

- **Raw-hypothetical path:** input = `sensor.<zone>_temperature_truth`,
  memory = `sensor.<zone>_shadow_raw_call` latch.
- **Filtered-hypothetical path:** input = `sensor.<zone>_temperature_control`,
  memory = `sensor.<zone>_shadow_filtered_call` latch.

Both hypothetical paths use the **same memory mechanism** (own latch), so the
comparison isolates the input path — the only variable Packet B is allowed to
vary. The live head's reported mode is recorded as telemetry and as the
**mirror-parity calibration** (does the raw-hypothetical path reproduce what
the live M1 controller actually did when ungated?) — it is never used as
either hypothetical path's memory.

Entity inventory (replaces Rev 3's 28 flat sensors): per zone, three
**trigger-based** template sensors (triggers: `/15` time pattern +
`input_select.hvac_season_mode` state + HA start — mirroring the supervisor's
triggers):

| Entity | State | Notes |
|---|---|---|
| `sensor.<zone>_shadow_raw_call` | `off`/`cool` | Latch; self-references `this.state` for hold; restores across restart; `memory_warmup` attribute per §3.2 |
| `sensor.<zone>_shadow_filtered_call` | `off`/`cool` | Same, on filtered input |
| `sensor.<zone>_shadow_record` | `same`/`different`/`not_eligible` | Full per-tick record in attributes (§6.2) |

12 entities total. One Section 17 automation (`v_shadow_evaluator`) remains,
emitting the one-line JSON `logbook.log` record per tick (only service call,
unchanged guarantee). Tick-ordering note: shadow evaluation and the
supervisor fire independently within the same minute; the record carries
`supervisor_last_triggered` so analysis can detect whether the sampled head
state is pre- or post-command for that tick — Rev 3's "ordering is
immaterial" claim is replaced by making ordering *observable*.

### 6.2 Per-zone per-tick record (the corrected schema)

| Field | Values / type |
|---|---|
| `eval_timestamp` | ISO8601 |
| `zone` | lr / master / lincoln / lilly |
| `profile_selected` | `away` / `daytime` / `master_night` / `kids_night` / `lr_night` / `not_eligible` / `override_gated` |
| `active_on_threshold`, `active_off_threshold` | °F per §1.3 (null if not eligible) |
| `engage_comparator` | `gt` / `ge` (P3 is `ge`) |
| `season_mode`, `away_state`, `lr_night_helper`, `kids_bedtime_active`, `master_sleep_active`, `manual_override_state` | gate inputs |
| `raw_truth`, `filtered_value`, `smoothed_value` | °F or null |
| `raw_call_before`, `filtered_call_before` | off/cool (latch states before transition) |
| `raw_decision`, `filtered_decision` | off/cool/unavailable (resulting call state per path) |
| `commanded_setpoint` | 61 if decision==cool else null (per path; constant by doctrine, recorded so replay never re-derives it) |
| `requested_fan_mode` | preflight token if decision==cool else null |
| `live_head_hvac_mode` | `states('climate.<zone>')` |
| `live_head_fan_mode` | `state_attr(..., 'fan_mode')` |
| `live_head_setpoint` | `state_attr(..., 'temperature')` |
| `live_hvac_action` | `state_attr(..., 'hvac_action')` — firing telemetry |
| `mirror_parity` | true/false/not_applicable — raw_decision vs live head mode, evaluated only when override idle and zone eligible |
| `divergence` | same / different |
| `divergence_direction` | none / raw_more_aggressive / filtered_more_aggressive |
| `raw_threshold_distance_on/off`, `filtered_threshold_distance_on/off` | signed °F |
| `raw_truth_available`, `filtered_available`, `memory_warmup` | bool flags |

Failure behavior table from Rev 3 §7 carries over, with one amendment: a
missing latch (unknown/unavailable) triggers stateless evaluation +
`memory_warmup: true`, never a fallback to head-mode memory.

### 6.3 Stage 1 tests

Rev 3's eight tests carry forward re-targeted at this schema (supervisor/
safety read raw truth; shadow makes zero `climate.*`/helper/timer calls;
shadow isolation; recorder safety; documentation routing; no Packet A
duplication). Three are strengthened/added:

1. `test_packet_b_shadow_policy_parity.py` (replaces Rev 3 Test 5) — every
   profile's thresholds, comparators, windows, and precedence in the shadow
   templates match Section 2 **as landed by Stage 0**, including kids
   bedtime (≥70/≤66), LR night (76/74), away precedence, and the
   `commanded_setpoint`/fan token constants. Any Section 2 threshold edit
   that is not mirrored fails CI.
2. `test_packet_b_shadow_latch_independence.py` — latch sensors
   self-reference only their own prior state and their input path; the
   filtered latch references no `*_truth` entity and no `climate.*` state;
   the raw latch references no `*_control`/`*_smoothed` entity; neither
   latch appears in any non-shadow automation or template.
3. `test_packet_b_shadow_actuator_fields.py` — the record template includes
   the head mode, fan mode, setpoint, and `hvac_action` fields, and the
   shadow never *writes* any of them.

### 6.4 Evidence gates

Rev 3's Gates 0–8 carry forward with two amendments:

- **Gate 1 adds mirror-parity calibration:** over the first 24 h,
  `mirror_parity == true` for ≥ 95% of override-idle eligible ticks. If the
  raw-hypothetical path cannot reproduce the live controller, the mirror is
  wrong — fix instrumentation before opening the evidence window (and the
  measured parity gap feeds the §3.2 M1-versus-latch decision).
- **Gate 7 metrics are computed per profile**, not just per zone: divergence
  concentrated in the kids' 66–70 bedtime band has different operational
  meaning than divergence in the away 74–76 band.

The final raw-versus-filtered routing decision remains blocked until Gate 6
cross-validation and Gate 7 classification clear (PR #138 §3.4; PR #139
Document 1). Nothing in Stage 0 or Stage 1 pre-decides it.

---

## 7. Season-transition rules

1. **Auto season mode (Section 5, unchanged):** deck truth > 72 °F for 2 h →
   `cooling`; 50–68 °F for 2 h → `shoulder`; < 45 °F for 2 h → `heating`.
   A season change immediately re-triggers the supervisor (existing state
   trigger), so transitions are evaluated at flip time, not at the next tick.
2. **Kids bedtime pull-down is flip-immune:** the P3 block is
   season-independent across {cooling, shoulder}; a `cooling→shoulder` flip
   mid-pull-down re-enters the same block with call==cool and continues to
   ≤ 66 °F. Shoulder bulk-offs no longer include the kids' heads. (PR #134
   contract, preserved verbatim.)
3. **Master night is structurally flip-immune:** the cooling-branch sleep
   band and the shoulder-night escape share thresholds (66/62) and memory
   semantics, so a night flip preserves the call. A flip *into heating*
   season ends all cooling calls (next evaluation commands per heating
   branch) — intended.
4. **Daytime pull-downs are eligibility-gated, not flip-protected:** a
   `cooling→shoulder` flip with cool/mild outdoor conditions ends daytime
   bedroom cooling at the flip evaluation (zones leave cooling eligibility).
   This is intended conservation behavior, now documented rather than
   implicit. Only P3 carries an operator-granted flip exemption.
5. **`shoulder→cooling`:** no special handling; latches/memory carry, the
   wider eligibility simply adds zones.
6. **Shadow mirror:** the shadow evaluator applies these exact eligibility
   rules; ineligible ticks record `profile_selected: not_eligible` rather
   than fabricating a decision (Rev 3 recorded kids decisions during
   shoulder bulk-offs that the real controller could never take — that class
   of phantom divergence is eliminated).

---

## 8. Safety invariants (all unchanged, all outrank this contract)

| Invariant | Value | Status |
|---|---|---|
| Master emergency cooling floor | truth < 58 °F → force off | Unchanged (Section 3) |
| LR runaway cooling cutoff | truth < 60 °F while cooling → force off | Unchanged |
| Safety ceiling gates (Master/Lincoln/Lilly) | truth > 76 °F → cool@68 for 45 min (cooling season) | Unchanged. Known interplay: the supervisor may reassert 61 within the gate's 45-min window; pre-existing behavior, out of scope. |
| Manual override | `timer.manual_hvac_override != idle` gates Section 2 and the ceiling gates; WAF watcher starts it on human action | Unchanged; the kids/LR-night/away blocks live inside the supervisor and inherit the gate |
| Sleep Priority Interlock | Master cool + LR heat → LR off (LR truth > 60) | Unchanged |
| Ghost assassin / Samsung auto guardrail | 01:20 Lincoln heat kill; auto-mode policing | Unchanged; turbo is a fan mode and never sets `auto` (§4 check 6) |
| Shadow path | zero `climate.*`/helper/timer calls; failure cannot propagate to control | Carried from Rev 3 §6–§7, binding |
| Recorder | no include/exclude; `purge_keep_days: 30`; `commit_interval: 5` | Carried from Rev 3 §5.5, binding |
| Truth freshness | `last_reported` semantics | Unchanged |

Turbo adds no new safety surface: it changes air-mover speed, not thresholds,
floors, or mode policing. The 61 °F command setpoint remains backstopped by
the 58/60 °F truth floors exactly as under PR #126.

---

## 9. Rollback plans

### 9.1 Stage 0

Change set = `automations.yaml` Section 2 + tests + preflight doc. Rollback =
`git revert` of the Stage 0 commit(s) + reload. No helpers, entities, or
migrations. Restores: legacy kids 68/72 all-hours, no LR night cooling
profile, no turbo commands, legacy shoulder away gap. One post-rollback
manual step: heads last commanded turbo retain it until the next manual or
automated fan command — issue `climate.set_fan_mode: auto` once per head (or
accept it; cosmetic). Verify post-rollback with the pre-Stage-0 test suite.

### 9.2 Stage 1

Identical to Rev 3 §11: remove Section 17 automation + Section 16 template
block; one reload; zero effect on live control; recorder untouched in both
directions. The 12 shadow entities disappear from states; recorder history
of them ages out via normal purge.

### 9.3 Independence

Stage 0 and Stage 1 ship as **separate PRs with independent rollbacks** so a
comfort-policy regression and an instrumentation regression can be reverted
without touching each other. Stage 1's policy-parity test (§6.3.1) means a
Stage 0 rollback intentionally fails Stage 1 CI until the shadow is
re-pointed or rolled back too — desired: the mirror must never silently
drift from the policy.

### 9.4 Documentation

The §8 (Rev 3) documentation corrections and this document are docs-only;
revert via `git revert` with no control-path effect.

---

## 10. Air-gapped Codex handoff requirements

### 10.1 Revocation

The Hermes air-gapped Codex implementation bundle generated from the PR
#139/#140 Shadow Evidence design (Rev 3 §13 handoff and any derivative
package) is **REVOKED, effective 2026-06-10**. It must not be executed
against the live system or the repository. Defects: §0 items 1–5. Any
implementation PR produced from it must be closed unmerged.

### 10.2 Regeneration preconditions (in order)

1. This Revision 4 is operator-approved.
2. The turbo capability preflight artifact exists
   (`docs/analysis/turbo_capability_preflight.md`, §4) with live-verified
   tokens for all four heads.
3. CHANGE-5 variant confirmed by operator (recommended default: align).
4. PR #139 is updated so its Document 2 defers to / incorporates Revision 4,
   and PR #140 is closed or marked superseded (no competing canonical doc).

### 10.3 Bundle requirements (two bundles, one per stage)

**Stage 0 bundle** must contain: this document §§1–5, 7–9; the preflight
artifact; the PR #134 plan (`docs/kids-bedroom-overnight-cooling-plan.md`)
with the §5.1 CHANGE-1 away-precedence correction noted; the live-diff-first
instruction (diff live Section 2 vs Git and commit live state before
patching — Git may lag live); the Stage 0 test list (§5.2); the prohibition
list below; the validation procedure (§5.2 + PR #134 plan §9) and rollback
(§9.1). Exactly one implementation PR.

**Stage 1 bundle** may be generated **only after Stage 0 is merged and
live-verified**, and must contain: this document §§6–9; the as-merged
Stage 0 Section 2 (the mirror source of truth); Rev 3's carried-forward
sections (isolation §6–§7, recorder §5.5, doc corrections §8, export §5.4
with its schema warnings); the Stage 1 test list (§6.3); gates (§6.4).
Exactly one implementation PR.

**Prohibitions (both bundles):** no invented fan-mode strings (preflight
token only); no `recorder: include:`/`exclude:`; no `purge_keep_days`
reduction; no Section 3 / safety threshold changes; no supervisor input-path
change (routing stays blocked); no new helpers beyond this spec (Stage 0:
none); no shadow `climate.*`/`input_*`/`timer.*` calls; no edits to PR #139's
design branch from an implementation task; no splitting a stage across
multiple PRs; if live state contradicts the bundle, **stop and report** —
never improvise.

### 10.4 Repository reconciliation (status ledger)

| Artifact | Status under Revision 4 |
|---|---|
| PR #126 (merged) | Actuator-shove doctrine — authoritative, unchanged |
| PR #134 | Authoritative kids' bedtime decision record — implement via Stage 0 CHANGE-1 (with away-precedence correction) |
| PR #138 | §3.4 evidence block — remains in force |
| PR #139 Document 1 (decision review) | Stands unchanged (REMAIN BLOCKED) |
| PR #139 Document 2 (Shadow MVP) | Revised by this document; PR #139 to be updated to the Revision 4 lineage rather than a new competing design PR |
| PR #140 (Rev 3) | **SUPERSEDED** in full by this document |
| Hermes air-gap bundle | **REVOKED** (§10.1) |
| This document | Canonical Packet B design, Revision 4 |

---

## 11. Self-check against the required outputs

1. Final profile/precedence matrix — §1. 2. Exact hysteresis state-machine
semantics — §2. 3. Controller-call memory recommendation — §3. 4. Turbo
capability preflight — §4. 5. Stage 0 scope and tests — §5. 6. Stage 1
corrected shadow schema and tests — §6. 7. Season-transition rules — §7.
8. Safety invariants — §8. 9. Rollback plans — §9. 10. New air-gapped Codex
handoff requirements — §10.

No unresolved fact blocks this design: the only live-unknowable item (the
exact Samsung turbo token/service/persistence) is converted into a blocking
preflight gate (§4) that Stage 0 cannot bypass, and the single
operator-visible judgment call (CHANGE-5) ships with a recommended default
and an explicit approval checkpoint (§10.2.3).

---

```
═══════════════════════════════════════════════════════════════
PACKET B REVISION 4 READY — CONTROL CONTRACT RECONCILED
═══════════════════════════════════════════════════════════════
```
