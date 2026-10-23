"""findfmt automated performance benchmarking harness tracking throughput and memory."""

from __future__ import annotations

import argparse
import io
import json
import platform
import sys
import tempfile
import time
import tracemalloc
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from rich import box
from rich.console import Console
from rich.table import Table

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

from tools.benchmark_models import (
    BenchmarkMetric,
    BenchmarkReport,
    ComparisonRow,
    compute_comparisons,
    load_baseline_report,
    save_baseline_report,
)
from tools.benchmark_topologies import (
    DEFAULT_SEED,
    count_directories,
    generate_synthetic_tree,
)

from findfmt.diagnostics import get_version
from findfmt.formatters import (
    CsvFormatter,
    JsonFormatter,
    JsonlFormatter,
    RichTableFormatter,
    RichTreeFormatter,
    TextFormatter,
    TsvFormatter,
)
from findfmt.models import TraversalConfig
from findfmt.traversal.engine import find_files

try:
    import resource
except ImportError:  # pragma: no cover
    resource = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from findfmt.models import FileInfo

DEFAULT_RUNS = 1

TIER_FILE_COUNTS: dict[str, int] = {"small": 800, "medium": 12_000, "monorepo": 100_000}


class _NullSink(io.StringIO):
    """Sink that discards formatted output while measuring TTFR and write count."""

    __slots__ = ("first_write_time", "write_count")

    def __init__(self) -> None:
        """Initialize empty null sink."""
        super().__init__()
        self.first_write_time: float | None = None
        self.write_count: int = 0

    @override
    def write(self, s: str) -> int:
        """Discard content while recording first write timestamp."""
        if self.first_write_time is None and s:
            self.first_write_time = time.perf_counter()

        self.write_count += 1
        return len(s)

    @override
    def writelines(self, lines: Iterable[str]) -> None:
        """Discard lines while recording first write timestamp."""
        for line in lines:
            self.write(line)


def get_peak_rss_mb() -> float:
    """Measure peak resident set size in megabytes."""
    if resource is None:
        return 0.0

    try:
        rss = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        if sys.platform == "darwin":
            return rss / (1024.0 * 1024.0)

        return rss / 1024.0
    except (AttributeError, OSError):
        return 0.0


def _run_single_traversal(  # noqa: PLR0913
    target_path: Path,
    tier_name: str,
    *,
    tag_filter: str | None = None,
    total_dirs: int = 0,
    output_format: str = "traversal",
    show_tags: bool = False,
) -> BenchmarkMetric:
    """Execute a single traversal measurement run."""
    config = TraversalConfig(
        root_paths=(target_path,),
        respect_gitignore=True,
        include_tags=frozenset([tag_filter]) if tag_filter else frozenset(),
    )
    tracemalloc.start()
    start_time = time.perf_counter()
    first_latency: float | None = None
    files_count = 0

    if output_format == "traversal":
        for _ in find_files(config):
            if first_latency is None:
                first_latency = time.perf_counter() - start_time

            files_count += 1
    else:
        sink = _NullSink()
        fmt_factories = {
            "text": lambda: TextFormatter(show_tags=show_tags),
            "jsonl": JsonlFormatter,
            "tsv": TsvFormatter,
            "csv": CsvFormatter,
            "json": JsonFormatter,
            "tree": RichTreeFormatter,
            "table": RichTableFormatter,
        }
        formatter = fmt_factories.get(output_format, TextFormatter)()

        def _counting_stream() -> Iterator[FileInfo]:
            nonlocal files_count
            for item in find_files(config):
                files_count += 1
                yield item

        formatter.stream(_counting_stream(), sink)
        if sink.first_write_time is not None:
            first_latency = sink.first_write_time - start_time

    end_time = time.perf_counter()
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    duration = max(end_time - start_time, 1e-9)
    first_latency_ms = (first_latency * 1000.0) if first_latency is not None else 0.0
    rss_mb = get_peak_rss_mb()

    return BenchmarkMetric(
        tier_name,
        str(target_path),
        files_count,
        total_dirs,
        duration,
        files_count / duration,
        total_dirs / duration,
        first_latency_ms,
        peak_bytes,
        peak_bytes / (1024.0 * 1024.0),
        rss_mb,
    )


def measure_traversal(  # noqa: PLR0913
    target_path: Path,
    tier_name: str,
    *,
    runs: int = 1,
    warmup: int = 0,
    tag_filter: str | None = None,
    total_dirs: int | None = None,
    output_format: str = "traversal",
    show_tags: bool = False,
) -> BenchmarkMetric:
    """Measure throughput, latency to first file, and peak heap memory."""
    dirs_count = total_dirs if total_dirs is not None else count_directories(target_path)
    for _ in range(warmup):
        _run_single_traversal(
            target_path,
            tier_name,
            tag_filter=tag_filter,
            total_dirs=dirs_count,
            output_format=output_format,
            show_tags=show_tags,
        )

    results = [
        _run_single_traversal(
            target_path,
            tier_name,
            tag_filter=tag_filter,
            total_dirs=dirs_count,
            output_format=output_format,
            show_tags=show_tags,
        )
        for _ in range(max(1, runs))
    ]
    cnt = len(results)
    first = results[0]
    return BenchmarkMetric(
        tier_name,
        first.target_path,
        first.files_count,
        first.dirs_count,
        sum(r.duration_seconds for r in results) / cnt,
        sum(r.files_per_sec for r in results) / cnt,
        sum(r.dirs_per_sec for r in results) / cnt,
        sum(r.first_file_latency_ms for r in results) / cnt,
        int(sum(r.peak_memory_bytes for r in results) / cnt),
        sum(r.peak_memory_mb for r in results) / cnt,
        sum(r.peak_rss_mb for r in results) / cnt,
    )


def render_metrics_table(metrics: list[BenchmarkMetric], console: Console | None = None) -> None:
    """Display benchmark metrics in a formatted terminal table."""
    con = console or Console()
    table = Table(
        title="findfmt Traversal Performance Benchmarks",
        box=box.ROUNDED,
        header_style="bold magenta",
    )
    table.add_column("Tier", style="cyan", justify="left")
    for name in ("Files", "Dirs", "Duration"):
        table.add_column(name, justify="right")

    table.add_column("Throughput", style="green", justify="right")
    table.add_column("Dirs/sec", justify="right")
    table.add_column("TTFR Latency", style="yellow", justify="right")
    table.add_column("Peak Heap", style="blue", justify="right")
    table.add_column("Peak RSS", style="cyan", justify="right")

    for m in metrics:
        table.add_row(
            m.tier,
            f"{m.files_count:,}",
            f"{m.dirs_count:,}",
            f"{m.duration_seconds:.4f}s",
            f"{m.files_per_sec:,.1f} f/s",
            f"{m.dirs_per_sec:,.1f} d/s",
            f"{m.first_file_latency_ms:.2f} ms",
            f"{m.peak_memory_mb:.2f} MB",
            f"{m.peak_rss_mb:.2f} MB" if m.peak_rss_mb > 0 else "N/A",
        )

    con.print(table)


def render_comparison_table(
    comparisons: list[ComparisonRow],
    console: Console | None = None,
) -> None:
    """Display comparison rows showing performance deltas against baseline."""
    con = console or Console()
    table = Table(
        title="findfmt Performance Baseline Comparison",
        box=box.ROUNDED,
        header_style="bold magenta",
    )
    table.add_column("Tier", style="cyan", justify="left")
    cols = (
        "Base (f/s),Curr (f/s),Throughput Δ,"
        "Base TTFR,Curr TTFR,Latency Δ,Base Heap,Curr Heap,Memory Δ"
    )
    for name in cols.split(","):
        table.add_column(name, justify="right")

    for c in comparisons:

        def _fmt(val: float, *, invert: bool = False) -> str:
            color = "green" if (val <= 0 if invert else val >= 0) else "red"
            sign = "+" if val >= 0 else ""
            return f"[{color}]{sign}{val:.1f}%[/{color}]"

        table.add_row(
            c.tier,
            f"{c.baseline_files_per_sec:,.1f}",
            f"{c.current_files_per_sec:,.1f}",
            _fmt(c.throughput_delta_pct),
            f"{c.baseline_latency_ms:.2f}ms",
            f"{c.current_latency_ms:.2f}ms",
            _fmt(c.latency_delta_pct, invert=True),
            f"{c.baseline_memory_mb:.2f}MB",
            f"{c.current_memory_mb:.2f}MB",
            _fmt(c.memory_delta_pct, invert=True),
        )

    con.print(table)


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    p = argparse.ArgumentParser(prog="benchmark", description="findfmt benchmark harness.")
    p.add_argument("--tier", "-t", choices=["small", "medium", "monorepo", "all"], default="small")
    p.add_argument(
        "--topology",
        "-T",
        choices=["standard", "flat", "deep", "real-world", "all"],
        default="standard",
        help="Filesystem hierarchy topology to benchmark (default: standard).",
    )
    p.add_argument(
        "--format",
        "-F",
        choices=["traversal", "text", "jsonl", "tsv", "csv", "json", "tree", "table", "all"],
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
    selected_formats = (
        ["traversal", "text", "jsonl", "tsv", "csv", "json", "tree", "table"]
        if args.format == "all"
        else [args.format]
    )

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
                ),
            )

        return metrics, []

    selected_tiers = ["small", "medium", "monorepo"] if args.tier == "all" else [args.tier]
    selected_topologies = (
        ["standard", "flat", "deep", "real-world"] if args.topology == "all" else [args.topology]
    )

    cleanups: list[tempfile.TemporaryDirectory[str]] = []
    metrics = []

    for top in selected_topologies:
        for tier in selected_tiers:
            target_files = args.files if args.files is not None else TIER_FILE_COUNTS[tier]
            td = tempfile.TemporaryDirectory(prefix=f"findfmt_bench_{tier}_{top}_")
            if not args.keep_temp:
                cleanups.append(td)

            root_path = Path(td.name)
            _, total_dirs = generate_synthetic_tree(
                root_path,
                target_files,
                seed=args.seed,
                topology=top,
            )

            for fmt in selected_formats:
                tier_parts = [tier]
                if len(selected_topologies) > 1 or top != "standard":
                    tier_parts.append(top)

                if len(selected_formats) > 1 or fmt != "traversal":
                    tier_parts.append(fmt)

                tier_label = " ".join(tier_parts)
                metrics.append(
                    measure_traversal(
                        root_path,
                        tier_name=tier_label,
                        runs=args.runs,
                        warmup=args.warmup,
                        tag_filter=args.tag,
                        total_dirs=total_dirs,
                        output_format=fmt,
                        show_tags=args.show_tags,
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


def main(argv: list[str] | None = None) -> int:
    """Execute benchmarking harness."""
    args = build_parser().parse_args(argv)
    metrics, cleanups = _collect_metrics(args)
    if not metrics and args.target_dir is not None:
        return 1

    try:
        report = BenchmarkReport(
            datetime.now(UTC).isoformat(),
            get_version(),
            platform.python_version(),
            f"{platform.system()}-{platform.machine()}",
            args.seed,
            metrics,
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
