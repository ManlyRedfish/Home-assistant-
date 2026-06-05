#!/usr/bin/env python3
"""Guard docs-only pull requests from changing executable/runtime files."""

from __future__ import annotations

import argparse
import fnmatch
import json
from pathlib import PurePosixPath
from typing import Any, Iterable

DOCS_ONLY_LABEL = "docs-only"

PROTECTED_ROOT_FILES = {
    "configuration.yaml",
    "automations.yaml",
    "scripts.yaml",
    "scenes.yaml",
    "secrets.yaml",
}

PROTECTED_PREFIXES = (
    "custom_components/",
    "packages/",
    "blueprints/",
    "tools/",
    "tests/",
    ".github/workflows/",
)

PROTECTED_SUFFIXES = (
    ".yaml",
    ".yml",
    ".py",
    ".ps1",
    ".sh",
)

PROTECTED_GLOBS = (
    "requirements*.txt",
)


def normalize_path(path: str) -> str:
    """Return a repository-relative POSIX path without leading './' segments."""
    normalized = PurePosixPath(path.strip()).as_posix()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def is_protected_path(path: str) -> bool:
    """Return True when a changed path is outside docs-only PR scope."""
    normalized = normalize_path(path)
    lowered = normalized.lower()

    if not normalized:
        return False

    if lowered in PROTECTED_ROOT_FILES:
        return True

    if lowered.startswith(PROTECTED_PREFIXES):
        return True

    if lowered.endswith(PROTECTED_SUFFIXES):
        return True

    name = PurePosixPath(lowered).name
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in PROTECTED_GLOBS)


def prohibited_paths(changed_paths: Iterable[str]) -> list[str]:
    """Return every protected changed path, preserving input order."""
    return [path for path in (normalize_path(p) for p in changed_paths) if is_protected_path(path)]


def event_has_docs_only_label(event: dict[str, Any]) -> bool:
    """Return True when the pull request event contains the exact docs-only label."""
    labels = event.get("pull_request", {}).get("labels", [])
    return any(label.get("name") == DOCS_ONLY_LABEL for label in labels if isinstance(label, dict))


def read_changed_paths(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as file:
        return [line.rstrip("\n") for line in file if line.rstrip("\n")]


def read_event(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True, help="Path to the GitHub pull_request event JSON")
    parser.add_argument("--changed-files", required=True, help="Newline-delimited changed-file list")
    args = parser.parse_args()

    event = read_event(args.event)
    changed_paths = read_changed_paths(args.changed_files)

    if not event_has_docs_only_label(event):
        print("docs-only label is absent; docs-only scope guard is not enforcing this PR.")
        return 0

    blocked = prohibited_paths(changed_paths)
    if not blocked:
        print("docs-only label is present and all changed files are within permitted documentation scope.")
        return 0

    print("::error::docs-only PR modifies protected files or paths.")
    print("The docs-only label permits documentation-only changes, but blocks runtime, executable, test, configuration, automation, workflow, and dependency files.")
    print("Prohibited changed paths:")
    for path in blocked:
        print(f" - {path}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
