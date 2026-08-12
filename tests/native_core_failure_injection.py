"""Native Home Assistant Core proof for parent zone-failure isolation.

This is a synthetic action-engine topology, not an execution of automations.yaml.
It must be run inside the pinned Home Assistant Core container documented in
scripts/run_native_core_failure_injection.sh.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
import tempfile
from typing import Any

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import Context, Event, HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, script, trace


ZONES = ("master", "lincoln", "lilly", "living_room")


def boundary(zone: str, *, off_via_else: bool = False) -> dict[str, Any]:
    """Build the F1-shaped isolation boundary for one synthetic zone."""
    service_action: dict[str, Any] = {
        "alias": f"{zone}: climate action",
        "action": "climate.set_temperature",
        "target": {"entity_id": f"climate.{zone}_air"},
        "data": {"temperature": 61},
    }

    zone_boundary: dict[str, Any] = {
        "alias": f"{zone}: isolated boundary",
        "continue_on_error": True,
        "if": [
            {
                "condition": "template",
                "value_template": "{{ false }}" if off_via_else else "{{ true }}",
            }
        ],
        "then": [
            service_action,
            {
                "event": "g_native_fan_action",
                "event_data": {"zone": zone},
            },
        ],
    }
    if off_via_else:
        zone_boundary["else"] = [
            {
                "alias": f"{zone}: off action",
                "action": "climate.set_hvac_mode",
                "target": {"entity_id": f"climate.{zone}_air"},
                "data": {"hvac_mode": "off"},
            }
        ]
    return zone_boundary


def sequence(lilly_off: bool = False) -> list[dict[str, Any]]:
    """Return a synthetic parent sequence with four independent boundaries."""
    actions: list[dict[str, Any]] = []
    for zone in ZONES:
        actions.extend(
            (
                {
                    "event": "g_native_boundary_entered",
                    "event_data": {"zone": zone},
                },
                boundary(zone, off_via_else=lilly_off and zone == "lilly"),
            )
        )
    return actions


def entity_zone(call: ServiceCall) -> str:
    """Extract the synthetic zone name from a climate service target."""
    entity_ids = call.data[ATTR_ENTITY_ID]
    entity_id = entity_ids[0] if isinstance(entity_ids, list) else entity_ids
    return entity_id.removeprefix("climate.").removesuffix("_air")


def trace_snapshot() -> tuple[set[str], dict[str, str]]:
    """Return paths and path/error pairs retained by Core's action tracer."""
    action_trace = trace.trace_get(clear=False)
    errors = {
        path: details["error"]
        for path, elements in action_trace.items()
        for element in elements
        if "error" in (details := element.as_dict())
    }
    return set(action_trace), errors


async def run_case(
    hass: HomeAssistant,
    *,
    name: str,
    failed_zones: Iterable[str],
    lilly_off: bool = False,
) -> None:
    """Execute and assert one failure-injection case through script.Script."""
    failures = set(failed_zones)
    attempted: list[tuple[str, str]] = []
    hvac_modes: list[tuple[str, str]] = []
    entered: list[str] = []
    fans: list[str] = []

    @callback
    def climate_service(call: ServiceCall) -> None:
        zone = entity_zone(call)
        attempted.append((zone, call.service))
        if call.service == "set_hvac_mode":
            hvac_modes.append((zone, call.data["hvac_mode"]))
        if zone in failures:
            raise HomeAssistantError(f"injected {zone} set_temperature failure")

    @callback
    def capture_entered(event: Event) -> None:
        entered.append(event.data["zone"])

    @callback
    def capture_fan(event: Event) -> None:
        fans.append(event.data["zone"])

    hass.services.async_register("climate", "set_temperature", climate_service)
    hass.services.async_register("climate", "set_hvac_mode", climate_service)
    remove_entered = hass.bus.async_listen("g_native_boundary_entered", capture_entered)
    remove_fan = hass.bus.async_listen("g_native_fan_action", capture_fan)

    trace.trace_clear()
    validated = cv.SCRIPT_SCHEMA(sequence(lilly_off=lilly_off))
    proof = script.Script(hass, validated, name, "g_native_proof")
    await proof.async_run(context=Context())
    await hass.async_block_till_done()

    remove_entered()
    remove_fan()
    hass.services.async_remove("climate", "set_temperature")
    hass.services.async_remove("climate", "set_hvac_mode")

    assert entered == list(ZONES), (name, entered)
    assert [zone for zone, _ in attempted] == list(ZONES), (name, attempted)
    expected_fans = [
        zone for zone in ZONES if zone not in failures and not (lilly_off and zone == "lilly")
    ]
    assert fans == expected_fans, (name, fans)

    if lilly_off:
        assert ("lilly", "set_hvac_mode") in attempted, (name, attempted)
        assert ("lilly", "off") in hvac_modes, (name, hvac_modes)
        assert "lilly" not in fans, (name, fans)

    paths, errors = trace_snapshot()
    for zone in failures:
        expected = f"injected {zone} set_temperature failure"
        assert expected in errors.values(), (name, errors)
    assert set(errors.values()) == {
        f"injected {zone} set_temperature failure" for zone in failures
    }, (name, errors)
    for index, zone in enumerate(ZONES):
        parent_path = str(index * 2 + 1)
        false_else = lilly_off and zone == "lilly"
        climate_path = f"{parent_path}/else/0" if false_else else f"{parent_path}/then/0"
        fan_path = f"{parent_path}/then/1"
        assert climate_path in paths, (name, zone, paths)
        assert (fan_path in paths) is (zone not in failures and not false_else), (name, zone, paths)
        if false_else:
            assert f"{parent_path}/if/condition/0" in paths, (name, zone, paths)
            assert f"{parent_path}/then/0" not in paths, (name, zone, paths)

    print(f"PASS {name}: failures={sorted(failures)} entered={entered} fans={fans}")


async def main() -> None:
    """Run all G cases against a single native Core instance."""
    with tempfile.TemporaryDirectory(prefix="g-native-core-") as config_dir:
        hass = HomeAssistant(config_dir)
        try:
            await run_case(hass, name="master_failure", failed_zones={"master"})
            await run_case(
                hass,
                name="lincoln_failure_lilly_off",
                failed_zones={"lincoln"},
                lilly_off=True,
            )
            await run_case(hass, name="lilly_failure", failed_zones={"lilly"})
            await run_case(
                hass,
                name="multiple_failures",
                failed_zones={"master", "lilly"},
            )
            await run_case(hass, name="all_failures", failed_zones=set(ZONES))
        finally:
            await hass.async_stop(force=True)

    print("G_NATIVE_STATUS: PASS")


if __name__ == "__main__":
    asyncio.run(main())
