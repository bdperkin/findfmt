"""Collect combined Rust unit/proptest and PyO3 pytest coverage via cargo-llvm-cov (#590)."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import sysconfig
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

try:
    from tools.quality_steps import CARGO_MANIFEST, prepare_step_execution
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools.quality_steps import CARGO_MANIFEST, prepare_step_execution

DEFAULT_LCOV_OUTPUT = "rust-lcov.info"
DEFAULT_MIN_LINES = 100.0
DEFAULT_IGNORE_REGEX = r"(^|[\\/])(fuzz|tests)[\\/]|_tests\.rs$"


def parse_llvm_cov_env(stdout: str) -> dict[str, str]:
    """Parse `cargo llvm-cov show-env` (`--cmd` or `--sh`) output into an environment mapping."""
    parsed: dict[str, str] = {}
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("set "):
            assignment = line[4:]
        elif line.startswith("export "):
            tokens = shlex.split(line, posix=True)
            assignment = tokens[1] if len(tokens) > 1 else tokens[0]
        else:
            assignment = line

        if "=" in assignment:
            key, val = assignment.split("=", 1)
            parsed[key] = val

    return parsed


def _prepend_search_path(env: dict[str, str], var_name: str, directory: str) -> None:
    """Prepend `directory` to an OS path-list environment variable if not already leading."""
    if not directory:
        return

    existing = env.get(var_name, "")
    parts = [p for p in existing.split(os.pathsep) if p]
    if directory not in parts:
        env[var_name] = os.pathsep.join([directory, *parts]) if parts else directory


def build_base_env(
    *,
    home_dir: Path | None = None,
    raw_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Construct clean subprocess environment with Cargo and active libpython paths configured."""
    source_env = dict(raw_env) if raw_env is not None else dict(os.environ)
    source_env.pop("FINDFMT_NO_EXTENSIONS", None)
    source_env.setdefault("PYO3_PYTHON", sys.executable)

    libdir = sysconfig.get_config_var("LIBDIR") or ""
    base_prefix = sys.base_prefix
    if sys.platform == "win32":
        _prepend_search_path(source_env, "PATH", base_prefix)
    elif sys.platform == "darwin":
        _prepend_search_path(source_env, "DYLD_FALLBACK_LIBRARY_PATH", libdir)
    else:
        _prepend_search_path(source_env, "LD_LIBRARY_PATH", libdir)

    _, cargo_env = prepare_step_execution(("cargo",), home_dir=home_dir, base_env=source_env)
    return cargo_env if cargo_env is not None else source_env


def _run_step(label: str, cmd: Sequence[str], env: Mapping[str, str]) -> int:
    """Print and execute a single coverage pipeline command."""
    resolved_cmd, _ = prepare_step_execution(cmd, base_env=env)
    sys.stdout.write(f"\n[+] {label}: {' '.join(cmd)}\n")
    sys.stdout.flush()
    result = subprocess.run(resolved_cmd, env=dict(env), check=False)
    if result.returncode != 0:
        sys.stderr.write(f"[-] Step '{label}' failed with exit code {result.returncode}\n")

    return result.returncode


def verify_lcov_line_coverage(lcov_path: Path, fail_under_lines: float) -> int:
    """Normalize LF/LH summaries from merged DA records and enforce minimum line coverage."""
    if not lcov_path.is_file():
        sys.stderr.write(f"[-] Missing expected LCOV report: {lcov_path}\n")
        return 1

    normalized_lines: list[str] = []
    current_sf = ""
    file_da: dict[int, int] = {}
    total_lines = 0
    covered_lines = 0
    uncovered_by_file: dict[str, list[int]] = {}

    for raw in lcov_path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("SF:"):
            current_sf = raw[3:]
            file_da = {}
            normalized_lines.append(raw)
        elif raw.startswith("DA:"):
            parts = raw[3:].split(",")
            line_no = int(parts[0])
            hit_count = int(parts[1])
            file_da[line_no] = max(file_da.get(line_no, 0), hit_count)
            normalized_lines.append(raw)
        elif raw.startswith(("LF:", "LH:")):
            continue
        elif raw == "end_of_record":
            lf = len(file_da)
            lh = sum(1 for hits in file_da.values() if hits > 0)
            missed = sorted(ln for ln, hits in file_da.items() if hits == 0)
            if missed:
                uncovered_by_file[current_sf] = missed

            total_lines += lf
            covered_lines += lh
            normalized_lines.append(f"LF:{lf}")
            normalized_lines.append(f"LH:{lh}")
            normalized_lines.append(raw)
        else:
            normalized_lines.append(raw)

    lcov_path.write_text("\n".join(normalized_lines) + "\n", encoding="utf-8")
    pct = 100.0 if total_lines == 0 else (covered_lines / total_lines) * 100.0
    sys.stdout.write(
        f"\n[+] Unified LCOV Line Coverage: {covered_lines}/{total_lines} lines "
        f"({pct:.2f}%, threshold: {fail_under_lines:g}%)\n",
    )
    sys.stdout.flush()
    if pct + 1e-9 < fail_under_lines:
        sys.stderr.write(
            f"[-] Rust line coverage {pct:.2f}% is below required {fail_under_lines:g}%:\n",
        )
        for sf_path, lines in sorted(uncovered_by_file.items()):
            joined = ", ".join(str(ln) for ln in lines)
            sys.stderr.write(f"    {sf_path}: {joined}\n")

        return 1

    return 0


def collect_rust_coverage(
    *,
    manifest_path: str = CARGO_MANIFEST,
    output_path: str = DEFAULT_LCOV_OUTPUT,
    ignore_regex: str = DEFAULT_IGNORE_REGEX,
    fail_under_lines: float = DEFAULT_MIN_LINES,
    pytest_mode: Literal["skip", "fast", "cov"] = "fast",
) -> int:
    """Run Rust unit/proptest and PyO3 pytest suites under LLVM coverage and emit LCOV."""
    base_env = build_base_env()
    target_dir = Path(manifest_path).resolve().parent / "target" / "llvm-cov-target"
    base_env.setdefault("CARGO_TARGET_DIR", str(target_dir))
    show_env_cmd, _ = prepare_step_execution(
        ("cargo", "llvm-cov", "show-env", "--cmd", "--no-cfg-coverage", "--manifest-path", manifest_path),
        base_env=base_env,
    )
    proc = subprocess.run(show_env_cmd, env=base_env, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr or "Failed to query cargo llvm-cov show-env\n")
        return proc.returncode

    cov_env = {**base_env, **parse_llvm_cov_env(proc.stdout)}

    steps: list[tuple[str, tuple[str, ...]]] = [
        (
            "Clean Stale LLVM Coverage Profiles",
            ("cargo", "llvm-cov", "clean", "--workspace", "--manifest-path", manifest_path),
        ),
        (
            "Run Instrumented Rust Unit & Proptest Suites",
            ("cargo", "test", "--manifest-path", manifest_path, "--locked", "--no-default-features"),
        ),
    ]
    if pytest_mode != "skip":
        pytest_cmd: tuple[str, ...] = (
            ("uv", "run", "--no-sync", "pytest")
            if pytest_mode == "cov"
            else ("uv", "run", "--no-sync", "pytest", "--no-cov", "-q")
        )
        steps.extend(
            [
                (
                    "Build Instrumented PyO3 Extension (findfmt._rust_ext)",
                    ("uv", "run", "--no-sync", "maturin", "develop", "--manifest-path", manifest_path),
                ),
                (
                    "Run Pytest Against Instrumented findfmt._rust_ext",
                    pytest_cmd,
                ),
            ],
        )

    steps.extend(
        [
            (
                "Export LCOV Rust Coverage Report",
                (
                    "cargo",
                    "llvm-cov",
                    "report",
                    "--manifest-path",
                    manifest_path,
                    "--ignore-filename-regex",
                    ignore_regex,
                    "--lcov",
                    "--output-path",
                    output_path,
                ),
            ),
            (
                "Display Rust Coverage Summary",
                (
                    "cargo",
                    "llvm-cov",
                    "report",
                    "--manifest-path",
                    manifest_path,
                    "--ignore-filename-regex",
                    ignore_regex,
                    "--show-missing-lines",
                ),
            ),
        ],
    )

    for label, cmd in steps:
        rc = _run_step(label, cmd, cov_env)
        if rc != 0:
            return rc

    return verify_lcov_line_coverage(Path(output_path), fail_under_lines)


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser for tools/rust_coverage.py."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest-path",
        default=CARGO_MANIFEST,
        help="Path to findfmt_rs/Cargo.toml.",
    )
    parser.add_argument(
        "--output-path",
        default=DEFAULT_LCOV_OUTPUT,
        help="Destination path for LCOV coverage report (default: rust-lcov.info).",
    )
    parser.add_argument(
        "--ignore-filename-regex",
        default=DEFAULT_IGNORE_REGEX,
        help="Regex of test/fuzz file paths excluded from coverage metrics.",
    )
    parser.add_argument(
        "--fail-under-lines",
        type=float,
        default=DEFAULT_MIN_LINES,
        help="Minimum required line coverage percentage (default: 100).",
    )
    parser.add_argument(
        "--skip-pyo3",
        action="store_true",
        help="Only run pure-Rust (--no-default-features) tests without maturin/pytest.",
    )
    parser.add_argument(
        "--pytest-cov",
        action="store_true",
        help="Keep pytest-cov active during the pytest pass to emit Python coverage.xml simultaneously.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for collecting and verifying findfmt_rs coverage."""
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    mode: Literal["skip", "fast", "cov"] = (
        "skip" if args.skip_pyo3 else ("cov" if args.pytest_cov else "fast")
    )
    return collect_rust_coverage(
        manifest_path=args.manifest_path,
        output_path=args.output_path,
        ignore_regex=args.ignore_filename_regex,
        fail_under_lines=args.fail_under_lines,
        pytest_mode=mode,
    )


if __name__ == "__main__":
    sys.exit(main())
