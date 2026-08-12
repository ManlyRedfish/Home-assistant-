"""Small structural fixture for the current Section 2 supervisor."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import yaml


SUPERVISOR_ID = "v7_5_main_supervisor"
ZONE_ENTITIES = (
    "climate.master_bedroom_air",
    "climate.lincoln_air",
    "climate.lilly_air",
    "climate.living_room_air",
)


class MooseAutomationLoader(yaml.SafeLoader):
    """Match the custom-tag handling already used by automation tests."""


def _scalar_tag(prefix: str):
    return lambda loader, node: f"{prefix}_{loader.construct_scalar(node)}"


MooseAutomationLoader.add_constructor("!secret", _scalar_tag("SECRET"))
MooseAutomationLoader.add_constructor("!include", _scalar_tag("INCLUDE"))
MooseAutomationLoader.add_constructor("!input", _scalar_tag("INPUT"))
MooseAutomationLoader.add_constructor(
    "!include_dir_merge_list", lambda loader, node: []
)
MooseAutomationLoader.add_constructor("!include_dir_named", lambda loader, node: [])


@dataclass(frozen=True)
class ZoneActionGroup:
    """An outermost single-zone action subtree and its deterministic YAML path."""

    entity_id: str
    path: tuple[str | int, ...]
    action: dict[str, Any]
    alias: str | None
    continue_on_error: bool


def load_supervisor(path: Path) -> dict[str, Any]:
    automations = yaml.load(path.read_text(encoding="utf-8"), Loader=MooseAutomationLoader)
    return next(automation for automation in automations if automation.get("id") == SUPERVISOR_ID)


def _targets(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        entity_id = (value.get("target") or {}).get("entity_id")
        if isinstance(entity_id, str):
            found.add(entity_id)
        elif isinstance(entity_id, list):
            found.update(entity_id)
        for child in value.values():
            found.update(_targets(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_targets(child))
    return found


def _walk_action_boundaries(
    value: Any, path: tuple[str | int, ...] = ()
) -> Iterator[ZoneActionGroup]:
    if isinstance(value, dict):
        targets = _targets(value) & set(ZONE_ENTITIES)
        is_action_group = any(key in value for key in ("if", "choose", "repeat", "parallel"))
        if is_action_group and len(targets) == 1:
            entity_id = next(iter(targets))
            # The reviewed artifact is the zone policy subtree. Parent-only
            # orchestration metadata is intentionally kept alongside, rather
            # than folded into, that extracted policy contract.
            action = {
                key: child
                for key, child in value.items()
                if key not in ("alias", "continue_on_error")
            }
            yield ZoneActionGroup(
                entity_id,
                path,
                action,
                value.get("alias"),
                value.get("continue_on_error") is True,
            )
            return
        for key, child in value.items():
            yield from _walk_action_boundaries(child, path + (key,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_action_boundaries(child, path + (index,))


def zone_action_groups(supervisor: dict[str, Any]) -> dict[str, tuple[ZoneActionGroup, ...]]:
    """Index the supervisor's outermost single-zone execution boundaries."""

    groups = {entity_id: [] for entity_id in ZONE_ENTITIES}
    for group in _walk_action_boundaries(supervisor.get("action", []), ("action",)):
        groups[group.entity_id].append(group)
    return {entity_id: tuple(found) for entity_id, found in groups.items()}
