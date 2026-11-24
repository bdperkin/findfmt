"""Tests for .github/dependabot.yml ecosystems and action grouping (#415, #729)."""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any

import yaml


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


def _load_dependabot_config() -> dict[str, Any]:
    """Load and parse .github/dependabot.yml."""
    cfg_path = _repo_root() / ".github" / "dependabot.yml"
    assert cfg_path.is_file(), f"Missing Dependabot configuration at {cfg_path}"
    with cfg_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), f"Expected YAML mapping in {cfg_path}"
    return data


def _get_gh_actions_groups() -> dict[str, Any]:
    """Return the groups dictionary for the github-actions ecosystem."""
    config = _load_dependabot_config()
    gh_actions = next(
        entry for entry in config["updates"] if entry.get("package-ecosystem") == "github-actions"
    )
    assert gh_actions.get("directory") == "/"
    groups = gh_actions.get("groups")
    assert isinstance(groups, dict), "github-actions entry must define dependency groups"
    return groups


def test_dependabot_config_structure_and_groups() -> None:
    """Validate Dependabot ecosystems and github-actions groups including rust-cache (#729)."""
    config = _load_dependabot_config()
    assert config.get("version") == 2
    updates = config.get("updates")
    assert isinstance(updates, list)
    ecosystems = {entry.get("package-ecosystem"): entry for entry in updates if isinstance(entry, dict)}
    assert {"github-actions", "pip"} <= set(ecosystems)

    pip_groups = ecosystems["pip"]["groups"]
    assert pip_groups["dev-dependencies"]["dependency-type"] == "development"
    assert pip_groups["production-dependencies"]["dependency-type"] == "production"

    groups = _get_gh_actions_groups()
    for group_name, sample_action in (
        ("codeql-action", "github/codeql-action/init"),
        ("actions", "actions/checkout"),
        ("docker", "docker/build-push-action"),
        ("clusterfuzzlite", "google/clusterfuzzlite/actions/build_fuzzers"),
        ("rust-cache", "Swatinem/rust-cache"),
    ):
        assert group_name in groups
        patterns = groups[group_name].get("patterns")
        assert isinstance(patterns, list)
        assert any(fnmatch.fnmatch(sample_action, pat) for pat in patterns)


def test_dependabot_covers_workflow_codeql_actions() -> None:
    """Assert all CodeQL action steps used across workflows match the group pattern."""
    codeql_patterns = _get_gh_actions_groups()["codeql-action"]["patterns"]
    workflow_files = list((_repo_root() / ".github" / "workflows").glob("*.yml"))
    assert workflow_files
    codeql_uses: set[str] = set()
    for wf in workflow_files:
        for line in wf.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("uses:") and "github/codeql-action" in stripped:
                action_ref = stripped.split("uses:")[1].strip().split("@")[0].split("#")[0].strip()
                codeql_uses.add(action_ref)

    assert codeql_uses
    for action in codeql_uses:
        assert any(fnmatch.fnmatch(action, pat) for pat in codeql_patterns)
