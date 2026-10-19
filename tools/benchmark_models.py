"""Data models, serialization, and comparison logic for findfmt benchmarks."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from pathlib import Path

__all__ = [
    "BenchmarkMetric",
    "BenchmarkReport",
    "ComparisonRow",
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
    metrics: list[BenchmarkMetric] = []
    for item in data.get("metrics", []):
        if "peak_rss_mb" not in item:
            item["peak_rss_mb"] = 0.0

        metrics.append(BenchmarkMetric(**item))

    return metrics
