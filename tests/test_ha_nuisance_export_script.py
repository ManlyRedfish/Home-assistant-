from pathlib import Path


def test_export_script_is_read_only_get_only() -> None:
    script = Path('tools/export_ha_nuisance_evidence.ps1').read_text(encoding='utf-8').lower()

    assert '-method get' in script
    assert '-method post' not in script
    assert '/api/services' not in script


def test_export_script_expected_categories_and_logbook_output() -> None:
    script = Path('tools/export_ha_nuisance_evidence.ps1').read_text(encoding='utf-8')

    required_tokens = [
        "Export-Category -Category 'climates'",
        "Export-Category -Category 'automations'",
        "Export-Category -Category 'timers'",
        'ha_logbook.json',
    ]

    for token in required_tokens:
        assert token in script
