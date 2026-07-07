# Master Bedroom Fan ↔ AC Sync (Sections 17 & 18)

**Doc Date:** 2026-06-16
**Document Role:** Runtime note for the SwitchBot fan that follows the Master
mini-split.
**Status:** Living. Update when the fan↔AC contract, the actuator entity, or the
SmartThings transport changes.
**Scope:** Documents `automations.yaml` Section 17 (`master_bedroom_fan_sync`)
and Section 18 (`master_bedroom_fan_reconcile`). Locked by
`tests/test_master_fan_sync.py`.

---

## 1. Contract

The SwitchBot fan `fan.master_bedroom_switch_fan` follows the Master mini-split
`climate.master_bedroom_air`:

- **AC off** → fan **off**.
- **AC running** (any of `cool`, `heat`, `dry`, `fan_only`, `auto`) → fan **on
  @ 100%**.

`100%` and `off` are the **only** states either automation commands. Any other
percentage (e.g. `66%`) is a leftover/manual speed and is, by definition, stale
relative to the contract.

## 2. Why two automations

### Section 17 — edge-driven sync (`master_bedroom_fan_sync`)

`mode: single`. Triggers only on `climate.master_bedroom_air` **mode
transitions** and issues a single `fan.turn_off` / `fan.turn_on` on the edge.
Fast, but fire-once: it does not verify the command or look at the fan again.

### Section 18 — reconcile / self-heal (`master_bedroom_fan_reconcile`)

`mode: single`, `max_exceeded: silent`. Triggers on the **fan's own
state/percentage changes** and a **5-minute time pattern**, and re-asserts the
same contract whenever the fan and AC disagree.

The fan reaches HA through the **SmartThings cloud**, which can drop or stale a
single command. When Section 17's lone `fan.turn_off` is dropped, the fan stays
out of sync until the next AC mode change. The canonical observed failure:

> AC went `cool → off` (04:45) and the supervisor confirmed the branch and
> called `fan.turn_off`, but the fan stayed `on @ 66%` from the night before.
> A direct `fan.turn_off` also returned *"state change could not be verified
> within timeout."*

Section 18 closes that gap: on the next fan state change or within 5 minutes it
re-issues the missing command, so a dropped command self-heals instead of
persisting as a telemetry mismatch (`fan_percentage = 66` while
`Master_Air_Mode = off`).

## 3. Boundaries

- Reconcile issues a command **only when the fan and AC actually disagree**, so a
  correctly-synced fan generates no traffic.
- Reconcile **never commands the climate entity** — it reconciles the fan *to*
  the AC, not the reverse (`tests/test_master_fan_sync.py::test_section18_reconcile_only_touches_the_fan`).
- Reconcile skips when `climate.master_bedroom_air` is `unknown`/`unavailable`
  (the correct fan state is undefined; re-asserting would be guessing).
- **It cannot move a physically offline device.** If the SwitchBot is
  unresponsive, the re-issued command is a harmless no-op until SmartThings
  connectivity returns; recovering a genuinely dead device still needs a
  state refresh (`homeassistant.update_entity`) or a physical check.

## 4. Relationship to telemetry

A stuck `fan_percentage` against a contradicting `Master_Air_Mode` is a
**SmartThings transport artifact**, not a comfort-control failure. Treat such a
window the way `docs/telemetry_confounders.md` treats other
transport/stale-state artifacts: do not read it as the fan logic
malfunctioning. Section 18 reduces how long such artifacts persist; it does not
change the telemetry schema or any HVAC control authority.
