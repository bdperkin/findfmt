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
_ADD_DEP_LINE_RE = re.compile(r"^(\s*-\s*)([A-Za-z0-9_.-]+)==(\S+)(.*)$")


def _normalize_pkg_name(name: str) -> str:
    """Normalize a Python package name per PEP 503."""
    return name.strip().lower().replace("_", "-")


def _load_locked_versions(lock_file: Path) -> dict[str, str]:
    """Return mapping of normalized package name to version from uv.lock."""
    with lock_file.open("rb") as f:
        lock_data = tomllib.load(f)

    locked: dict[str, str] = {}
    for pkg in lock_data.get("package", []):
        name = pkg.get("name")
        version = pkg.get("version")
        if isinstance(name, str) and isinstance(version, str):
            locked[_normalize_pkg_name(name)] = version

    return locked


def _find_hook_dep_mismatches(
    repo_url: str,
    hooks: object,
    locked_versions: dict[str, str],
) -> list[tuple[str, str, str, str]]:
    """Find pinned additional_dependencies entries in hooks that diverge from uv.lock."""
    mismatches: list[tuple[str, str, str, str]] = []
    if not isinstance(hooks, list):
        return mismatches

    for hook in hooks:
        if not isinstance(hook, dict):
            continue

        hook_id = str(hook.get("id", ""))
        add_deps = hook.get("additional_dependencies", [])
        if not isinstance(add_deps, list):
            continue

        for dep in add_deps:
            if not isinstance(dep, str) or "==" not in dep:
                continue

            raw_name, current_ver = dep.split("==", 1)
            pkg_name = _normalize_pkg_name(raw_name)
            current_ver = current_ver.strip()
            locked_ver = locked_versions.get(pkg_name)
            if locked_ver is not None and current_ver != locked_ver:
                mismatches.append((pkg_name, f"{repo_url}#{hook_id}", current_ver, locked_ver))

    return mismatches


def _find_mismatches(
    pre_commit_data: dict[str, Any],
    locked_versions: dict[str, str],
) -> list[tuple[str, str, str, str]]:
    """Find pre-commit hook repositories and pinned additional_dependencies diverging from uv.lock."""
    mismatches: list[tuple[str, str, str, str]] = []
    for repo_entry in pre_commit_data.get("repos", []):
        if not isinstance(repo_entry, dict):
            continue

        repo_url = str(repo_entry.get("repo", ""))
        current_rev = str(repo_entry.get("rev", ""))
        if not repo_url or not current_rev or repo_url in {"local", "meta"}:
            continue

        slug = repo_url.rstrip("/").rsplit("/", 1)[-1].lower()
        pkg_name = _normalize_pkg_name(slug.removesuffix("-pre-commit"))
        locked_ver = locked_versions.get(pkg_name)
        if locked_ver is not None:
            expected_rev = f"v{locked_ver}" if current_rev.startswith("v") else locked_ver
            if current_rev != expected_rev:
                mismatches.append((pkg_name, repo_url, current_rev, expected_rev))

        mismatches.extend(_find_hook_dep_mismatches(repo_url, repo_entry.get("hooks"), locked_versions))

    return mismatches


def _apply_rev_updates(
    pre_commit_file: Path,
    mismatches: list[tuple[str, str, str, str]],
) -> None:
    """Update mismatched rev and additional_dependencies lines in .pre-commit-config.yaml in place."""
    updates_by_repo = {target: expected_rev for _, target, _, expected_rev in mismatches if "#" not in target}
    dep_updates = {
        pkg_name: expected_ver for pkg_name, target, _, expected_ver in mismatches if "#" in target
    }
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

        add_dep_match = _ADD_DEP_LINE_RE.match(line)
        if add_dep_match is not None:
            prefix, raw_name, _, suffix = add_dep_match.groups()
            norm_name = _normalize_pkg_name(raw_name)
            if norm_name in dep_updates:
                newline = "\n" if line.endswith("\n") else ""
                updated_lines.append(f"{prefix}{raw_name}=={dep_updates[norm_name]}{suffix}{newline}")
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
