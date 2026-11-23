"""Rich terminal table renderers for findfmt benchmark reports and comparisons."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich import box
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from tools.benchmark_models import BackendComparisonRow, BenchmarkMetric, ComparisonRow

__all__ = [
    "render_backend_comparison_table",
    "render_comparison_table",
    "render_metrics_table",
]


def render_metrics_table(metrics: list[BenchmarkMetric], console: Console | None = None) -> None:
    """Display benchmark metrics in a formatted terminal table."""
    con = console or Console()
    table = Table(
        title="findfmt Traversal Performance Benchmarks",
        box=box.ROUNDED,
        header_style="bold magenta",
    )
    table.add_column("Tier", style="cyan", justify="left")
    table.add_column("Backend", style="magenta", justify="left")
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
            m.backend,
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


def _format_pct_delta(val: float, *, invert: bool = False) -> str:
    color = "green" if (val <= 0 if invert else val >= 0) else "red"
    sign = "+" if val >= 0 else ""
    return f"[{color}]{sign}{val:.1f}%[/{color}]"


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
    cols = "Base (f/s),Curr (f/s),Throughput Δ,Base TTFR,Curr TTFR,Latency Δ,Base Heap,Curr Heap,Memory Δ"
    for name in cols.split(","):
        table.add_column(name, justify="right")

    for c in comparisons:
        table.add_row(
            c.tier,
            f"{c.baseline_files_per_sec:,.1f}",
            f"{c.current_files_per_sec:,.1f}",
            _format_pct_delta(c.throughput_delta_pct),
            f"{c.baseline_latency_ms:.2f}ms",
            f"{c.current_latency_ms:.2f}ms",
            _format_pct_delta(c.latency_delta_pct, invert=True),
            f"{c.baseline_memory_mb:.2f}MB",
            f"{c.current_memory_mb:.2f}MB",
            _format_pct_delta(c.memory_delta_pct, invert=True),
        )

    con.print(table)


def _format_speedup(multiplier: float) -> str:
    color = "green" if multiplier >= 1.0 else "red"
    return f"[{color}]{multiplier:.2f}x[/{color}]"


def _format_rss_delta(py_rss: float, rust_rss: float, delta_mb: float, delta_pct: float) -> str:
    if py_rss <= 0.0 and rust_rss <= 0.0:
        return "N/A"

    color = "green" if delta_mb <= 0.0 else "red"
    sign = "+" if delta_mb >= 0.0 else ""
    return f"[{color}]{sign}{delta_mb:.2f}MB ({sign}{delta_pct:.1f}%)[/{color}]"


def render_backend_comparison_table(
    comparisons: list[BackendComparisonRow],
    console: Console | None = None,
    *,
    rust_backend_status: str = "native",
) -> None:
    """Display side-by-side Rust (_rust_ext) vs. pure-Python (_fallback) comparison table."""
    con = console or Console()
    title_label = "Rust" if rust_backend_status == "native" else "Rust (fallback)"
    col_label = "Rust" if rust_backend_status == "native" else "Rust*"
    caption = "* Measured via findfmt.core gateway fallback" if rust_backend_status != "native" else None
    table = Table(
        title=f"findfmt {title_label} vs. Python Backend Comparison",
        caption=caption,
        box=box.ROUNDED,
        header_style="bold magenta",
    )
    table.add_column("Scenario", style="cyan", justify="left")
    for col in (
        "Files",
        "Py Time",
        f"{col_label} Time",
        "Py f/s",
        f"{col_label} f/s",
        "Speedup",
        "Py RSS",
        f"{col_label} RSS",
        "RSS Δ",
    ):
        table.add_column(col, justify="right")

    for row in comparisons:
        py_rss_str = f"{row.python_peak_rss_mb:.2f}MB" if row.python_peak_rss_mb > 0 else "N/A"
        rust_rss_str = f"{row.rust_peak_rss_mb:.2f}MB" if row.rust_peak_rss_mb > 0 else "N/A"
        table.add_row(
            row.tier,
            f"{row.files_count:,}",
            f"{row.python_duration_seconds * 1000.0:.1f}ms",
            f"{row.rust_duration_seconds * 1000.0:.1f}ms",
            f"{row.python_files_per_sec:,.1f}",
            f"{row.rust_files_per_sec:,.1f}",
            _format_speedup(row.throughput_speedup),
            py_rss_str,
            rust_rss_str,
            _format_rss_delta(
                row.python_peak_rss_mb,
                row.rust_peak_rss_mb,
                row.peak_rss_delta_mb,
                row.peak_rss_delta_pct,
            ),
        )

    con.print(table)
