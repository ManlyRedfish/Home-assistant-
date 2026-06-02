"""
Comfort-Band vs Safety-Gate Separation Guardrails
==================================================

First guardrail PR after PR #122 ("Add comfort-band & sensor-truth confidence
planning proposal"). This test converts the comfort-band / safety doctrine into
regression guardrails. It does NOT change runtime behavior.

Doctrine source of truth:
  docs/comfort_band_and_truth_confidence_plan.md
  docs/1_startup_canon.md §5.1 (Comfort Contract)
  docs/5_runtime_layer.md §7.9 (Planned Comfort-Profile and Truth-Confidence Model)

What this test locks:

  1. The Section 3 true-safety floors are unchanged:
       - Living Room runaway cooling cutoff trigger remains 60°F.
       - Master emergency cooling floor trigger remains 58°F.
  2. Those two true-safety gates do NOT gate on timer.manual_hvac_override
     (they must be able to override manual intent — they are equipment
     protection, not comfort policy).
  3. The docs document comfort bands as preferences that are separate from
     safety gates, and document the planned comfort profiles.
  4. Comfort thresholds are documented as profile preferences, not safety
     invariants (a comfort threshold must never alias a safety floor).

This test reads YAML and Markdown only. It asserts nothing about, and changes
nothing in, active HVAC behavior.
"""

import os

import pytest
import yaml


REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")

PROFILE_NAMES = ["eric_cold", "family_normal", "sleep_cold", "away_relaxed", "safety_only"]


class MooseSeparationLoader(yaml.SafeLoader):
    pass


def _secret(loader, node):
    return f"SECRET_{node.value}"


def _include(loader, node):
    return f"INCLUDE_{node.value}"


def _input(loader, node):
    return f"INPUT_{node.value}"


def _include_dir_merge_list(loader, node):
    return []


MooseSeparationLoader.add_constructor("!secret", _secret)
MooseSeparationLoader.add_constructor("!include", _include)
MooseSeparationLoader.add_constructor("!input", _input)
MooseSeparationLoader.add_constructor("!include_dir_merge_list", _include_dir_merge_list)
MooseSeparationLoader.add_constructor("!include_dir_named", _include_dir_merge_list)


@pytest.fixture(scope="module")
def automations_data():
    path = os.path.join(REPO_ROOT, "automations.yaml")
    if not os.path.exists(path):
        pytest.skip("automations.yaml not found.")
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.load(fh, Loader=MooseSeparationLoader)


def _find(automations, auto_id):
    return next((a for a in automations if a.get("id") == auto_id), None)


def _trigger_threshold(auto, entity_id, key):
    for trigger in auto.get("trigger", []):
        if (
            trigger.get("platform") == "numeric_state"
            and trigger.get("entity_id") == entity_id
            and key in trigger
        ):
            return trigger[key]
    return None


def _gates_on_manual_override(auto):
    conditions = auto.get("condition", [])
    if isinstance(conditions, dict):
        conditions = [conditions]
    text = repr(conditions)
    return "timer.manual_hvac_override" in text


def _read_doc(rel_path):
    path = os.path.join(REPO_ROOT, "docs", rel_path)
    assert os.path.exists(path), f"Expected doctrine doc missing: docs/{rel_path}"
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------------------- #
# 1. Section 3 true-safety floors are unchanged.
# --------------------------------------------------------------------------- #

def test_lr_runaway_floor_remains_60(automations_data):
    auto = _find(automations_data, "v8_2_lr_runaway_cooling_cutoff")
    assert auto is not None, "LR runaway cooling cutoff (v8_2_lr_runaway_cooling_cutoff) missing"
    threshold = _trigger_threshold(auto, "sensor.living_room_temperature_truth", "below")
    assert threshold == 60, (
        "LR runaway cooling cutoff must remain a 60°F equipment-protection floor; "
        f"found below={threshold!r}. Comfort-band work must not retune safety floors."
    )


def test_master_emergency_floor_remains_58(automations_data):
    auto = _find(automations_data, "v8_2_master_emergency_floor")
    assert auto is not None, "Master emergency floor (v8_2_master_emergency_floor) missing"
    threshold = _trigger_threshold(auto, "sensor.master_bedroom_temperature_truth", "below")
    assert threshold == 58, (
        "Master emergency cooling floor must remain a 58°F equipment-protection floor; "
        f"found below={threshold!r}. Comfort-band work must not retune safety floors."
    )


# --------------------------------------------------------------------------- #
# 2. True-safety gates must not gate on manual override (they override intent).
# --------------------------------------------------------------------------- #

def test_true_safety_floors_do_not_gate_on_manual_override(automations_data):
    for auto_id in ("v8_2_lr_runaway_cooling_cutoff", "v8_2_master_emergency_floor"):
        auto = _find(automations_data, auto_id)
        assert auto is not None, f"{auto_id} missing"
        assert not _gates_on_manual_override(auto), (
            f"{auto_id} is a true safety gate (equipment protection) and must NOT "
            "gate on timer.manual_hvac_override. Safety gates override manual intent; "
            "comfort policy yields to it."
        )


# --------------------------------------------------------------------------- #
# 3. Docs document comfort bands as preferences, separate from safety gates.
# --------------------------------------------------------------------------- #

def test_canon_documents_comfort_bands_not_thermostat_targets():
    canon = _read_doc("1_startup_canon.md")
    assert "comfort bands" in canon.lower()
    assert "deadband" in canon.lower()
    # Samsung setpoints are actuator commands, not comfort truth.
    assert "actuator" in canon.lower()
    assert "not comfort truth" in canon.lower()


def test_canon_documents_comfort_vs_safety_separation():
    canon = _read_doc("1_startup_canon.md")
    lower = canon.lower()
    assert "comfort bands are preferences" in lower, (
        "Canon must state comfort bands are preferences (distinct from safety)."
    )
    # Comfort thresholds must never be a safety gate / alias a safety floor.
    assert "alias a safety floor" in lower or "never alias" in lower, (
        "Canon must state a comfort threshold may never alias a safety floor."
    )


def test_canon_documents_planned_profiles():
    canon = _read_doc("1_startup_canon.md")
    missing = [p for p in PROFILE_NAMES if p not in canon]
    assert not missing, f"Canon is missing planned comfort profile names: {missing}"


def test_runtime_layer_documents_profiles_and_separation():
    runtime = _read_doc("5_runtime_layer.md")
    lower = runtime.lower()
    assert "not yet live" in lower or "not yet runtime" in lower, (
        "Runtime layer must mark the comfort-profile/truth model as not yet live."
    )
    assert "comfort bands are preferences" in lower
    missing = [p for p in PROFILE_NAMES if p not in runtime]
    assert not missing, f"Runtime layer is missing planned comfort profile names: {missing}"


# --------------------------------------------------------------------------- #
# 4. Comfort thresholds are documented as preferences, not safety invariants.
# --------------------------------------------------------------------------- #

def test_safety_floors_documented_as_equipment_protection_not_comfort():
    """
    The 60°F / 58°F floors must be described as physical/equipment protection,
    not as comfort bands. This keeps the comfort vs safety boundary in the docs
    aligned with the runtime separation asserted above.
    """
    runtime = _read_doc("5_runtime_layer.md")
    lower = runtime.lower()
    assert "60" in runtime and "58" in runtime
    assert "equipment protection" in lower or "physical protection" in lower, (
        "Safety floors must be documented as equipment/physical protection."
    )
