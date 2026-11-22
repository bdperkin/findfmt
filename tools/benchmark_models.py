"""Data models, serialization, and comparison logic for findfmt benchmarks."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from pathlib import Path

__all__ = [
    "BackendComparisonReport",
    "BackendComparisonRow",
    "BenchmarkMetric",
    "BenchmarkReport",
    "ComparisonRow",
    "compute_backend_comparisons",
    "compute_comparisons",
    "load_baseline_report",
    "save_baseline_report",
]


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
    peak_rss_mb: float = 0.0
    backend: str = "python"


@dataclass(frozen=True, slots=True)
class BenchmarkReport(_DictMixin):
    """Comprehensive benchmark report with environment metadata."""

    timestamp: str
    findfmt_version: str
    python_version: str
    platform: str
    seed: int
    metrics: list[BenchmarkMetric]
    measured_in: str = "subprocess"
    backend: str = "python"


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


@dataclass(frozen=True, slots=True)
class BackendComparisonRow(_DictMixin):
    """Side-by-side comparison between Rust (_rust_ext) and pure-Python (_fallback) runs."""

    tier: str
    files_count: int
    dirs_count: int
    rust_backend_status: str
    python_duration_seconds: float
    rust_duration_seconds: float
    duration_speedup: float
    python_files_per_sec: float
    rust_files_per_sec: float
    throughput_speedup: float
    python_first_file_latency_ms: float
    rust_first_file_latency_ms: float
    latency_delta_ms: float
    python_peak_memory_mb: float
    rust_peak_memory_mb: float
    peak_memory_delta_mb: float
    python_peak_rss_mb: float
    rust_peak_rss_mb: float
    peak_rss_delta_mb: float
    peak_rss_delta_pct: float


@dataclass(frozen=True, slots=True)
class BackendComparisonReport(_DictMixin):
    """Structured side-by-side Rust vs. Python benchmark comparison report."""

    timestamp: str
    findfmt_version: str
    python_version: str
    platform: str
    seed: int
    rust_backend_status: str
    measured_in: str
    python_metrics: list[BenchmarkMetric]
    rust_metrics: list[BenchmarkMetric]
    comparisons: list[BackendComparisonRow]


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


def compute_backend_comparisons(
    python_metrics: list[BenchmarkMetric],
    rust_metrics: list[BenchmarkMetric],
    *,
    rust_backend_status: str = "native",
) -> list[BackendComparisonRow]:
    """Compute side-by-side throughput, wall-clock latency, and memory deltas (Rust vs. Python)."""
    py_map = {m.tier: m for m in python_metrics}
    rows: list[BackendComparisonRow] = []

    for rust_m in rust_metrics:
        py_m = py_map.get(rust_m.tier)
        if py_m is None:
            continue

        duration_speedup = (
            py_m.duration_seconds / rust_m.duration_seconds if rust_m.duration_seconds > 0 else 0.0
        )
        throughput_speedup = rust_m.files_per_sec / py_m.files_per_sec if py_m.files_per_sec > 0 else 0.0
        rows.append(
            BackendComparisonRow(
                tier=rust_m.tier,
                files_count=rust_m.files_count,
                dirs_count=rust_m.dirs_count,
                rust_backend_status=rust_backend_status,
                python_duration_seconds=py_m.duration_seconds,
                rust_duration_seconds=rust_m.duration_seconds,
                duration_speedup=duration_speedup,
                python_files_per_sec=py_m.files_per_sec,
                rust_files_per_sec=rust_m.files_per_sec,
                throughput_speedup=throughput_speedup,
                python_first_file_latency_ms=py_m.first_file_latency_ms,
                rust_first_file_latency_ms=rust_m.first_file_latency_ms,
                latency_delta_ms=rust_m.first_file_latency_ms - py_m.first_file_latency_ms,
                python_peak_memory_mb=py_m.peak_memory_mb,
                rust_peak_memory_mb=rust_m.peak_memory_mb,
                peak_memory_delta_mb=rust_m.peak_memory_mb - py_m.peak_memory_mb,
                python_peak_rss_mb=py_m.peak_rss_mb,
                rust_peak_rss_mb=rust_m.peak_rss_mb,
                peak_rss_delta_mb=rust_m.peak_rss_mb - py_m.peak_rss_mb,
                peak_rss_delta_pct=_pct_delta(py_m.peak_rss_mb, rust_m.peak_rss_mb),
            ),
        )

    return rows


def save_baseline_report(report: BenchmarkReport, file_path: Path) -> None:
    """Save benchmark report to a JSON baseline file."""
    file_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")


def load_baseline_report(file_path: Path) -> list[BenchmarkMetric]:
    """Load baseline metrics from a JSON baseline file."""
    data = json.loads(file_path.read_text(encoding="utf-8"))
    metrics: list[BenchmarkMetric] = []
    for item in data.get("metrics", []):
        item.setdefault("peak_rss_mb", 0.0)
        item.setdefault("backend", "python")
        metrics.append(BenchmarkMetric(**item))

    return metrics
