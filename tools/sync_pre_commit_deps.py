"""Synchronize dependency versions between uv.lock and .pre-commit-config.yaml."""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

import yaml

_REPO_LINE_RE = re.compile(r"^\s*-\s*repo:\s*(\S+)")
_REV_LINE_RE = re.compile(r"^(\s*rev:\s*)(\S+)(.*)$")


def _load_locked_versions(lock_file: Path) -> dict[str, str]:
    """Return mapping of lowercased package name to version from uv.lock."""
    with lock_file.open("rb") as f:
        lock_data = tomllib.load(f)

    locked: dict[str, str] = {}
    for pkg in lock_data.get("package", []):
        name = pkg.get("name")
        version = pkg.get("version")
        if isinstance(name, str) and isinstance(version, str):
            locked[name.lower()] = version

    return locked


def _find_mismatches(
    pre_commit_data: dict[str, Any],
    locked_versions: dict[str, str],
) -> list[tuple[str, str, str, str]]:
    """Find pre-commit hook repositories whose rev diverges from uv.lock."""
    mismatches: list[tuple[str, str, str, str]] = []
    for repo_entry in pre_commit_data.get("repos", []):
        if not isinstance(repo_entry, dict):
            continue

        repo_url = str(repo_entry.get("repo", ""))
        current_rev = str(repo_entry.get("rev", ""))
        if not repo_url or not current_rev or repo_url in {"local", "meta"}:
            continue

        slug = repo_url.rstrip("/").rsplit("/", 1)[-1].lower()
        pkg_name = slug.removesuffix("-pre-commit")
        locked_ver = locked_versions.get(pkg_name)
        if locked_ver is None:
            continue

        expected_rev = f"v{locked_ver}" if current_rev.startswith("v") else locked_ver
        if current_rev != expected_rev:
            mismatches.append((pkg_name, repo_url, current_rev, expected_rev))

    return mismatches


def _apply_rev_updates(
    pre_commit_file: Path,
    mismatches: list[tuple[str, str, str, str]],
) -> None:
    """Update mismatched rev lines in .pre-commit-config.yaml in place."""
    updates_by_repo = {repo_url: expected_rev for _, repo_url, _, expected_rev in mismatches}
    lines = pre_commit_file.read_text(encoding="utf-8").splitlines(keepends=True)
    active_repo: str = ""
    updated_lines: list[str] = []

    for line in lines:
        repo_match = _REPO_LINE_RE.match(line)
        if repo_match is not None:
            active_repo = str(repo_match.group(1))
            updated_lines.append(line)
            continue

        rev_match = _REV_LINE_RE.match(line)
        if rev_match is not None and active_repo in updates_by_repo:
            prefix, _, suffix = rev_match.groups()
            newline = "\n" if line.endswith("\n") else ""
            updated_lines.append(f"{prefix}{updates_by_repo[active_repo]}{suffix}{newline}")
            active_repo = ""
            continue

        updated_lines.append(line)

    pre_commit_file.write_text("".join(updated_lines), encoding="utf-8")


def sync_deps(project_root: Path, *, write: bool = False) -> int:
    """Verify and optionally synchronize versions between uv.lock and .pre-commit-config.yaml."""
    lock_file = project_root / "uv.lock"
    pre_commit_file = project_root / ".pre-commit-config.yaml"

    if not lock_file.is_file() or not pre_commit_file.is_file():
        sys.stderr.write("Missing uv.lock or .pre-commit-config.yaml\n")
        return 1

    locked_versions = _load_locked_versions(lock_file)
    with pre_commit_file.open("r", encoding="utf-8") as f:
        pre_commit_data = yaml.safe_load(f)

    if not isinstance(pre_commit_data, dict):
        sys.stderr.write("Invalid .pre-commit-config.yaml structure\n")
        return 1

    mismatches = _find_mismatches(pre_commit_data, locked_versions)
    if not mismatches:
        return 0

    if write:
        _apply_rev_updates(pre_commit_file, mismatches)
        for pkg_name, _, current_rev, expected_rev in mismatches:
            sys.stdout.write(f"Synchronized {pkg_name}: {current_rev} -> {expected_rev}\n")

        return 0

    for pkg_name, repo_url, current_rev, expected_rev in mismatches:
        sys.stderr.write(
            f"Version mismatch for {pkg_name} ({repo_url}): "
            f"pre-commit rev={current_rev} != expected {expected_rev}\n",
        )

    return 1


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for checking or synchronizing pre-commit hook versions."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        "--sync",
        action="store_true",
        dest="write",
        help="Rewrite .pre-commit-config.yaml in place to match uv.lock versions.",
    )
    args = parser.parse_args(argv)
    return sync_deps(Path(__file__).resolve().parent.parent, write=args.write)


if __name__ == "__main__":
    sys.exit(main())
