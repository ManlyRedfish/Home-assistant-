import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path("tools/docs_only_guard.py")
spec = importlib.util.spec_from_file_location("docs_only_guard", MODULE_PATH)
docs_only_guard = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(docs_only_guard)


def event_with_labels(*labels: str) -> dict:
    return {"pull_request": {"labels": [{"name": label} for label in labels]}}


def test_markdown_only_pr_passes() -> None:
    assert docs_only_guard.prohibited_paths(["README.md", "architecture/notes.md"]) == []


def test_files_under_docs_pass() -> None:
    changed = ["docs/v9_v10_goals.md", "docs/assets/stack-effect.png", "docs/diagrams/floorplan.svg"]

    assert docs_only_guard.prohibited_paths(changed) == []


def test_automations_yaml_fails() -> None:
    assert docs_only_guard.prohibited_paths(["automations.yaml"]) == ["automations.yaml"]


def test_nested_yaml_fails() -> None:
    assert docs_only_guard.prohibited_paths(["docs/examples/sample.yaml", "nested/config.yml"]) == [
        "docs/examples/sample.yaml",
        "nested/config.yml",
    ]


def test_python_and_powershell_scripts_fail() -> None:
    changed = ["analysis/model.py", "tools/export_ha_nuisance_evidence.ps1", "scripts/check.sh"]

    assert docs_only_guard.prohibited_paths(changed) == changed


def test_tests_and_tools_paths_fail() -> None:
    changed = ["tests/test_yaml_syntax.txt", "tools/readme.md"]

    assert docs_only_guard.prohibited_paths(changed) == changed


def test_workflow_modifications_fail() -> None:
    changed = [".github/workflows/docs-only-guard.yml"]

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

    assert docs_only_guard.prohibited_paths(changed) == [
        "automations.yaml",
        "custom_components/moose/__init__.py",
        "requirements-dev.txt",
        ".github/workflows/ci.yaml",
    ]


def test_no_docs_only_label_means_guard_does_not_enforce(tmp_path, monkeypatch) -> None:
    event_path = tmp_path / "event.json"
    changed_files_path = tmp_path / "changed-files.txt"
    event_path.write_text(json.dumps(event_with_labels("bug", "documentation")), encoding="utf-8")
    changed_files_path.write_text("automations.yaml\n.github/workflows/ci.yaml\n", encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "docs_only_guard.py",
            "--event",
            str(event_path),
            "--changed-files",
            str(changed_files_path),
        ],
    )

    assert docs_only_guard.main() == 0


def test_exact_docs_only_label_enforces() -> None:
    assert docs_only_guard.event_has_docs_only_label(event_with_labels("bug", "docs-only"))
