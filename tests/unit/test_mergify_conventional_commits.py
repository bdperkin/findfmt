"""Unit tests for Mergify Conventional Commit labeling and stale-label reconciliation (#632)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml


@dataclass(frozen=True)
class StaleLabelCase:
    """Behavioral test vector for Mergify stale-label removal rules."""

    rule_name: str
    label_name: str
    title: str
    expected_remove: bool
    author: str = "bdperkin"
    closed: bool = False


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


def _load_mergify() -> dict[str, Any]:
    """Load and parse .mergify.yml from repository root."""
    path = _repo_root() / ".mergify.yml"
    assert path.is_file(), f"Missing .mergify.yml at {path}"
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), ".mergify.yml must parse to a YAML mapping"
    return data


def _defined_label_names() -> set[str]:
    """Return the set of label names declared in .github/labels.yml."""
    labels_path = _repo_root() / ".github" / "labels.yml"
    with labels_path.open(encoding="utf-8") as f:
        labels_data = yaml.safe_load(f)

    assert isinstance(labels_data, list)
    return {str(item.get("name")) for item in labels_data if isinstance(item, dict) and item.get("name")}


def _evaluate_mergify_condition(cond: str, *, case: StaleLabelCase) -> bool:
    """Evaluate a Mergify pull_request_rules condition against synthetic PR state."""
    if cond == "-closed":
        return not case.closed

    if cond.startswith("-title ~= "):
        return re.search(cond.removeprefix("-title ~= "), case.title) is None

    if cond.startswith("title ~= "):
        return re.search(cond.removeprefix("title ~= "), case.title) is not None

    if cond.startswith("-author = "):
        return case.author != cond.removeprefix("-author = ")

    if cond.startswith("label = "):
        return cond.removeprefix("label = ") == case.label_name

    msg = f"Unsupported Mergify condition in test: {cond!r}"
    raise AssertionError(msg)


def test_mergify_conventional_commit_queue_and_label_rules() -> None:
    """Validate Mergify queue conditions and Conventional Commit label rules (#632)."""
    mergify = _load_mergify()
    default_queue = mergify["queue_rules"][0]
    assert "check-success = Validate Conventional Commit PR Title" in default_queue["queue_conditions"]
    assert "check-success = Validate Conventional Commit PR Title" not in default_queue["merge_conditions"]

    pr_rules = mergify.get("pull_request_rules", [])
    by_name = {str(r.get("name")): r for r in pr_rules if isinstance(r, dict)}
    defined_labels = _defined_label_names()

    expected_title_label_rules = {
        "Label breaking-change pull requests from Conventional Commit title": "breaking change",
        "Label feature pull requests from Conventional Commit title": "enhancement",
        "Label bug-fix pull requests from Conventional Commit title": "bug",
        "Label documentation pull requests from Conventional Commit title": "documentation",
        "Label performance pull requests from Conventional Commit title": "performance",
        "Label refactoring pull requests from Conventional Commit title": "refactor",
        "Label security pull requests from Conventional Commit title": "security",
        "Label testing pull requests from Conventional Commit title": "testing",
        "Label CI/CD pull requests from Conventional Commit title": "ci/cd",
        "Label dependency pull requests from Conventional Commit title": "dependencies",
        "Label release-preparation pull requests from Conventional Commit title": "release",
        "Label maintenance pull requests from Conventional Commit title": "type:chore",
    }
    for rule_name, label_name in expected_title_label_rules.items():
        assert rule_name in by_name, f"Missing Mergify rule: {rule_name}"
        assert label_name in defined_labels
        added = by_name[rule_name].get("actions", {}).get("label", {}).get("add", [])
        assert added == [label_name]

    expected_stale_removal_rules = {
        "Remove stale breaking-change label when open PR title changes": "breaking change",
        "Remove stale enhancement label when open PR title changes": "enhancement",
        "Remove stale bug label when open PR title changes": "bug",
        "Remove stale performance label when open PR title changes": "performance",
        "Remove stale refactor label when open PR title changes": "refactor",
        "Remove stale dependencies label when open PR title changes": "dependencies",
        "Remove stale release label when open PR title changes": "release",
    }
    for rule_name, label_name in expected_stale_removal_rules.items():
        assert rule_name in by_name, f"Missing Mergify stale-removal rule: {rule_name}"
        conds = by_name[rule_name].get("conditions", [])
        assert "-closed" in conds
        assert any(isinstance(c, str) and c.startswith("-title ~= ") for c in conds)
        removed = by_name[rule_name].get("actions", {}).get("label", {}).get("remove", [])
        assert removed == [label_name]


@pytest.mark.parametrize(
    "case",
    [
        StaleLabelCase(
            rule_name="Remove stale breaking-change label when open PR title changes",
            label_name="breaking change",
            title="feat(api)!: make TraversalConfig keyword-only",
            expected_remove=False,
        ),
        StaleLabelCase(
            rule_name="Remove stale breaking-change label when open PR title changes",
            label_name="breaking change",
            title="fix!: drop deprecated flag",
            expected_remove=False,
        ),
        StaleLabelCase(
            rule_name="Remove stale breaking-change label when open PR title changes",
            label_name="breaking change",
            title="fix(api): preserve backwards compatibility",
            expected_remove=True,
        ),
        StaleLabelCase(
            rule_name="Remove stale breaking-change label when open PR title changes",
            label_name="breaking change",
            title="fix(api): preserve backwards compatibility",
            closed=True,
            expected_remove=False,
        ),
        StaleLabelCase(
            rule_name="Remove stale enhancement label when open PR title changes",
            label_name="enhancement",
            title="feat(cli): add JSONL output formatter",
            expected_remove=False,
        ),
        StaleLabelCase(
            rule_name="Remove stale enhancement label when open PR title changes",
            label_name="enhancement",
            title="feat!: overhaul exit codes",
            expected_remove=False,
        ),
        StaleLabelCase(
            rule_name="Remove stale enhancement label when open PR title changes",
            label_name="enhancement",
            title="fix(cli): repair JSONL output formatter",
            expected_remove=True,
        ),
        StaleLabelCase(
            rule_name="Remove stale bug label when open PR title changes",
            label_name="bug",
            title="fix(traversal)!: tighten symlink loop check",
            expected_remove=False,
        ),
        StaleLabelCase(
            rule_name="Remove stale bug label when open PR title changes",
            label_name="bug",
            title="refactor(traversal): simplify loop state",
            expected_remove=True,
        ),
        StaleLabelCase(
            rule_name="Remove stale performance label when open PR title changes",
            label_name="performance",
            title="perf(traversal)!: avoid redundant stat calls",
            expected_remove=False,
        ),
        StaleLabelCase(
            rule_name="Remove stale performance label when open PR title changes",
            label_name="performance",
            title="chore: tidy benchmark notes",
            expected_remove=True,
        ),
        StaleLabelCase(
            rule_name="Remove stale refactor label when open PR title changes",
            label_name="refactor",
            title="refactor(cli)!: split runner pipeline",
            expected_remove=False,
        ),
        StaleLabelCase(
            rule_name="Remove stale refactor label when open PR title changes",
            label_name="refactor",
            title="docs(cli): clarify runner pipeline",
            expected_remove=True,
        ),
        StaleLabelCase(
            rule_name="Remove stale dependencies label when open PR title changes",
            label_name="dependencies",
            title="chore(deps): update dependency typer to v0.29.0",
            expected_remove=False,
        ),
        StaleLabelCase(
            rule_name="Remove stale dependencies label when open PR title changes",
            label_name="dependencies",
            title="chore(deps)!: bump minimum supported Python",
            expected_remove=False,
        ),
        StaleLabelCase(
            rule_name="Remove stale dependencies label when open PR title changes",
            label_name="dependencies",
            title="Update dependency ruff to v0.15.0",
            author="renovate[bot]",
            expected_remove=False,
        ),
        StaleLabelCase(
            rule_name="Remove stale dependencies label when open PR title changes",
            label_name="dependencies",
            title="ci(deps): pin workflow actions",
            expected_remove=True,
        ),
        StaleLabelCase(
            rule_name="Remove stale release label when open PR title changes",
            label_name="release",
            title="chore(release): prepare v1.3.3",
            expected_remove=False,
        ),
        StaleLabelCase(
            rule_name="Remove stale release label when open PR title changes",
            label_name="release",
            title="chore(release)!: prepare v2.0.0",
            expected_remove=False,
        ),
        StaleLabelCase(
            rule_name="Remove stale release label when open PR title changes",
            label_name="release",
            title="ci(release): configure Release Drafter (#632)",
            expected_remove=True,
        ),
    ],
)
def test_mergify_stale_label_removal_predicates(case: StaleLabelCase) -> None:
    """Behaviorally evaluate Mergify stale-label removal predicates across PR states (#632)."""
    mergify = _load_mergify()
    pr_rules = mergify.get("pull_request_rules", [])
    by_name = {str(r.get("name")): r for r in pr_rules if isinstance(r, dict)}
    rule = by_name[case.rule_name]
    conds = [str(c) for c in rule.get("conditions", [])]
    matched = all(_evaluate_mergify_condition(c, case=case) for c in conds)
    assert matched is case.expected_remove
