# Post-Change Evidence Analyzer

This read-only tool analyzes a local CSV export of `VTherm_Launch_Data_v5_5` and may optionally join a local `supervisor_state_log` CSV.

## Direct context rule

Rows are classified as operator/context contaminated only when direct evidence exists:

- `Supervisor_Enabled` is false.
- `Manual_Override_State` is `active`.
- For older exports without `Manual_Override_State`, `Section14_WAF_Active` is true.
- A supplied annotation overlaps the row and uses a confounding kind such as `supervisor_disabled` or `manual_setpoint_nudge`.

The analyzer does not infer operator intent from temperatures, setpoints, HVAC modes, action values, or zero-runtime patterns. Those are observations only.

This prevents a repeat of the June 3-5, 2026 misclassification, when an operator-directed cold experiment with the supervisor disabled was initially mistaken for autonomous controller failure.

## Usage

Run with telemetry only:

`python tools/analyze_post_change_evidence.py telemetry.csv --no-write`

Run with annotations:

`python tools/analyze_post_change_evidence.py telemetry.csv --annotations supervisor_state_log.csv`

The annotation CSV uses: `start_local,end_local,kind,note,created_at`.

## Posture labels

- `NO_DATA`
- `MISSING_CORE_COLUMNS`
- `CONTAMINATED_WINDOW`
- `CONTEXT_INCOMPLETE`
- `INSUFFICIENT_WINDOW`
- `CLEAN_OBSERVATION_CANDIDATE`

`CLEAN_OBSERVATION_CANDIDATE` means only that direct context shows no contamination and the window is long enough. It is not a claim that the controller is effective.

## Forensic boundary

The analyzer has no network client, no Home Assistant credentials, and no write path to Home Assistant or Google Sheets. Telemetry and annotations remain forensic-only and may not become input to Section 2, Section 3, Section 14, truth calculations, or safety gates.
