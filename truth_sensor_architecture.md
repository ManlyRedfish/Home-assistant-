# Truth Sensor Architecture

## Purpose

Moose House Climate uses custom "truth sensors" instead of relying on:

- thermostat-integrated thermistors
- single room probes
- naive averaging

The goal is to create stable, evidence-based environmental state estimation suitable for HVAC orchestration and long-term experimentation.

---

# Core Philosophy

The system prioritizes:

- stability
- graceful degradation
- observability
- telemetry integrity
- regression resistance

The system intentionally avoids:

- blind averaging
- equal-weight assumptions
- single-point failure dependence
- hidden filtering logic

---

# Truth Sensor Pipeline

Physical Sensors
→ Truth Sensors
→ Smoothed Sensors
→ Control Wrappers
→ HVAC Supervisor
→ Telemetry Logging

---

# Sensor Freshness

All truth sensors implement:

- freshness validation
- stale sensor rejection
- availability gating

Standard staleness threshold:

- 7200 seconds (2 hours)

Stale sensors are excluded from weighted calculations.

Freshness is measured by **report time** (`last_reported`), not value-change
time (`last_changed`). A stable sensor that keeps reporting the same temperature
for hours is still fresh; only a sensor that has stopped reporting (or is
`unavailable`/`unknown`, or fails value-sanity) is treated as stale. Using
`last_changed` here would false-stale a healthy but thermally stable room. See
`docs/comfort_band_and_truth_confidence_plan.md` and `docs/5_runtime_layer.md`
§7.9.

---

# Weighting Philosophy

Human-space sensors are prioritized.

Mini-split internal thermistors are intentionally low-weight because:

- they become thermally biased during operation
- they do not represent occupied room air accurately
- they over-report during heating
- they under-report during cooling

Typical Samsung weighting:

- 0.20 temperature
- 0.25 humidity

---

# Lincoln Pilot Architecture

Lincoln's room is the pilot environment for:

- outlier rejection
- contributor diagnostics
- sensor rejection telemetry

Features:

- base-mean outlier detection
- 3°F rejection threshold
- contributor tracking
- rejected-sensor diagnostics

Samsung internal sensors are excluded from outlier detection because their thermal bias is intentional and expected.

---

# Smoothed Sensor Layer

Truth sensors feed lowpass-filtered smoothing sensors.

Purpose:

- reduce control jitter
- reduce compressor short cycling
- stabilize automation behavior

Current filter:

- lowpass
- time_constant=10
- precision=2

---

# Control Wrappers

Control wrapper sensors exist because:

- Home Assistant UI management benefits from stable wrappers
- future orchestration layers may migrate without breaking entity compatibility

The wrapper architecture remains useful for compatibility and migration stability.

---

# Experimental Philosophy

This system is:

- telemetry-first
- iterative
- evidence-driven

Changes should:

- preserve observability
- preserve telemetry continuity
- preserve regression comparability

Avoid:

- silent behavior changes
- architecture rewrites without evidence
- premature complexity

---

# Important Dependencies

Critical consumers of truth sensors:

- Main Supervisor
- Safety Gates
- Runtime Tracking
- Telemetry Pipeline
- Presence Logic
- HVAC Transition Logging

Breaking truth sensors breaks the entire orchestration stack.
