# Operator Annotation Design — Out-of-Band Forensic Workflow

**Doc Date:** 2026-05-07
**Document Role:** Architecture Design Document (Docs-Only)
**Status:** Adopted — sheet-side, manual. Apps Script / Form ingest remain Proposed.

---

## 0. Adopted vs. proposed at a glance

| Component                                                       | Status     |
| --------------------------------------------------------------- | ---------- |
| Sheet-side annotation surface (`supervisor_state_log`)          | **Adopted** |
| Workbook: existing **Home Assistant** Google Sheet               | **Adopted** |
| Manual operator entry into the worksheet                        | **Adopted** |
| Forensic-only join from annotations to V5/V5.5 telemetry windows | **Adopted** |
| Google Form ingest path                                         | Proposed (not implemented) |
| Apps Script validation / formatting                             | Proposed (not implemented) |
| Home Assistant helper, automation, webhook, or event-bus path   | **Forbidden** |

The current implementation is the **manual sheet-side practice**. There is **no
Apps Script in production**, **no Google Form in production**, and **no Home
Assistant integration of any kind** consuming annotation data. The Form/Apps
Script sections below remain in this document as a forward-looking design
sketch only; they are not deployed.

## 1. Purpose

This document outlines the design for an out-of-band forensic annotation workflow for Moose House telemetry. Its primary goal is to provide a structured method for operators to log external confounders—such as manual overrides, maintenance, or environmental anomalies—that impact telemetry but are invisible to the Home Assistant (HA) state engine.

The currently adopted workflow is the **manual sheet-side practice** described
in §4.0 below. The Form / Apps Script flow described in §4.1–§4.4 remains
proposed and is **not implemented**.

## 2. Why Annotations Must Remain Forensic-Only

Annotations exist exclusively to provide context during post-incident analysis or behavior modeling. They must be forensic-only to preserve the integrity of the automated system. If annotations were allowed to influence active behavior:

- They would become undocumented state, creating complex feedback loops.
- They would violate the "single source of truth" principle, where physical sensors and declared thresholds govern system actions.
- An outdated or errant annotation could suppress valid automation indefinitely.

## 3. Why Annotations Should Live Outside Home Assistant

The Home Assistant instance at Moose House is designed for orchestration, not free-text data entry or structured logging. Keeping annotations out-of-band (outside HA) is critical because:

1. **Separation of Concerns:** HA excels at reactive control loops based on discrete states. Human-entered forensic notes require a different schema and interface.
2. **System Stability:** Routing arbitrary text through the HA event bus risks polluting the state machine, triggering unintended observers, or causing database bloat.
3. **No State Pollution:** Creating `input_text` or `input_boolean` helpers inside HA invites the temptation to use them in automations. Removing them entirely removes the temptation.
4. **Resilience:** If the HA instance reboots or crashes, the forensic logs must remain accessible and intact.

## 4. Workflow

### 4.0 Adopted: manual sheet-side annotation (live)

The live operator workflow is:

1. **Worksheet:** `supervisor_state_log`, inside the existing **Home Assistant**
   Google Sheets workbook (the same workbook that holds
   `VTherm_Launch_Data_v5` and `VTherm_Launch_Data_v5_5`).
2. **Entry method:** the operator types a row directly into the worksheet.
3. **Header row (minimum):** `start_local`, `end_local`, `kind`, `note`,
   `created_at`. Additional columns (e.g., `operator_id`) are tolerated and
   should not break analysis.
4. **Recommended `kind` values:** `supervisor_disabled`,
   `manual_setpoint_nudge`, `waf_observed`, `boost_observed`, `away_window`,
   `truth_unavailable`, `stale_setpoint_artifact`, `hardware_maintenance`,
   `sensor_relocation`, `comfort_complaint`, `other`. See
   `docs/telemetry_confounders.md` §6.3 for the canonical list.
5. **Consumers:** **none in Home Assistant.** Annotations are read only by
   downstream forensic analysis (humans, notebooks, future BigQuery /
   pandas joins).
6. **Join semantics:** an annotation applies to any 15-minute V5/V5.5
   telemetry row whose timestamp overlaps `[start_local, end_local]`. Point
   annotations (no `end_local`) snap to the nearest telemetry row plus
   adjacent rows as needed. See `docs/telemetry_confounders.md` §6.4.

The manual sheet-side practice is **the** practice today. The richer
Form/Apps Script flow described below is a future design and is not
implemented.

### 4.1 Proposed Google Sheets / Apps Script Workflow (not implemented)

The following is a forward-looking design for a richer ingest path. It is
**not deployed** and must not be assumed to exist. The proposed workflow
utilizes Google Forms/Sheets as a decoupled, out-of-band system.

### 4.1.1 Logical Workflow (proposed)

1. **Submission:** An operator encounters a confounder (e.g., opened a window) and submits a Google Form from their mobile device or workstation.
2. **Ingestion:** The Google Form directly populates a new row in a dedicated "Annotations" sheet within the telemetry Google Workbook.
3. **Validation (Apps Script):** A Google Apps Script triggers on form submission. It performs basic validation (e.g., ensuring `Start_Time` is before `End_Time`) and standardizes formatting.
4. **Storage:** The validated annotation rests in the Google Sheet, entirely isolated from Home Assistant.

> Reminder: §4.1.1–§4.1.4 describe a *proposed* future ingest path. The
> currently live workflow is the manual sheet-side practice in §4.0.
> The live worksheet is `supervisor_state_log` and uses the schema in
> `docs/telemetry_confounders.md` §6.2 (`start_local`, `end_local`, `kind`,
> `note`, `created_at`), not the PascalCase schema below.

### 4.1.2 Annotation Schema (proposed; not currently in use)

The following fields would be captured for each annotation if the Form / Apps
Script ingest path were ever built. The currently adopted live schema is the
five-field snake_case schema in `docs/telemetry_confounders.md` §6.2.

| Field          | Type     | Description                                                                       |
| -------------- | -------- | --------------------------------------------------------------------------------- |
| Timestamp      | DateTime | Automatically generated when the form is submitted.                               |
| Operator_ID    | String   | Identifier of the person making the annotation (e.g., "Jules").                   |
| Event_Kind     | Enum     | Categorized type of event (see allowed values below).                             |
| Start_Time     | DateTime | Exact time the event began.                                                       |
| End_Time       | DateTime | Exact time the event concluded (can be left null if ongoing, though discouraged). |
| Forensic_Notes | Text     | Free-form explanation of the event and its context.                               |

### 4.1.3 Allowed Event_Kind Values (proposed)

To ensure consistent filtering during analysis, `Event_Kind` should be restricted via a dropdown to the following values. The live `kind` column today uses
the snake_case set in `docs/telemetry_confounders.md` §6.3.

| Event_Kind                | Usage Context                                                                    |
| ------------------------- | -------------------------------------------------------------------------------- |
| Manual Override           | Operator manually disabled supervisor or adjusted setpoints outside of doctrine. |
| Open Window               | Significant thermal envelope breach (e.g., cooling house naturally).             |
| Hardware Maintenance      | Sensor battery swap, HVAC filter cleaning, network outage.                       |
| Sensor Relocation         | Moving a Netatmo module, temporarily changing thermal truth.                     |
| Occupancy Anomaly         | Unusual heat load (e.g., large party, intense cooking).                          |
| Cleaning / Backwash Cycle | Specific high-impact household routines.                                         |
| Comfort Complaint         | WAF-driven adjustment or reported discomfort without immediate manual action.    |
| Other                     | Unforeseen confounders; requires detailed `Forensic_Notes`.                      |

### 4.1.4 Conceptual Apps Script Flow (proposed; not deployed)

_Note: The following is conceptual pseudocode to illustrate the validation step, not deployable production code. **No Apps Script is currently deployed.**_

```javascript
// NON-PRODUCTION PSEUDOCODE
function onFormSubmit(e) {
  var sheet =
    SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Annotations");
  var rowData = e.values;

  var timestamp = rowData[0];
  var operatorId = rowData[1];
  var eventKind = rowData[2];
  var startTime = new Date(rowData[3]);
  var endTime = new Date(rowData[4]);
  var notes = rowData[5];

  // Validation Rule: Start time must precede End time
  if (endTime <= startTime) {
    markRowAsInvalid(sheet, e.range.getRow());
    return;
  }

  // Format standardization could happen here
  formatRow(sheet, e.range.getRow());
}
```

## 5. Joining Annotations to Telemetry Windows

Current V5/V5.5 analysis uses 15-minute windows (`:00`, `:15`, `:30`, `:45`).
Future V6 event telemetry may support more granular joins.

Live annotations carry `start_local`, `end_local`, and `created_at`. During analysis (humans, notebooks, future BigQuery / pandas):

- Perform a timeline overlap or "snap" to join the annotation interval against
  the discrete telemetry windows.
- Any 15-minute telemetry row whose timestamp intersects
  `[start_local, end_local]` is flagged with that annotation's `kind` and
  `note`.
- Point annotations (no `end_local`) snap to the nearest telemetry row, plus
  adjacent rows if the analyst's evaluation window plausibly extends into
  them.
- For #49 V8.4 LR boost clean-cycle evaluation, any overlapping operator
  annotation must be reviewed before classifying a cycle as `clean_auto`.
- Annotations let analysts filter out contaminated windows (e.g., drop rows
  where `kind == 'manual_setpoint_nudge'`) without altering V5/V5.5 data.

> The proposed Form / Apps Script ingest in §4.1 uses PascalCase
> (`Start_Time`, `End_Time`, `Event_Kind`, `Forensic_Notes`). Until that path
> is built, **the live schema is the snake_case schema in
> `docs/telemetry_confounders.md` §6.2** and analysts should treat that as
> authoritative.

## 6. Forbidden Paths

To protect the architecture, the following actions are explicitly forbidden regarding this annotation workflow — under both the adopted sheet-side practice and any future ingest path:

- **NO Home Assistant Helpers:** Do not create `input_text`, `input_boolean`, or any other helper entities in HA to track annotations.
- **NO Webhooks:** Do not expose webhooks in HA to receive annotation payloads.
- **NO Automations:** Do not write HA automations that trigger off, or interact with, annotation data.
- **NO Runtime YAML Changes:** `configuration.yaml`, `automations.yaml`, and other runtime files must remain untouched by this design.
- **NO State Machine Triggers:** Annotations must never trigger, pause, or alter Home Assistant state machines.
- **NO Event Bus Routing:** Do not route annotations through the HA event bus. They must remain entirely out-of-band.
- **NO Control-Loop Inputs:** Annotations are forensic labels only. They must
  never be consumed by Section 2 supervisor logic, Section 3 safety gates,
  Section 14 LR boost, or any other control surface.
- **NO Apps Script in production:** Until and unless the Form / Apps Script
  path in §4.1 is explicitly approved and reviewed, no Apps Script bound to
  this workbook may write back into HA, mutate telemetry rows, or call any
  HA-facing endpoint.
