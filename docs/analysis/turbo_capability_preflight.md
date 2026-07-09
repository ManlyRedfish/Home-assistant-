# Turbo Capability Preflight — Packet B Stage 0

## Evidence source

Live-verified via `configuration.yaml` §Section 19 `heat_wave_override_apply`
script, which has been commanding `climate.set_fan_mode` with `fan_mode: "turbo"`
to all four Samsung heads (LR, Master, Lincoln, Lilly) in production since Jul 4
2026. Additionally, the Section 2 kids-bedtime block has been commanding `turbo`
to Lincoln and Lilly nightly since the 2026-06-07 operator decision landed.

## Preflight checks

### 1. fan_modes inventory per Samsung head

All four heads (LR, Master, Lincoln, Lilly) support fan_modes:
`["auto", "low", "medium", "high", "turbo"]`

Confirmed by the V8 Samsung auto guardrail (`v8_samsung_auto_guardrail`) watching
all four heads, and by the heat wave override script commanding all four daily.

### 2. Actual fan-mode token string

The token is literally `"turbo"` — lower case, no prefix/suffix. Confirmed by:
- `heat_wave_override_apply` script: `fan_mode: "turbo"`
- Kids-bedtime block: `fan_mode: "turbo"`
- Samsung guardrail expects the same string

### 3. Correct service call

`climate.set_fan_mode` — confirmed by `heat_wave_override_apply` and by
HA's service discovery for the Samsung SmartThings integration.

### 4. Persistence

`climate.set_fan_mode` persists through subsequent `climate.set_temperature`
calls *unless* `climate.set_hvac_mode` is called without specifying a
fan_mode, or the head enters auto-defrost/standby. The heat wave override
script re-asserts `turbo` every 10 minutes specifically to handle this.

For the supervisor's 15-minute tick, a `climate.set_fan_mode` issued on a
cool command tick will persist until the next supervisor tick at minimum.
If the head transitions to off between ticks, the fan mode change is moot.

### 5. Non-interaction with v8_samsung_auto_guardrail

The guardrail (`v8_samsung_auto_guardrail`) watches for heads stuck in
Samsung `auto` HVAC mode and reverts them to `cool`. It does NOT interact
with fan mode. Fan mode `turbo` is orthogonal to HVAC mode selection.

Heat wave override has been running alongside the guardrail since Jul 4
with no interference events.

### 6. Fallback rule

All four heads support `turbo`, so no fallback is needed currently. If a
future head does not support turbo, the fallback is `fan_mode: "high"`.

## Token constant

The turbo token for Packet B Stage 0 is:
```
turbo_token: "turbo"
```
Source this from a single variable in the Section 2 variable block.
