"""Dependency resolution matrix definitions and 3-stage failure diagnostic engine."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

VALID_RESOLUTIONS: tuple[str, ...] = ("highest", "lowest", "lowest-direct")
VALID_PRERELEASES: tuple[str, ...] = (
    "disallow",
    "allow",
    "if-necessary",
    "explicit",
    "if-necessary-or-explicit",
)
VALID_FORK_STRATEGIES: tuple[str, ...] = ("fewest", "requires-python")


@dataclass(frozen=True)
class MatrixCell:
    """Single dependency resolution permutation cell."""

    cell_id: str
    resolution: str
    prerelease: str
    fork_strategy: str = "fewest"

    @property
    def label(self) -> str:
        """Return human-readable label for the matrix cell."""
        return (
            f"{self.cell_id} (resolution={self.resolution}, "
            f"prerelease={self.prerelease}, fork-strategy={self.fork_strategy})"
        )


@dataclass(frozen=True)
class DiagnosticSnapshot:
    """Captured environment state and project metadata for failure diagnostics."""

    tree_output: str
    installed: dict[str, str]
    declared_bounds: dict[str, str]
    locked_versions: dict[str, str]
    error_output: str = ""


SMOKE_MATRIX: tuple[MatrixCell, ...] = (
    MatrixCell("M1", "lowest-direct", "disallow", "fewest"),
    MatrixCell("M2", "highest", "allow", "fewest"),
)

FULL_MATRIX: tuple[MatrixCell, ...] = (
    MatrixCell("M1", "lowest-direct", "disallow", "fewest"),
    MatrixCell("M2", "highest", "allow", "fewest"),
    MatrixCell("M3", "highest", "disallow", "fewest"),
    MatrixCell("M4", "lowest-direct", "allow", "fewest"),
    MatrixCell("M5", "lowest", "if-necessary", "fewest"),
    MatrixCell("M6", "highest", "disallow", "requires-python"),
)

_NORM_RE = re.compile(r"[-_.]+")
_PRERELEASE_RE = re.compile(r"(?:a|b|rc|dev)\d+", re.IGNORECASE)
_IMPORT_ERR_RE = re.compile(
    r"(?:No module named ['\"]([^'\"]+)['\"]|"
    r"cannot import name ['\"][^'\"]+['\"] from ['\"]([^'\"]+)['\"]|"
    r"module ['\"]([^'\"]+)['\"] has no attribute)",
)
_REQ_NAME_RE = re.compile(r"^([A-Za-z0-9_.-]+)")
_CLASSIFIER_PREFIX = "Programming Language :: Python :: "


def load_supported_pythons(pyproject_path: Path | None = None) -> tuple[str, ...]:
    """Load supported Python `3.X` versions from `pyproject.toml` Trove classifiers."""
    target = pyproject_path or (Path(__file__).resolve().parent.parent / "pyproject.toml")
    if not target.is_file():
        return ()

    with target.open("rb") as f:
        data = tomllib.load(f)

    project = data.get("project", {})
    classifiers = project.get("classifiers", []) if isinstance(project, dict) else []
    if not isinstance(classifiers, list):
        return ()

    versions = [
        c.removeprefix(_CLASSIFIER_PREFIX)
        for c in classifiers
        if isinstance(c, str)
        and c.startswith(_CLASSIFIER_PREFIX + "3.")
        and c.removeprefix(_CLASSIFIER_PREFIX)[2:].isdigit()
    ]
    return tuple(sorted(versions, key=lambda v: tuple(int(p) for p in v.split("."))))


def normalize_pkg_name(name: str) -> str:
    """Normalize package name according to PEP 503."""
    return _NORM_RE.sub("-", name.strip()).lower()


def is_prerelease_version(version: str) -> bool:
    """Return True if a version string contains a PEP 440 pre-release or dev segment."""
    return bool(_PRERELEASE_RE.search(version))


def load_declared_bounds(pyproject_path: Path) -> dict[str, str]:
    """Load declared direct and test dependency specifiers from pyproject.toml."""
    if not pyproject_path.is_file():
        return {}

    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    raw_specs: list[object] = []
    project = data.get("project", {})
    if isinstance(project, dict) and isinstance(project.get("dependencies"), list):
        raw_specs.extend(project["dependencies"])

    groups = data.get("dependency-groups", {})
    if isinstance(groups, dict) and isinstance(groups.get("test"), list):
        raw_specs.extend(groups["test"])

    bounds: dict[str, str] = {}
    for entry in raw_specs:
        if isinstance(entry, str):
            spec_no_marker = entry.split(";")[0].strip()
            match = _REQ_NAME_RE.match(spec_no_marker)
            if match:
                bounds[normalize_pkg_name(match.group(1))] = spec_no_marker

    return bounds


def load_locked_versions(lock_path: Path) -> dict[str, str]:
    """Load pinned baseline package versions from uv.lock."""
    if not lock_path.is_file():
        return {}

    with lock_path.open("rb") as f:
        data = tomllib.load(f)

    packages = data.get("package", [])
    if not isinstance(packages, list):
        return {}

    return {
        normalize_pkg_name(pkg["name"]): pkg["version"]
        for pkg in packages
        if isinstance(pkg, dict)
        and isinstance(pkg.get("name"), str)
        and isinstance(pkg.get("version"), str)
    }


def extract_failed_modules(error_output: str) -> list[str]:
    """Extract top-level package/module names from ImportError or AttributeError traces."""
    found: list[str] = []
    for match in _IMPORT_ERR_RE.finditer(error_output):
        raw_mod = next((g for g in match.groups() if g is not None), "")
        top_mod = normalize_pkg_name(raw_mod.split(".")[0])
        if top_mod and top_mod not in found:
            found.append(top_mod)

    return found


def format_failure_diagnostics(cell: MatrixCell, snapshot: DiagnosticSnapshot) -> str:
    """Format the 3-stage failure diagnostic report for a failed matrix cell."""
    lines: list[str] = [
        f"\n=== Dependency Failure Diagnostics: {cell.label} ===",
        "\n[Stage 1] Resolved Dependency Tree (uv pip tree):",
        snapshot.tree_output.strip() or "(dependency tree unavailable)",
    ]

    deltas = [
        f"  - {pkg}: installed={inst_ver} (uv.lock={snapshot.locked_versions[pkg]})"
        for pkg, inst_ver in sorted(snapshot.installed.items())
        if pkg in snapshot.locked_versions and snapshot.locked_versions[pkg] != inst_ver
    ]
    lines.append("\n[Stage 2] Version Deltas vs. uv.lock:")
    lines.extend(deltas or ["  (all installed packages match uv.lock)"])

    failed_mods = extract_failed_modules(snapshot.error_output)
    if failed_mods:
        lines.append(f"  Implicated modules from traceback: {', '.join(failed_mods)}")

    recommendations: list[str] = []
    for pkg, spec in sorted(snapshot.declared_bounds.items()):
        inst_ver = snapshot.installed.get(pkg)
        lock_ver = snapshot.locked_versions.get(pkg)
        if inst_ver is None:
            continue

        is_lower_drift = (
            cell.resolution in {"lowest-direct", "lowest"}
            and lock_ver is not None
            and inst_ver != lock_ver
        )
        if pkg in failed_mods or is_lower_drift:
            target = f">={lock_ver}" if lock_ver is not None else f">{inst_ver}"
            recommendations.append(
                f"  - Update '{spec}' in pyproject.toml (resolved {pkg}=={inst_ver}; "
                f"recommend '{pkg}{target}')",
            )

    if cell.prerelease != "disallow":
        for pkg, inst_ver in sorted(snapshot.installed.items()):
            if is_prerelease_version(inst_ver):
                recommendations.append(
                    f"  - Pre-release package detected: {pkg}=={inst_ver} "
                    f"(add upper bound in pyproject.toml or report upstream breakage)",
                )

    lines.append("\n[Stage 3] Actionable pyproject.toml Bound Remediation:")
    fallback = (
        "  - Inspect the dependency tree above and bump the offending floor in pyproject.toml."
    )
    lines.extend(recommendations or [fallback])
    return "\n".join(lines) + "\n"


def capture_diagnostics(
    cell: MatrixCell,
    env_dir: Path,
    repo_root: Path,
    error_output: str,
) -> str:
    """Capture uv pip tree and installed package list and format failure diagnostics."""
    tree_proc = subprocess.run(
        ["uv", "pip", "tree", "--python", str(env_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    list_proc = subprocess.run(
        ["uv", "pip", "list", "--format", "json", "--python", str(env_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    installed: dict[str, str] = {}
    if list_proc.returncode == 0 and list_proc.stdout.strip():
        try:
            raw_list = json.loads(list_proc.stdout)
            if isinstance(raw_list, list):
                installed = {
                    normalize_pkg_name(str(item["name"])): str(item["version"])
                    for item in raw_list
                    if isinstance(item, dict) and "name" in item and "version" in item
                }
        except json.JSONDecodeError:
            pass

    snapshot = DiagnosticSnapshot(
        tree_output=tree_proc.stdout or tree_proc.stderr,
        installed=installed,
        declared_bounds=load_declared_bounds(repo_root / "pyproject.toml"),
        locked_versions=load_locked_versions(repo_root / "uv.lock"),
        error_output=error_output,
    )
    return format_failure_diagnostics(cell, snapshot)


def select_cells(
    *,
    smoke: bool = False,
    full: bool = False,
    resolution: str | None = None,
    prerelease: str | None = None,
    fork_strategy: str | None = None,
) -> tuple[MatrixCell, ...]:
    """Select the tuple of matrix cells to execute from CLI options."""
    if full:
        return FULL_MATRIX

    if smoke:
        return SMOKE_MATRIX

    if resolution is not None or prerelease is not None or fork_strategy is not None:
        return (
            MatrixCell(
                cell_id="CUSTOM",
                resolution=resolution or "highest",
                prerelease=prerelease or "disallow",
                fork_strategy=fork_strategy or "fewest",
            ),
        )

    return SMOKE_MATRIX


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for direct dependency matrix execution."""
    args = list(argv) if argv is not None else (sys.argv[1:] or ["--smoke"])
    runner_script = Path(__file__).resolve().with_name("verify_quality.py")
    proc = subprocess.run([sys.executable, str(runner_script), *args], check=False)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
