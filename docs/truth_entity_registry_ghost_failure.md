# Truth Entity Registry Ghost Failure (Lincoln/Lilly)

## Failure Signature

This failure is caused by Home Assistant restoring ghost entities into canonical truth IDs while the live template entities are forced to `*_2` IDs.

Observed broken pattern:

- Canonical truth entities (`sensor.lincoln_s_room_temperature_truth`, `sensor.lilly_s_room_temperature_truth`) exist as `restored: true` and `state: unavailable`.
- Live truth entities appear as `_2` suffixes.
- Canonical smoothed entities still point at canonical truth IDs, so they become `unknown`.
- Canonical control wrappers become unavailable because smoothed truth is unavailable.

## Canonical Entity IDs (must remain stable)

- `sensor.lincoln_s_room_temperature_truth`
- `sensor.lilly_s_room_temperature_truth`
- `sensor.lincoln_s_room_temperature_smoothed`
- `sensor.lilly_s_room_temperature_smoothed`
- `sensor.lincoln_s_room_temperature_control`
- `sensor.lilly_s_room_temperature_control`

## Test-Harness Coverage Added

`tests/test_truth_entity_registry_integrity.py` now checks exported HA state snapshots for the following invariants:

1. A required canonical truth/smoothed/control entity must not be `restored: true`.
2. No canonical climate truth entity may have a live `*_2` duplicate.
3. Smoothed entities must not be unavailable because they are linked to unavailable/restored canonical truth.
4. If raw room probes are live, canonical truth/smoothed/control must not be unavailable.

Fixtures:

- `tests/fixtures/ha_states_truth_entity_broken.json` (reproduces failure)
- `tests/fixtures/ha_states_truth_entity_healthy.json` (expected healthy behavior)

## Runtime Repair (outside git)

Home Assistant entity registry cleanup is the runtime fix:

1. Delete restored ghost canonical entities.
2. Rename live `_2` entities back to canonical IDs.
3. Verify smoothed/control wrappers recover and Section 2/3 consumers stop seeing unknown truth.

No YAML rewrite to `_2` should be performed; canonical IDs are the long-term contract.


## Final confirmed cause

Entity registry drift was caused by a `unique_id` slug mismatch between restored historical entries and current template definitions.

Old restored canonical entries were using apostrophe-stripped `unique_id` values:

- `lincolns_room_temperature_truth_v3`
- `lillys_room_temperature_truth_v3`
- `lincolns_room_humidity_truth_v3`
- `lillys_room_humidity_truth_v3`
- `lincolns_room_temperature_control_v3`
- `lillys_room_temperature_control_v3`

Current live template entities used corrected apostrophe-slug `unique_id` values:

- `lincoln_s_room_temperature_truth_v3`
- `lilly_s_room_temperature_truth_v3`
- `lincoln_s_room_humidity_truth_v3`
- `lilly_s_room_humidity_truth_v3`
- `lincoln_s_room_temperature_control_v3`
- `lilly_s_room_temperature_control_v3`

Home Assistant treated those as different registry objects. That forced live entities to `*_2` entity IDs while restored ghosts retained the canonical IDs.

## Verified runtime repair

Runtime remediation that was executed in live Home Assistant:

1. Deleted old restored canonical registry entries.
2. Renamed live `*_2` entries back to canonical entity IDs.
3. Re-ran the truth-chain verification export.

Verification result after repair:

- `overall_status: PASS`
- `problems: []`
