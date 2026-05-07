# Apollo MSR Observability Validation Checklist

## Purpose

To document how Apollo MSR sensors should be validated during an initial observation phase before any future use beyond pure observability. This document provides standardized guidelines for tracking entity availability, verifying CO2 presence, tuning mmWave configurations, and capturing false positive/negative presence data.

## Observability-Only Doctrine

All Apollo MSR sensors are currently strictly designated as **observability-only** devices within the Moose House architecture.

As explicitly codified in the [Startup Canon](1_startup_canon.md) and [Runtime Layer](5_runtime_layer.md), MSR-2 DPS310 sensors (temperature, pressure, etc.) are actively excluded from all truth calculations due to historical hardware failures. Any MSR telemetry introduced to the platform must exclusively be used for human observation or data logging and must not interlock with or influence core HVAC control loops.

## Forbidden Uses

- **No HVAC Control:** MSR entities must not be used as triggers, conditions, or data sources for HVAC automations.
- **No Truth Layer Impact:** Do not make DPS310, MSR temperature, pressure, CO2, or presence part of the Truth Layer calculation.
- **No Assumptions of Hardware Features:** Do not assume a given MSR device exposes CO2 unless verified.
- **No State Alteration:** MSR sensors must not mutate the state of the climate control systems or related logic.

## Entity Inventory Checklist

_Identify and verify all exposed entities for each MSR device. Mark unknowns as "needs verification"._

| Room            | Device          | Presence Entity                          | CO2 Entity           | Temperature Entity                   | Pressure/DPS310 Entity            | Verified? | Notes                                  |
| :-------------- | :-------------- | :--------------------------------------- | :------------------- | :----------------------------------- | :-------------------------------- | :-------- | :------------------------------------- |
| Living Room     | Living Room MSR | `binary_sensor.living_room_msr_presence` | [needs verification] | `sensor.living_room_msr_temperature` | `sensor.living_room_msr_pressure` | [ ]       | Example known MSR.                     |
| Lincoln's Room  | Lincoln MSR     | `binary_sensor.lincoln_msr_presence`     | [needs verification] | `sensor.lincoln_msr_temperature`     | `sensor.lincoln_msr_pressure`     | [ ]       | Do not assume Lincoln MSR exposes CO2. |
| [Template Room] | [Device Name]   | `binary_sensor.[name]_presence`          | [needs verification] | `sensor.[name]_temperature`          | `sensor.[name]_pressure`          | [ ]       | Generic Room Template.                 |

## CO2 Availability Checklist

_CO2 availability must be explicitly verified per device._

- [ ] Living Room MSR: Verify if CO2 entity exists and outputs valid ppm readings.
- [ ] Lincoln MSR: Verify if CO2 entity exists and outputs valid ppm readings.
- [ ] [Template Room] MSR: Verify if CO2 entity exists and outputs valid ppm readings.

## mmWave Tuning Notes

mmWave tuning must be validated room-by-room and adjusted based on observed false positives and false negatives.

- **Iterative Tuning:** Gate sensitivity should be adjusted incrementally.
- **Outer Gates Caution:** Outer/far gates should be treated cautiously as they may detect hallway or adjacent-room movement.
- **Desensitization:** Gates 6–8 should be reviewed for desensitization if hallway/adjacent-room false positives occur.
- **State Separation:** Static/still detection and moving detection should be logged separately where the hardware/entities allow.
- **Annotation-backed:** Tuning changes must be supported by recorded data and annotations, not memory or anecdote.

## False Positive / False Negative Log Template

_Use this structure to log anomalous presence behavior during the observability phase._

| Date/Time        | Room      | Expected State | Observed State | Potential Cause / Trigger | Tuning Adjustment Made       |
| :--------------- | :-------- | :------------- | :------------- | :------------------------ | :--------------------------- |
| YYYY-MM-DD HH:MM | Room Name | Clear          | Detected       | Hallway walking / Gate 7  | Decreased Gate 7 sensitivity |
| YYYY-MM-DD HH:MM | Room Name | Detected       | Clear          | Sitting perfectly still   | Increased Static fading time |

## DPS310 / Temperature / Pressure Warning

**WARNING:** The DPS310 sensor component on MSR-2 hardware has a documented history of failure and unreliability in this environment. Temperature, pressure, and derived metrics from these components must **strictly remain out of truth and control loops**. They are to be used for observability and comparison logging only.

## Promotion Criteria Placeholder

_This criteria outlines the minimum prerequisites for promoting an MSR sensor beyond pure observability. Promotion is strictly forbidden without meeting these criteria and acquiring explicit human approval._

- [ ] **Minimum Observation Window:** The sensor has operated in the observability layer for a defined, significant period without severe regressions.
- [ ] **Stale-State Review:** The sensor has demonstrated reliable reporting intervals without unhandled stale/unavailable states.
- [ ] **False-Positive Review:** mmWave tuning has mitigated adjacent-room or ghost presence detections.
- [ ] **False-Negative Review:** Still/static presence is reliably maintained during occupancy.
- [ ] **Truth Sensor Comparison:** Observability telemetry has been cross-referenced with existing trusted sensors (e.g., Netatmo, SwitchBot) and found mathematically agreeable or reliably offset.
- [ ] **Documented Human Approval:** A human maintainer has signed off on the promotion.
- [ ] **Separate PR:** Promotion must occur in a dedicated Pull Request.
- [ ] **Semantic Safety Tests:** Tests are in place to ensure failure of the new sensor will not destabilize the control loops.

## PR Review Checklist

_To be completed by the reviewer when evaluating PRs related to MSR configuration or tuning._

- [ ] Does this PR adhere to the "Observability-Only Doctrine"?
- [ ] Are any MSR entities introduced into HVAC automations or the Truth Layer? (If yes, REJECT).
- [ ] Are CO2 entities verified as existing before being integrated into logging dashboards?
- [ ] Are mmWave tuning adjustments documented and annotation-backed?
- [ ] Has the DPS310/Temperature warning been respected?
