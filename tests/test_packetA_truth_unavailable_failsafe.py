"""Packet A contract tests — truth-sensor-unavailable cooling fail-safe.

Design source: docs/packets/packetA_truth_unavailable_failsafe.md (PR #135).

These encode the APPROVED Packet A Design 1 contract:
  * Supervisor validates each zone's truth with a shared FINITE-VALUE definition
    BEFORE any float(70) fallback / deadband comparison, and commands OFF when
    truth is invalid (unavailable / unknown / parse failure / NaN / infinity).
  * A separate event-triggered automation forces a cooling unit OFF after a
    2-minute persistent truth outage, OFF-only, ignoring manual override, never
    restoring cooling.
  * A restart/reload-safe reconciliation automation closes the for:-reset blind
    spot, but ONLY forces OFF when the invalid state has persisted >= 2 minutes
    (it must not bypass the approved 2-minute debounce after an automation
    reload).

Shared finite-value validity (BLOCKER 1):
  The previous ``float(none) is not none`` test rejected ordinary parse failures
  (``"err"``) but ACCEPTED ``"NaN"``/``"inf"`` because those parse to floating
  point values. NaN collapses every threshold comparison to false (false HOLD)
  and +/-infinity forces extreme threshold outcomes. The hardened definition
  parses with ``float(none)`` and additionally requires the value to equal
  itself (rejects NaN) and to fall inside a deliberately BROAD safety
  plausibility window (rejects +/-infinity and absurd values). These bounds are
  SAFETY-VALIDATION limits only and are intentionally far outside any HVAC
  comfort/control threshold.

IMPORTANT — xfail policy:
  The implementation-facing checks (they read automations.yaml, which is NOT
  changed on this design/test branch) are marked ``xfail(strict=False)``. They
  register as expected-failures today and flip to passing once Codex applies
  Design 1; at that point every xfail mark MUST be removed (the enforceable gate
  below fails the suite if the guard is implemented but markers remain).

  The healthy-state / doctrine-preservation checks AND the design-proving
  behavioral checks of the canonical validity + reconciliation expressions are
  NOT xfail — they must pass now and continue to pass after implementation,
  because they prove the chosen *definition* is sound independent of where it is
  wired in.
"""

import datetime
import json
import os
import types

import pytest
import yaml

PENDING = (
    "Pending Packet A Design 1 implementation in automations.yaml "
    "(Codex handoff). Design: docs/packets/packetA_truth_unavailable_failsafe.md"
)

SUPERVISOR_ID = "v7_5_main_supervisor"
FAILSAFE_ID = "v8_6_truth_unavailable_cooling_failsafe"
RECON_ID = "v8_6b_truth_unavailable_cooling_reconciliation"

# Broad SAFETY plausibility window for VALIDITY only (degrees F). These are NOT
# comfort/control thresholds — they exist solely to reject +/-infinity and
# absurd values while never rejecting any conceivable real indoor reading. They
# are documented separately from every HVAC threshold (61 target; 68/72 home;
# 74/76 away; 62/66 Master sleep; 60/58/76 safety gates).
SAFETY_TEMP_MIN_F = -90
SAFETY_TEMP_MAX_F = 200

# Minimum duration a truth entity must remain invalid before the periodic /
# startup reconciliation sweep is allowed to force OFF — identical to the event
# automation's 2-minute debounce, so reconciliation never bypasses it.
MIN_INVALID_SECONDS = 120

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


# ---------------------------------------------------------------------------
# Canonical shared expressions (single source of truth for the contract).
# The implementation in automations.yaml must be SEMANTICALLY IDENTICAL to
# these; the xfail tests below assert the YAML carries the same fragments.
# ---------------------------------------------------------------------------

def truth_ok_expr(entity):
    """Supervisor ``*_truth_ok`` form: truth is VALID (finite, usable)."""
    return (
        "{% set x = states('" + entity + "') | float(none) %}"
        "{{ x is not none and x == x"
        " and " + str(SAFETY_TEMP_MIN_F) + " <= x <= " + str(SAFETY_TEMP_MAX_F) + " }}"
    )


def truth_invalid_expr(entity):
    """Event-trigger / reconciliation form: truth is INVALID (== not valid)."""
    return (
        "{% set x = states('" + entity + "') | float(none) %}"
        "{{ x is none or x != x"
        " or x < " + str(SAFETY_TEMP_MIN_F) + " or x > " + str(SAFETY_TEMP_MAX_F) + " }}"
    )


def reconciliation_decision_expr(truth_var="truth", climate_var="climate"):
    """Per-zone reconciliation decision: force OFF iff the unit is cooling AND
    truth is invalid AND that invalid state has persisted >= 2 minutes.

    The age basis is the truth entity's current-state timestamp
    (``last_changed``): when a numeric value transitions to an invalid state HA
    updates ``last_changed``, so ``now() - last_changed`` is the age of the
    current invalid episode. An automation reload does NOT reset entity states,
    so this age survives a reload and the debounce is preserved.
    """
    return (
        "{% set x = states(" + truth_var + ") | float(none) %}"
        "{% set invalid = x is none or x != x"
        " or x < " + str(SAFETY_TEMP_MIN_F) + " or x > " + str(SAFETY_TEMP_MAX_F) + " %}"
        "{% set st = states[" + truth_var + "] %}"
        "{% set invalid_age = (now() - st.last_changed).total_seconds()"
        " if st is not none else 0 %}"
        "{{ is_state(" + climate_var + ", 'cool')"
        " and invalid and invalid_age >= " + str(MIN_INVALID_SECONDS) + " }}"
    )


# Adversarial truth values that MUST be treated as invalid (BLOCKER 1).
INVALID_TRUTH_VALUES = [
    "err",          # ordinary parse failure
    "NaN", "nan",   # not-a-number (parses to a float, but x != x)
    "inf", "-inf",  # infinities (parse to a float)
    "Infinity", "-Infinity",
    "",             # empty string
    "unknown",
    "unavailable",
]

# Ordinary signed / decimal temperatures that MUST remain valid (BLOCKER 1 / 7).
HEALTHY_TRUTH_VALUES = ["70", "61.5", "-3.2", "0", "68.0", "75.2"]


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


def _collect_hvac_modes(node):
    """Recursively gather every ``data.hvac_mode`` value in an action tree.

    Handles nested structures: choose/sequence/default, repeat/for_each, if/then/
    else, and plain action lists.
    """
    modes = []

    def walk(obj):
        if isinstance(obj, list):
            for item in obj:
                walk(item)
        elif isinstance(obj, dict):
            if isinstance(obj.get("data"), dict) and "hvac_mode" in obj["data"]:
                modes.append(obj["data"]["hvac_mode"])
            for key, val in obj.items():
                if key == "data":
                    continue
                if isinstance(val, (list, dict)):
                    walk(val)

    walk(node)
    return modes


def _render(template, **ctx):
    jinja2 = pytest.importorskip("jinja2")
    return jinja2.Environment().from_string(template).render(**ctx).strip()


def _render_validity(expr, value):
    """Render a validity expression with ``states()`` returning ``value``."""
    jinja2 = pytest.importorskip("jinja2")
    return jinja2.Environment().from_string(expr).render(states=lambda _e: value).strip()


class _FakeStates:
    """Stands in for HA's ``states`` object: callable (``states(e)`` -> value)
    and subscriptable (``states[e]`` -> a state object with ``last_changed``)."""

    def __init__(self, value, last_changed):
        self._value = value
        self._last_changed = last_changed

    def __call__(self, _entity_id):
        return self._value

    def __getitem__(self, _entity_id):
        return types.SimpleNamespace(last_changed=self._last_changed)


def _render_reconciliation(expr, *, climate_state, truth_value, invalid_age_seconds):
    """Render the reconciliation decision with controllable state-age."""
    jinja2 = pytest.importorskip("jinja2")
    now = datetime.datetime(2026, 6, 9, 12, 0, 0)
    last_changed = now - datetime.timedelta(seconds=invalid_age_seconds)
    return (
        jinja2.Environment()
        .from_string(expr)
        .render(
            truth="sensor.t",
            climate="climate.c",
            states=_FakeStates(truth_value, last_changed),
            now=lambda: now,
            is_state=lambda _e, state: climate_state == state,
        )
        .strip()
    )


def _assert_finite_validity_fragments(text, where):
    """Assert a YAML-embedded validity expression carries the shared finite
    definition: parse with float(none), reject NaN via self-(in)equality, and
    bound to the broad safety window (rejects +/-infinity)."""
    assert "float(none)" in text, f"{where} must parse with float(none)"
    assert ("x == x" in text or "x != x" in text), (
        f"{where} must reject NaN via a self-(in)equality test (x == x / x != x)"
    )
    assert str(SAFETY_TEMP_MIN_F) in text and str(SAFETY_TEMP_MAX_F) in text, (
        f"{where} must bound to the broad safety window "
        f"[{SAFETY_TEMP_MIN_F}, {SAFETY_TEMP_MAX_F}] to reject infinity"
    )


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
# GROUP 1b — Canonical finite-value validity definition (DESIGN-PROVING, green)
# Proves the chosen definition rejects NaN/infinity/parse-failures and keeps
# ordinary temperatures valid, independent of where it is wired in. (BLOCKER 1)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", INVALID_TRUTH_VALUES)
def test_finite_validity_rejects_invalid_values(value):
    """err / NaN / nan / inf / -inf / Infinity / unknown / unavailable / empty
    are all INVALID under the shared finite-value definition (both forms)."""
    entity = "sensor.living_room_temperature_truth"
    # supervisor VALID form -> "False"; event/recon INVALID form -> "True"
    assert _render_validity(truth_ok_expr(entity), value) == "False", (
        f"{value!r} must NOT be a valid control temperature"
    )
    assert _render_validity(truth_invalid_expr(entity), value) == "True", (
        f"{value!r} must be detected as invalid"
    )


@pytest.mark.parametrize("value", HEALTHY_TRUTH_VALUES)
def test_finite_validity_accepts_healthy_temperatures(value):
    """Ordinary signed and decimal temperatures remain valid (BLOCKER 1 / 7)."""
    entity = "sensor.living_room_temperature_truth"
    assert _render_validity(truth_ok_expr(entity), value) == "True", (
        f"{value!r} is an ordinary temperature and must stay valid"
    )
    assert _render_validity(truth_invalid_expr(entity), value) == "False", (
        f"{value!r} must NOT be flagged invalid"
    )


def test_supervisor_and_event_validity_are_semantically_identical():
    """The supervisor VALID form and the event/reconciliation INVALID form are
    exact logical negations across all candidates — i.e. one shared definition
    (BLOCKER 1 test 3)."""
    entity = "sensor.master_bedroom_temperature_truth"
    for value in INVALID_TRUTH_VALUES + HEALTHY_TRUTH_VALUES:
        valid = _render_validity(truth_ok_expr(entity), value)
        invalid = _render_validity(truth_invalid_expr(entity), value)
        assert {valid, invalid} == {"True", "False"}, (
            f"{value!r}: valid={valid} invalid={invalid} are not negations"
        )


# ---------------------------------------------------------------------------
# GROUP 1c — Canonical reconciliation persistence decision (DESIGN-PROVING)
# Proves the periodic/startup sweep honours the 2-minute debounce. (BLOCKER 2)
# ---------------------------------------------------------------------------

def test_reconciliation_decision_holds_off_when_invalid_age_under_two_minutes():
    """A brief invalid state (e.g. just after a reload) must NOT force OFF."""
    expr = reconciliation_decision_expr()
    assert _render_reconciliation(
        expr, climate_state="cool", truth_value="unavailable", invalid_age_seconds=60
    ) == "False", "invalid for <2 min must not force OFF"
    assert _render_reconciliation(
        expr, climate_state="cool", truth_value="unavailable", invalid_age_seconds=119
    ) == "False", "still under 2 min must not force OFF"


def test_reconciliation_decision_forces_off_when_invalid_age_at_least_two_minutes():
    """Sustained (>=2 min) invalid truth while cooling forces OFF — including
    NaN/infinity, which share the finite-value definition (BLOCKER 2 test 5)."""
    expr = reconciliation_decision_expr()
    assert _render_reconciliation(
        expr, climate_state="cool", truth_value="unavailable", invalid_age_seconds=120
    ) == "True", "exactly 2 min invalid + cooling must force OFF"
    assert _render_reconciliation(
        expr, climate_state="cool", truth_value="unavailable", invalid_age_seconds=600
    ) == "True"
    assert _render_reconciliation(
        expr, climate_state="cool", truth_value="NaN", invalid_age_seconds=600
    ) == "True", "NaN is invalid for reconciliation too"


def test_reconciliation_decision_ignores_healthy_and_noncooling():
    """No OFF for healthy truth, and no OFF for a unit that is not cooling."""
    expr = reconciliation_decision_expr()
    assert _render_reconciliation(
        expr, climate_state="cool", truth_value="70", invalid_age_seconds=600
    ) == "False", "healthy truth must never force OFF"
    assert _render_reconciliation(
        expr, climate_state="off", truth_value="unavailable", invalid_age_seconds=600
    ) == "False", "a non-cooling unit must never be touched"


# ---------------------------------------------------------------------------
# GROUP 2 — Supervisor truth-validity guard (xfail until implemented)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason=PENDING, strict=False)
def test_supervisor_defines_per_zone_truth_ok(automations):
    """Each zone validates truth via the shared FINITE-VALUE definition before
    the deadband: parse with float(none), reject NaN (self-equality), and bound
    to the broad safety window (rejects infinity). Same definition the event
    path uses."""
    v = _supervisor_control_variables(_supervisor(automations))
    for _key, (truth, _clim, ok) in ZONES.items():
        assert ok in v, f"supervisor must define {ok}"
        expr = v[ok]
        assert truth in expr, f"{ok} must reference {truth}"
        _assert_finite_validity_fragments(expr, ok)


@pytest.mark.xfail(reason=PENDING, strict=False)
def test_supervisor_guard_rejects_nan_and_infinity(automations):
    """Behavioral: render each zone's actual ``*_truth_ok`` expression from the
    live YAML against NaN / +inf / -inf and confirm it reports invalid (False),
    while ordinary temperatures report valid (True). (BLOCKER 1 tests 1 & 2)"""
    v = _supervisor_control_variables(_supervisor(automations))
    for _key, (_truth, _clim, ok) in ZONES.items():
        expr = v.get(ok, "")
        for bad in ("NaN", "nan", "inf", "-inf", "err", "unavailable"):
            assert _render_validity(expr, bad) == "False", (
                f"{ok}: {bad!r} must be rejected by the supervisor guard"
            )
        for good in ("70", "61.5", "-3.2"):
            assert _render_validity(expr, good) == "True", (
                f"{ok}: {good!r} must remain valid"
            )


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
    every zone renders OFF — no invalid truth reaches float(70) as control.
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
        assert out == "off", f"{clim}: invalid truth must force OFF, got {out!r}"


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
    assert out == "off", f"Master sleep + invalid truth must be OFF, got {out!r}"


# ---------------------------------------------------------------------------
# GROUP 3 — Event-triggered protective-OFF automation (xfail until implemented)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason=PENDING, strict=False)
def test_event_failsafe_present_per_zone_validity_triggers(automations):
    """Template triggers (not state-to-unavailable), one per zone, id=climate."""
    auto = _auto(automations, FAILSAFE_ID)
    assert auto is not None, f"{FAILSAFE_ID} automation must exist"
    template_trigs = {
        t.get("id"): t
        for t in auto.get("trigger", [])
        if t.get("platform") == "template"
    }
    for _key, (truth, clim, _ok) in ZONES.items():
        trig = template_trigs.get(clim)
        assert trig is not None, f"missing template trigger with id={clim}"
        vt = trig.get("value_template", "")
        assert truth in vt, f"trigger {clim} must reference {truth}"


@pytest.mark.xfail(reason=PENDING, strict=False)
def test_event_failsafe_validity_uses_finite_value_definition(automations):
    """Each trigger must use the shared FINITE-VALUE definition, not the old
    ``float(none) is not none`` test — so NaN / infinity cannot bypass the event
    path while being caught by the supervisor guard. (BLOCKER 1 test 3)"""
    auto = _auto(automations, FAILSAFE_ID)
    assert auto is not None
    trigs = [t for t in auto.get("trigger", []) if t.get("platform") == "template"]
    assert trigs, "fail-safe must have template triggers"
    for trig in trigs:
        vt = trig.get("value_template", "")
        _assert_finite_validity_fragments(vt, f"event trigger {trig.get('id')}")
        # And it must actually flag NaN/inf/etc as invalid when rendered.
        for bad in ("NaN", "inf", "-inf", "err", "unavailable"):
            assert _render_validity(vt, bad) == "True", (
                f"event trigger {trig.get('id')}: {bad!r} must read invalid"
            )
        assert _render_validity(vt, "70") == "False", "70 must read valid"


@pytest.mark.xfail(reason=PENDING, strict=False)
def test_event_failsafe_two_minute_persistence(automations):
    auto = _auto(automations, FAILSAFE_ID)
    assert auto is not None
    trigs = [t for t in auto.get("trigger", []) if t.get("platform") == "template"]
    assert trigs, "fail-safe must have template triggers"
    for trig in trigs:
        for_val = trig.get("for")
        assert for_val in ("00:02:00", 120, {"minutes": 2}, {"seconds": 120}), (
            f"each validity trigger needs a 2-minute persistence, got {for_val!r}"
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


@pytest.mark.xfail(reason=PENDING, strict=False)
def test_protective_off_not_blocked_by_notification(automations):
    """Climate OFF must precede any notify, and any notify must be non-blocking.

    Guarantees a missing/failed notification service cannot prevent or invalidate
    the protective OFF.
    """
    auto = _auto(automations, FAILSAFE_ID)
    assert auto is not None
    actions = [s for s in auto.get("action", []) if isinstance(s, dict)]

    def _svc(s):
        return s.get("action") or s.get("service") or ""

    off_idx = next(
        (i for i, s in enumerate(actions)
         if _svc(s) == "climate.set_hvac_mode"
         and s.get("data", {}).get("hvac_mode") in ("off", False)),
        None,
    )
    assert off_idx is not None, "fail-safe must issue climate.set_hvac_mode off"
    for i, s in enumerate(actions):
        if _svc(s).startswith("notify."):
            assert i > off_idx, "notify must come AFTER the protective OFF"
            assert s.get("continue_on_error") is True, (
                "notify must be non-blocking (continue_on_error: true)"
            )


# ---------------------------------------------------------------------------
# GROUP 4 — Restart/reload reconciliation (xfail until implemented)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason=PENDING, strict=False)
def test_reconciliation_present_restart_and_reload_safe(automations):
    """Reconciliation has a homeassistant start trigger AND a periodic sweep.

    Start trigger covers HA restart; the periodic time_pattern covers automation
    reload (which fires no start event) and bounds any blind spot.
    """
    auto = _auto(automations, RECON_ID)
    assert auto is not None, f"{RECON_ID} automation must exist"
    platforms = {t.get("platform") for t in auto.get("trigger", [])}
    assert "homeassistant" in platforms, "needs a homeassistant start trigger"
    assert "time_pattern" in platforms, "needs a periodic reconciliation trigger"


@pytest.mark.xfail(reason=PENDING, strict=False)
def test_reconciliation_startup_settle_delay(automations):
    """Start path waits a bounded delay so briefly-unavailable startup entities
    do not cause false protective shutdowns."""
    auto = _auto(automations, RECON_ID)
    assert auto is not None
    assert "delay" in json.dumps(auto.get("action", [])), (
        "reconciliation start path must include a bounded settle delay"
    )


@pytest.mark.xfail(reason=PENDING, strict=False)
def test_reconciliation_uses_finite_value_definition(automations):
    """Reconciliation sweeps all four zones, OFF-only, and uses the SAME shared
    finite-value definition as the supervisor guard and event path."""
    auto = _auto(automations, RECON_ID)
    assert auto is not None
    blob = json.dumps(auto.get("action", []))
    for _key, (truth, clim, _ok) in ZONES.items():
        assert truth in blob, f"reconciliation must consider {truth}"
        assert clim in blob, f"reconciliation must consider {clim}"
    _assert_finite_validity_fragments(blob, "reconciliation")
    assert "'cool'" in blob or '"cool"' in blob, "must gate on a unit being cool"
    # OFF-only: every hvac_mode set in the action tree is 'off'
    for mode in _collect_hvac_modes(auto.get("action", [])):
        assert mode in ("off", False), f"reconciliation may only set off, got {mode!r}"


@pytest.mark.xfail(reason=PENDING, strict=False)
def test_reconciliation_requires_two_minute_invalid_persistence(automations):
    """BLOCKER 2: the periodic/startup sweep must only force OFF once the invalid
    state has persisted >= 2 minutes (state-age check on the truth entity's
    current invalid-state timestamp). It must NOT force OFF on a brief invalid
    state right after an automation reload."""
    auto = _auto(automations, RECON_ID)
    assert auto is not None
    blob = json.dumps(auto.get("action", []))
    assert "last_changed" in blob, (
        "reconciliation must check the invalid-state age via last_changed"
    )
    # The 2-minute floor must be present in some accepted form.
    assert any(
        tok in blob
        for tok in (str(MIN_INVALID_SECONDS), "00:02:00", "minutes=2", "minutes': 2")
    ), "reconciliation must require >= 2 minutes of persistent invalid truth"


@pytest.mark.xfail(reason=PENDING, strict=False)
def test_reconciliation_startup_does_not_bypass_persistence(automations):
    """BLOCKER 2 / test 6: startup may keep its settle delay, but after that
    delay it must use the SAME age-gated sweep — there must be no OFF action that
    is reachable without the >=2-minute invalid-age condition."""
    auto = _auto(automations, RECON_ID)
    assert auto is not None
    actions = auto.get("action", [])
    blob = json.dumps(actions)
    # A settle delay exists for the start path...
    assert "delay" in blob, "start path must retain a bounded settle delay"
    # ...and every OFF is age-gated: each if/then that forces OFF must carry the
    # last_changed age check in its condition.
    ifs_with_age = []

    def walk(obj):
        if isinstance(obj, list):
            for item in obj:
                walk(item)
        elif isinstance(obj, dict):
            if "if" in obj:
                cond_blob = json.dumps(obj.get("if"))
                then_modes = _collect_hvac_modes(obj.get("then", []))
                if any(m in ("off", False) for m in then_modes):
                    ifs_with_age.append("last_changed" in cond_blob)
            for val in obj.values():
                if isinstance(val, (list, dict)):
                    walk(val)

    walk(actions)
    assert ifs_with_age, "reconciliation must force OFF inside an if/then block"
    assert all(ifs_with_age), (
        "every reconciliation OFF must be gated by the invalid-age (last_changed) "
        "check — startup must not bypass the 2-minute persistence"
    )
    # And there must be no top-level/unconditional OFF outside an if.
    for step in actions:
        if isinstance(step, dict) and (
            (step.get("action") or step.get("service")) == "climate.set_hvac_mode"
        ):
            pytest.fail("reconciliation must not issue an unconditional climate.set_hvac_mode")


# ---------------------------------------------------------------------------
# ENFORCEABLE GATE — must be a NORMAL test (green in both phases)
# ---------------------------------------------------------------------------

def test_packet_a_xfail_markers_removed_once_implemented(automations):
    """Make the test gate enforceable.

    ``xfail(strict=False)`` lets an XPASS slip through a green suite, so once the
    runtime guard is implemented every Packet A marker MUST be removed and the
    tests must run as ordinary assertions. This gate ties marker-removal to the
    implementation signal (supervisor truth guards present in YAML):

      * design phase  (guards absent): markers expected -> pass.
      * implemented   (guards present) AND markers removed: pass.
      * implemented but markers left (the dangerous XPASS state): FAIL the suite.
    """
    v = _supervisor_control_variables(_supervisor(automations))
    implemented = all(ok in v for _k, (_t, _c, ok) in ZONES.items())

    marker = "@pytest.mark." + "xfail"  # built by concat so this line isn't a hit
    with open(__file__, "r") as fh:
        marker_count = fh.read().count(marker)

    if implemented:
        assert marker_count == 0, (
            "Packet A runtime guard is implemented but xfail markers remain. "
            "Remove every xfail marker so the contract tests run as enforced "
            "assertions (zero XFAIL, zero XPASS)."
        )
    else:
        assert marker_count >= 1, (
            "Design phase expected: xfail markers should be present until the "
            "runtime change lands."
        )
