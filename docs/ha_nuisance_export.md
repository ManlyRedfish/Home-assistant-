# HA Nuisance Evidence Export (Read-Only)

This tool exports 7-day Home Assistant evidence for nuisance investigation and offline join with Google Sheets telemetry.

## Runtime safety

- **Read-only only**: script uses Home Assistant REST **GET** endpoints only.
- **No runtime changes**: does not modify `automations.yaml`, `configuration.yaml`, helpers, thresholds, or any services.
- **No POST service calls**: no write operations to Home Assistant.

## Files added

- `tools/export_ha_nuisance_evidence.ps1`
- `docs/ha_nuisance_export.md`

## Prerequisites

- Windows PowerShell 5.1+ or PowerShell 7+
- Network access to Home Assistant
- A long-lived access token

## Create a long-lived access token

In Home Assistant UI:

1. Click your user profile (bottom-left sidebar).
2. Scroll to **Long-Lived Access Tokens**.
3. Click **Create Token**.
4. Name it (example: `nuisance-export-readonly`).
5. Copy and store the token securely.

> Treat this token like a password. Do not commit it to git.

## Usage (Windows PowerShell)

```powershell
pwsh -File .\tools\export_ha_nuisance_evidence.ps1 \
  -BaseUrl "http://homeassistant.local:8123" \
  -AccessToken "YOUR_LONG_LIVED_TOKEN" \
  -StartDate "2026-05-09T00:00:00" \
  -EndDate "2026-05-16T00:00:00" \
  -OutputFolder ".\exports\ha_nuisance_2026-05-09_2026-05-16" \
  -Format both
```

`-Format` options:
- `both` (default): write JSON + CSV history files
- `json`: write JSON history only
- `csv`: write CSV history only

## History API request mode and row contract

- For `-Format csv` and `-Format both`, history requests intentionally **do not** include `minimal_response`.
  - This preserves per-row metadata used for joins (`entity_id`, `last_updated`, and context fields).
- For `-Format json`, the script may use `minimal_response` to reduce payload size for raw archival JSON.
- `no_attributes` remains enabled in all modes to reduce payload size without dropping join-critical identity/timestamp/context fields.
- CSV flattening includes an entity-id carry-forward guard so rows derived from minimal-style history points still emit a non-blank `entity_id`.

## Export scope

The script exports history for:

1. **Automations**
   - `automation.v8_3_hvac_transition_log`
   - `automation.v8_samsung_auto_guardrail`
   - `automation.v7_5_ghost_assassin`
   - `automation.v9_sleep_priority_interlock`

2. **Climates**
   - `climate.living_room_air`
   - `climate.master_bedroom_air`
   - `climate.lincoln_air`
   - `climate.lilly_air`

3. **Timers**
   - `timer.lr_compressor_cooldown`
   - `timer.master_compressor_cooldown`
   - `timer.lincoln_compressor_cooldown`
   - `timer.lilly_compressor_cooldown`

4. **Shade entities**
   - discovered via state query pattern `cover.*shade*`
   - discovered entities are written to `ha_export_manifest.json` for downstream joining

5. **Logbook**
   - full window logbook export as `ha_logbook.json`

## Output files

- `ha_history_climates.json` and/or `ha_history_climates.csv`
- `ha_history_automations.json` and/or `ha_history_automations.csv`
- `ha_history_timers.json` and/or `ha_history_timers.csv`
- `ha_logbook.json`
- `ha_export_manifest.json` (metadata + discovered shade entities)

## Upload/export for analysis

Recommended workflow:

1. Run script for the same 7-day window used in Google Sheets telemetry.
2. Zip the output folder.
3. Upload or share files with your analysis notebook/workflow.
4. Join on timestamp and entity IDs:
   - HA history entity state changes
   - HA logbook narrative entries
   - Google Sheets VTherm telemetry rows

## Security and logging notes

- Token is sent only in `Authorization: Bearer` header.
- Script redacts token if it appears in an exception message.
- Avoid pasting raw tokens into shell history on shared systems.
