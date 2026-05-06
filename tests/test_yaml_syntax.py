import pytest
import yaml
import os

def yaml_include(loader, node):
    return node.value

def yaml_secret(loader, node):
    return node.value

yaml.add_constructor('!include', yaml_include, Loader=yaml.SafeLoader)
yaml.add_constructor('!secret', yaml_secret, Loader=yaml.SafeLoader)

def check_yaml_file(filepath):
    """Parses a YAML file and raises an exception if it's invalid."""
    if not os.path.exists(filepath):
        pytest.skip(f"{filepath} not found.")
        return

    with open(filepath, 'r') as file:
        try:
            yaml.safe_load(file)
        except Exception as e:
            pytest.fail(f"Invalid YAML in {filepath}:\n{e}")

def test_configuration_yaml_syntax():
    """Validates the syntax of configuration.yaml."""
    check_yaml_file('configuration.yaml')

def test_automations_yaml_syntax():
    """Validates the syntax of automations.yaml."""
    check_yaml_file('automations.yaml')
