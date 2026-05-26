"""
Apollo / MSR Observability Boundary Tests
=========================================

MSR observability-only is the default. This test prevents accidental promotion
of Apollo / MSR sensors into climate control. The Lincoln fan-only path is a
documented narrow exception, not a precedent.

Doctrine source of truth:
  docs/apollo_msr_observability_checklist.md
    §"Forbidden Uses"
    §"Explicit Exception: Lincoln Fan-Only Destratification"
  docs/v6_observability_roadmap.md §4 Non-Negotiable Guardrails
  docs/5_runtime_layer.md §7.7 Apollo / MSR Observability Boundary

Implementation summary the tests enforce:

  1. All Apollo / MSR raw entities and their documented wrappers are listed in
     ``MSR_DERIVED_ENTITIES`` below.
  2. Two automations are allowed to reference any of those entities freely,
     because they are the telemetry exporters (HA-write-only, observability):
       - ``vtherm_mega_tracker_v5``    → ``VTherm_Launch_Data_v5_5``
       - ``v8_5_hvac_provenance_logger`` → ``hvac_provenance_log``
  3. One automation is allowed to reference exactly one MSR-derived entity as
     a narrow legacy/experimental exception:
       - ``v8_comfort_fan_destratification``
         may reference ``binary_sensor.lincoln_presence_debounced_v3`` only.
       - Allowed action surface: ``climate.set_hvac_mode`` for
         ``climate.lincoln_air`` with ``hvac_mode`` in {``fan_only``, ``off``}.
       - Forbidden in this exception path: ``climate.set_temperature``,
         and any ``hvac_mode`` outside {``fan_only``, ``off``}.
  4. Safety automations and the main supervisor must remain MSR-free.
  5. A forward-looking regex sweep catches future MSR-shaped entity names that
     are not yet in ``MSR_DERIVED_ENTITIES``, so a new ``_msr_`` / ``apollo`` /
     ``dps310`` / ``mmwave`` / ``ld2410`` / ``scd40`` / ``radar_zone`` /
     ``co2`` reference cannot land in a control automation silently.

If a future PR legitimately extends this boundary (e.g., adds a new room or a
new MSR-derived wrapper), it must update both the doctrine doc and this test
in the same PR. See the PR Review Checklist at the bottom of
``docs/apollo_msr_observability_checklist.md``.
"""

import os
import re

import pytest
import yaml


# ---------------------------------------------------------------------------
# YAML loader (mirrors the other test files; preserves !secret/!include shape).
# ---------------------------------------------------------------------------
class MooseMSRLoader(yaml.SafeLoader):
    pass


def _secret(loader, node):
    return f"SECRET_{node.value}"


def _include(loader, node):
    return f"INCLUDE_{node.value}"


def _input(loader, node):
    return f"INPUT_{node.value}"


def _include_dir_merge_list(loader, node):
    return []


MooseMSRLoader.add_constructor("!secret", _secret)
MooseMSRLoader.add_constructor("!include", _include)
MooseMSRLoader.add_constructor("!input", _input)
MooseMSRLoader.add_constructor("!include_dir_merge_list", _include_dir_merge_list)
MooseMSRLoader.add_constructor("!include_dir_named", _include_dir_merge_list)


# ---------------------------------------------------------------------------
# Allow-list and entity inventory.
# ---------------------------------------------------------------------------

# Telemetry exporters: HA-write-only, observability, may freely reference
# MSR-derived entities as data values being shipped to Google Sheets.
ALLOWED_MSR_TELEMETRY_AUTOMATIONS = {
    "vtherm_mega_tracker_v5",
    "v8_5_hvac_provenance_logger",
}

# The single narrow legacy/experimental exception (§Explicit Exception in
# docs/apollo_msr_observability_checklist.md).
LINCOLN_FAN_EXCEPTION_AUTOMATION = "v8_comfort_fan_destratification"
LINCOLN_FAN_EXCEPTION_ENTITY = "binary_sensor.lincoln_presence_debounced_v3"
LINCOLN_FAN_EXCEPTION_CLIMATE = "climate.lincoln_air"
LINCOLN_FAN_EXCEPTION_ALLOWED_HVAC_MODES = {"fan_only", "off"}

# Safety automations and the main supervisor must remain MSR-free.
SAFETY_AUTOMATION_IDS = {
    "v8_2_lr_runaway_cooling_cutoff",   # 60°F LR runaway cooling cutoff
    "v8_2_master_emergency_floor",      # 58°F Master emergency cooling floor
    "v7_5_safety_ceiling_gates",        # 76°F all-season ceiling
}
MAIN_SUPERVISOR_ID = "v7_5_main_supervisor"

# Apollo / MSR raw sensors and their documented wrappers (configuration.yaml).
# If a new MSR-derived entity is introduced, add it here AND update the
# Apollo MSR observability checklist in the same PR.
MSR_DERIVED_ENTITIES = frozenset({
    # Raw Apollo MSR sensors
    "binary_sensor.living_room_msr_radar_zone_3_occupancy",
    "binary_sensor.lincoln_msr_radar_zone_3_occupancy",
    "sensor.living_room_msr_co2",
    "sensor.lincoln_msr_dps310_temperature",
    "sensor.lincoln_msr_dps310_pressure",
    "sensor.lincoln_msr_esp_temperature",
    # Documented wrappers that derive from Apollo MSR data
    # (configuration.yaml Section 2 debounced presence + Section 3 CO2 truth +
    # Section 11 history_stats counters).
    "binary_sensor.living_room_presence_debounced_v3",
    "binary_sensor.lincoln_presence_debounced_v3",
    "sensor.living_room_co2_truth",
    "sensor.lr_presence_today",
    "sensor.lincoln_presence_today",
})

# Forward-looking sweep: catches future MSR-shaped tokens that are not yet
# enumerated in MSR_DERIVED_ENTITIES. Keep this conservative — it is meant to
# fail loudly when a new MSR-shape entity is added so the maintainer remembers
# to update both the doctrine doc and the explicit allow-list.
MSR_PATTERN = re.compile(
    r"(msr|apollo|dps310|mmwave|ld2410|scd40|radar_zone|co2)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Fixtures and helpers.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def automations_data():
    file_path = os.path.join(
        os.path.dirname(__file__), "..", "automations.yaml"
    )
    with open(file_path, "r") as f:
        return yaml.load(f, Loader=MooseMSRLoader)


@pytest.fixture(scope="module")
def configuration_text():
    file_path = os.path.join(
        os.path.dirname(__file__), "..", "configuration.yaml"
    )
    with open(file_path, "r") as f:
        return f.read()


def _iter_action_items(action):
    """Walk a possibly-nested action sequence and yield every action dict.

    Mirrors ``tests/test_provenance_observability.py::_iter_action_items`` so
    the two boundary tests reason about the same action surface.
    """
    if action is None:
        return
    if isinstance(action, dict):
        action = [action]
    for item in action:
        if not isinstance(item, dict):
            continue
        yield item
        for nested_key in (
            "choose",
            "if",
            "repeat",
            "parallel",
            "default",
            "then",
            "else",
            "sequence",
        ):
            nested = item.get(nested_key)
            if nested is None:
                continue
            if nested_key == "choose" and isinstance(nested, list):
                for choice in nested:
                    if isinstance(choice, dict):
                        for sub in _iter_action_items(choice.get("sequence")):
                            yield sub
                continue
            if isinstance(nested, list):
                for sub in _iter_action_items(nested):
                    yield sub
            elif isinstance(nested, dict):
                for sub in _iter_action_items([nested]):
                    yield sub


def _service_of(item):
    if not isinstance(item, dict):
        return None
    return item.get("action") or item.get("service")


def _render(auto):
    """Render an automation dict to a stable YAML string for substring search."""
    return yaml.safe_dump(auto, default_flow_style=False, sort_keys=True)


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------

def test_msr_inventory_is_non_empty():
    """Sanity guard — the inventory must not silently empty itself out."""
    assert MSR_DERIVED_ENTITIES, (
        "MSR_DERIVED_ENTITIES must enumerate Apollo/MSR raw entities and "
        "their documented wrappers. An empty set would silently disable the "
        "boundary tests below."
    )


def test_msr_wrappers_match_configuration_definitions(configuration_text):
    """The documented wrappers in MSR_DERIVED_ENTITIES must actually be
    defined as MSR-derived in configuration.yaml. This catches the case
    where a wrapper is renamed or rewired to a non-MSR source — at which
    point the doctrine entry must be revisited."""
    # Lincoln debounced presence wraps the Lincoln MSR mmWave radar.
    assert (
        "lincoln_msr_radar_zone_3_occupancy" in configuration_text
        and "lincoln_presence_debounced_v3" in configuration_text
    ), (
        "Expected configuration.yaml to define "
        "binary_sensor.lincoln_presence_debounced_v3 as a wrapper around "
        "binary_sensor.lincoln_msr_radar_zone_3_occupancy. If the wiring "
        "changed, update MSR_DERIVED_ENTITIES and "
        "docs/apollo_msr_observability_checklist.md."
    )
    # LR debounced presence wraps the LR MSR mmWave radar.
    assert (
        "living_room_msr_radar_zone_3_occupancy" in configuration_text
        and "lr_presence_debounced_v3" in configuration_text
    ), (
        "Expected configuration.yaml to define the LR debounced presence "
        "template as a wrapper around "
        "binary_sensor.living_room_msr_radar_zone_3_occupancy."
    )
    # LR CO2 truth wraps the LR MSR CO2 sensor.
    assert (
        "living_room_co2_truth_v3" in configuration_text
        and "living_room_msr_co2" in configuration_text
    ), (
        "Expected configuration.yaml to define sensor.living_room_co2_truth "
        "as a wrapper around sensor.living_room_msr_co2."
    )


def test_no_msr_in_control_automations_except_lincoln_fan(automations_data):
    """No automation other than the documented telemetry exporters and the
    Lincoln fan-only exception may reference any MSR-derived entity.

    MSR observability-only is the default. This test prevents accidental
    promotion of Apollo / MSR sensors into climate control. The Lincoln
    fan-only path is a documented narrow exception, not a precedent.
    """
    failures = []
    for auto in automations_data:
        auto_id = auto.get("id")
        if auto_id in ALLOWED_MSR_TELEMETRY_AUTOMATIONS:
            continue
        rendered = _render(auto)
        offenders = sorted(
            {ent for ent in MSR_DERIVED_ENTITIES if ent in rendered}
        )
        if not offenders:
            continue
        if auto_id == LINCOLN_FAN_EXCEPTION_AUTOMATION:
            extra = [e for e in offenders if e != LINCOLN_FAN_EXCEPTION_ENTITY]
            if extra:
                failures.append(
                    f"{auto_id}: extra MSR refs beyond the documented "
                    f"exception: {extra}"
                )
            continue
        failures.append(f"{auto_id}: forbidden MSR refs: {offenders}")

    assert not failures, (
        "MSR observability-only is the default. The following automations "
        "reference Apollo/MSR-derived entities outside the allow-list:\n  - "
        + "\n  - ".join(failures)
        + "\nSee docs/apollo_msr_observability_checklist.md "
        "§\"Explicit Exception: Lincoln Fan-Only Destratification\". The only "
        f"narrow exception today is automation {LINCOLN_FAN_EXCEPTION_AUTOMATION!r} "
        f"using {LINCOLN_FAN_EXCEPTION_ENTITY!r} to gate "
        f"{LINCOLN_FAN_EXCEPTION_CLIMATE!r} between fan_only and off."
    )


def test_lincoln_fan_exception_is_present(automations_data):
    """The Lincoln fan-only exception must actually exist while the doctrine
    documents it. If the path is removed, the doctrine must be updated and
    this test (plus its allow-list constants) must be deleted in the same PR.
    """
    auto = next(
        (a for a in automations_data if a.get("id") == LINCOLN_FAN_EXCEPTION_AUTOMATION),
        None,
    )
    assert auto is not None, (
        f"Automation {LINCOLN_FAN_EXCEPTION_AUTOMATION!r} not found. If the "
        "Lincoln fan-only destratification path was removed, also remove the "
        "'Explicit Exception: Lincoln Fan-Only Destratification' section from "
        "docs/apollo_msr_observability_checklist.md and the allow-list "
        "constants in this test file."
    )
    rendered = _render(auto)
    assert LINCOLN_FAN_EXCEPTION_ENTITY in rendered, (
        f"Documented exception expects {LINCOLN_FAN_EXCEPTION_ENTITY!r} to "
        f"appear in {LINCOLN_FAN_EXCEPTION_AUTOMATION!r}. If the wiring was "
        "rewritten to use a non-MSR source, update both the doctrine doc "
        "and this test."
    )


def test_lincoln_fan_exception_does_not_use_set_temperature(automations_data):
    """The narrow exception is fan-only mode gating only. Setpoint changes
    must never depend on MSR data, so ``climate.set_temperature`` for
    ``climate.lincoln_air`` is forbidden inside the exception automation."""
    auto = next(
        (a for a in automations_data if a.get("id") == LINCOLN_FAN_EXCEPTION_AUTOMATION),
        None,
    )
    assert auto is not None, (
        f"{LINCOLN_FAN_EXCEPTION_AUTOMATION!r} not found"
    )
    offenders = []
    for item in _iter_action_items(auto.get("action")):
        if _service_of(item) != "climate.set_temperature":
            continue
        target = item.get("target") or {}
        entity = target.get("entity_id") or item.get("data", {}).get("entity_id")
        if isinstance(entity, list):
            if LINCOLN_FAN_EXCEPTION_CLIMATE in entity:
                offenders.append(item)
        elif entity == LINCOLN_FAN_EXCEPTION_CLIMATE:
            offenders.append(item)
    assert not offenders, (
        f"In {LINCOLN_FAN_EXCEPTION_AUTOMATION!r}, climate.set_temperature for "
        f"{LINCOLN_FAN_EXCEPTION_CLIMATE!r} is forbidden. The Lincoln "
        "fan-only exception is setpoint-neutral by doctrine; setpoint changes "
        "must not depend on MSR data. See "
        "docs/apollo_msr_observability_checklist.md §Explicit Exception."
    )


def test_lincoln_fan_exception_only_sets_fan_only_or_off(automations_data):
    """Every ``climate.set_hvac_mode`` for ``climate.lincoln_air`` inside the
    exception automation must set ``hvac_mode`` to ``fan_only`` or ``off``.
    Heating, cooling, auto, heat_cool, and dry are not part of the narrow
    exception."""
    auto = next(
        (a for a in automations_data if a.get("id") == LINCOLN_FAN_EXCEPTION_AUTOMATION),
        None,
    )
    assert auto is not None, (
        f"{LINCOLN_FAN_EXCEPTION_AUTOMATION!r} not found"
    )
    offenders = []
    for item in _iter_action_items(auto.get("action")):
        if _service_of(item) != "climate.set_hvac_mode":
            continue
        target = item.get("target") or {}
        entity = target.get("entity_id") or item.get("data", {}).get("entity_id")
        if isinstance(entity, list):
            if LINCOLN_FAN_EXCEPTION_CLIMATE not in entity:
                continue
        elif entity != LINCOLN_FAN_EXCEPTION_CLIMATE:
            continue
        mode = (item.get("data") or {}).get("hvac_mode")
        if mode not in LINCOLN_FAN_EXCEPTION_ALLOWED_HVAC_MODES:
            offenders.append(mode)

    assert not offenders, (
        f"In {LINCOLN_FAN_EXCEPTION_AUTOMATION!r}, climate.set_hvac_mode for "
        f"{LINCOLN_FAN_EXCEPTION_CLIMATE!r} sets disallowed modes: "
        f"{offenders}. The narrow exception only permits "
        f"{sorted(LINCOLN_FAN_EXCEPTION_ALLOWED_HVAC_MODES)}. See "
        "docs/apollo_msr_observability_checklist.md §Explicit Exception."
    )


def test_msr_not_used_in_safety_automations(automations_data):
    """Safety gates and runaway cutoffs must remain Apollo/MSR-free.

    The 60°F LR runaway cooling cutoff, 58°F Master emergency floor, and
    76°F all-season ceiling gates are pure equipment-protection logic and
    must not depend on observability-only MSR data.
    """
    failures = []
    for auto in automations_data:
        if auto.get("id") not in SAFETY_AUTOMATION_IDS:
            continue
        rendered = _render(auto)
        offenders = sorted(
            {ent for ent in MSR_DERIVED_ENTITIES if ent in rendered}
        )
        if offenders:
            failures.append(f"{auto.get('id')}: {offenders}")

    assert not failures, (
        "Safety automations must remain MSR-free:\n  - "
        + "\n  - ".join(failures)
        + "\nSee docs/apollo_msr_observability_checklist.md §Forbidden Uses."
    )


def test_msr_not_used_in_main_supervisor(automations_data):
    """The Section 2 main supervisor authority must remain MSR-free. The
    only documented MSR-to-control path is the Section 6 Lincoln fan-only
    destratification automation, not the supervisor."""
    auto = next(
        (a for a in automations_data if a.get("id") == MAIN_SUPERVISOR_ID),
        None,
    )
    assert auto is not None, f"Could not find supervisor {MAIN_SUPERVISOR_ID!r}"
    rendered = _render(auto)
    offenders = sorted(
        {ent for ent in MSR_DERIVED_ENTITIES if ent in rendered}
    )
    assert not offenders, (
        f"Main supervisor {MAIN_SUPERVISOR_ID!r} references MSR-derived "
        f"entities: {offenders}. The supervisor is Apollo/MSR-free by "
        "doctrine. See docs/apollo_msr_observability_checklist.md "
        "§Forbidden Uses."
    )


def test_msr_pattern_sweep_finds_no_unknown_tokens(automations_data):
    """Forward-looking sweep: any new MSR-shaped token (msr / apollo /
    dps310 / mmwave / ld2410 / scd40 / radar_zone / co2) appearing in a
    non-telemetry automation will fail this test, even if the entity name
    is not yet enumerated in ``MSR_DERIVED_ENTITIES``.

    If a new MSR-derived entity is being introduced legitimately, add it to
    ``MSR_DERIVED_ENTITIES`` and update
    ``docs/apollo_msr_observability_checklist.md`` in the same PR.
    """
    failures = []
    for auto in automations_data:
        auto_id = auto.get("id")
        if auto_id in ALLOWED_MSR_TELEMETRY_AUTOMATIONS:
            continue
        rendered = _render(auto)
        # The Lincoln exception entity does not match MSR_PATTERN by name
        # (no msr/apollo/dps310/mmwave/ld2410/scd40/radar_zone/co2 substring),
        # so no allow-list stripping is needed here. If a future allow-list
        # entry happens to match the pattern, strip it before .findall().
        raw_matches = MSR_PATTERN.findall(rendered)
        if raw_matches:
            matches = sorted({m.lower() for m in raw_matches})
            failures.append(f"{auto_id}: tokens={matches}")

    assert not failures, (
        "Unexpected Apollo/MSR-shaped tokens in non-telemetry automations:\n"
        "  - " + "\n  - ".join(failures)
        + "\nIf this is a deliberate addition, update both "
        "MSR_DERIVED_ENTITIES (and the relevant allow-list constants) in "
        "this test and docs/apollo_msr_observability_checklist.md before "
        "merging. MSR observability-only is the default; the Lincoln fan-only "
        "path is a narrow exception, not a precedent."
    )
