"""Backend resolution and subprocess-isolated comparison runner for findfmt benchmarks."""

from __future__ import annotations

import dataclasses
import importlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast

from tools.benchmark_models import (
    BackendComparisonReport,
    BenchmarkMetric,
    compute_backend_comparisons,
)
from tools.benchmark_topologies import generate_synthetic_tree

from findfmt import _fallback, core, get_version

if TYPE_CHECKING:
    import argparse
    from collections.abc import Callable, Iterable

    from findfmt.models import FileInfo, TraversalConfig

    FindFilesFn = Callable[[TraversalConfig], Iterable[FileInfo]]

__all__ = [
    "ALL_FORMATS",
    "ALL_TIERS",
    "ALL_TOPOLOGIES",
    "TIER_FILE_COUNTS",
    "VALID_BACKENDS",
    "BackendUnavailableError",
    "is_native_rust_find_available",
    "resolve_find_files_backend",
    "run_compare_mode",
]

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_SCRIPT = Path(__file__).resolve().with_name("benchmark.py")

VALID_BACKENDS: tuple[str, ...] = ("auto", "rust", "python", "compare")
ALL_TIERS: tuple[str, ...] = ("small", "medium", "monorepo")
ALL_TOPOLOGIES: tuple[str, ...] = ("standard", "flat", "deep", "real-world")
ALL_FORMATS: tuple[str, ...] = ("traversal", "text", "jsonl", "tsv", "csv", "json", "tree", "table")
TIER_FILE_COUNTS: dict[str, int] = {"small": 800, "medium": 12_000, "monorepo": 100_000}


class BackendUnavailableError(RuntimeError):
    """Raised when an explicitly requested native benchmark backend is unavailable."""


def _load_rust_find() -> FindFilesFn | None:
    """Return findfmt._rust_ext.find_files when enabled and callable, else None."""
    if not core.is_rust_extension_loaded():
        return None

    try:
        rust_ext = importlib.import_module("findfmt._rust_ext")
    except ImportError:
        return None

    candidate = getattr(rust_ext, "find_files", None)
    return cast("FindFilesFn", candidate) if callable(candidate) else None


def is_native_rust_find_available() -> bool:
    """Return True when findfmt._rust_ext is enabled and exports a callable find_files."""
    return _load_rust_find() is not None


def resolve_find_files_backend(backend: str) -> tuple[str, FindFilesFn]:
    """Resolve backend identifier ('auto', 'rust', 'python') to (label, find_files_callable)."""
    if backend == "python":
        return "python", _fallback.find_files

    if backend == "auto":
        return core.get_active_backend(), core.find_files

    if backend == "rust":
        rust_find = _load_rust_find()
        if rust_find is None:
            msg = (
                "Native Rust backend (findfmt._rust_ext.find_files) is unavailable or disabled "
                "via FINDFMT_NO_EXTENSIONS."
            )
            raise BackendUnavailableError(msg)

        return "rust", rust_find

    msg = f"Unsupported benchmark backend: {backend!r}"
    raise ValueError(msg)


def _build_subprocess_cmd(
    target_dir: Path,
    backend: str,
    args: argparse.Namespace,
) -> list[str]:
    cmd = [
        sys.executable,
        str(BENCHMARK_SCRIPT),
        "--backend",
        backend,
        "--target-dir",
        str(target_dir),
        "--format",
        str(args.format),
        "--runs",
        str(args.runs),
        "--warmup",
        str(args.warmup),
        "--json",
    ]
    if args.show_tags:
        cmd.append("--list-tags")

    if args.tag:
        cmd.extend(["--tag", str(args.tag)])

    return cmd


def _measure_scenario_subprocess(
    target_dir: Path,
    backend: str,
    tier_labels: list[str],
    backend_label: str,
    args: argparse.Namespace,
) -> list[BenchmarkMetric]:
    """Run benchmark in a fresh child subprocess to isolate OS ru_maxrss per backend."""
    env = os.environ.copy()
    existing_py_path = env.get("PYTHONPATH", "")
    repo_str = str(REPO_ROOT)
    env["PYTHONPATH"] = f"{repo_str}{os.pathsep}{existing_py_path}" if existing_py_path else repo_str

    proc = subprocess.run(
        _build_subprocess_cmd(target_dir, backend, args),
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip() or f"exit code {proc.returncode}"
        msg = f"Subprocess benchmark failed for backend '{backend}': {detail}"
        raise RuntimeError(msg)

    try:
        payload = json.loads(proc.stdout)
        raw_metrics = payload["metrics"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        msg = f"Invalid JSON output from subprocess benchmark for backend '{backend}': {exc}"
        raise RuntimeError(msg) from exc

    parsed: list[BenchmarkMetric] = []
    for idx, item in enumerate(raw_metrics):
        item.setdefault("peak_rss_mb", 0.0)
        item.setdefault("backend", backend_label)
        metric = BenchmarkMetric(**item)
        new_tier = tier_labels[idx] if idx < len(tier_labels) else metric.tier
        parsed.append(dataclasses.replace(metric, tier=new_tier, backend=backend_label))

    return parsed


def _build_tier_labels(
    tier: str,
    top: str,
    selected_topologies: list[str],
    selected_formats: list[str],
) -> list[str]:
    labels: list[str] = []
    for fmt in selected_formats:
        parts = [tier]
        if len(selected_topologies) > 1 or top != "standard":
            parts.append(top)

        if len(selected_formats) > 1 or fmt != "traversal":
            parts.append(fmt)

        labels.append(" ".join(parts))

    return labels


def run_compare_mode(args: argparse.Namespace) -> BackendComparisonReport | None:
    """Run side-by-side Rust vs. Python benchmarks across selected scenarios in isolated subprocesses."""
    selected_formats = list(ALL_FORMATS) if args.format == "all" else [str(args.format)]
    native_rust = is_native_rust_find_available()
    rust_sub_backend = "rust" if native_rust else "auto"
    rust_status = "native" if native_rust else "fallback"
    rust_metric_label = "rust" if native_rust else "rust (fallback)"
    if not native_rust:
        sys.stderr.write(
            "Warning: findfmt._rust_ext.find_files is not available; "
            "measuring findfmt.core gateway fallback against _fallback.\n",
        )

    scenarios: list[tuple[Path, list[str]]] = []
    cleanups: list[tempfile.TemporaryDirectory[str]] = []
    try:
        if args.target_dir is not None:
            target = args.target_dir.resolve()
            if not target.exists():
                sys.stderr.write(f"Error: Target directory does not exist: {target}\n")
                return None

            custom_labels = [
                f"custom [{fmt}]" if len(selected_formats) > 1 else "custom" for fmt in selected_formats
            ]
            scenarios.append((target, custom_labels))
        else:
            selected_tiers = list(ALL_TIERS) if args.tier == "all" else [str(args.tier)]
            selected_topologies = list(ALL_TOPOLOGIES) if args.topology == "all" else [str(args.topology)]
            for top in selected_topologies:
                for tier in selected_tiers:
                    target_files = args.files if args.files is not None else TIER_FILE_COUNTS[tier]
                    if args.keep_temp:
                        root_path = Path(tempfile.mkdtemp(prefix=f"findfmt_bench_{tier}_{top}_"))
                        sys.stderr.write(f"Keeping benchmark tree: {root_path}\n")
                    else:
                        td = tempfile.TemporaryDirectory(prefix=f"findfmt_bench_{tier}_{top}_")
                        cleanups.append(td)
                        root_path = Path(td.name)

                    generate_synthetic_tree(root_path, target_files, seed=args.seed, topology=top)
                    labels = _build_tier_labels(tier, top, selected_topologies, selected_formats)
                    scenarios.append((root_path, labels))

        python_metrics: list[BenchmarkMetric] = []
        rust_metrics: list[BenchmarkMetric] = []
        for scenario_path, labels in scenarios:
            python_metrics.extend(
                _measure_scenario_subprocess(scenario_path, "python", labels, "python", args),
            )
            rust_metrics.extend(
                _measure_scenario_subprocess(
                    scenario_path, rust_sub_backend, labels, rust_metric_label, args
                ),
            )

        comparisons = compute_backend_comparisons(
            python_metrics,
            rust_metrics,
            rust_backend_status=rust_status,
        )
        return BackendComparisonReport(
            timestamp=datetime.now(UTC).isoformat(),
            findfmt_version=get_version(),
            python_version=platform.python_version(),
            platform=f"{platform.system()}-{platform.machine()}",
            seed=args.seed,
            rust_backend_status=rust_status,
            measured_in="subprocess",
            python_metrics=python_metrics,
            rust_metrics=rust_metrics,
            comparisons=comparisons,
        )
    finally:
        for td in cleanups:
            td.cleanup()
