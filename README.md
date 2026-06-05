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

## Running Static Safety Tests

```bash
python -m pytest tests/
```

## Docs-only pull request guardrail

Pull requests that are intended to change documentation only should use the exact GitHub label `docs-only`.
Apply the label from the pull request sidebar after opening the PR; the docs-only guard also re-runs when the label is added or removed.

When `docs-only` is present, CI checks the complete changed-file list between the pull request base and head commits.
The guard permits Markdown documentation and documentation assets, including content stored beneath `docs/**`.

The guard blocks files and paths that can affect Home Assistant runtime behavior, executable logic, tests, CI, configuration, automations, or dependencies, including:

- `*.yaml` and `*.yml`
- `*.py`, `*.ps1`, and `*.sh`
- `configuration.yaml`, `automations.yaml`, `scripts.yaml`, `scenes.yaml`, and `secrets.yaml`
- `custom_components/**`, `packages/**`, and `blueprints/**`
- `tools/**` and `tests/**`
- `.github/workflows/**`
- `requirements*.txt`

If a docs-only PR touches any blocked path, the failed check prints every prohibited changed path so the author can either remove the label or move the runtime change to a normal PR.
Normal pull requests without the `docs-only` label are unaffected by this guard.

This guard is a repository-safety scope check only. It does not replace normal pytest CI or any other validation for non-documentation changes.
