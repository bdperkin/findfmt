"""findfmt automated performance benchmarking harness tracking throughput and memory."""

from __future__ import annotations

import argparse
import json
import platform
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

try:
    from tools.benchmark_backends import (
        ALL_FORMATS,
        ALL_TIERS,
        ALL_TOPOLOGIES,
        TIER_FILE_COUNTS,
        VALID_BACKENDS,
        BackendUnavailableError,
        is_native_rust_find_available,
        resolve_find_files_backend,
        run_compare_mode,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools.benchmark_backends import (
        ALL_FORMATS,
        ALL_TIERS,
        ALL_TOPOLOGIES,
        TIER_FILE_COUNTS,
        VALID_BACKENDS,
        BackendUnavailableError,
        is_native_rust_find_available,
        resolve_find_files_backend,
        run_compare_mode,
    )

from tools.benchmark_models import (
    BackendComparisonReport,
    BackendComparisonRow,
    BenchmarkMetric,
    BenchmarkReport,
    ComparisonRow,
    compute_backend_comparisons,
    compute_comparisons,
    load_baseline_report,
    save_baseline_report,
)
from tools.benchmark_render import (
    render_backend_comparison_table,
    render_comparison_table,
    render_metrics_table,
)
from tools.benchmark_runner import (
    _NullSink,
    _run_single_traversal,
    get_peak_rss_mb,
    measure_traversal,
)
from tools.benchmark_topologies import (
    DEFAULT_SEED,
    generate_synthetic_tree,
)

from findfmt import get_version

DEFAULT_RUNS = 1

__all__ = [
    "DEFAULT_RUNS",
    "DEFAULT_SEED",
    "TIER_FILE_COUNTS",
    "VALID_BACKENDS",
    "BackendComparisonReport",
    "BackendComparisonRow",
    "BackendUnavailableError",
    "BenchmarkMetric",
    "BenchmarkReport",
    "ComparisonRow",
    "_NullSink",
    "_collect_metrics",
    "_handle_output",
    "_run_single_traversal",
    "build_parser",
    "compute_backend_comparisons",
    "compute_comparisons",
    "generate_synthetic_tree",
    "get_peak_rss_mb",
    "is_native_rust_find_available",
    "load_baseline_report",
    "main",
    "measure_traversal",
    "render_backend_comparison_table",
    "render_comparison_table",
    "render_metrics_table",
    "resolve_find_files_backend",
    "run_compare_mode",
    "save_baseline_report",
]


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    p = argparse.ArgumentParser(prog="benchmark", description="findfmt benchmark harness.")
    p.add_argument(
        "--backend",
        choices=list(VALID_BACKENDS),
        default="auto",
        help="Execution backend to benchmark or 'compare' for Rust vs. Python (default: auto).",
    )
    p.add_argument("--tier", "-t", choices=[*ALL_TIERS, "all"], default="small")
    p.add_argument(
        "--topology",
        "-T",
        choices=[*ALL_TOPOLOGIES, "all"],
        default="standard",
        help="Filesystem hierarchy topology to benchmark (default: standard).",
    )
    p.add_argument(
        "--format",
        "-F",
        choices=[*ALL_FORMATS, "all"],
        default="traversal",
        help="Output formatter to benchmark (default: traversal).",
    )
    p.add_argument(
        "--list-tags",
        "--show-tags",
        dest="show_tags",
        action="store_true",
        help="Measure MIME and tag classification overhead.",
    )
    p.add_argument("--target-dir", "-d", type=Path)
    p.add_argument("--files", "-f", type=int)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--runs", "-r", type=int, default=DEFAULT_RUNS)
    p.add_argument("--warmup", type=int, default=0)
    p.add_argument("--tag", type=str)
    p.add_argument("--baseline", "-b", type=Path)
    p.add_argument("--save-baseline", type=Path)
    p.add_argument("--threshold", type=float)
    p.add_argument("--json", action="store_true")
    p.add_argument("--output", "-o", type=Path)
    p.add_argument("--keep-temp", action="store_true")
    return p


def _collect_metrics(
    args: argparse.Namespace,
) -> tuple[list[BenchmarkMetric], list[tempfile.TemporaryDirectory[str]]]:
    """Execute benchmark measurements across selected targets, topologies, or tiers."""
    backend_choice = str(getattr(args, "backend", "auto"))
    selected_formats = list(ALL_FORMATS) if args.format == "all" else [str(args.format)]

    if args.target_dir is not None:
        target = args.target_dir.resolve()
        if not target.exists():
            sys.stderr.write(f"Error: Target directory does not exist: {target}\n")
            return [], []

        metrics: list[BenchmarkMetric] = []
        for fmt in selected_formats:
            tier_label = f"custom [{fmt}]" if len(selected_formats) > 1 else "custom"
            metrics.append(
                measure_traversal(
                    target,
                    tier_name=tier_label,
                    runs=args.runs,
                    warmup=args.warmup,
                    tag_filter=args.tag,
                    output_format=fmt,
                    show_tags=args.show_tags,
                    backend=backend_choice,
                ),
            )

        return metrics, []

    selected_tiers = list(ALL_TIERS) if args.tier == "all" else [str(args.tier)]
    selected_topologies = list(ALL_TOPOLOGIES) if args.topology == "all" else [str(args.topology)]
    cleanups: list[tempfile.TemporaryDirectory[str]] = []
    metrics = []

    for top in selected_topologies:
        for tier in selected_tiers:
            target_files = args.files if args.files is not None else TIER_FILE_COUNTS[tier]
            if args.keep_temp:  # mkdtemp has no finalizer, so the tree survives (#489)
                root_path = Path(tempfile.mkdtemp(prefix=f"findfmt_bench_{tier}_{top}_"))
                sys.stderr.write(f"Keeping benchmark tree: {root_path}\n")
            else:
                td = tempfile.TemporaryDirectory(prefix=f"findfmt_bench_{tier}_{top}_")
                cleanups.append(td)
                root_path = Path(td.name)

            _, total_dirs = generate_synthetic_tree(root_path, target_files, seed=args.seed, topology=top)
            for fmt in selected_formats:
                tier_parts = [tier]
                if len(selected_topologies) > 1 or top != "standard":
                    tier_parts.append(top)

                if len(selected_formats) > 1 or fmt != "traversal":
                    tier_parts.append(fmt)

                metrics.append(
                    measure_traversal(
                        root_path,
                        tier_name=" ".join(tier_parts),
                        runs=args.runs,
                        warmup=args.warmup,
                        tag_filter=args.tag,
                        total_dirs=total_dirs,
                        output_format=fmt,
                        show_tags=args.show_tags,
                        backend=backend_choice,
                    ),
                )

    return metrics, cleanups


def _handle_output(
    report: BenchmarkReport,
    comparisons: list[ComparisonRow],
    args: argparse.Namespace,
) -> None:
    """Output formatted tables or JSON output to destination."""
    if not (args.json or args.output is not None):
        render_metrics_table(report.metrics)
        if comparisons:
            render_comparison_table(comparisons)

        return

    out_dict = report.to_dict()
    if comparisons:
        out_dict["comparisons"] = [c.to_dict() for c in comparisons]

    json_str = json.dumps(out_dict, indent=2) + "\n"
    if args.output is not None:
        args.output.write_text(json_str, encoding="utf-8")

    if args.json:
        sys.stdout.write(json_str)


def _handle_compare_output(report: BackendComparisonReport, args: argparse.Namespace) -> None:
    """Output side-by-side backend comparison table or JSON report."""
    if not (args.json or args.output is not None):
        render_backend_comparison_table(
            report.comparisons,
            rust_backend_status=report.rust_backend_status,
        )
        return

    json_str = json.dumps(report.to_dict(), indent=2) + "\n"
    if args.output is not None:
        args.output.write_text(json_str, encoding="utf-8")

    if args.json:
        sys.stdout.write(json_str)


def _run_compare_cli(args: argparse.Namespace) -> int:
    """Execute side-by-side Rust vs. Python comparison mode."""
    if (args.baseline, args.save_baseline, args.threshold) != (None, None, None):
        sys.stderr.write(
            "Error: --baseline, --save-baseline, and --threshold are not supported with --backend compare.\n",
        )
        return 2

    try:
        compare_report = run_compare_mode(args)
    except RuntimeError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1

    if compare_report is None:
        return 1

    _handle_compare_output(compare_report, args)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Execute benchmarking harness."""
    args = build_parser().parse_args(argv)
    if args.backend == "compare":
        return _run_compare_cli(args)

    try:
        metrics, cleanups = _collect_metrics(args)
    except BackendUnavailableError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1

    if not metrics and args.target_dir is not None:
        return 1

    try:
        active_backend = metrics[0].backend if metrics else str(args.backend)
        report = BenchmarkReport(
            datetime.now(UTC).isoformat(),
            get_version(),
            platform.python_version(),
            f"{platform.system()}-{platform.machine()}",
            args.seed,
            metrics,
            backend=active_backend,
        )

        comparisons: list[ComparisonRow] = []
        if args.baseline is not None:
            if not args.baseline.exists():
                sys.stderr.write(f"Error: Baseline file not found: {args.baseline}\n")
                return 1

            base_metrics = load_baseline_report(args.baseline)
            comparisons = compute_comparisons(base_metrics, metrics, threshold_pct=args.threshold)

        if args.save_baseline is not None:
            save_baseline_report(report, args.save_baseline)

        _handle_output(report, comparisons, args)

        if any(c.regressed for c in comparisons):
            sys.stderr.write("Error: Performance regression detected!\n")
            return 1

        return 0
    finally:
        for td in cleanups:
            td.cleanup()


if __name__ == "__main__":
    sys.exit(main())
