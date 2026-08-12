"""Test-only execution seam for the reviewed, unwired zone artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

import yaml

from parent_orchestration_harness import (
    OrchestrationReport,
    ZONE_ORDER,
    ZoneFailure,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ZONE_ARTIFACTS = {
    "Master": REPOSITORY_ROOT / "supervisor_zones/master.yaml",
    "Lincoln": REPOSITORY_ROOT / "supervisor_zones/lincoln.yaml",
    "Lilly": REPOSITORY_ROOT / "supervisor_zones/lilly.yaml",
    "Living Room": REPOSITORY_ROOT / "supervisor_zones/living_room.yaml",
}


@dataclass(frozen=True)
class ClimateServiceCall:
    zone: str
    service: str
    target: object
    data: object


def _climate_actions(node: object) -> Iterator[dict]:
    if isinstance(node, list):
        for item in node:
            yield from _climate_actions(item)
    elif isinstance(node, dict):
        action = node.get("action")
        if isinstance(action, str) and action.startswith("climate."):
            yield node
        else:
            for value in node.values():
                yield from _climate_actions(value)


def load_zone_calls(zone: str) -> tuple[ClimateServiceCall, ...]:
    """Load one reviewed artifact and enumerate its climate calls in YAML order."""

    document = yaml.safe_load(ZONE_ARTIFACTS[zone].read_text(encoding="utf-8"))
    return tuple(
        ClimateServiceCall(zone, action["action"], action.get("target"), action.get("data"))
        for action in _climate_actions(document)
    )


def run_parent(executor: Callable[[ClimateServiceCall], None]) -> OrchestrationReport:
    """Execute each complete zone unit sequentially, containing zone failures."""

    invoked: list[str] = []
    successful: list[str] = []
    failures: list[ZoneFailure] = []

    for zone in ZONE_ORDER:
        invoked.append(zone)
        try:
            for call in load_zone_calls(zone):
                executor(call)
        except Exception as exception:
            failures.append(ZoneFailure(zone, exception))
        else:
            successful.append(zone)

    return OrchestrationReport(tuple(invoked), tuple(successful), tuple(failures))
