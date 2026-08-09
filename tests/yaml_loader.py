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
MooseAutomationLoader.add_constructor(
    "!include_dir_merge_list", _include_dir_merge_list
)
MooseAutomationLoader.add_constructor("!include_dir_named", _include_dir_merge_list)
