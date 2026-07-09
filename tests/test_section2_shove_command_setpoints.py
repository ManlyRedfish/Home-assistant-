"""
Section 2 Samsung actuator shove command regression guards.

This PR changes only actuator command setpoints in the existing supervisor:
Samsung cooling commands shove to 61°F and Samsung heating commands shove to
79°F. Room-truth comparisons, on/off thresholds, safety gates, arbitration,
comfort profiles, MSR/Apollo boundaries, and truth freshness are deliberately
out of scope.
"""

import os
import re

import yaml


class MooseAutomationLoader(yaml.SafeLoader):
    pass


def _secret(loader, node):
    return f"SECRET_{node.value}"


def _include(loader, node):
    return f"INCLUDE_{node.value}"


def _input(loader, node):
    return f"INPUT_{node.value}"


def _include_dir_merge_list(loader, node):
    return []


MooseAutomationLoader.add_constructor("!secret", _secret)
MooseAutomationLoader.add_constructor("!include", _include)
MooseAutomationLoader.add_constructor("!input", _input)
MooseAutomationLoader.add_constructor("!include_dir_merge_list", _include_dir_merge_list)
MooseAutomationLoader.add_constructor("!include_dir_named", _include_dir_merge_list)


REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
AUTOMATIONS = os.path.join(REPO_ROOT, "automations.yaml")
CONFIGURATION = os.path.join(REPO_ROOT, "configuration.yaml")
SUPERVISOR_ID = "v7_5_main_supervisor"
MINI_SPLITS = {
    "climate.living_room_air",
    "climate.master_bedroom_air",
    "climate.lincoln_air",
    "climate.lilly_air",
}


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _load_automations():
    with open(AUTOMATIONS, "r", encoding="utf-8") as fh:
        return yaml.load(fh, Loader=MooseAutomationLoader)


def _supervisor():
    supervisor = next(
        (a for a in _load_automations() if a.get("id") == SUPERVISOR_ID),
        None,
    )
    assert supervisor is not None, f"{SUPERVISOR_ID} not found"
    return supervisor


def _walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk(value)


def _section2_text():
    text = _read(AUTOMATIONS)
    return text.split("# SECTION 2: MAIN SUPERVISOR", 1)[1].split(
        "# SECTION 3: SAFETY GATES", 1
    )[0]


def _variable_values(supervisor):
    values = {}
    for node in _walk(supervisor):
        variables = node.get("variables")
        if isinstance(variables, dict):
            for name, value in variables.items():
                values.setdefault(name, set()).add(value)
    return values


def _temperature_value(command, variables):
    raw = command.get("data", {}).get("temperature")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        direct = re.fullmatch(r"\{\{\s*(\d+)\s*\}\}", raw)
        if direct:
            return int(direct.group(1))
        var = re.fullmatch(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", raw)
        if var:
            name = var.group(1)
            assert name in variables, f"Command temperature references unknown variable {name!r}"
            resolved = variables[name]
            assert len(resolved) == 1, f"Variable {name!r} has ambiguous command values: {resolved!r}"
            value = next(iter(resolved))
            if isinstance(value, int):
                return value
            if isinstance(value, str):
                direct_var = re.fullmatch(r"\{\{\s*(\d+)\s*\}\}", value)
                if direct_var:
                    return int(direct_var.group(1))
            raise AssertionError(f"Variable {name!r} does not resolve to a shove setpoint: {value!r}")
    raise AssertionError(f"Unsupported command temperature payload: {raw!r}")


def _section2_set_temperature_commands():
    supervisor = _supervisor()
    commands = []
    for node in _walk(supervisor):
        if (node.get("action") or node.get("service")) == "climate.set_temperature":
            commands.append(node)
    return commands, _variable_values(supervisor)


def test_section2_cooling_actuator_commands_use_61_separate_from_thresholds():
    commands, variables = _section2_set_temperature_commands()
    cooling_commands = []
    for command in commands:
        entity = command.get("target", {}).get("entity_id")
        hvac_template = str(command.get("data", {}).get("hvac_mode", ""))
        if entity in MINI_SPLITS and "cool" in hvac_template and "heat" not in hvac_template:
            cooling_commands.append(command)
            assert _temperature_value(command, variables) == 61

    # Ten cooling command paths: 4 in the cooling branch (Master, Lincoln, Lilly,
    # LR), 3 in the shoulder-day warm block (Master, Lincoln, Lilly), 1 in the
    # shoulder-night Master escape, and 2 in the kids' bedtime block (Lincoln
    # and Lilly, added by the 2026-06-07 operator decision).
    assert len(cooling_commands) == 10, "Expected the ten mini-split cooling command paths."

    text = _section2_text()
    # Cooling comparisons / stop thresholds remain exactly as before; command
    # payloads are tested separately above.
    assert "m_off_at: \"{{ 74 if away else (62 if is_master_sleep else 68) }}\"" in text
    assert "m_on_at: \"{{ 76 if away else (66 if is_master_sleep else 72) }}\"" in text
    assert "l_off_at: \"{{ 74 if away else 68 }}\"" in text
    assert "l_on_at: \"{{ 76 if away else 72 }}\"" in text
    assert "ly_off_at: \"{{ 74 if away else 68 }}\"" in text
    assert "ly_on_at: \"{{ 76 if away else 72 }}\"" in text
    assert "lr_conservation: \"{{ away or lr_night_primary }}\"" in text
    assert "lr_off_at: \"{{ 74 if lr_conservation else 68 }}\"" in text
    assert "lr_on_at: \"{{ 76 if lr_conservation else 72 }}\"" in text
    assert "m_sleep_on_at: \"{{ 76 if away else 66 }}\"" in text
    assert "m_sleep_off_at: \"{{ 74 if away else 62 }}\"" in text
    assert "master_temp > 70" in text
    assert "lincoln_temp > 70" in text
    assert "lilly_temp > 70" in text


def test_section2_heating_actuator_commands_use_79_separate_from_thresholds():
    commands, variables = _section2_set_temperature_commands()
    heating_commands = []
    for command in commands:
        entity = command.get("target", {}).get("entity_id")
        hvac_template = str(command.get("data", {}).get("hvac_mode", ""))
        if entity in MINI_SPLITS and "heat" in hvac_template and "cool" not in hvac_template:
            heating_commands.append(command)
            assert _temperature_value(command, variables) == 79

    assert len(heating_commands) == 12, "Expected the existing twelve mini-split heating command paths."

    text = _section2_text()
    # Heating thresholds remain exactly where they were; target_lr remains an
    # off threshold, not an actuator command temperature.
    for threshold in (
        "lr_temp < (58 if away else 65)",
        "lr_temp < (65 if away else 71)",
        "master_temp < 62",
        "lincoln_temp < 62",
        "lilly_temp < 62",
        "master_temp < 67",
        "lincoln_temp < 67",
        "lilly_temp < 67",
        "lr_temp < 60",
        "lr_temp < (lr_on_at | int)",
        "lr_temp >= (lr_off_at | int)",
    ):
        assert threshold in text

    assert text.count('lr_off_at: "{{ target_lr }}"') == 2
    assert 'temperature: "{{ target_lr }}"' not in text
    assert text.count("lr_heat_command_setpoint: 79") == 2


def test_section2_dining_room_nest_setpoint_not_promoted_to_samsung_shove():
    commands, _variables = _section2_set_temperature_commands()
    dining_commands = [
        command
        for command in commands
        if command.get("target", {}).get("entity_id") == "climate.dining_room"
    ]
    assert len(dining_commands) == 1
    assert dining_commands[0].get("data", {}).get("temperature") == 68


def test_section3_safety_floors_remain_unchanged_by_shove_commands():
    text = _read(AUTOMATIONS)
    assert "below: 60" in text, "Living Room runaway cooling cutoff must remain 60°F."
    assert "below: 58" in text, "Master emergency floor must remain 58°F."


def test_shove_pr_does_not_introduce_arbitration_or_comfort_profiles():
    runtime_text = _read(AUTOMATIONS) + "\n" + _read(CONFIGURATION)
    lowered = runtime_text.lower()
    assert "opposite_mode_lockout" not in lowered
    assert "moose_house_arbitration_state" not in lowered
    assert "comfort_profile" not in lowered
    assert "input_select.moose_comfort" not in lowered


def test_shove_pr_does_not_promote_msr_or_apollo_into_supervisor_control():
    supervisor_text = str(_supervisor()).lower()
    for forbidden in ("msr", "apollo", "dps310", "mmwave", "ld2410", "scd40", "radar_zone", "co2"):
        assert forbidden not in supervisor_text


def test_truth_freshness_still_uses_report_time_not_last_changed():
    config_text = _read(CONFIGURATION)
    assert ".last_reported).total_seconds()" in config_text
    assert ".last_changed).total_seconds()" not in config_text
