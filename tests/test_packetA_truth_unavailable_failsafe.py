"""Packet A contract tests — truth-sensor-unavailable cooling fail-safe.

Design source: docs/packets/packetA_truth_unavailable_failsafe.md (PR #135).

These encode the APPROVED Packet A Design 1 contract:
  * Supervisor validates each zone's truth (has_value + numeric) BEFORE any
    float(70) fallback / deadband comparison, and commands OFF when truth is
    unavailable/non-numeric.
  * A separate event-triggered automation forces a cooling unit OFF after a
    2-minute persistent truth outage, OFF-only, ignoring manual override, never
    restoring cooling.

IMPORTANT — xfail policy:
  The implementation-facing checks are marked ``xfail(strict=False)`` because the
  runtime change is intentionally NOT applied on this design/test branch (no
  automations.yaml change). They register as expected-failures today and will
  flip to passing once Codex applies Design 1; at that point remove the xfail
  marks (or set strict=True). The healthy-state / doctrine-preservation checks
  are NOT xfail — they must pass now and continue to pass after implementation.
"""

import os

import pytest
import yaml

PENDING = (
    "Pending Packet A Design 1 implementation in automations.yaml "
    "(Codex handoff). Design: docs/packets/packetA_truth_unavailable_failsafe.md"
)

SUPERVISOR_ID = "v7_5_main_supervisor"
FAILSAFE_ID = "v8_6_truth_unavailable_cooling_failsafe"

# zone-key -> (truth sensor, climate entity, truth_ok variable name)
ZONES = {
    "lr": (
        "sensor.living_room_temperature_truth",
        "climate.living_room_air",
        "lr_truth_ok",
    ),
    "master": (
        "sensor.master_bedroom_temperature_truth",
        "climate.master_bedroom_air",
        "master_truth_ok",
    ),
    "lincoln": (
        "sensor.lincoln_s_room_temperature_truth",
        "climate.lincoln_air",
        "lincoln_truth_ok",
    ),
    "lilly": (
        "sensor.lilly_s_room_temperature_truth",
        "climate.lilly_air",
        "lilly_truth_ok",
    ),
}


class MooseLoader(yaml.SafeLoader):
    pass


def _scalar(prefix):
    def _c(loader, node):
        return f"{prefix}_{node.value}"

    return _c


def _empty_list(loader, node):
    return []


MooseLoader.add_constructor("!secret", _scalar("SECRET"))
MooseLoader.add_constructor("!include", _scalar("INCLUDE"))
MooseLoader.add_constructor("!input", _scalar("INPUT"))
MooseLoader.add_constructor("!include_dir_merge_list", _empty_list)
MooseLoader.add_constructor("!include_dir_named", _empty_list)


@pytest.fixture(scope="module")
def automations():
    path = os.path.join(os.path.dirname(__file__), "..", "automations.yaml")
    with open(path, "r") as fh:
        return yaml.load(fh, Loader=MooseLoader)


def _auto(automations, auto_id):
    return next((a for a in automations if a.get("id") == auto_id), None)


def _supervisor(automations):
    sup = _auto(automations, SUPERVISOR_ID)
    assert sup is not None, f"{SUPERVISOR_ID} must exist"
    return sup


def _cooling_branch(supervisor):
    for step in supervisor.get("action", []):
        if isinstance(step, dict) and "choose" in step:
            for branch in step["choose"]:
                for cond in branch.get("conditions", []):
                    if "season == 'cooling'" in cond.get("value_template", ""):
                        return branch
    pytest.fail("Could not find the cooling-season branch in the supervisor")


def _zone_hvac_template(branch, climate_entity):
    for step in branch.get("sequence", []):
        if not isinstance(step, dict):
            continue
        if (step.get("action") or step.get("service")) != "climate.set_temperature":
            continue
        target = step.get("target", {}).get("entity_id")
        if target == climate_entity:
            return step.get("data", {}).get("hvac_mode", "")
    return None


def _supervisor_control_variables(supervisor):
    """Merge top-level + cooling-branch-direct ``variables`` (non-recursive).

    Deliberately does NOT recurse into the shoulder/heating branches, which
    redefine names like ``lr_off_at`` (as ``{{ target_lr }}``). The cooling
    setpoint/threshold doctrine and the per-zone ``*_truth_ok`` flags both live
    at the supervisor's top level or the cooling branch's direct sequence.
    """
    merged = {}
    for step in supervisor.get("action", []):
        if isinstance(step, dict) and isinstance(step.get("variables"), dict):
            merged.update(step["variables"])
    for step in _cooling_branch(supervisor).get("sequence", []):
        if isinstance(step, dict) and isinstance(step.get("variables"), dict):
            merged.update(step["variables"])
    return merged


def _render(template, **ctx):
    jinja2 = pytest.importorskip("jinja2")
    return jinja2.Environment().from_string(template).render(**ctx).strip()


# Generic context covering every zone's variable names, so a single dict can
# render any zone's hvac_mode template (extras are ignored by Jinja).
def _ctx(**overrides):
    base = dict(
        lr_temp=70, master_temp=70, lincoln_temp=70, lilly_temp=70,
        m_on_at=72, m_off_at=68, m_current="off",
        l_on_at=72, l_off_at=68, l_current="off",
        ly_on_at=72, ly_off_at=68, ly_current="off",
        lr_on_at=72, lr_off_at=68, lr_current="off",
        lr_truth_ok=True, master_truth_ok=True,
        lincoln_truth_ok=True, lilly_truth_ok=True,
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# GROUP 1 — Healthy-state / doctrine preservation (MUST pass now and after)
# ---------------------------------------------------------------------------

def test_healthy_state_doctrine_unchanged(automations):
    """Packet A must not change setpoints, thresholds, away, or Master sleep."""
    v = _supervisor_control_variables(_supervisor(automations))
    assert v.get("m_setpoint") == "{{ 61 }}"
    assert v.get("l_setpoint") == "{{ 61 }}"
    assert v.get("ly_setpoint") == "{{ 61 }}"
    assert v.get("lr_setpoint") == "{{ 61 }}"
    assert v.get("m_off_at") == "{{ 74 if away else (62 if is_master_sleep else 68) }}"
    assert v.get("m_on_at") == "{{ 76 if away else (66 if is_master_sleep else 72) }}"
    assert v.get("lr_off_at") == "{{ 74 if away else 68 }}"
    assert v.get("lr_on_at") == "{{ 76 if away else 72 }}"
    assert v.get("l_off_at") == "{{ 74 if away else 68 }}"
    assert v.get("ly_on_at") == "{{ 76 if away else 72 }}"


def test_healthy_deadband_behavior_unchanged(automations):
    """With healthy truth, > on_at COOL / <= off_at OFF / else HOLD is intact.

    Passes pre-implementation (no guard) and post-implementation (guard with
    truth_ok=True passes through to the existing logic).
    """
    branch = _cooling_branch(_supervisor(automations))
    tmpl = _zone_hvac_template(branch, "climate.master_bedroom_air")
    assert tmpl, "Master cooling hvac_mode template must exist"
    # daytime band 68/72, truth healthy
    assert _render(tmpl, **_ctx(master_temp=73)) == "cool"             # above on_at
    assert _render(tmpl, **_ctx(master_temp=72)) in ("off", "cool")    # equality boundary (HOLD off)
    assert _render(tmpl, **_ctx(master_temp=72, m_current="off")) == "off"
    assert _render(tmpl, **_ctx(master_temp=68)) == "off"              # at off_at
    assert _render(tmpl, **_ctx(master_temp=70, m_current="off")) == "off"   # hold prior off
    assert _render(tmpl, **_ctx(master_temp=70, m_current="cool")) == "cool"  # hold prior cool


# ---------------------------------------------------------------------------
# GROUP 2 — Supervisor truth-validity guard (xfail until implemented)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason=PENDING, strict=False)
def test_supervisor_defines_per_zone_truth_ok(automations):
    """Each zone validates truth via has_value BEFORE numeric conversion."""
    v = _supervisor_control_variables(_supervisor(automations))
    for _key, (truth, _clim, ok) in ZONES.items():
        assert ok in v, f"supervisor must define {ok}"
        assert "has_value" in v[ok], f"{ok} must validate via has_value (not float)"
        assert truth in v[ok], f"{ok} must reference {truth}"


@pytest.mark.xfail(reason=PENDING, strict=False)
def test_cooling_hvac_templates_guard_unavailable_before_cool(automations):
    """Structural: each zone's hvac_mode guards on `not <zone>_truth_ok`,
    and that guard precedes any `cool` decision (truth checked before deadband).
    """
    branch = _cooling_branch(_supervisor(automations))
    for _key, (_truth, clim, ok) in ZONES.items():
        tmpl = _zone_hvac_template(branch, clim) or ""
        guard_idx = tmpl.find(f"not {ok}")
        assert guard_idx != -1, f"{clim} hvac_mode must guard on `not {ok}`"
        cool_idx = tmpl.find("cool")
        assert cool_idx == -1 or guard_idx < cool_idx, (
            f"{clim}: truth guard must come before any cool decision"
        )


@pytest.mark.xfail(reason=PENDING, strict=False)
def test_unavailable_truth_forces_off_each_zone(automations):
    """Behavioral: with truth_ok=False and the float(70) value in/above band,
    every zone renders OFF — no unavailable truth reaches float(70) as control.
    """
    branch = _cooling_branch(_supervisor(automations))
    # current='cool' is the adversarial case (would HOLD cool without a guard)
    for _key, (_truth, clim, ok) in ZONES.items():
        tmpl = _zone_hvac_template(branch, clim)
        assert tmpl, f"{clim} cooling hvac_mode template must exist"
        ctx = _ctx(
            **{ok: False},
            m_current="cool", l_current="cool",
            ly_current="cool", lr_current="cool",
        )
        out = _render(tmpl, **ctx)
        assert out == "off", f"{clim}: unavailable truth must force OFF, got {out!r}"


@pytest.mark.xfail(reason=PENDING, strict=False)
def test_master_sleep_unavailable_cannot_create_cool(automations):
    """The float(70) Master-sleep false-COOL path is prevented.

    Master sleep band is 62/66; float(70) > 66 would COOL without a guard.
    """
    branch = _cooling_branch(_supervisor(automations))
    tmpl = _zone_hvac_template(branch, "climate.master_bedroom_air")
    out = _render(
        tmpl,
        **_ctx(master_truth_ok=False, master_temp=70,
               m_on_at=66, m_off_at=62, m_current="off"),
    )
    assert out == "off", f"Master sleep + unavailable truth must be OFF, got {out!r}"


# ---------------------------------------------------------------------------
# GROUP 3 — Event-triggered protective-OFF automation (xfail until implemented)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason=PENDING, strict=False)
def test_event_failsafe_present_per_zone_unavailable_triggers(automations):
    auto = _auto(automations, FAILSAFE_ID)
    assert auto is not None, f"{FAILSAFE_ID} automation must exist"
    triggered = {}
    for trig in auto.get("trigger", []):
        if trig.get("platform") != "state":
            continue
        to = trig.get("to")
        to_set = set(to if isinstance(to, list) else [to])
        if to_set & {"unavailable", "unknown"}:
            triggered[trig.get("entity_id")] = trig
    for _key, (truth, _clim, _ok) in ZONES.items():
        assert truth in triggered, f"missing unavailable trigger for {truth}"


@pytest.mark.xfail(reason=PENDING, strict=False)
def test_event_failsafe_two_minute_persistence(automations):
    auto = _auto(automations, FAILSAFE_ID)
    assert auto is not None
    state_trigs = [t for t in auto.get("trigger", []) if t.get("platform") == "state"]
    assert state_trigs, "fail-safe must have state triggers"
    for trig in state_trigs:
        for_val = trig.get("for")
        assert for_val in ("00:02:00", 120, {"minutes": 2}, {"seconds": 120}), (
            f"each truth trigger needs a 2-minute persistence, got {for_val!r}"
        )


@pytest.mark.xfail(reason=PENDING, strict=False)
def test_event_failsafe_only_commands_off_and_gates_on_cooling(automations):
    auto = _auto(automations, FAILSAFE_ID)
    assert auto is not None
    actions = auto.get("action", [])
    climate_calls = [
        s for s in actions
        if isinstance(s, dict)
        and (s.get("action") or s.get("service"))
        in ("climate.set_hvac_mode", "climate.set_temperature")
    ]
    assert climate_calls, "fail-safe must issue a climate command"
    for call in climate_calls:
        assert call.get("data", {}).get("hvac_mode") in ("off", False), (
            "fail-safe may only command hvac_mode: off"
        )
    conds = auto.get("condition", [])
    assert any("cool" in c.get("value_template", "") for c in conds), (
        "fail-safe must act only when the unit is currently cooling"
    )


@pytest.mark.xfail(reason=PENDING, strict=False)
def test_event_failsafe_ignores_manual_override(automations):
    """Approved: the safety path must NOT gate on manual override."""
    auto = _auto(automations, FAILSAFE_ID)
    assert auto is not None
    import json

    assert "manual_hvac_override" not in json.dumps(auto), (
        "fail-safe must not reference timer.manual_hvac_override"
    )


@pytest.mark.xfail(reason=PENDING, strict=False)
def test_event_failsafe_recovery_never_turns_cooling_on(automations):
    """No action in the fail-safe may command cool or otherwise restore cooling."""
    auto = _auto(automations, FAILSAFE_ID)
    assert auto is not None
    for step in auto.get("action", []):
        if not isinstance(step, dict):
            continue
        assert step.get("data", {}).get("hvac_mode") != "cool", (
            "fail-safe action must never command cool"
        )
        service = step.get("action") or step.get("service")
        assert service not in ("climate.turn_on",), (
            "fail-safe must not turn climate on"
        )
