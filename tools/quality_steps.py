"""Quality verification step definitions, Cargo PATH resolution, and CLI parser."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from tools.dep_matrix import VALID_FORK_STRATEGIES, VALID_PRERELEASES, VALID_RESOLUTIONS

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

CARGO_MANIFEST = "findfmt_rs/Cargo.toml"

QUALITY_STEPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Ruff Linter", ("uv", "run", "ruff", "check")),
    ("Ruff Formatter", ("uv", "run", "ruff", "format", "--check")),
    ("Ty Type Checker", ("uv", "run", "ty", "check")),
    ("Cargo Formatter", ("cargo", "fmt", "--manifest-path", CARGO_MANIFEST, "--check")),
    ("Cargo Check", ("cargo", "check", "--manifest-path", CARGO_MANIFEST, "--locked")),
    (
        "Cargo Clippy (Extension)",
        ("cargo", "clippy", "--manifest-path", CARGO_MANIFEST, "--locked", "--lib", "--", "-D", "warnings"),
    ),
    (
        "Cargo Clippy (All Targets)",
        (
            "cargo",
            "clippy",
            "--manifest-path",
            CARGO_MANIFEST,
            "--locked",
            "--no-default-features",
            "--all-targets",
            "--",
            "-D",
            "warnings",
        ),
    ),
    ("Pytest & Coverage", ("uv", "run", "pytest")),
    ("Interrogate Docstrings", ("uv", "run", "interrogate", "src")),
    ("Radon Cyclomatic Complexity", ("uv", "run", "radon", "cc", "src", "-s", "-a")),
    ("Xenon Complexity Assertions", ("uv", "run", "xenon", "-b", "B", "-m", "B", "-a", "A", "src")),
    ("Deptry Dependencies", ("uv", "run", "deptry", ".")),
    ("Vulture Dead Code", ("uv", "run", "vulture", "src")),
    ("Codespell Spelling", ("uv", "run", "codespell")),
    ("Pre-Commit Dependency Sync", ("uv", "run", "python", "tools/sync_pre_commit_deps.py")),
    ("CLI & Markdown Docs SoT Sync", ("uv", "run", "python", "tools/sync_cli_docs.py")),
    ("UV Dependency Audit", ("uv", "audit", "--preview-features", "audit-command")),
)


def prepare_step_execution(
    cmd: Sequence[str],
    *,
    home_dir: Path | None = None,
    base_env: Mapping[str, str] | None = None,
) -> tuple[list[str], dict[str, str] | None]:
    """Resolve executable and subprocess environment, prioritizing ~/.cargo/bin for Cargo steps."""
    argv = list(cmd)
    if not argv or argv[0] != "cargo":
        return argv, None

    env = dict(base_env) if base_env is not None else dict(os.environ)
    cargo_bin_dir = (home_dir or Path.home()) / ".cargo" / "bin"
    current_path = env.get("PATH", "")
    if cargo_bin_dir.is_dir():
        cargo_bin_str = str(cargo_bin_dir)
        path_parts = [p for p in current_path.split(os.pathsep) if p]
        if not path_parts or path_parts[0] != cargo_bin_str:
            deduped = [p for p in path_parts if p != cargo_bin_str]
            env["PATH"] = os.pathsep.join([cargo_bin_str, *deduped])

    resolved_cargo = shutil.which("cargo", path=env.get("PATH"))
    if resolved_cargo is not None:
        argv[0] = resolved_cargo

    return argv, env


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser for verify_quality.py and dependency matrix modes."""
    parser = argparse.ArgumentParser(
        description="Run findfmt quality suite, multi-Python runner, or dependency matrix.",
    )
    parser.add_argument(
        "--list",
        dest="list_sessions",
        action="store_true",
        help="List supported Python interpreter sessions and dependency matrix cells.",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--all-pythons",
        action="store_true",
        help="Run pytest across every supported Python interpreter (3.11-3.15).",
    )
    mode_group.add_argument(
        "--pythons",
        help="Comma-separated list of Python versions to test (e.g. '3.11,3.15').",
    )
    mode_group.add_argument(
        "--smoke",
        action="store_true",
        help="Run curated 2-cell PR dependency smoke matrix (M1, M2).",
    )
    mode_group.add_argument(
        "--full",
        action="store_true",
        help="Run all 6 pruned dependency matrix permutations (M1-M6).",
    )
    parser.add_argument("--resolution", choices=VALID_RESOLUTIONS, help="uv --resolution mode.")
    parser.add_argument("--prerelease", choices=VALID_PRERELEASES, help="uv --prerelease mode.")
    parser.add_argument("--fork-strategy", choices=VALID_FORK_STRATEGIES, help="uv --fork-strategy mode.")
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python interpreter version or path for ephemeral virtualenvs.",
    )
    return parser
