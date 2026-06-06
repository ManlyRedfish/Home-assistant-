import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "docs_only_guard.py"
spec = importlib.util.spec_from_file_location("docs_only_guard", MODULE_PATH)
docs_only_guard = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = docs_only_guard
spec.loader.exec_module(docs_only_guard)


def event_with_labels(*labels: str) -> dict:
    return {"pull_request": {"labels": [{"name": label} for label in labels]}}


def test_markdown_only_pr_passes() -> None:
    assert docs_only_guard.prohibited_paths(
        ["README.md", "architecture/notes.md"]
    ) == []


def test_documentation_assets_under_docs_pass() -> None:
    changed = [
        "docs/v9_v10_goals.md",
        "docs/assets/stack-effect.png",
        "docs/diagrams/floorplan.svg",
    ]
    assert docs_only_guard.prohibited_paths(changed) == []


def test_automations_yaml_fails() -> None:
    assert docs_only_guard.prohibited_paths(
        ["automations.yaml"]
    ) == ["automations.yaml"]


def test_nested_yaml_fails_even_under_docs() -> None:
    changed = ["docs/examples/sample.yaml", "nested/config.yml"]
    assert docs_only_guard.prohibited_paths(changed) == changed


def test_python_powershell_and_shell_scripts_fail() -> None:
    changed = [
        "analysis/model.py",
        "tools/export_ha_nuisance_evidence.ps1",
        "scripts/check.sh",
    ]
    assert docs_only_guard.prohibited_paths(changed) == changed


def test_tests_and_tools_paths_fail_regardless_of_extension() -> None:
    changed = ["tests/test_yaml_syntax.txt", "tools/readme.md"]
    assert docs_only_guard.prohibited_paths(changed) == changed


def test_workflow_modifications_fail() -> None:
    changed = [".github/workflows/docs-only-guard.yml"]
    assert docs_only_guard.prohibited_paths(changed) == changed


def test_dependency_and_executable_configuration_fails() -> None:
    changed = [
        "requirements-dev.txt",
        "pyproject.toml",
        "package-lock.json",
        "Dockerfile",
    ]
    assert docs_only_guard.prohibited_paths(changed) == changed


def test_multiple_changed_files_report_every_prohibited_path() -> None:
    changed = [
        "docs/overview.md",
        "automations.yaml",
        "custom_components/moose/__init__.py",
        "requirements-dev.txt",
        "README.md",
        ".github/workflows/ci.yaml",
    ]
    code, output = docs_only_guard.run(event_with_labels("docs-only"), changed)
    assert code == 1
    for path in (
        "automations.yaml",
        "custom_components/moose/__init__.py",
        "requirements-dev.txt",
        ".github/workflows/ci.yaml",
    ):
        assert f" - {path}" in output
    assert "docs/overview.md" not in output
    assert "README.md" not in output


def test_no_docs_only_label_means_guard_does_not_enforce() -> None:
    code, output = docs_only_guard.run(
        event_with_labels("bug", "documentation"),
        ["automations.yaml"],
    )
    assert code == 0
    assert "not enforcing" in output


def test_exact_docs_only_label_enforces() -> None:
    code, output = docs_only_guard.run(
        event_with_labels("bug", "docs-only"),
        ["automations.yaml"],
    )
    assert code == 1
    assert "automations.yaml" in output
