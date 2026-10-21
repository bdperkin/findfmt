"""Tests for CI workflows and Dependabot configuration."""

import fnmatch
from pathlib import Path
from typing import Any

import yaml


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


def _load_dependabot_config() -> dict[str, Any]:
    """Load and parse .github/dependabot.yml."""
    config_path = _repo_root() / ".github" / "dependabot.yml"
    assert config_path.is_file(), f"Missing dependabot configuration at {config_path}"
    with config_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), "Dependabot config must be a YAML mapping"
    return data


def _get_gh_actions_groups() -> dict[str, Any]:
    """Return the groups dictionary for the github-actions ecosystem."""
    config = _load_dependabot_config()
    updates = config["updates"]
    gh_actions = next(
        entry for entry in updates if entry.get("package-ecosystem") == "github-actions"
    )
    assert gh_actions.get("directory") == "/"
    groups = gh_actions.get("groups")
    assert isinstance(groups, dict), "github-actions entry must define dependency groups"
    return groups


def test_dependabot_config_structure() -> None:
    """Validate root structure and required package ecosystems."""
    config = _load_dependabot_config()
    assert config.get("version") == 2
    updates = config.get("updates")
    assert isinstance(updates, list)

    ecosystems = {
        entry.get("package-ecosystem"): entry for entry in updates if isinstance(entry, dict)
    }
    assert "github-actions" in ecosystems
    assert "pip" in ecosystems


def test_dependabot_codeql_action_group() -> None:
    """Validate CodeQL Action dependency group and patterns."""
    groups = _get_gh_actions_groups()
    assert "codeql-action" in groups
    patterns = groups["codeql-action"].get("patterns")
    assert isinstance(patterns, list)
    assert any(fnmatch.fnmatch("github/codeql-action/init", pat) for pat in patterns)
    assert any(fnmatch.fnmatch("github/codeql-action/analyze", pat) for pat in patterns)
    assert any(fnmatch.fnmatch("github/codeql-action/upload-sarif", pat) for pat in patterns)


def test_dependabot_actions_group() -> None:
    """Validate official actions dependency group and patterns."""
    groups = _get_gh_actions_groups()
    assert "actions" in groups
    patterns = groups["actions"].get("patterns")
    assert isinstance(patterns, list)
    assert any(fnmatch.fnmatch("actions/checkout", pat) for pat in patterns)
    assert any(fnmatch.fnmatch("actions/setup-python", pat) for pat in patterns)


def test_dependabot_docker_and_fuzz_groups() -> None:
    """Validate docker and clusterfuzzlite dependency groups and patterns."""
    groups = _get_gh_actions_groups()
    assert "docker" in groups
    docker_patterns = groups["docker"].get("patterns")
    assert isinstance(docker_patterns, list)
    assert any(fnmatch.fnmatch("docker/build-push-action", pat) for pat in docker_patterns)

    assert "clusterfuzzlite" in groups
    fuzz_patterns = groups["clusterfuzzlite"].get("patterns")
    assert isinstance(fuzz_patterns, list)
    assert any(
        fnmatch.fnmatch("google/clusterfuzzlite/actions/build_fuzzers", pat)
        for pat in fuzz_patterns
    )


def _collect_workflow_codeql_actions() -> set[str]:
    """Scan all workflow files and collect github/codeql-action references."""
    repo = _repo_root()
    workflow_files = list((repo / ".github" / "workflows").glob("*.yml"))
    assert workflow_files, "No workflow files found in .github/workflows"

    codeql_uses: set[str] = set()
    for wf in workflow_files:
        with wf.open(encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("uses:") and "github/codeql-action" in stripped:
                    action_ref = (
                        stripped.split("uses:")[1].strip().split("@")[0].split("#")[0].strip()
                    )
                    codeql_uses.add(action_ref)

    return codeql_uses


def test_dependabot_covers_workflow_codeql_actions() -> None:
    """Assert all CodeQL action steps used across workflows match the group pattern."""
    groups = _get_gh_actions_groups()
    codeql_patterns = groups["codeql-action"]["patterns"]
    codeql_uses = _collect_workflow_codeql_actions()

    assert codeql_uses, "Expected at least one github/codeql-action step in workflows"
    for action in codeql_uses:
        assert any(fnmatch.fnmatch(action, pat) for pat in codeql_patterns), (
            f"Action {action} is not matched by codeql-action group patterns {codeql_patterns}"
        )


def test_dependabot_pip_groups() -> None:
    """Validate pip ecosystem groups for development and production dependencies."""
    config = _load_dependabot_config()
    updates = config["updates"]
    pip_entry = next(entry for entry in updates if entry.get("package-ecosystem") == "pip")

    assert pip_entry.get("directory") == "/"
    groups = pip_entry.get("groups")
    assert isinstance(groups, dict), "pip entry must define dependency groups"

    assert "dev-dependencies" in groups
    assert groups["dev-dependencies"].get("dependency-type") == "development"

    assert "production-dependencies" in groups
    assert groups["production-dependencies"].get("dependency-type") == "production"
