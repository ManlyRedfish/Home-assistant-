from pathlib import Path


def _script_text() -> str:
    return Path('tools/export_ha_nuisance_evidence.ps1').read_text(encoding='utf-8')


def test_export_script_uses_get_only_and_no_service_writes() -> None:
    script = _script_text().lower()

    assert '-method get' in script
    assert '-method post' not in script
    assert '-method put' not in script
    assert '-method patch' not in script
    assert '-method delete' not in script
    assert '/api/services' not in script


def test_export_script_has_dynamic_output_templates_and_required_files() -> None:
    script = _script_text()

    required_tokens = [
        'ha_history_${Category}.json',
        'ha_history_${Category}.csv',
        'ha_logbook.json',
        'ha_export_manifest.json',
    ]

    for token in required_tokens:
        assert token in script


def test_export_script_has_required_entities() -> None:
    script = _script_text()

    required_entities = [
        'automation.v8_3_hvac_transition_log',
        'automation.v8_samsung_auto_guardrail',
        'automation.v7_5_ghost_assassin',
        'automation.v9_sleep_priority_interlock',
        'climate.living_room_air',
        'climate.master_bedroom_air',
        'climate.lincoln_air',
        'climate.lilly_air',
        'timer.lr_compressor_cooldown',
        'timer.master_compressor_cooldown',
        'timer.lincoln_compressor_cooldown',
        'timer.lilly_compressor_cooldown',
    ]

    for entity in required_entities:
        assert entity in script


def test_export_script_has_shade_discovery_and_token_redaction() -> None:
    script = _script_text()

    assert 'cover.*shade*' in script
    assert 'Get-RedactedMessage' in script
    assert '[REDACTED_TOKEN]' in script
