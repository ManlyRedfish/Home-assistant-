# Moose House HVAC Research Platform

This repository contains an experimental HVAC orchestration framework built on Home Assistant.

## Core Philosophy

This is **not** a conventional thermostat project.

The system prioritizes:

- evidence-driven experimentation
- observability
- telemetry-first architecture
- graceful degradation
- modular design
- operational stability

Avoid:

- naive bang-bang logic
- blind averaging
- hidden state
- polling-heavy designs
- fixed HVAC bias assumptions

## Architecture Concepts

### Room Truth

Virtual environmental state generated from:

- temperature sensors
- occupancy sensors
- HVAC state
- freshness weighting
- outlier rejection

### Dynamic Bias Estimation

Mini split thermistors become biased during active HVAC cycles.
The system attempts to estimate this dynamically instead of using fixed offsets.

### Telemetry

All meaningful state transitions should be observable and loggable.

### Regression Awareness

Preserve experimental comparability whenever possible.
Avoid silently changing behavior.

## Coding Rules

- Use Home Assistant package structure.
- Add comments to YAML.
- Use aliases for automations.
- Expose debugging attributes.
- Prefer maintainability over cleverness.
- Explain **why** changes are being made.
- Preserve entity compatibility when possible.

## Testing Priorities

1. Stability
2. Observability
3. Graceful failure handling
4. Experimental repeatability
5. Performance

## Important

If architecture assumptions are unclear:
**ask instead of inventing behavior**.
