"""Run exhaustive code quality, linting, typing, testing, and dependency matrix checks."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

try:
    from tools.dep_matrix import (
        VALID_FORK_STRATEGIES,
        VALID_PRERELEASES,
        VALID_RESOLUTIONS,
        MatrixCell,
        capture_diagnostics,
        select_cells,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools.dep_matrix import (
        VALID_FORK_STRATEGIES,
        VALID_PRERELEASES,
        VALID_RESOLUTIONS,
        MatrixCell,
        capture_diagnostics,
        select_cells,
    )


def run_step(name: str, cmd: list[str]) -> bool:
    """Run a quality check step and print output."""
    sys.stdout.write(f"\n[+] Running {name}: {' '.join(cmd)}\n")
    sys.stdout.flush()
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        sys.stderr.write(f"[-] Step '{name}' failed with exit code {proc.returncode}\n")
        return False

    return True


def run_quality_suite() -> int:
    """Execute the standard 12-step verification suite."""
    steps = [
        ("Ruff Linter", ["uv", "run", "ruff", "check"]),
        ("Ruff Formatter", ["uv", "run", "ruff", "format", "--check"]),
        ("Ty Type Checker", ["uv", "run", "ty", "check"]),
        ("Pytest & Coverage", ["uv", "run", "pytest"]),
        ("Interrogate Docstrings", ["uv", "run", "interrogate", "src"]),
        ("Radon Cyclomatic Complexity", ["uv", "run", "radon", "cc", "src", "-s", "-a"]),
        (
            "Xenon Complexity Assertions",
            ["uv", "run", "xenon", "-b", "B", "-m", "B", "-a", "A", "src"],
        ),
        ("Deptry Dependencies", ["uv", "run", "deptry", "."]),
        ("Vulture Dead Code", ["uv", "run", "vulture", "src"]),
        ("Codespell Spelling", ["uv", "run", "codespell"]),
        (
            "Pre-Commit Dependency Sync",
            ["uv", "run", "python", "tools/sync_pre_commit_deps.py"],
        ),
        ("UV Dependency Audit", ["uv", "audit", "--preview-features", "audit-command"]),
    ]

    for name, cmd in steps:
        if not run_step(name, cmd):
            return 1

    sys.stdout.write("\n[✓] All quality verification steps passed successfully!\n")
    return 0


def resolve_venv_python(env_dir: Path) -> Path:
    """Resolve the Python interpreter binary inside a virtual environment."""
    posix_py = env_dir / "bin" / "python"
    win_py = env_dir / "Scripts" / "python.exe"
    return win_py if not posix_py.exists() and win_py.exists() else posix_py


def run_matrix_cell(
    cell: MatrixCell,
    python_spec: str,
    repo_root: Path,
    pytest_args: Sequence[str] = (),
) -> bool:
    """Execute a single dependency resolution permutation in a clean temporary virtualenv."""
    sys.stdout.write(f"\n[+] Matrix Cell {cell.label}\n")
    sys.stdout.flush()
    with tempfile.TemporaryDirectory(prefix=f"findfmt-matrix-{cell.cell_id.lower()}-") as tmp_dir:
        env_dir = Path(tmp_dir) / "venv"
        venv_proc = subprocess.run(
            ["uv", "venv", "--python", python_spec, str(env_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        if venv_proc.returncode != 0:
            sys.stderr.write(f"[-] Failed to create virtualenv for {cell.cell_id}:\n")
            sys.stderr.write(venv_proc.stderr or venv_proc.stdout)
            return False

        install_cmd = [
            "uv",
            "pip",
            "install",
            "--python",
            str(env_dir),
            "--group",
            "test",
            "-e",
            str(repo_root),
            "--resolution",
            cell.resolution,
            "--prerelease",
            cell.prerelease,
            "--fork-strategy",
            cell.fork_strategy,
        ]
        install_proc = subprocess.run(install_cmd, capture_output=True, text=True, check=False)
        if install_proc.returncode != 0:
            err_text = f"{install_proc.stdout or ''}\n{install_proc.stderr or ''}"
            sys.stderr.write(f"[-] Dependency resolution failed for {cell.cell_id}:\n{err_text}")
            sys.stderr.write(capture_diagnostics(cell, env_dir, repo_root, err_text))
            return False

        test_cmd = [str(resolve_venv_python(env_dir)), "-m", "pytest", *pytest_args]
        test_proc = subprocess.run(
            test_cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if test_proc.returncode != 0:
            err_text = f"{test_proc.stdout or ''}\n{test_proc.stderr or ''}"
            sys.stderr.write(f"[-] Pytest failed for {cell.cell_id}:\n{err_text}")
            sys.stderr.write(capture_diagnostics(cell, env_dir, repo_root, err_text))
            return False

        sys.stdout.write(f"[✓] Cell {cell.cell_id} passed.\n")
        return True


def run_matrix(
    cells: Sequence[MatrixCell],
    python_spec: str,
    repo_root: Path,
    pytest_args: Sequence[str] = (),
) -> int:
    """Run all selected dependency resolution matrix cells and return exit code."""
    failed = [
        cell.cell_id
        for cell in cells
        if not run_matrix_cell(cell, python_spec, repo_root, pytest_args)
    ]
    if failed:
        sys.stderr.write(f"\n[-] Dependency matrix failed in cell(s): {', '.join(failed)}\n")
        return 1

    sys.stdout.write(f"\n[✓] All {len(cells)} dependency matrix cell(s) passed!\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser for verify_quality.py and dependency matrix modes."""
    parser = argparse.ArgumentParser(
        description="Run findfmt quality verification suite or local dependency resolution matrix.",
    )
    mode_group = parser.add_mutually_exclusive_group()
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
    parser.add_argument(
        "--fork-strategy",
        choices=VALID_FORK_STRATEGIES,
        help="uv --fork-strategy mode.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python interpreter version or path for ephemeral virtualenvs.",
    )
    return parser


def main(argv: Sequence[str] | None = None, repo_root: Path | None = None) -> int:
    """Execute standard verification suite or dependency resolution matrix."""
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    is_matrix_mode = bool(
        args.smoke or args.full or args.resolution or args.prerelease or args.fork_strategy,
    )
    if not is_matrix_mode:
        return run_quality_suite()

    cells = select_cells(
        smoke=args.smoke,
        full=args.full,
        resolution=args.resolution,
        prerelease=args.prerelease,
        fork_strategy=args.fork_strategy,
    )
    root = repo_root or Path(__file__).resolve().parent.parent
    return run_matrix(cells, args.python, root)


if __name__ == "__main__":
    sys.exit(main())
