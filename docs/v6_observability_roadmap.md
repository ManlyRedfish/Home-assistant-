# V6 Observability Roadmap

## 1. Summary of V5 → V6 Telemetry Direction

The transition from V5 to V6 telemetry is driven by the need to mature the Moose House observability architecture. While the V5 schema has proven useful, it is becoming too wide, brittle, and prone to "zombie columns."

The V6 schema aims to address this by becoming a cleaner, evidence-first layer. Key principles for the V6 direction include:

- **Event-Oriented Design:** Prefer narrow, event-oriented telemetry over monolithic, wide tables.
- **Schema Discipline:** Maintain strict structure with required core identifiers, such as `SchemaVersionID` and `DeviceID`.
- **Observability First:** Keep V6 strictly focused on observability and gathering evidence. This is _not_ a rewrite of the control loop.
- **Migration Strategy:** The legacy V5 schema will remain intact and will not be removed or migrated during this initial PR phase.

## 2. Existing Issue Map

The following issues are actively tracked and relate to the V6 observability and safety work:

- **#49** Living Room V8.4 boost effectiveness
- **#50** Operator annotations
- **#51** Semantic safety tests
- **#53** Apollo MSR observability
- **#54** VTherm_Launch_Data_v6 schema

## 3. Safe Phase Order

To ensure system stability, all observability and V6 work must follow this strict implementation sequence:

1. **Docs first:** Establish the engineering roadmap and constraints.
2. **Tests second:** Implement semantic safety tests before any runtime changes (#51).
3. **V6 schema scaffold third:** Define the core structure for `VTherm_Launch_Data_v6` (#54).
4. **Annotation design fourth:** Finalize the design for operator annotations without HA helpers (#50).
5. **MSR observability fifth:** Safely integrate Apollo MSR observability data without control loop promotion (#53).
6. **Runtime changes later:** Modify runtime configurations _only_ after tests and clear evidence have been established.

## 4. Non-Negotiable Guardrails

All work in this pipeline must adhere to the following strict guardrails:

- **No MSR control-loop promotion:** Apollo MSR data must remain strictly observational.
- **No HA helpers for annotations:** Operator annotations must not rely on new Home Assistant helper entities.
- **No local high-frequency event journal:** Do not implement local high-frequency SQLite/MariaDB event journaling.
- **No weakening safety gates:** Existing Section 3 safety gates must remain absolute.
- **No V8.4 effectiveness claim without evidence:** Any claims regarding the Living Room boost (#49) must be backed by clean V6 telemetry evidence.

## 5. PR Blocker Checklist

A future PR should be blocked if it:

- [ ] Promotes Apollo MSR presence, CO2, DPS310, pressure, or temperature into HVAC control.
- [ ] Adds Home Assistant helpers for operator annotations.
- [ ] Revives local high-frequency SQLite/MariaDB event journaling.
- [ ] Weakens Section 3 safety gates.
- [ ] Claims V8.4 Living Room boost effectiveness without clean telemetry evidence.
- [ ] Changes runtime YAML before semantic safety tests exist.
