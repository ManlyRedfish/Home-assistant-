"""Structural contract for Heat Wave Override per-head failure isolation."""

from pathlib import Path

import yaml


class ConfigurationLoader(yaml.SafeLoader):
    pass


ConfigurationLoader.add_constructor("!secret", lambda loader, node: node.value)
ConfigurationLoader.add_constructor("!include", lambda loader, node: node.value)
ConfigurationLoader.add_constructor("!include_dir_named", lambda loader, node: {})
ConfigurationLoader.add_constructor("!include_dir_merge_list", lambda loader, node: [])

CONFIGURATION = yaml.load(
    Path("configuration.yaml").read_text(encoding="utf-8"),
    Loader=ConfigurationLoader,
)

EXPECTED_HEADS = [
    (
        "Living Room",
        "climate.living_room_air",
        "lr_truth",
        "x is not none and x == x and x > -90 and x < 200 and x > 60",
    ),
    (
        "Master",
        "climate.master_bedroom_air",
        "master_truth",
        "x is not none and x == x and x > -90 and x < 200 and x > 58",
    ),
    (
        "Lincoln",
        "climate.lincoln_air",
        "lincoln_truth",
        "x is not none and x == x and x > -90 and x < 200",
    ),
    (
        "Lilly",
        "climate.lilly_air",
        "lilly_truth",
        "x is not none and x == x and x > -90 and x < 200",
    ),
]


def _script():
    return CONFIGURATION["script"]["heat_wave_override_apply"]


def _boundaries():
    return _script()["sequence"][1:]


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_override_remains_mode_single_with_exactly_four_isolated_head_units():
    assert _script()["mode"] == "single"
    assert len(_boundaries()) == 4

    for boundary, (name, _, _, _) in zip(_boundaries(), EXPECTED_HEADS):
        assert boundary["alias"] == f"Head boundary: Heat Wave Override {name}"
        assert boundary["continue_on_error"] is True
        assert set(boundary) == {"alias", "continue_on_error", "choose"}
        assert len(boundary["choose"]) == 1


def test_each_head_unit_preserves_truth_guard_and_exact_command_sequence():
    for boundary, (_, entity, truth_variable, guard_text) in zip(
        _boundaries(), EXPECTED_HEADS
    ):
        choice = boundary["choose"][0]
        assert choice["conditions"] == [
            {
                "condition": "template",
                "value_template": choice["conditions"][0]["value_template"],
            }
        ]
        guard = choice["conditions"][0]["value_template"]
        assert f"{{% set x = {truth_variable} %}}" in guard
        assert guard_text in guard
        assert choice["sequence"] == [
            {
                "action": "climate.set_hvac_mode",
                "target": {"entity_id": entity},
                "data": {"hvac_mode": "cool"},
            },
            {"delay": "00:00:02"},
            {
                "action": "climate.set_temperature",
                "target": {"entity_id": entity},
                "data": {"temperature": 61},
            },
            {"delay": "00:00:01"},
            {
                "action": "climate.set_fan_mode",
                "target": {"entity_id": entity},
                "data": {"fan_mode": "turbo"},
            },
        ]


def test_continuation_exists_only_at_complete_head_boundaries_and_dining_is_untouched():
    climate_calls = [
        node
        for node in _walk(_script())
        if str(node.get("action", "")).startswith("climate.")
    ]

    assert len(climate_calls) == 12
    assert all("continue_on_error" not in call for call in climate_calls)
    assert {
        call["target"]["entity_id"] for call in climate_calls
    } == {entity for _, entity, _, _ in EXPECTED_HEADS}
    assert all("climate.dining_room" not in str(node) for node in _walk(_script()))
