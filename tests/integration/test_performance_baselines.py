"""Integration tests verifying performance baselines, memory bounds, and streaming efficiency."""

from __future__ import annotations

import time
import tracemalloc
from collections.abc import Iterator
from pathlib import Path

from tools.benchmark import (
    BenchmarkMetric,
    _NullSink,
    compute_comparisons,
    generate_synthetic_tree,
    load_baseline_report,
    measure_traversal,
)

from findfmt.formatters import (
    CsvFormatter,
    JsonFormatter,
    JsonlFormatter,
    TextFormatter,
    TsvFormatter,
)
from findfmt.models import FileInfo, TraversalConfig
from findfmt.traversal.engine import find_files


def _generate_synthetic_file_infos(count: int) -> Iterator[FileInfo]:
    """Generate a lazy stream of FileInfo instances without buffering."""
    base = Path("/app/project")
    for idx in range(count):
        rel = Path(f"src/module_{idx // 100}/file_{idx:05d}.py")
        yield FileInfo(
            path=base / rel,
            relative_path=rel,
            tags=frozenset(["python", "source", "text"]),
            mime_type="text/x-python",
            is_executable=False,
            is_symlink=False,
            size_bytes=1024,
        )


def test_streaming_formatters_maintain_bounded_memory():
    """Verify streaming formatters maintain O(1) memory while buffering formatters scale."""
    count = 5000

    # 1. Measure peak heap for streaming formatters
    streaming_peaks: dict[str, float] = {}
    for name, fmt in (
        ("text", TextFormatter()),
        ("jsonl", JsonlFormatter()),
        ("tsv", TsvFormatter()),
        ("csv", CsvFormatter()),
    ):
        tracemalloc.start()
        sink = _NullSink()
        fmt.stream(_generate_synthetic_file_infos(count), sink)
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak_bytes / (1024.0 * 1024.0)
        streaming_peaks[name] = peak_mb
        # Streaming formatters should maintain bounded peak heap (< 5.0 MB for 5,000 files)
        assert peak_mb < 5.0, f"Formatter '{name}' peak memory exceeded ceiling: {peak_mb:.2f} MB"
        assert sink.write_count >= count

    # 2. Compare against buffered JsonFormatter which accumulates all items into a list
    tracemalloc.start()
    sink_json = _NullSink()
    JsonFormatter().stream(_generate_synthetic_file_infos(count), sink_json)
    _, json_peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    json_peak_mb = json_peak_bytes / (1024.0 * 1024.0)

    # JsonFormatter buffers all dicts, requiring significantly more memory than streaming
    assert json_peak_mb > max(streaming_peaks["text"], streaming_peaks["jsonl"])


def test_early_gitignore_pruning_bounds_memory_and_traversal_time(tmp_path: Path):
    """Verify early .gitignore pruning skips massive ignored directories in O(1) time."""
    # Create ignored directories with 3,000 dummy files
    (tmp_path / ".gitignore").write_text("node_modules/\n.venv/\nbuild/\n", encoding="utf-8")
    for ignored_name in ("node_modules/pkg_a", "node_modules/pkg_b", ".venv/lib", "build"):
        idir = tmp_path / ignored_name
        idir.mkdir(parents=True, exist_ok=True)
        for i in range(750):
            (idir / f"dep_{i:04d}.js").write_text("module.exports = {};\n", encoding="utf-8")

    # Create active source files (50 files)
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    for i in range(50):
        (src_dir / f"mod_{i:03d}.py").write_text(f"x = {i}\n", encoding="utf-8")

    config = TraversalConfig(root_paths=(tmp_path,), respect_gitignore=True)
    tracemalloc.start()
    t_start = time.perf_counter()
    matched_files = list(find_files(config))
    t_end = time.perf_counter()
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak_bytes / (1024.0 * 1024.0)
    duration = t_end - t_start

    # Only the 50 unignored source files should be returned
    assert len(matched_files) == 50
    # Directory pruning should complete rapidly (< 1.0s) without scanning 3,000 ignored files
    assert duration < 1.0
    # Peak heap memory should remain very small (< 1.5 MB)
    assert peak_mb < 1.5


def test_continuous_traversal_no_unbounded_memory_growth(tmp_path: Path):
    """Verify repeated continuous traversals do not leak heap memory across runs."""
    generate_synthetic_tree(tmp_path, target_files=200, seed=42)
    config = TraversalConfig(root_paths=(tmp_path,), respect_gitignore=True)

    # Warmup
    _ = list(find_files(config))

    peaks: list[int] = []
    for _ in range(5):
        tracemalloc.start()
        _ = list(find_files(config))
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peaks.append(peak)

    # The peak memory of the 5th run should not exceed the 1st run by more than 25%
    assert peaks[-1] <= peaks[0] * 1.25


def test_topology_baselines_execution(tmp_path: Path):
    """Verify performance harness executes across flat, deep, and real-world topologies."""
    # 1. Flat
    flat_root = tmp_path / "flat"
    f_flat, d_flat = generate_synthetic_tree(flat_root, target_files=50, topology="flat")
    m_flat = measure_traversal(flat_root, "flat_tier", total_dirs=d_flat)
    assert 0 < m_flat.files_count <= f_flat
    assert m_flat.files_per_sec > 0

    # 2. Deep
    deep_root = tmp_path / "deep"
    _, d_deep = generate_synthetic_tree(deep_root, target_files=50, topology="deep")
    m_deep = measure_traversal(deep_root, "deep_tier", total_dirs=d_deep)
    assert m_deep.files_count > 0
    assert m_deep.dirs_count == d_deep

    # 3. Real-world
    rw_root = tmp_path / "rw"
    _, d_rw = generate_synthetic_tree(rw_root, target_files=50, topology="real-world")
    m_rw = measure_traversal(rw_root, "rw_tier", total_dirs=d_rw)
    assert m_rw.files_count > 0
    assert m_rw.peak_memory_mb > 0


def test_regression_gate_threshold_detection():
    """Verify threshold comparison logic triggers regression warnings appropriately."""
    base = [BenchmarkMetric("small", "/p", 100, 10, 0.1, 1000.0, 100.0, 10.0, 1000, 1.0)]
    curr_ok = [BenchmarkMetric("small", "/p", 100, 10, 0.1, 950.0, 100.0, 10.0, 1000, 1.0)]
    curr_regressed = [BenchmarkMetric("small", "/p", 100, 10, 0.1, 800.0, 100.0, 10.0, 1000, 1.0)]

    # 10% threshold: 5% drop is ok, 20% drop is regressed
    rows_ok = compute_comparisons(base, curr_ok, threshold_pct=10.0)
    assert not rows_ok[0].regressed

    rows_bad = compute_comparisons(base, curr_regressed, threshold_pct=10.0)
    assert rows_bad[0].regressed


def test_canonical_v1_baseline_fixture_loads():
    """Verify the canonical v1.0.0 baseline fixture loads and computes valid comparisons."""
    baseline_path = Path(__file__).parent.parent / "fixtures" / "v1_baseline.json"
    assert baseline_path.exists()
    metrics = load_baseline_report(baseline_path)
    assert len(metrics) == 6
    tiers = {m.tier for m in metrics}
    assert "small" in tiers
    assert "medium" in tiers
    assert "flat" in tiers
    assert "deep" in tiers
    assert "real-world" in tiers
    assert "findfmt-repo" in tiers

    # Compare with itself -> all deltas 0.0, no regression
    comparisons = compute_comparisons(metrics, metrics, threshold_pct=10.0)
    assert len(comparisons) == 6
    for c in comparisons:
        assert not c.regressed
        assert c.throughput_delta_pct == 0.0


def test_prune_runs_in_linear_time_on_deep_tree(tmp_path: Path):
    """Verify --prune runs in linear time on a deep tree without quadratic rescanning."""
    depth = 25
    curr = tmp_path
    for i in range(depth):
        curr = curr / f"level_{i:02d}"
        curr.mkdir()

    (curr / "leaf.py").write_text("print('leaf')\n", encoding="utf-8")

    config = TraversalConfig(
        root_paths=(tmp_path,),
        dirs_only=True,
        prune_empty=True,
        include_tags=frozenset({"python"}),
    )

    t0 = time.perf_counter()
    results = list(find_files(config))
    duration = time.perf_counter() - t0

    assert len(results) == depth
    # Pruning on a 25-deep directory tree should complete in well under 1 second with memoization
    assert duration < 1.0
