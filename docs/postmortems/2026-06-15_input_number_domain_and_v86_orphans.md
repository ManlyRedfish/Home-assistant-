# Postmortem — `input_number` Domain De-registration (V9-E repair) & V8.6 Registry Orphans

**Incident Date:** 2026-06-15
**Author Role:** Senior Systems Reviewer
**Document Role:** Root-cause record + operator remediation handoff
**Status:** Repo already carries the fix (commit `e05a740`). Live remediation is host-side (deploy + reload). No new runtime YAML change required.
**Scope Lock:** Documentation only. No runtime config or automation changes in this commit.

---

## 1. Executive Summary

Three live symptoms were reported (confirmed by Codex/Hermes):

1. The `input_number` service domain was not loaded — `input_number.set_value` did not exist.
2. All six `input_number.precool_*` entities were `unavailable` since 2026-06-13.
3. An active repair on `automation.v9_e_master_pre_cool_nightly_reset`:
   *"…has an unknown action: input_number.set_value."*
4. Two V8.6 safety automations were `unavailable` with `restored: true`:
   - `automation.v8_6_truth_unavailable_cooling_fail_safe_per_zone_protective_off`
   - `automation.v8_6b_truth_unavailable_cooling_reconciliation_restart_reload_safe`

Symptoms 1–3 are a **single root cause with a cascade**. Symptom 4 is a
**separate, unrelated** issue (stale entity-registry orphans) that the repo
cannot resolve and that must not be "fixed" by inventing automations.

---

## 2. Root Cause — `input_number` domain (symptoms 1–3)

### What happened

The V9-E precool revision (commit `587e180`, 2026-06-13) retired two tunables
(`precool_max_runtime`, `precool_drop_rate_limit` — the slope/runtime guard
removal) but left a **stray, valueless duplicate key**
`precool_previous_master_temp:` at the end of the `input_number:` block.

Home Assistant's YAML loader **rejects a mapping that contains a duplicate
key**. (PyYAML's `SafeLoader` silently keeps the last value and does *not*
error, which is why the repo's `tests/test_yaml_syntax.py` did not catch it —
see §6.) Because the whole `input_number:` mapping was rejected:

```
input_number:  ──► mapping rejected on duplicate key
   ├─ integration fails to set up
   ├─ service input_number.set_value never registers
   │     └─ V9-E nightly reset action ⇒ "unknown action: input_number.set_value" (the repair)
   └─ every input_number.precool_* entity ⇒ unavailable
```

So the V9-E repair was a **downstream symptom**, not a bad action. The generic
HA repair suggestion ("remove the action") would have been wrong — it would
have broken the nightly runtime-budget zeroing and slope-memory seed.

### Already fixed in the repo

Commit `e05a740` (2026-06-15, merged in PR #149) removed the stray duplicate
key. The current repo is verified clean:

- Strict duplicate-key parse (mirroring HA's loader) of `configuration.yaml`
  and `automations.yaml`: **both pass**.
- `input_number:` parses to a dict of four well-formed helpers.
- Full suite: **161 passed**, including the `EXPECTED_CONFIGURATION_HASH` pin.
- `git merge-base --is-ancestor e05a740 HEAD` ⇒ true.

**Therefore no further repo YAML change is required for symptoms 1–3.** The
live symptoms indicate the HA host has not yet loaded the fixed config — the
remediation is host-side (deploy + config check + reload/restart, §5).

---

## 3. The "six helpers" — only four are current by design

| Helper | In current config? | Status |
| --- | --- | --- |
| `input_number.precool_runtime_counter` | ✅ defined | loads once fixed config is active |
| `input_number.precool_previous_master_temp` | ✅ defined | loads once fixed config is active |
| `input_number.precool_target_temp` | ✅ defined (`initial: 64`) | loads once fixed config is active |
| `input_number.precool_thermal_floor` | ✅ defined (`initial: 63.5`) | loads once fixed config is active |
| `input_number.precool_max_runtime` | ❌ retired (`587e180`) | **orphaned registry entry** — clean via UI, do **not** re-add |
| `input_number.precool_drop_rate_limit` | ❌ retired (`587e180`) | **orphaned registry entry** — clean via UI, do **not** re-add |

The two retired helpers are referenced by **zero** automations (verified by
grep across `automations.yaml`). Re-adding them would contradict the V9-E
slope/runtime guard removal. They linger only as entity-registry rows and will
read `unavailable` until removed from **Settings → Devices & Services →
Entities** (filter: Unavailable). This is registry cleanup, **not** a config
change.

> Note: the `input_number:` header comment still lists
> "target/floor/drop-limit/max-runtime" as the tunable set. That comment is now
> stale (only target/floor remain). It is left untouched here because editing it
> would change `configuration.yaml` and break the pinned config hash for a
> cosmetic edit; fold it into the next intentional config-hash re-pin.

---

## 4. V8.6 automations — registry orphans; real source located on an unmerged branch

The two V8.6 entities are **absent from `main`** (`automations.yaml` on `main`
has 23 automations: V7.5, V8.2, V9-* … no V8.6). They are registry-enabled but
show `restored: true` / `unavailable` because `automation: !include
automations.yaml` is the **only** automation source (packages are commented
out) and their definitions are not in the loaded file.

**Update (source found — do NOT reconstruct; recover instead).** The real
definitions exist on the **unmerged Packet A branch**
`codex/clarify-codex-stage-1-and-2-implementation` (tip = commit `9e39e42`,
"Implement Packet A truth unavailable cooling failsafe", 2026-06-09):

- `automations.yaml` lines 718–774: `id: v8_6_truth_unavailable_cooling_failsafe`
- `automations.yaml` lines 775–831: `id: v8_6b_truth_unavailable_cooling_reconciliation`
- companion contract test: `tests/test_packetA_truth_unavailable_failsafe.py`

Both are **OFF-only** safety automations (force a head's `climate.set_hvac_mode:
off` when its room-truth sensor is invalid for ≥2 min while the head reports
`cool`; the V8.6B variant adds a start/periodic 5-min reconciliation sweep to
close the restart race). They parse cleanly, and all four referenced truth
sensors (`sensor.{living_room,master_bedroom,lincoln_s_room,lilly_s_room}_temperature_truth`)
plus `climate.{living_room,master_bedroom,lincoln,lilly}_air` exist on `main`/live.

### ⚠️ Entity-ID vs unique-ID mismatch (decisive for cleanup)

The branch aliases slugify to **shorter** IDs than the live orphans:

| Live orphan entity_id | Alias in `9e39e42` (slug) |
| --- | --- |
| `automation.v8_6_truth_unavailable_cooling_fail_safe_per_zone_protective_off` | `…cooling_failsafe` |
| `automation.v8_6b_truth_unavailable_cooling_reconciliation_restart_reload_safe` | `…reconciliation` |

The long-form text (`per_zone_protective`, `restart_reload`) appears in **no
branch**, so the live orphans came from a deployment whose aliases differed from
`9e39e42`. HA links registry rows by the automation **`id:` (unique_id)**, not
the alias. Therefore:

- If the orphan rows' unique_id == `v8_6_truth_unavailable_cooling_failsafe` /
  `…reconciliation`, deploying `9e39e42`'s definitions **re-links** them and they
  go available (any customized entity_id is retained). Orphans resolved.
- If the unique_ids differ, deploying `9e39e42` creates **two new** entities and
  the orphans remain → then delete the orphan rows via the UI.

**Still an operator decision (§7).** AGENTS.md: never simplify away safety
systems, never invent behavior. Recovering the verbatim `9e39e42` source is
*not* invention; choosing whether to re-merge that safety layer vs. retire it is
the operator's call.

---

## 5. Remediation — host-side (operator)

The corrective config already lives in the repo. On the HA host:

1. **Sync** the host's `configuration.yaml` to the repo HEAD (must include
   `e05a740`). Confirm the `input_number:` block ends at
   `precool_thermal_floor` with **no** trailing `precool_previous_master_temp:`.
2. **Config check first:** Developer Tools → YAML → *Check Configuration*
   (or `ha core check`). Must be green before any reload.
3. **Reload** (no full restart needed for the domain):
   - Developer Tools → YAML → *Input Numbers* (reload helpers)
   - Developer Tools → YAML → *Automations* (reload automations)
   - If `input_number.set_value` still does not appear, restart HA Core.
4. **Registry cleanup (separate from config):** remove the orphaned
   `precool_max_runtime` and `precool_drop_rate_limit` entity rows via the UI.

---

## 6. Verification checklist

After the host reload, confirm:

- [ ] `input_number.set_value` appears in Developer Tools → Actions.
- [ ] The four current `input_number.precool_*` helpers are no longer
      `unavailable` (target_temp ≈ 64, thermal_floor ≈ 63.5 on first load).
- [ ] The V9-E "unknown action" repair is gone.
- [ ] `precool_max_runtime` / `precool_drop_rate_limit` removed from the registry
      (expected to remain `unavailable` until then — by design).
- [ ] Logs show no new `input_number` / automation setup errors.
- [ ] The two V8.6 entities: see §7 (not resolved by this remediation).

Repo-side guard gap (now closed): `tests/test_yaml_syntax.py` used PyYAML
`SafeLoader`, which does **not** flag duplicate keys, so it missed this class of
bug. A strict duplicate-key check was added (PR #151) and mirrors HA's loader.

---

## 7. Follow-ups (handled separately)

1. **V8.6 automations (operator decision required — source now located).** The
   verbatim definitions are on branch
   `codex/clarify-codex-stage-1-and-2-implementation` @ `9e39e42` (see §4).
   Choose one:
   - **(a) Restore:** cherry-pick the two automations (and
     `tests/test_packetA_truth_unavailable_failsafe.py`) onto a fresh branch,
     review, merge, deploy, then reload automations. If the orphans' unique_ids
     match (§4), they re-link and go available; otherwise delete the leftover
     orphan rows after the new entities appear. Recommended if `main`'s Section 2/3
     does not already cover *truth-invalid-while-cooling* — the design is OFF-only
     and low-risk, and AGENTS.md weights toward preserving safety layers.
   - **(b) Retire:** if V8.6 was deliberately superseded, delete the two orphan
     rows via Settings → Devices & Services → Entities (filter: Unavailable).
   This commit does **not** edit `automations.yaml` (per the task's
   sync-with-GitHub rule); restoration must go through its own reviewed PR.
2. **Repo ↔ live sync direction.** The recurring "sync live → GitHub" job pushes
   host changes up; it does not push repo fixes down. Confirm the host actually
   picked up `e05a740`, or the duplicate-key state could persist live despite a
   green repo.
3. **Strict duplicate-key test** — ✅ done in PR #151 (see §6).
4. **Stale `input_number:` header comment** — fold the target/floor-only tunable
   set into the next intentional config-hash re-pin.
