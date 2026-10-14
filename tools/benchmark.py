"""findfmt automated performance benchmarking harness tracking throughput and memory."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import platform
import random
import sys
import tempfile
import time
import tracemalloc
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from rich import box
from rich.console import Console
from rich.table import Table

from findfmt.diagnostics import get_version
from findfmt.models import TraversalConfig
from findfmt.traversal.engine import find_files

DEFAULT_SEED = 42
DEFAULT_RUNS = 1

TIER_FILE_COUNTS: dict[str, int] = {"small": 800, "medium": 12_000, "monorepo": 100_000}


class _DictMixin:
    """Mixin for dataclass dictionary serialization."""

    __slots__ = ()

    def to_dict(self) -> dict[str, Any]:
        """Convert dataclass to dictionary representation."""
        return asdict(cast("Any", self))


@dataclass(frozen=True, slots=True)
class BenchmarkMetric(_DictMixin):
    """Performance metrics recorded for a benchmark tier."""

    tier: str
    target_path: str
    files_count: int
    dirs_count: int
    duration_seconds: float
    files_per_sec: float
    dirs_per_sec: float
    first_file_latency_ms: float
    peak_memory_bytes: int
    peak_memory_mb: float


@dataclass(frozen=True, slots=True)
class BenchmarkReport(_DictMixin):
    """Comprehensive benchmark report with environment metadata."""

    timestamp: str
    findfmt_version: str
    python_version: str
    platform: str
    seed: int
    metrics: list[BenchmarkMetric]


@dataclass(frozen=True, slots=True)
class ComparisonRow(_DictMixin):
    """Comparison deltas between baseline and current runs."""

    tier: str
    baseline_files_per_sec: float
    current_files_per_sec: float
    throughput_delta_pct: float
    baseline_latency_ms: float
    current_latency_ms: float
    latency_delta_pct: float
    baseline_memory_mb: float
    current_memory_mb: float
    memory_delta_pct: float
    regressed: bool


def count_directories(root: Path) -> int:
    """Count total subdirectories beneath root path."""
    return sum(len(dirs) for _, dirs, _ in os.walk(root))


def generate_synthetic_tree(
    root: Path,
    target_files: int,
    seed: int = DEFAULT_SEED,
) -> tuple[int, int]:
    """Generate a reproducible, tiered synthetic directory tree."""
    rng = random.Random(seed)
    top_names = (
        "src",
        "lib",
        "pkg",
        "components",
        "utils",
        "tests",
        "docs",
        "scripts",
        "build",
        "node_modules",
    )
    sub_names = ("core", "api", "handlers", "models", "helpers")
    dirs: list[Path] = [root]
    dirs.extend(root / top for top in top_names)
    dirs.extend(root / top / sub for top in top_names for sub in sub_names)
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    ignore_rules = "node_modules/\nbuild/\n*.tmp\n*.log\n.cache/\n"
    (root / ".gitignore").write_text(ignore_rules, encoding="utf-8")
    extensions = [".py"] * 3 + [".sh", ".md", ".json", ".yaml", ".txt", ".tmp", ".log", ".bin"]
    templates: dict[str, Any] = {
        ".py": "def action() -> int:\n    return 42\n",
        ".sh": "#!/usr/bin/env bash\necho 42\n",
        ".md": "# Doc\nContent.\n",
        ".json": '{"id": 42}\n',
        ".yaml": "id: 42\n",
        ".bin": b"\x00\x01\x02\x03",
    }

    files_created = 0
    for i in range(max(1, target_files)):
        target_dir = rng.choice(dirs)
        ext = rng.choice(extensions)
        fp = target_dir / f"item_{i:06d}{ext}"
        content = templates.get(ext, f"content {i}\n")
        if isinstance(content, bytes):
            fp.write_bytes(content)
        else:
            fp.write_text(content, encoding="utf-8")

        files_created += 1

    shebang = "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n"
    for s_name in ("worker", "deploy"):
        sp = root / "scripts" / s_name
        sp.write_text(shebang, encoding="utf-8")
        with contextlib.suppress(OSError):
            sp.chmod(0o755)

        files_created += 1

    return files_created, count_directories(root)


def _run_single_traversal(
    target_path: Path,
    tier_name: str,
    *,
    tag_filter: str | None = None,
    total_dirs: int = 0,
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

    for _ in find_files(config):
        if first_latency is None:
            first_latency = time.perf_counter() - start_time

        files_count += 1

    end_time = time.perf_counter()
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    duration = max(end_time - start_time, 1e-9)
    first_latency_ms = (first_latency * 1000.0) if first_latency is not None else 0.0

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
    )


def measure_traversal(  # noqa: PLR0913
    target_path: Path,
    tier_name: str,
    *,
    runs: int = 1,
    warmup: int = 0,
    tag_filter: str | None = None,
    total_dirs: int | None = None,
) -> BenchmarkMetric:
    """Measure throughput, latency to first file, and peak heap memory."""
    dirs_count = total_dirs if total_dirs is not None else count_directories(target_path)
    for _ in range(warmup):
        _run_single_traversal(target_path, tier_name, tag_filter=tag_filter, total_dirs=dirs_count)

    results = [
        _run_single_traversal(target_path, tier_name, tag_filter=tag_filter, total_dirs=dirs_count)
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
    )


def _pct_delta(base: float, curr: float) -> float:
    return ((curr - base) / base * 100.0) if base > 0 else 0.0


def compute_comparisons(
    baseline_metrics: list[BenchmarkMetric],
    current_metrics: list[BenchmarkMetric],
    threshold_pct: float | None = None,
) -> list[ComparisonRow]:
    """Compare current benchmark metrics against a baseline."""
    base_map = {m.tier: m for m in baseline_metrics}
    comparisons: list[ComparisonRow] = []

    for curr in current_metrics:
        base = base_map.get(curr.tier)
        if not base:
            continue

        tp_b, tp_c = base.files_per_sec, curr.files_per_sec
        lat_b, lat_c = base.first_file_latency_ms, curr.first_file_latency_ms
        mem_b, mem_c = base.peak_memory_mb, curr.peak_memory_mb
        tp_d = _pct_delta(tp_b, tp_c)
        lat_d = _pct_delta(lat_b, lat_c)
        mem_d = _pct_delta(mem_b, mem_c)
        regressed = bool(threshold_pct and threshold_pct > 0 and tp_d < -threshold_pct)
        comparisons.append(
            ComparisonRow(
                curr.tier,
                tp_b,
                tp_c,
                tp_d,
                lat_b,
                lat_c,
                lat_d,
                mem_b,
                mem_c,
                mem_d,
                regressed,
            ),
        )

    return comparisons


def save_baseline_report(report: BenchmarkReport, file_path: Path) -> None:
    """Save benchmark report to a JSON baseline file."""
    file_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")


def load_baseline_report(file_path: Path) -> list[BenchmarkMetric]:
    """Load baseline metrics from a JSON baseline file."""
    data = json.loads(file_path.read_text(encoding="utf-8"))
    return [BenchmarkMetric(**item) for item in data.get("metrics", [])]


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
    """Execute benchmark measurements across selected targets or tiers."""
    if args.target_dir is not None:
        target = args.target_dir.resolve()
        if not target.exists():
            sys.stderr.write(f"Error: Target directory does not exist: {target}\n")
            return [], []

        metric = measure_traversal(
            target,
            tier_name="custom",
            runs=args.runs,
            warmup=args.warmup,
            tag_filter=args.tag,
        )
        return [metric], []

    selected = ["small", "medium", "monorepo"] if args.tier == "all" else [args.tier]
    cleanups: list[tempfile.TemporaryDirectory[str]] = []
    metrics: list[BenchmarkMetric] = []
    for tier in selected:
        target_files = args.files if args.files is not None else TIER_FILE_COUNTS[tier]
        td = tempfile.TemporaryDirectory(prefix=f"findfmt_bench_{tier}_")
        if not args.keep_temp:
            cleanups.append(td)

        root_path = Path(td.name)
        _, total_dirs = generate_synthetic_tree(root_path, target_files, seed=args.seed)
        metrics.append(
            measure_traversal(
                root_path,
                tier_name=tier,
                runs=args.runs,
                warmup=args.warmup,
                tag_filter=args.tag,
                total_dirs=total_dirs,
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
            datetime.now(timezone.utc).isoformat(),
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
