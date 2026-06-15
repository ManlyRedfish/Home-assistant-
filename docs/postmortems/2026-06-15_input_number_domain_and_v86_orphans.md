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

## 4. V8.6 automations — registry orphans, NOT reconstructable from the repo

Both reported V8.6 entities are **absent from the repo and from its entire git
history**:

- No definition in `automations.yaml` (23 automations present: V7.5, V8.2,
  V9-* … **no V8.6**).
- No commit ever added `truth_unavailable_cooling` / "Truth Unavailable" /
  "Per-Zone Protective" to `automations.yaml` (`git log -S` ⇒ empty).
- No V8.6 fail-safe / reconciliation spec anywhere in `docs/`. The string
  `truth_unavailable` exists only as a **release-reason / event-kind label**
  and a trigger `id:`, never as these automations.

`automation: !include automations.yaml` is the **only** automation source
(packages are commented out). So an automation that is registry-enabled but
shows `restored: true` / `unavailable` means **its definition is not in the
loaded `automations.yaml`** — i.e. these are stale registry rows from a prior
(V8.6-era) architecture or live-host-only definitions that were never synced
to this repo.

**Decision: do not reconstruct them.** AGENTS.md forbids inventing entities or
behavior ("ask instead of inventing"), and these are *safety* automations —
fabricating per-zone protective-off / restart-reload-safe logic from an entity
ID alone would be unsafe guesswork. This requires operator input (§7).

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

Repo-side guard gap to consider: `tests/test_yaml_syntax.py` uses PyYAML
`SafeLoader`, which does **not** flag duplicate keys, so it missed this class of
bug. A strict duplicate-key check (as used to verify this incident) would have
caught it — worth adding as a follow-up test.

---

## 7. Follow-ups (handled separately)

1. **V8.6 automations (operator decision required).** Provide the live host's
   `automations.yaml` (or the original V8.6 definitions). Then either:
   (a) faithfully restore the two definitions into `automations.yaml` so HA loads
   them, or (b) if V8.6 was intentionally superseded by V9 safety gates, delete
   the stale registry rows via the UI. **No reconstruction from the entity ID
   will be attempted.**
2. **Repo ↔ live sync direction.** The recurring "sync live → GitHub" job pushes
   host changes up; it does not push repo fixes down. Confirm the host actually
   picked up `e05a740`, or the duplicate-key state could persist live despite a
   green repo.
3. **Strict duplicate-key test** (see §6).
4. **Stale `input_number:` header comment** — fold the target/floor-only tunable
   set into the next intentional config-hash re-pin.
