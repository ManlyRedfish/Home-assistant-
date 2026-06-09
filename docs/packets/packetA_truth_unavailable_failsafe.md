# Packet A — Truth-Unavailable Cooling Failsafe

Stage-1 implementation contract for Packet A Design 1.

## Intent

The V8.3 supervisor historically converted an invalid room truth sensor to the
same `float(70)` fallback used for ordinary numeric control. During cooling, that
can hide total truth failure and let a mini-split remain in `cool` through the
healthy-state deadband HOLD branch.

Packet A keeps the healthy deadband doctrine intact, but adds an explicit truth
validity layer:

1. The supervisor computes per-zone truth-validity variables before any
   `float(70)` temperature fallback is used for control.
2. Cooling `hvac_mode` templates are OFF-biased when the associated truth sensor
   is invalid.
3. An independent Section 3 failsafe forces a climate entity OFF if its truth
   sensor remains invalid for two minutes while the climate entity reports
   `cool`.
4. A startup/periodic reconciliation sweep closes the restart race without
   adding inhibit helpers or authorizing cooling.

## Validity contract

A room truth sensor is valid for Packet A control only when it parses as a finite
ordinary temperature in the supported operating envelope:

```jinja
{% set x = states('<truth_entity>') | float(none) %}
{{ x is not none and x == x and -90 <= x <= 200 }}
```

The invalid form is the exact complement used by the failsafe triggers and
reconciliation sweep:

```jinja
{% set x = states('<truth_entity>') | float(none) %}
{{ x is none or x != x or x < -90 or x > 200 }}
```

This rejects `unknown`, `unavailable`, non-numeric strings, NaN, positive
infinity, negative infinity, and implausible temperatures outside `[-90, 200]`.

## Non-goals / exclusions

Packet A does not change thresholds, setpoints, away behavior, the master sleep
band, Packet B smoothing/control architecture, V9 cooldown work,
`configuration.yaml`, hardware mappings, or the four-zone topology. It does not
treat template firing sensors as physical compressor proof.

## Stage-2 live verification requirement

The repository cannot resolve the live Home Assistant entity suffix situation.
Before deployment, Codex inside HA must verify the live supervisor automation
entity and any `_rev_b` suffix behavior against the approved repository diff.
