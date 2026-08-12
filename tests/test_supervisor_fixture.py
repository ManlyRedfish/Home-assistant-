from pathlib import Path

from supervisor_fixture import SUPERVISOR_ID, ZONE_ENTITIES, load_supervisor, zone_action_groups


def test_fixture_loads_supervisor_and_identifies_all_four_zones():
    supervisor = load_supervisor(Path(__file__).parents[1] / "automations.yaml")
    groups = zone_action_groups(supervisor)

    assert supervisor["id"] == SUPERVISOR_ID
    assert tuple(groups) == ZONE_ENTITIES
    assert all(groups[entity_id] for entity_id in ZONE_ENTITIES)
    assert all(group.entity_id == entity_id for entity_id, found in groups.items() for group in found)
