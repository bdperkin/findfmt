"""Unit tests for tools/benchmark.py performance benchmarking harness."""

from __future__ import annotations

import io
import json
import runpy
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from rich.console import Console
from tools.benchmark import (
    DEFAULT_SEED,
    BenchmarkMetric,
    BenchmarkReport,
    ComparisonRow,
    _collect_metrics,
    _handle_output,
    _NullSink,
    _run_single_traversal,
    build_parser,
    compute_comparisons,
    get_peak_rss_mb,
    load_baseline_report,
    main,
    measure_traversal,
    render_comparison_table,
    render_metrics_table,
    save_baseline_report,
)


def test_data_model_conversions():
    """Verify serialization methods for BenchmarkMetric, BenchmarkReport, and ComparisonRow."""
    metric = BenchmarkMetric(
        tier="small",
        target_path="/tmp/test",
        files_count=10,
        dirs_count=2,
        duration_seconds=0.05,
        files_per_sec=200.0,
        dirs_per_sec=40.0,
        first_file_latency_ms=1.5,
        peak_memory_bytes=1048576,
        peak_memory_mb=1.0,
    )
    metric_dict = metric.to_dict()
    assert metric_dict["tier"] == "small"
    assert metric_dict["files_count"] == 10

    report = BenchmarkReport(
        timestamp="2026-10-14T00:00:00Z",
        findfmt_version="0.5.1",
        python_version="3.13.0",
        platform="Linux-x86_64",
        seed=42,
        metrics=[metric],
    )
    report_dict = report.to_dict()
    assert report_dict["findfmt_version"] == "0.5.1"
    assert len(report_dict["metrics"]) == 1

    row = ComparisonRow(
        tier="small",
        baseline_files_per_sec=180.0,
        current_files_per_sec=200.0,
        throughput_delta_pct=11.11,
        baseline_latency_ms=2.0,
        current_latency_ms=1.5,
        latency_delta_pct=-25.0,
        baseline_memory_mb=1.2,
        current_memory_mb=1.0,
        memory_delta_pct=-16.67,
        regressed=False,
    )
    row_dict = row.to_dict()
    assert row_dict["regressed"] is False
    assert row_dict["throughput_delta_pct"] == 11.11


def test_run_single_traversal_empty_and_populated(tmp_path: Path):
    """Test single traversal execution with and without files."""
    # Empty dir
    metric_empty = _run_single_traversal(tmp_path, "empty", total_dirs=0)
    assert metric_empty.files_count == 0
    assert metric_empty.first_file_latency_ms == 0.0

    # Populated dir
    (tmp_path / "test.py").write_text("print('hi')\n")
    metric_pop = _run_single_traversal(tmp_path, "pop", tag_filter="python", total_dirs=1)
    assert metric_pop.files_count == 1
    assert metric_pop.first_file_latency_ms >= 0.0
    assert metric_pop.files_per_sec > 0.0


def test_measure_traversal_warmup_and_runs(tmp_path: Path):
    """Test measure_traversal multi-run averaging and warmup iterations."""
    (tmp_path / "sample.py").write_text("x = 1\n")
    metric = measure_traversal(tmp_path, "bench", runs=2, warmup=1, total_dirs=None)
    assert metric.tier == "bench"
    assert metric.files_count == 1
    assert metric.duration_seconds > 0


def test_compute_comparisons():
    """Verify comparison deltas and regression detection."""
    base = [
        BenchmarkMetric("small", "/p1", 100, 10, 0.1, 1000.0, 100.0, 10.0, 1000, 1.0),
        BenchmarkMetric("zeros", "/p2", 0, 0, 0.0, 0.0, 0.0, 0.0, 0, 0.0),
    ]
    curr = [
        BenchmarkMetric("small", "/p1", 100, 10, 0.1, 800.0, 100.0, 12.0, 1200, 1.2),
        BenchmarkMetric("zeros", "/p2", 0, 0, 0.0, 0.0, 0.0, 0.0, 0, 0.0),
        BenchmarkMetric("unknown", "/p3", 10, 1, 0.01, 100.0, 10.0, 1.0, 100, 0.1),
    ]

    # Without threshold
    rows = compute_comparisons(base, curr, threshold_pct=None)
    assert len(rows) == 2
    r_small = rows[0]
    assert r_small.tier == "small"
    assert r_small.throughput_delta_pct == -20.0
    assert r_small.regressed is False

    r_zeros = rows[1]
    assert r_zeros.throughput_delta_pct == 0.0
    assert r_zeros.latency_delta_pct == 0.0
    assert r_zeros.memory_delta_pct == 0.0

    # With threshold 15% (small regressed by 20%, so regressed=True)
    rows_thresh = compute_comparisons(base, curr, threshold_pct=15.0)
    assert rows_thresh[0].regressed is True

    # With threshold 25% (20% is within 25%, so regressed=False)
    rows_thresh2 = compute_comparisons(base, curr, threshold_pct=25.0)
    assert rows_thresh2[0].regressed is False


def test_baseline_save_and_load(tmp_path: Path):
    """Test saving and loading baseline JSON reports."""
    metric = BenchmarkMetric("small", "/t", 50, 5, 0.05, 1000.0, 100.0, 2.0, 1024, 0.5)
    report = BenchmarkReport(
        timestamp="2026-10-14T00:00:00Z",
        findfmt_version="0.5.1",
        python_version="3.13.0",
        platform="Linux-x86_64",
        seed=DEFAULT_SEED,
        metrics=[metric],
    )
    baseline_file = tmp_path / "baseline.json"
    save_baseline_report(report, baseline_file)
    assert baseline_file.exists()

    loaded_metrics = load_baseline_report(baseline_file)
    assert len(loaded_metrics) == 1
    assert loaded_metrics[0].tier == "small"
    assert loaded_metrics[0].files_per_sec == 1000.0


def test_render_tables():
    """Test console table rendering for metrics and comparisons."""
    metric = BenchmarkMetric("small", "/p", 10, 2, 0.01, 1000.0, 200.0, 1.5, 512, 0.5)
    row_pos = ComparisonRow(
        "small",
        900.0,
        1000.0,
        11.1,
        2.0,
        1.5,
        -25.0,
        0.6,
        0.5,
        -16.7,
        regressed=False,
    )
    row_neg = ComparisonRow(
        "med",
        1200.0,
        1000.0,
        -16.7,
        1.0,
        2.0,
        100.0,
        0.5,
        0.7,
        40.0,
        regressed=True,
    )

    str_io = io.StringIO()
    console = Console(file=str_io, force_terminal=False)
    render_metrics_table([metric], console=console)
    render_comparison_table([row_pos, row_neg], console=console)

    output = str_io.getvalue()
    assert "findfmt Traversal Performance Benchmarks" in output
    assert "findfmt Performance Baseline Comparison" in output
    assert "small" in output


def test_build_parser():
    """Verify CLI parser construction and argument defaults."""
    parser = build_parser()
    args = parser.parse_args(["--tier", "medium", "--runs", "3", "--threshold", "10.0"])
    assert args.tier == "medium"
    assert args.runs == 3
    assert args.threshold == 10.0
    assert args.seed == DEFAULT_SEED


def test_collect_metrics_synthetic():
    """Test metric collection for synthetic datasets."""
    parser = build_parser()
    args = parser.parse_args(["--tier", "small", "--files", "10", "--keep-temp"])
    metrics, cleanups = _collect_metrics(args)
    assert len(metrics) == 1
    assert metrics[0].tier == "small"
    assert len(cleanups) == 0  # keep-temp suppresses cleanup accumulation


def test_collect_metrics_target_dir(tmp_path: Path):
    """Test metric collection against an existing and nonexistent target directory."""
    parser = build_parser()

    # Nonexistent
    args_bad = parser.parse_args(["--target-dir", str(tmp_path / "nonexistent")])
    m_bad, _ = _collect_metrics(args_bad)
    assert len(m_bad) == 0

    # Exists
    (tmp_path / "file.py").write_text("print(1)\n")
    args_good = parser.parse_args(["--target-dir", str(tmp_path)])
    m_good, _ = _collect_metrics(args_good)
    assert len(m_good) == 1
    assert m_good[0].tier == "custom"


def test_collect_metrics_all_tiers():
    """Test metric collection for all tiers with small file count."""
    parser = build_parser()
    args = parser.parse_args(["--tier", "all", "--files", "5"])
    metrics, cleanups = _collect_metrics(args)
    assert len(metrics) == 3
    assert [m.tier for m in metrics] == ["small", "medium", "monorepo"]
    for td in cleanups:
        td.cleanup()


def test_handle_output_json_and_file(tmp_path: Path):
    """Test JSON output formatting to stdout and output file."""
    metric = BenchmarkMetric("small", "/p", 5, 1, 0.01, 500.0, 100.0, 1.0, 1024, 0.1)
    report = BenchmarkReport("2026-10-14T00:00:00Z", "0.5.1", "3.13.0", "Linux", 42, [metric])
    row = ComparisonRow("small", 500.0, 500.0, 0.0, 1.0, 1.0, 0.0, 0.1, 0.1, 0.0, regressed=False)

    out_file = tmp_path / "out.json"
    parser = build_parser()

    # 1. Output file only (no --json)
    args_file_only = parser.parse_args(["--output", str(out_file)])
    _handle_output(report, [row], args_file_only)
    assert out_file.exists()

    # 2. JSON stdout only (no --output, no comparisons)
    args_json_only = parser.parse_args(["--json"])
    cap_json = io.StringIO()
    with patch("sys.stdout", cap_json):
        _handle_output(report, [], args_json_only)

    stdout_content = json.loads(cap_json.getvalue())
    assert stdout_content["findfmt_version"] == "0.5.1"
    assert "comparisons" not in stdout_content

    # 3. Terminal rendering without comparisons
    args_default = parser.parse_args([])
    cap_table = io.StringIO()
    with patch("sys.stdout", cap_table):
        _handle_output(report, [], args_default)
        _handle_output(report, [row], args_default)


def test_main_cli_flows(tmp_path: Path):
    """Test full CLI main entry point execution flows."""
    # 1. Nonexistent target directory returns 1
    ret = main(["--target-dir", str(tmp_path / "does_not_exist")])
    assert ret == 1

    # 2. Synthetic small run with --json
    captured = io.StringIO()
    with patch("sys.stdout", captured):
        ret = main(["--tier", "small", "--files", "10", "--json"])

    assert ret == 0
    assert '"tier": "small"' in captured.getvalue()

    # 3. Save baseline
    base_file = tmp_path / "base.json"
    ret = main(["--tier", "small", "--files", "10", "--save-baseline", str(base_file)])
    assert ret == 0
    assert base_file.exists()

    # 4. Compare with missing baseline file returns 1
    ret = main(["--tier", "small", "--files", "10", "--baseline", str(tmp_path / "missing.json")])
    assert ret == 1

    # 5. Compare with baseline and no regression returns 0
    ret = main(
        [
            "--tier",
            "small",
            "--files",
            "10",
            "--baseline",
            str(base_file),
            "--threshold",
            "99.9",
        ],
    )
    assert ret == 0

    # 6. Compare with baseline and forced regression
    fast_base = BenchmarkReport(
        "2026-10-14T00:00:00Z",
        "0.5.1",
        "3.13.0",
        "Linux",
        42,
        [
            BenchmarkMetric(
                "small",
                "/p",
                100,
                10,
                0.0001,
                10000000.0,
                1000000.0,
                0.01,
                1024,
                0.1,
            ),
        ],
    )
    save_baseline_report(fast_base, base_file)
    ret = main(
        [
            "--tier",
            "small",
            "--files",
            "10",
            "--baseline",
            str(base_file),
            "--threshold",
            "5.0",
        ],
    )
    assert ret == 1


def test_main_dunder_main():
    """Verify execution via python -m tools.benchmark."""
    sys.modules.pop("tools.benchmark", None)
    with (
        patch.object(sys, "argv", ["benchmark", "--tier", "small", "--files", "5"]),
        patch("sys.exit") as mock_exit,
    ):
        runpy.run_module("tools.benchmark", run_name="__main__")
        mock_exit.assert_called_with(0)


def test_null_sink():
    """Verify _NullSink discard semantics and latency tracking."""
    sink = _NullSink()
    assert sink.first_write_time is None
    assert sink.write_count == 0

    assert sink.write("") == 0
    assert sink.first_write_time is None
    assert sink.write_count == 1

    assert sink.write("sample line\n") == len("sample line\n")
    assert sink.first_write_time is not None
    assert sink.write_count == 2

    first_time = sink.first_write_time
    sink.writelines(["line 1\n", "line 2\n"])
    assert sink.write_count == 4
    assert sink.first_write_time == first_time


def test_get_peak_rss_mb():
    """Verify RSS extraction across Linux, macOS, Windows, and error handling."""
    # When resource is None
    with patch.dict(get_peak_rss_mb.__globals__, {"resource": None}):
        assert get_peak_rss_mb() == 0.0

    mock_res = MagicMock()
    mock_res.RUSAGE_SELF = 0
    mock_res.getrusage.return_value.ru_maxrss = 102400.0

    # Linux platform simulation (divided by 1024)
    with (
        patch.dict(get_peak_rss_mb.__globals__, {"resource": mock_res}),
        patch("sys.platform", "linux"),
    ):
        assert get_peak_rss_mb() == 100.0

    # macOS platform simulation (divided by 1024^2)
    with (
        patch.dict(get_peak_rss_mb.__globals__, {"resource": mock_res}),
        patch("sys.platform", "darwin"),
    ):
        assert round(get_peak_rss_mb(), 4) == round(102400.0 / (1024.0 * 1024.0), 4)

    # Exception tolerance (OSError)
    mock_err = MagicMock()
    mock_err.RUSAGE_SELF = 0
    mock_err.getrusage.side_effect = OSError("Resource error")
    with patch.dict(get_peak_rss_mb.__globals__, {"resource": mock_err}):
        assert get_peak_rss_mb() == 0.0

    # Exception tolerance (AttributeError)
    mock_attr_err = MagicMock()
    mock_attr_err.RUSAGE_SELF = 0
    mock_attr_err.getrusage.side_effect = AttributeError("No attribute")
    with patch.dict(get_peak_rss_mb.__globals__, {"resource": mock_attr_err}):
        assert get_peak_rss_mb() == 0.0

    # Real call on current platform
    assert get_peak_rss_mb() >= 0.0


def test_measure_traversal_formats_and_tags(tmp_path: Path):
    """Verify measurement with formatters and tag classification."""
    (tmp_path / "test.py").write_text("#!/usr/bin/env python3\nprint(1)\n")
    for fmt in ("text", "jsonl", "tsv", "csv", "json", "tree", "table"):
        metric = measure_traversal(
            tmp_path,
            f"test_{fmt}",
            runs=1,
            warmup=0,
            output_format=fmt,
            show_tags=True,
        )
        assert metric.files_count == 1
        assert metric.duration_seconds > 0


def test_baseline_load_backwards_compatible(tmp_path: Path):
    """Verify loading baseline reports that lack peak_rss_mb."""
    legacy_json = tmp_path / "legacy_baseline.json"
    legacy_json.write_text(
        json.dumps(
            {
                "timestamp": "2026-10-14T00:00:00Z",
                "findfmt_version": "0.5.1",
                "python_version": "3.13.0",
                "platform": "Linux-x86_64",
                "seed": 42,
                "metrics": [
                    {
                        "tier": "small",
                        "target_path": "/tmp/test",
                        "files_count": 10,
                        "dirs_count": 2,
                        "duration_seconds": 0.05,
                        "files_per_sec": 200.0,
                        "dirs_per_sec": 40.0,
                        "first_file_latency_ms": 1.5,
                        "peak_memory_bytes": 1048576,
                        "peak_memory_mb": 1.0,
                    },
                ],
            },
        ),
        encoding="utf-8",
    )
    metrics = load_baseline_report(legacy_json)
    assert len(metrics) == 1
    assert metrics[0].peak_rss_mb == 0.0


def test_collect_metrics_topologies_and_formats():
    """Test CLI metrics collection with topology=all and format=all."""
    parser = build_parser()
    args = parser.parse_args(
        ["--tier", "small", "--topology", "all", "--format", "all", "--files", "5"],
    )
    metrics, cleanups = _collect_metrics(args)
    # 4 topologies * 8 formats = 32 combinations
    assert len(metrics) == 32
    for td in cleanups:
        td.cleanup()
