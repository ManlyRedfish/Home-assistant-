"""Deterministic test-only model of parent-to-zone orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


ZONE_ORDER = ("Master", "Lincoln", "Lilly", "Living Room")


@dataclass(frozen=True)
class ZoneFailure:
    zone: str
    exception: Exception


@dataclass(frozen=True)
class OrchestrationReport:
    invoked: tuple[str, ...]
    successful: tuple[str, ...]
    failures: tuple[ZoneFailure, ...]


def run_parent(
    configured_exceptions: Mapping[str, Exception] | None = None,
) -> OrchestrationReport:
    """Invoke all abstract zones in order, recording rather than hiding failures."""

    configured_exceptions = configured_exceptions or {}
    invoked: list[str] = []
    successful: list[str] = []
    failures: list[ZoneFailure] = []

    for zone in ZONE_ORDER:
        invoked.append(zone)
        try:
            if exception := configured_exceptions.get(zone):
                raise exception
        except Exception as exception:  # The future parent contract isolates each zone.
            failures.append(ZoneFailure(zone, exception))
        else:
            successful.append(zone)

    return OrchestrationReport(tuple(invoked), tuple(successful), tuple(failures))
