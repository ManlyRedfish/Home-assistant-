import os
import yaml


class MooseAutomationLoader(yaml.SafeLoader):
    pass


def secret_constructor(loader, node):
    return f"SECRET_{node.value}"


def include_constructor(loader, node):
    return f"INCLUDE_{node.value}"


def input_constructor(loader, node):
    return f"INPUT_{node.value}"


def include_dir_merge_list_constructor(loader, node):
    return []


MooseAutomationLoader.add_constructor('!secret', secret_constructor)
MooseAutomationLoader.add_constructor('!include', include_constructor)
MooseAutomationLoader.add_constructor('!input', input_constructor)
MooseAutomationLoader.add_constructor('!include_dir_merge_list', include_dir_merge_list_constructor)
MooseAutomationLoader.add_constructor('!include_dir_named', include_dir_merge_list_constructor)


def _load_main_supervisor_actions():
    file_path = os.path.join(os.path.dirname(__file__), '..', 'automations.yaml')
    with open(file_path, 'r') as f:
        data = yaml.load(f, Loader=MooseAutomationLoader)

    supervisor = next(
        (a for a in data if a.get('id') == 'v7_5_main_supervisor'),
        None,
    )
    assert supervisor is not None, "Main supervisor automation v7_5_main_supervisor not found"

    actions = supervisor.get('action', [])
    assert isinstance(actions, list), "Main supervisor actions must be a list"
    return actions


def _extract_cooling_variable_templates(actions):
    templates = {}
    for item in actions:
        if isinstance(item, dict) and 'choose' in item:
            for choice in item.get('choose', []):
                sequence = choice.get('sequence', [])
                for step in sequence:
                    if isinstance(step, dict) and 'variables' in step:
                        for k, v in step['variables'].items():
                            if k in {
                                'm_setpoint', 'm_off_at', 'm_on_at',
                                'l_setpoint', 'l_off_at', 'l_on_at',
                                'ly_setpoint', 'ly_off_at', 'ly_on_at',
                                'lr_setpoint', 'lr_off_at', 'lr_on_at',
                            }:
                                templates[k] = v
            break

    missing = {
        'm_setpoint', 'm_off_at', 'm_on_at',
        'l_setpoint', 'l_off_at', 'l_on_at',
        'ly_setpoint', 'ly_off_at', 'ly_on_at',
        'lr_setpoint', 'lr_off_at', 'lr_on_at',
    } - templates.keys()
    assert not missing, f"Missing expected Section 2 cooling variable templates: {sorted(missing)}"
    return templates


def test_section2_cooling_setpoint_and_threshold_doctrine():
    templates = _extract_cooling_variable_templates(_load_main_supervisor_actions())

    assert templates['m_setpoint'] == "{{ 61 }}"
    assert templates['l_setpoint'] == "{{ 61 }}"
    assert templates['ly_setpoint'] == "{{ 61 }}"
    assert templates['lr_setpoint'] == "{{ 61 }}"

    assert templates['m_off_at'] == "{{ 74 if away else (62 if is_master_sleep else 68) }}"
    assert templates['m_on_at'] == "{{ 76 if away else (66 if is_master_sleep else 72) }}"

    assert templates['l_off_at'] == "{{ 74 if away else 68 }}"
    assert templates['l_on_at'] == "{{ 76 if away else 72 }}"
    assert templates['ly_off_at'] == "{{ 74 if away else 68 }}"
    assert templates['ly_on_at'] == "{{ 76 if away else 72 }}"
    assert templates['lr_off_at'] == "{{ 74 if away else 68 }}"
    assert templates['lr_on_at'] == "{{ 76 if away else 72 }}"
