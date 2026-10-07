"""Run exhaustive code quality, linting, typing, and testing checks."""

from __future__ import annotations

import subprocess
import sys


def run_step(name: str, cmd: list[str]) -> bool:
    """Run a quality check step and print output."""
    sys.stdout.write(f"\n[+] Running {name}: {' '.join(cmd)}\n")
    sys.stdout.flush()
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        sys.stderr.write(f"[-] Step '{name}' failed with exit code {proc.returncode}\n")
        return False

    return True


def main() -> int:
    """Execute complete verification suite."""
    steps = [
        ("Ruff Linter", ["uv", "run", "ruff", "check"]),
        ("Ruff Formatter", ["uv", "run", "ruff", "format", "--check"]),
        ("Ty Type Checker", ["uv", "run", "ty", "check"]),
        ("Pytest & Coverage", ["uv", "run", "pytest"]),
        ("Interrogate Docstrings", ["uv", "run", "interrogate", "src"]),
        ("Radon Cyclomatic Complexity", ["uv", "run", "radon", "cc", "src", "-s", "-a"]),
        ("Xenon Complexity Assertions", ["uv", "run", "xenon", "src"]),
        ("Deptry Dependencies", ["uv", "run", "deptry", "."]),
        ("Vulture Dead Code", ["uv", "run", "vulture", "src"]),
        ("Codespell Spelling", ["uv", "run", "codespell"]),
    ]

    for name, cmd in steps:
        if not run_step(name, cmd):
            return 1

    sys.stdout.write("\n[✓] All quality verification steps passed successfully!\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
