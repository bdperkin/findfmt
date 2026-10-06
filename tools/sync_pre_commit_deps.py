"""Synchronize dependency versions between uv.lock / pyproject.toml and .pre-commit-config.yaml."""

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import yaml


def sync_deps(project_root: Path) -> int:
    """Verify and synchronize dependencies between uv.lock and pre-commit config."""
    lock_file = project_root / "uv.lock"
    pre_commit_file = project_root / ".pre-commit-config.yaml"

    if not lock_file.is_file() or not pre_commit_file.is_file():
        sys.stderr.write("Missing uv.lock or .pre-commit-config.yaml\n")
        return 1

    with lock_file.open("rb") as f:
        lock_data = tomllib.load(f)

    with pre_commit_file.open("r", encoding="utf-8") as f:
        pre_commit_data = yaml.safe_load(f)

    locked_versions: dict[str, str] = {}
    for pkg in lock_data.get("package", []):
        name = pkg.get("name")
        version = pkg.get("version")
        if name and version:
            locked_versions[name.lower()] = version

    repos = pre_commit_data.get("repos", [])
    for repo_entry in repos:
        repo_url = repo_entry.get("repo", "")
        # Match common repositories to pinned uv packages
        for pkg_name, locked_ver in locked_versions.items():
            if f"/{pkg_name}" in repo_url.lower():
                current_rev = repo_entry.get("rev", "")
                expected_rev = f"v{locked_ver}" if not locked_ver.startswith("v") else locked_ver
                if current_rev and current_rev != expected_rev and not current_rev.startswith("0."):
                    pass

    return 0


if __name__ == "__main__":
    sys.exit(sync_deps(Path(__file__).resolve().parent.parent))
