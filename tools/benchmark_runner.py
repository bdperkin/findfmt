"""Core traversal measurement runner, RSS sampling, and null formatter sink."""

from __future__ import annotations

import io
import sys
import time
import tracemalloc
from typing import TYPE_CHECKING

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

from tools.benchmark_backends import resolve_find_files_backend
from tools.benchmark_models import BenchmarkMetric
from tools.benchmark_topologies import count_directories

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

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path
    from types import ModuleType

    from findfmt.models import FileInfo

resource: ModuleType | None
try:
    import resource
except ImportError:
    resource = None

__all__ = [
    "_NullSink",
    "_run_single_traversal",
    "get_peak_rss_mb",
    "measure_traversal",
]


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


def _run_single_traversal(  # noqa: PLR0913 - wide CLI/config signature
    target_path: Path,
    tier_name: str,
    *,
    tag_filter: str | None = None,
    total_dirs: int = 0,
    output_format: str = "traversal",
    show_tags: bool = False,
    backend: str = "auto",
) -> BenchmarkMetric:
    """Execute a single traversal measurement run against the requested backend."""
    backend_label, find_fn = resolve_find_files_backend(backend)
    config = TraversalConfig(
        root_paths=(target_path,),
        respect_gitignore=True,
        include_tags=frozenset(filter(None, [tag_filter])),
    )
    tracemalloc.start()
    start_time = time.perf_counter()
    first_latency: float | None = None
    files_count = 0

    if output_format == "traversal":
        for _ in find_fn(config):
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
            for item in find_fn(config):
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
        backend_label,
    )


def measure_traversal(  # noqa: PLR0913 - wide CLI/config signature
    target_path: Path,
    tier_name: str,
    *,
    runs: int = 1,
    warmup: int = 0,
    tag_filter: str | None = None,
    total_dirs: int | None = None,
    output_format: str = "traversal",
    show_tags: bool = False,
    backend: str = "auto",
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
            backend=backend,
        )

    results = [
        _run_single_traversal(
            target_path,
            tier_name,
            tag_filter=tag_filter,
            total_dirs=dirs_count,
            output_format=output_format,
            show_tags=show_tags,
            backend=backend,
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
        first.backend,
    )
