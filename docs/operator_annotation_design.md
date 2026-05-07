# Operator Annotation Design — Out-of-Band Forensic Workflow

**Doc Date:** 2026-05-06
**Document Role:** Architecture Design Document (Docs-Only)
**Status:** Proposed

---

## 1. Purpose

This document outlines the design for an out-of-band forensic annotation workflow for Moose House telemetry. Its primary goal is to provide a structured method for operators to log external confounders—such as manual overrides, maintenance, or environmental anomalies—that impact telemetry but are invisible to the Home Assistant (HA) state engine.

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

## 4. Proposed Google Sheets / Apps Script Workflow

The proposed workflow utilizes Google Forms/Sheets as a decoupled, out-of-band system.

### 4.1 Logical Workflow

1. **Submission:** An operator encounters a confounder (e.g., opened a window) and submits a Google Form from their mobile device or workstation.
2. **Ingestion:** The Google Form directly populates a new row in a dedicated "Annotations" sheet within the telemetry Google Workbook.
3. **Validation (Apps Script):** A Google Apps Script triggers on form submission. It performs basic validation (e.g., ensuring `Start_Time` is before `End_Time`) and standardizes formatting.
4. **Storage:** The validated annotation rests in the Google Sheet, entirely isolated from Home Assistant.

### 4.2 Annotation Schema

The following fields must be captured for each annotation:

| Field          | Type     | Description                                                                       |
| -------------- | -------- | --------------------------------------------------------------------------------- |
| Timestamp      | DateTime | Automatically generated when the form is submitted.                               |
| Operator_ID    | String   | Identifier of the person making the annotation (e.g., "Jules").                   |
| Event_Kind     | Enum     | Categorized type of event (see allowed values below).                             |
| Start_Time     | DateTime | Exact time the event began.                                                       |
| End_Time       | DateTime | Exact time the event concluded (can be left null if ongoing, though discouraged). |
| Forensic_Notes | Text     | Free-form explanation of the event and its context.                               |

### 4.3 Allowed Event_Kind Values

To ensure consistent filtering during analysis, `Event_Kind` should be restricted via a dropdown to the following values:

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

### 4.4 Conceptual Apps Script Flow

_Note: The following is conceptual pseudocode to illustrate the validation step, not deployable production code._

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

Current V5-style analysis commonly uses 15-minute windows (e.g., :00, :15, :30, :45), while future V6 event telemetry may support more granular joins.

Annotations are recorded with exact `Start_Time` and `End_Time`. During analysis (typically in pandas, BigQuery, or a secondary Apps Script process):

- Analysis scripts will perform a timeline overlap or "snap" to join the continuous annotation period against the discrete telemetry windows.
- Any 15-minute telemetry window that intersects the `[Start_Time, End_Time]` interval of an annotation is flagged with that annotation's `Event_Kind` and `Forensic_Notes`.
- This allows analysts to filter out contaminated windows (e.g., dropping all rows where `Event_Kind == 'Manual Override'`) without altering the original V5 data structure.

## 6. Forbidden Paths

To protect the architecture, the following actions are explicitly forbidden regarding this annotation workflow:

- **NO Home Assistant Helpers:** Do not create `input_text`, `input_boolean`, or any other helper entities in HA to track annotations.
- **NO Webhooks:** Do not expose webhooks in HA to receive annotation payloads.
- **NO Automations:** Do not write HA automations that trigger off, or interact with, annotation data.
- **NO Runtime YAML Changes:** `configuration.yaml`, `automations.yaml`, and other runtime files must remain untouched by this design.
- **NO State Machine Triggers:** Annotations must never trigger, pause, or alter Home Assistant state machines.
- **NO Event Bus Routing:** Do not route annotations through the HA event bus. They must remain entirely out-of-band.
