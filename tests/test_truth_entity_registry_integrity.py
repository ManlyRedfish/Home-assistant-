import json
from pathlib import Path

CANONICAL_TRUTH = {
    "sensor.lincoln_s_room_temperature_truth",
    "sensor.lilly_s_room_temperature_truth",
}

CANONICAL_HUMIDITY_TRUTH = {
    "sensor.lincoln_s_room_humidity_truth",
    "sensor.lilly_s_room_humidity_truth",
}
CANONICAL_SMOOTHED = {
    "sensor.lincoln_s_room_temperature_smoothed": "sensor.lincoln_s_room_temperature_truth",
    "sensor.lilly_s_room_temperature_smoothed": "sensor.lilly_s_room_temperature_truth",
}
CANONICAL_CONTROL = {
    "sensor.lincoln_s_room_temperature_control",
    "sensor.lilly_s_room_temperature_control",
}
CANONICAL_REQUIRED = CANONICAL_TRUTH | set(CANONICAL_SMOOTHED) | CANONICAL_CONTROL

RAW_ROOM_PROBES = {
    "sensor.lincoln_s_temp_temperature",
    "sensor.lincoln_s_room_temperature_temperature",
    "sensor.lincoln_temp_temperature",
    "sensor.lincoln_air_temperature",
    "sensor.lilly_temperature",
    "sensor.lilly_room_temperature_temperature",
    "sensor.lilly_temp_temperature_2",
    "sensor.lilly_air_temperature",
}

UNAVAILABLE_STATES = {"unknown", "unavailable"}


def _load_states(fixture_name: str) -> list[dict]:
    path = Path("tests/fixtures") / fixture_name
    return json.loads(path.read_text(encoding="utf-8"))


def _map_states(states: list[dict]) -> dict[str, dict]:
    return {item["entity_id"]: item for item in states}


def _is_unavailable(item: dict | None) -> bool:
    if item is None:
        return True
    return str(item.get("state", "")).lower() in UNAVAILABLE_STATES


def _is_restored(item: dict | None) -> bool:
    if item is None:
        return False
    attrs = item.get("attributes", {}) or {}
    return bool(attrs.get("restored", False))


def _is_live_numeric(item: dict | None) -> bool:
    if item is None:
        return False
    value = str(item.get("state", "")).lower()
    if value in UNAVAILABLE_STATES:
        return False
    try:
        float(value)
        return True
    except ValueError:
        return False


def _validate_truth_entity_integrity(states: list[dict]) -> list[str]:
    by_entity = _map_states(states)
    issues: list[str] = []

    for entity_id in sorted(CANONICAL_REQUIRED):
        state = by_entity.get(entity_id)
        if _is_restored(state):
            issues.append(f"canonical entity restored:true: {entity_id}")

    for truth_entity in sorted(CANONICAL_TRUTH | CANONICAL_HUMIDITY_TRUTH):
        duplicate_id = f"{truth_entity}_2"
        if duplicate_id in by_entity:
            issues.append(f"unexpected suffixed truth entity exists: {duplicate_id}")

    for smoothed_entity, expected_source in sorted(CANONICAL_SMOOTHED.items()):
        smoothed = by_entity.get(smoothed_entity)
        source = by_entity.get(expected_source)
        source_id = ((smoothed or {}).get("attributes", {}) or {}).get("source_entity_id")

        if source_id and source_id != expected_source:
            issues.append(
                f"smoothed source mismatch: {smoothed_entity} points to {source_id}, expected {expected_source}"
            )

        if _is_unavailable(smoothed) and (_is_unavailable(source) or _is_restored(source)):
            issues.append(
                f"smoothed unavailable from unavailable/restored source: {smoothed_entity} <- {expected_source}"
            )

    any_live_raw = any(_is_live_numeric(by_entity.get(probe)) for probe in RAW_ROOM_PROBES)
    any_canonical_down = any(_is_unavailable(by_entity.get(e)) for e in CANONICAL_REQUIRED)
    if any_live_raw and any_canonical_down:
        issues.append("raw room probe live while canonical truth/smoothed/control is unavailable")

    return issues


def test_broken_fixture_flags_truth_entity_registry_failure_modes() -> None:
    issues = _validate_truth_entity_integrity(_load_states("ha_states_truth_entity_broken.json"))

    assert issues, "Expected broken fixture to produce integrity violations"
    assert any("canonical entity restored:true" in issue for issue in issues)
    assert any("unexpected suffixed truth entity exists" in issue for issue in issues)
    assert any("smoothed unavailable from unavailable/restored source" in issue for issue in issues)
    assert any("raw room probe live while canonical truth/smoothed/control is unavailable" in issue for issue in issues)


def test_healthy_fixture_passes_truth_entity_registry_integrity_checks() -> None:
    issues = _validate_truth_entity_integrity(_load_states("ha_states_truth_entity_healthy.json"))
    assert issues == []
