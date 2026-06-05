"""
Truth-Source ↔ Live Transport Sync Regression Guards
====================================================

Locks the 2026-06-05 durability/sync PR that ported already-verified LIVE
truth-source edits into the repo. This is an ENTITY-SOURCE sync only — it
does not (and these tests assert it does not) redesign weighting or change
the statistical truth model.

Verified-live facts being locked (see configuration.yaml "LIVE-SYNC CHANGES
(June 5, 2026)" header and docs/2_reference_map.md §7):

  * Master truth includes the Matter transport copy of the Master room probe:
        sensor.master_bedroom_temp_temperature_3   (temperature)
        sensor.master_bedroom_temp_humidity_3      (humidity)
  * Lilly truth includes the Matter transport copy of the Lilly room probe:
        sensor.lilly_temp_temperature_2            (temperature)
        sensor.lilly_temp_humidity_2               (humidity)
  * The disabled/no-state Living Room secondary SwitchBot Hub 2 transport is
    EXCLUDED from active truth:
        sensor.hub_2_tempsensor_temperature        (temperature)
        sensor.hub_2_humisensor_humidity           (humidity)
  * Active temperature/humidity contributor counts:
        Living Room 3 · Master 4 · Lincoln 4 · Lilly 4

Transport model (documented, not changed here): a room's BT / SmartThings(ST)
/ Matter rows are alternate transports of ONE physical SwitchBot probe, not
independent thermometers. Truth currently averages every available transport;
"pick one best transport per physical probe" is a DEFERRED design question.
"""

import os
import re

import pytest
import yaml


REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
CONFIG = os.path.join(REPO_ROOT, "configuration.yaml")
REFERENCE_MAP = os.path.join(REPO_ROOT, "docs", "2_reference_map.md")


class _SyncLoader(yaml.SafeLoader):
    pass


_SyncLoader.add_constructor("!include", lambda loader, node: node.value)
_SyncLoader.add_constructor("!secret", lambda loader, node: node.value)


def _read(path):
    if not os.path.exists(path):
        pytest.skip(f"{os.path.basename(path)} not found.")
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _template_sensors():
    """Return {name: sensor_dict} for every sensor under the top-level
    `template:` → `- sensor:` list in configuration.yaml."""
    cfg = yaml.load(_read(CONFIG), Loader=_SyncLoader)
    sensors = {}
    for block in cfg.get("template", []) or []:
        if isinstance(block, dict) and "sensor" in block:
            for sensor in block["sensor"]:
                if isinstance(sensor, dict) and "name" in sensor:
                    sensors[sensor["name"]] = sensor
    assert sensors, "No template sensors parsed from configuration.yaml"
    return sensors


def _freshness_sources(template_text):
    """Entities gated by a report-time freshness check in a state/availability
    template: states.sensor.<id>.last_reported . This is exactly the set the
    weighted average and the active-count diagnostic iterate over."""
    return set(re.findall(r"states\.sensor\.([a-z0-9_]+)\.last_reported", template_text or ""))


def _source_weights(state_text):
    """Map active source entity -> weight by joining the two bindings the
    truth templates use:
        {% set <var> = states('sensor.<entity>') | float(none) %}
        ... (<var> * <weight>) ...
    Only returns entities that are actually multiplied into ns.total (i.e.
    genuinely contribute to the weighted average)."""
    var_to_entity = dict(
        re.findall(r"set\s+(\w+)\s*=\s*states\('sensor\.([a-z0-9_]+)'\)", state_text or "")
    )
    var_to_weight = {
        var: float(weight)
        for var, weight in re.findall(r"\((\w+)\s*\*\s*([0-9.]+)\)", state_text or "")
    }
    return {
        var_to_entity[var]: weight
        for var, weight in var_to_weight.items()
        if var in var_to_entity
    }


# Truth sensor display names.
LR_T, LR_H = "Living Room Temperature Truth", "Living Room Humidity Truth"
MAS_T, MAS_H = "Master Bedroom Temperature Truth", "Master Bedroom Humidity Truth"
LIN_T, LIN_H = "Lincoln's Room Temperature Truth", "Lincoln's Room Humidity Truth"
LIL_T, LIL_H = "Lilly's Room Temperature Truth", "Lilly's Room Humidity Truth"

DISABLED_LR_TEMP = "hub_2_tempsensor_temperature"
DISABLED_LR_HUM = "hub_2_humisensor_humidity"


# --------------------------------------------------------------------------- #
# Inclusion: Master + Lilly Matter transports are wired into truth
# --------------------------------------------------------------------------- #

def test_master_truth_includes_matter_temp_and_humidity():
    sensors = _template_sensors()

    temp = sensors[MAS_T]
    assert "master_bedroom_temp_temperature_3" in _freshness_sources(temp["state"])
    assert "master_bedroom_temp_temperature_3" in _freshness_sources(temp["availability"])
    assert "master_bedroom_temp_temperature_3" in _source_weights(temp["state"]), (
        "Master Matter temperature must be weighted into the average, not just read."
    )

    hum = sensors[MAS_H]
    assert "master_bedroom_temp_humidity_3" in _freshness_sources(hum["state"])
    assert "master_bedroom_temp_humidity_3" in _freshness_sources(hum["availability"])
    assert "master_bedroom_temp_humidity_3" in _source_weights(hum["state"])


def test_lilly_truth_includes_matter_temp_and_humidity():
    sensors = _template_sensors()

    temp = sensors[LIL_T]
    assert "lilly_temp_temperature_2" in _freshness_sources(temp["state"])
    assert "lilly_temp_temperature_2" in _freshness_sources(temp["availability"])
    assert "lilly_temp_temperature_2" in _source_weights(temp["state"]), (
        "Lilly Matter temperature must be weighted into the average, not just read."
    )

    hum = sensors[LIL_H]
    assert "lilly_temp_humidity_2" in _freshness_sources(hum["state"])
    assert "lilly_temp_humidity_2" in _freshness_sources(hum["availability"])
    assert "lilly_temp_humidity_2" in _source_weights(hum["state"])


# --------------------------------------------------------------------------- #
# Exclusion: disabled Living Room secondary route is out of active truth
# --------------------------------------------------------------------------- #

def test_living_room_truth_excludes_disabled_secondary_routes():
    sensors = _template_sensors()

    temp = sensors[LR_T]
    assert DISABLED_LR_TEMP not in _freshness_sources(temp["state"])
    assert DISABLED_LR_TEMP not in _freshness_sources(temp["availability"])
    assert DISABLED_LR_TEMP not in _source_weights(temp["state"])

    hum = sensors[LR_H]
    assert DISABLED_LR_HUM not in _freshness_sources(hum["state"])
    assert DISABLED_LR_HUM not in _freshness_sources(hum["availability"])
    assert DISABLED_LR_HUM not in _source_weights(hum["state"])


def test_living_room_diagnostics_exclude_disabled_route():
    """The Contributors list and Active Count diagnostic must also drop the
    disabled secondary route so the live count of 3 is reported."""
    sensors = _template_sensors()

    contributors = sensors["Living Room Temperature Truth Contributors"]["state"]
    active_count = sensors["Living Room Temperature Truth Active Count"]["state"]

    assert DISABLED_LR_TEMP not in _freshness_sources(contributors)
    assert DISABLED_LR_TEMP not in _freshness_sources(active_count)
    # The literal label string emitted into the Contributors attribute is gone too.
    assert "'hub_2_tempsensor_temperature'" not in contributors
    assert len(_freshness_sources(active_count)) == 3


# --------------------------------------------------------------------------- #
# Contributor counts match the verified-live numbers
# --------------------------------------------------------------------------- #

def test_contributor_counts_match_verified_live():
    sensors = _template_sensors()
    expected = {
        LR_T: 3, MAS_T: 4, LIN_T: 4, LIL_T: 4,
        LR_H: 3, MAS_H: 4, LIN_H: 4, LIL_H: 4,
    }
    actual = {name: len(_freshness_sources(sensors[name]["state"])) for name in expected}
    assert actual == expected, f"Contributor counts drifted from live: {actual}"


# --------------------------------------------------------------------------- #
# Weighting is PORTED, not redesigned
# --------------------------------------------------------------------------- #

def test_new_matter_routes_weighted_one_point_zero():
    """New Matter routes carry w=1.0 — matching Lincoln's live Matter route
    (lincoln_temp_temperature) and the sibling BT room-probe weight. This is
    the existing scheme, not a new one."""
    sensors = _template_sensors()
    assert _source_weights(sensors[MAS_T]["state"])["master_bedroom_temp_temperature_3"] == 1.0
    assert _source_weights(sensors[MAS_H]["state"])["master_bedroom_temp_humidity_3"] == 1.0
    assert _source_weights(sensors[LIL_T]["state"])["lilly_temp_temperature_2"] == 1.0
    assert _source_weights(sensors[LIL_H]["state"])["lilly_temp_humidity_2"] == 1.0


def test_existing_weights_unchanged_for_synced_rooms():
    """Guard the 'do not redesign weighting' rule: pre-existing source weights
    in the touched rooms are untouched (Samsung internal low-weight; ST/legacy
    secondary at 0.9; primaries at 1.0)."""
    sensors = _template_sensors()

    # Samsung internal stays low-weight everywhere it was.
    assert _source_weights(sensors[LR_T]["state"])["living_room_air_temperature"] == 0.20
    assert _source_weights(sensors[LR_H]["state"])["living_room_air_humidity"] == 0.25
    assert _source_weights(sensors[MAS_T]["state"])["master_bedroom_air_temperature"] == 0.20
    assert _source_weights(sensors[LIL_T]["state"])["lilly_air_temperature"] == 0.20

    # Primary BT probes keep w=1.0; ST/legacy secondaries keep w=0.9.
    assert _source_weights(sensors[LR_T]["state"])["hub_temperature"] == 1.0
    assert _source_weights(sensors[LR_T]["state"])["hub_temperature_2"] == 0.9
    assert _source_weights(sensors[MAS_T]["state"])["master_bedroom_temp_temperature_2"] == 1.0
    assert _source_weights(sensors[MAS_T]["state"])["master_bedroom_temperature_temperature_2"] == 0.9
    assert _source_weights(sensors[LIL_T]["state"])["lilly_temperature"] == 1.0
    assert _source_weights(sensors[LIL_T]["state"])["lilly_room_temperature_temperature"] == 0.9


# --------------------------------------------------------------------------- #
# Lilly documentation contradiction is resolved
# --------------------------------------------------------------------------- #

def test_lilly_matter_entity_not_marked_removed_or_fallback():
    """sensor.lilly_temp_temperature_2 must not be listed as both active Matter
    and removed/legacy. The old 'Outdoor Meter 58 fallback' REMOVED line is gone,
    and no line marks the entity as a fallback/removed source."""
    text = _read(CONFIG)
    assert "lilly_temp_temperature_2 (Outdoor Meter 58 fallback)" not in text
    for line in text.splitlines():
        if "lilly_temp_temperature_2" in line and "fallback" in line.lower():
            pytest.fail(f"lilly_temp_temperature_2 still framed as fallback: {line.strip()}")
    # It IS documented as the active Matter transport.
    assert any(
        "lilly_temp_temperature_2" in line and "Matter" in line
        for line in text.splitlines()
    ), "lilly_temp_temperature_2 should be documented as the Matter transport."


# --------------------------------------------------------------------------- #
# Reference map carries the durable transport inventory
# --------------------------------------------------------------------------- #

def test_reference_map_documents_transports_and_matter_entities():
    doc = _read(REFERENCE_MAP)
    # The transport principle is stated.
    for token in ("Matter", "SmartThings", "Bluetooth", "transport"):
        assert token in doc, f"Reference map must mention {token!r}."
    # The four newly-synced Matter entities appear in the inventory.
    for entity in (
        "sensor.master_bedroom_temp_temperature_3",
        "sensor.master_bedroom_temp_humidity_3",
        "sensor.lilly_temp_temperature_2",
        "sensor.lilly_temp_humidity_2",
    ):
        assert entity in doc, f"Reference map missing synced Matter entity {entity}."
    # The removed Living Room secondary route is documented as excluded.
    assert "hub_2_tempsensor_temperature" in doc
