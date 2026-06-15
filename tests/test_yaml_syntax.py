import pytest
import yaml
import os


class MooseSyntaxLoader(yaml.SafeLoader):
    pass


def yaml_include(loader, node):
    return node.value

def yaml_secret(loader, node):
    return node.value

MooseSyntaxLoader.add_constructor('!include', yaml_include)
MooseSyntaxLoader.add_constructor('!secret', yaml_secret)

def check_yaml_file(filepath):
    """Parses a YAML file and raises an exception if it's invalid."""
    if not os.path.exists(filepath):
        pytest.skip(f"{filepath} not found.")
        return

    with open(filepath, 'r') as file:
        try:
            yaml.load(file, Loader=MooseSyntaxLoader)
        except Exception as e:
            pytest.fail(f"Invalid YAML in {filepath}:\n{e}")

def test_configuration_yaml_syntax():
    """Validates the syntax of configuration.yaml."""
    check_yaml_file('configuration.yaml')

def test_automations_yaml_syntax():
    """Validates the syntax of automations.yaml."""
    check_yaml_file('automations.yaml')


# ---------------------------------------------------------------------------
# Strict duplicate-key guard (regression: 2026-06-15 input_number outage).
#
# PyYAML's SafeLoader silently keeps the LAST value when a mapping repeats a
# key, so MooseSyntaxLoader above could not catch a duplicated key. Home
# Assistant's own YAML loader REJECTS the whole mapping on a duplicate key —
# that is what de-registered the entire `input_number:` domain on 2026-06-13
# (a stray, valueless `precool_previous_master_temp:` left at EOF by the V9-E
# revision), surfacing as the V9-E "unknown action: input_number.set_value"
# repair. This guard mirrors HA's behavior so the class of bug fails in CI.
# See docs/postmortems/2026-06-15_input_number_domain_and_v86_orphans.md.
# ---------------------------------------------------------------------------
class StrictNoDuplicateLoader(yaml.SafeLoader):
    pass


def _no_duplicate_keys(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                None, None,
                f"duplicate key {key!r}", key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictNoDuplicateLoader.add_constructor('!include', yaml_include)
StrictNoDuplicateLoader.add_constructor('!secret', yaml_secret)
StrictNoDuplicateLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys)


def check_no_duplicate_keys(filepath):
    """Fails if any mapping repeats a key (matches Home Assistant's loader)."""
    if not os.path.exists(filepath):
        pytest.skip(f"{filepath} not found.")
        return

    with open(filepath, 'r') as file:
        try:
            yaml.load(file, Loader=StrictNoDuplicateLoader)
        except yaml.constructor.ConstructorError as e:
            pytest.fail(f"Duplicate key in {filepath} (HA would reject):\n{e}")


def test_configuration_yaml_no_duplicate_keys():
    """configuration.yaml must have no duplicate mapping keys."""
    check_no_duplicate_keys('configuration.yaml')


def test_automations_yaml_no_duplicate_keys():
    """automations.yaml must have no duplicate mapping keys."""
    check_no_duplicate_keys('automations.yaml')
