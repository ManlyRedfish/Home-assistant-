# V6 Telemetry Schema Proposal

This document outlines the proposed `VTherm_Launch_Data_v6` evidence-layer schema. It represents a planning target for a future implementation of event-driven telemetry within the Moose House architecture.

## 1. Why V6 Exists

V6 exists to transition the telemetry layer from a state-based, wide-table architecture to a narrow, event-oriented architecture. The proposed schema aims to capture discrete observability events (e.g., state transitions, specific sensor measurements) as structured, uniform payloads. This improves data density, simplifies external analysis, and ensures that the evidence layer remains robust as new devices are added.

## 2. The Problem with V5

The V5 schema suffers from wide-table and "zombie-column" growth.

- **Wide-Table Sprawl:** Historically, every new entity or measurement required adding new columns to the logging sheet.
- **Zombie Columns:** Because not all sensors update simultaneously, wide rows are mostly filled with empty or duplicated cells (zombie columns), making the dataset sparse and inefficient.
- **Maintenance Burden:** Adding or removing devices requires restructuring the downstream Google Sheets, which does not scale well as the Moose House architecture expands.

## 3. Proposed Schema Definition

The proposed V6 schema utilizes a narrow, standardized structure for all telemetry events.

| Field               | Type           | Description                                                                                       |
| :------------------ | :------------- | :------------------------------------------------------------------------------------------------ |
| **Timestamp**       | ISO8601 String | The exact time the event occurred (e.g., `2023-10-27T14:32:00Z`).                                 |
| **SchemaVersionID** | String         | Identifies the schema version used (e.g., `v6.0`).                                                |
| **DeviceID**        | String         | A stable identifier for the physical device or logical controller.                                |
| **SourceEntity**    | String         | The specific Home Assistant entity originating the event.                                         |
| **Measurement**     | String         | The property being recorded (e.g., `temperature`, `hvac_action`, `co2`).                          |
| **Value**           | String/Number  | The recorded state or measurement value.                                                          |
| **Unit**            | String         | The unit of measurement (e.g., `°F`, `ppm`, `boolean`), if applicable.                            |
| **Quality/Status**  | String         | Confidence or status of the reading (e.g., `good`, `stale`, `unavailable`).                       |
| **EventKind**       | String         | Categorization of the event (e.g., `state_transition`, `periodic_observation`, `safety_trigger`). |
| **Notes/Context**   | String         | (Optional) Additional contextual data or metadata.                                                |

## 4. Example Rows

The following table provides realistic, observability-only examples illustrating how Moose House data maps to the proposed schema.

| Timestamp              | SchemaVersionID | DeviceID               | SourceEntity                                     | Measurement   | Value     | Unit      | Quality/Status | EventKind              | Notes/Context                  |
| :--------------------- | :-------------- | :--------------------- | :----------------------------------------------- | :------------ | :-------- | :-------- | :------------- | :--------------------- | :----------------------------- |
| `2023-10-27T10:00:00Z` | `v6.0`          | `daikin_mini_split_lr` | `climate.living_room_vtherm_example`             | `hvac_action` | `heating` | `mode`    | `good`         | `state_transition`     | `Triggered by setpoint change` |
| `2023-10-27T10:05:00Z` | `v6.0`          | `netatmo_lr`           | `sensor.living_room_temperature_example`         | `temperature` | `68.5`    | `°F`      | `good`         | `periodic_observation` |                                |
| `2023-10-27T10:15:00Z` | `v6.0`          | `temp_probe_mb`        | `sensor.master_bedroom_temp_example`             | `temperature` | `55.0`    | `°F`      | `good`         | `safety_trigger`       | `Safety-floor observation`     |
| `2023-10-27T10:20:00Z` | `v6.0`          | `apollo_msr_1`         | `sensor.apollo_msr_co2_example`                  | `co2`         | `850`     | `ppm`     | `good`         | `periodic_observation` | `Observability-only`           |
| `2023-10-27T10:25:00Z` | `v6.0`          | `apollo_msr_1`         | `binary_sensor.living_room_msr_presence_example` | `presence`    | `on`      | `boolean` | `good`         | `state_transition`     | `Observability-only`           |

## 5. Schema Violation Handling

When a payload violates the schema, the event must be caught and handled gracefully to prevent poisoning the dataset.

- **Missing `SchemaVersionID`:** Reject the payload. Log an error locally indicating that the payload could not be routed.
- **Missing `DeviceID`:** Reject the payload. Device attribution is required for all V6 rows to maintain data integrity.
- **Wrong Value Type:** If the value cannot be coerced into the expected format for the given measurement (e.g., expecting a float for temperature but receiving "unknown"), flag the `Quality/Status` as `invalid_type` and record the raw string.
- **Unknown Measurement:** Accept the payload but flag the `Quality/Status` as `unknown_measurement`. Ensure the system logs a warning to update the allowed measurement registry.

### JSON Payload Examples

#### Valid Payload Example

```json
{
  "Timestamp": "2023-10-27T10:00:00Z",
  "SchemaVersionID": "v6.0",
  "DeviceID": "daikin_mini_split_lr",
  "SourceEntity": "climate.living_room_vtherm_example",
  "Measurement": "hvac_action",
  "Value": "heating",
  "Unit": "mode",
  "Quality/Status": "good",
  "EventKind": "state_transition",
  "Notes/Context": "Triggered by setpoint change"
}
```

#### Invalid Payload Example (Schema Violation)

```json
{
  "Timestamp": "2023-10-27T10:30:00Z",
  "DeviceID": "unknown_device",
  "SourceEntity": "sensor.broken_sensor_example",
  "Measurement": "temperature",
  "Value": "unavailable",
  "Unit": "°F"
  // Missing SchemaVersionID, Quality/Status, and EventKind
}
```

## 6. Debounce & Quota Considerations

Since Google Sheets serves as the primary data lake, specific planning constraints must be respected:

- **10 Million Cell Limit:** A Google Sheets workbook has a hard limit of 10 million cells. The narrow V6 schema reduces sparse data, optimizing cell usage.
- **API Quotas:** Google Sheets API limits are a firm planning constraint. We treat **60 write requests per minute per user** and **300 write requests per minute per project** as practical ceilings.
- **Write Pressure:** Designs must avoid writing every sensor every few seconds. V6 reduces write pressure by strongly preferring event-oriented rows over continuous polling.
- **Debouncing Transitions:** HVAC transition logging should include debouncing to prevent noisy state-flapping from exhausting quotas. A **500ms debounce** is the planning target from prior research.

_(Note: This proposal does not implement debounce logic yet, but outlines the requirement for the future implementation.)_

## 7. What This Does NOT Do Yet

To ensure a safe and phased rollout, this V6 proposal is strictly an evidence-layer planning document.

- **Docs-Only:** This is a documentation proposal only.
- **No Runtime YAML Changes:** No Home Assistant configurations or automations are modified.
- **No Google Sheets Automation Changes:** Downstream App Script or webhooks remain untouched.
- **No V5 Migration/Removal:** V5 wide-table logging will remain fully active. V6 will not replace V5 at this time.
- **No Data Export Behavior Changes:** Existing telemetry pipelines continue functioning as normal.
- **No Control-Loop Changes:** MSR data and other observability-only metrics are strictly for telemetry and are **not** made part of the HVAC control loops.
