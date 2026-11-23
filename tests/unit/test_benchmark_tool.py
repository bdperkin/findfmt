"""Unit tests for tools/benchmark.py Rust vs. Python comparison mode (#586)."""

from __future__ import annotations

import io
import json
import runpy
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console
from tools.benchmark import (
    VALID_BACKENDS,
    BackendUnavailableError,
    BenchmarkMetric,
    build_parser,
    compute_backend_comparisons,
    is_native_rust_find_available,
    main,
    measure_traversal,
    render_backend_comparison_table,
    resolve_find_files_backend,
    run_compare_mode,
)
from tools.benchmark_backends import ALL_FORMATS, _measure_scenario_subprocess

from findfmt import _fallback, core

if TYPE_CHECKING:
    from collections.abc import Iterator

    from findfmt.models import FileInfo, TraversalConfig


class _FakeRustExt(ModuleType):
    """Typed fake findfmt._rust_ext module exposing a callable find_files entrypoint."""

    def find_files(self, config: TraversalConfig) -> Iterator[FileInfo]:
        return _fallback.find_files(config)


def test_parser_backend_choices() -> None:
    """Verify --backend supports auto, rust, python, and compare with auto default."""
    parser = build_parser()
    assert VALID_BACKENDS == ("auto", "rust", "python", "compare")
    assert parser.parse_args([]).backend == "auto"
    for choice in VALID_BACKENDS:
        assert parser.parse_args(["--backend", choice]).backend == choice

    with pytest.raises(SystemExit):
        parser.parse_args(["--backend", "invalid"])


def test_resolve_find_files_backend_variants(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify backend resolution for python, auto, unavailable rust, active rust, and invalid input."""
    (tmp_path / "mod.py").write_text("x = 1\n", encoding="utf-8")

    label_py, fn_py = resolve_find_files_backend("python")
    assert label_py == "python"
    assert fn_py is _fallback.find_files

    label_auto, fn_auto = resolve_find_files_backend("auto")
    assert label_auto in {"python", "rust"}
    assert fn_auto is core.find_files

    with pytest.raises(ValueError, match="Unsupported benchmark backend"):
        resolve_find_files_backend("bogus")

    # Disabled via FINDFMT_NO_EXTENSIONS=1 -> rust unavailable
    monkeypatch.setenv("FINDFMT_NO_EXTENSIONS", "1")
    assert is_native_rust_find_available() is False
    with pytest.raises(BackendUnavailableError, match="unavailable or disabled"):
        resolve_find_files_backend("rust")

    err_buf = io.StringIO()
    with patch("sys.stderr", err_buf):
        assert main(["--backend", "rust", "--target-dir", str(tmp_path)]) == 1

    assert "Error:" in err_buf.getvalue()

    # ImportError fallback in _load_rust_find when extension reports loaded
    monkeypatch.delenv("FINDFMT_NO_EXTENSIONS", raising=False)
    with (
        patch.object(core, "is_rust_extension_loaded", return_value=True),
        patch("tools.benchmark_backends.importlib.import_module", side_effect=ImportError("no ext")),
    ):
        assert is_native_rust_find_available() is False

    # Simulated active native findfmt._rust_ext.find_files
    fake_ext = _FakeRustExt("findfmt._rust_ext")
    with (
        patch.object(core, "is_rust_extension_loaded", return_value=True),
        patch("tools.benchmark_backends.importlib.import_module", return_value=fake_ext),
    ):
        assert is_native_rust_find_available() is True
        label_rs, fn_rs = resolve_find_files_backend("rust")
        assert label_rs == "rust"
        assert callable(fn_rs)
        metric = measure_traversal(tmp_path, "small", backend="rust")
        assert metric.backend == "rust"
        assert metric.files_count == 1


def test_compute_and_render_backend_comparisons() -> None:
    """Verify speedup multipliers, memory deltas, zero-division guards, and Rich table rendering."""
    py_metrics = [
        BenchmarkMetric("small", "/p", 100, 10, 0.20, 500.0, 50.0, 2.0, 2097152, 2.0, 40.0, "python"),
        BenchmarkMetric("zero", "/z", 0, 0, 0.0, 0.0, 0.0, 0.0, 0, 0.0, 0.0, "python"),
    ]
    rs_metrics = [
        BenchmarkMetric("small", "/p", 100, 10, 0.05, 2000.0, 200.0, 0.5, 1048576, 1.0, 25.0, "rust"),
        BenchmarkMetric("zero", "/z", 0, 0, 0.0, 0.0, 0.0, 0.0, 0, 0.0, 0.0, "rust"),
        BenchmarkMetric("unmatched", "/u", 5, 1, 0.01, 500.0, 100.0, 0.2, 512, 0.1, 10.0, "rust"),
    ]

    rows = compute_backend_comparisons(py_metrics, rs_metrics, rust_backend_status="native")
    assert len(rows) == 2
    small = rows[0]
    assert small.tier == "small"
    assert small.duration_speedup == pytest.approx(4.0)
    assert small.throughput_speedup == pytest.approx(4.0)
    assert small.latency_delta_ms == pytest.approx(-1.5)
    assert small.peak_memory_delta_mb == pytest.approx(-1.0)
    assert small.peak_rss_delta_mb == pytest.approx(-15.0)
    assert small.peak_rss_delta_pct == pytest.approx(-37.5)

    zero = rows[1]
    assert zero.duration_speedup == 0.0
    assert zero.throughput_speedup == 0.0
    assert zero.peak_rss_delta_pct == 0.0

    # Render both native and fallback status tables (including slower <1.0x row)
    slower_py = [BenchmarkMetric("slow", "/s", 10, 1, 0.01, 1000.0, 100.0, 0.5, 512, 0.5, 20.0, "python")]
    slower_rs = [BenchmarkMetric("slow", "/s", 10, 1, 0.02, 500.0, 50.0, 1.0, 1024, 1.0, 25.0, "rust")]
    slower_rows = compute_backend_comparisons(slower_py, slower_rs, rust_backend_status="fallback")

    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, width=140)
    render_backend_comparison_table(rows, console=console, rust_backend_status="native")
    render_backend_comparison_table(slower_rows, console=console, rust_backend_status="fallback")
    rendered = buf.getvalue()
    assert "findfmt Rust vs. Python Backend Comparison" in rendered
    assert "findfmt Rust (fallback) vs. Python Backend Comparison" in rendered
    assert "4.00x" in rendered
    assert "0.50x" in rendered
    assert "N/A" in rendered


def test_compare_mode_end_to_end_cli_and_json(tmp_path: Path) -> None:
    """Verify --backend compare runs isolated subprocesses and emits Rich table and JSON reports."""
    # 1. Terminal table mode on synthetic small tree
    out_table = io.StringIO()
    err_table = io.StringIO()
    with patch("sys.stdout", out_table), patch("sys.stderr", err_table):
        rc = main(["--backend", "compare", "--tier", "small", "--files", "6"])

    assert rc == 0
    assert "Backend Comparison" in out_table.getvalue()
    assert "small" in out_table.getvalue()

    # 2. JSON stdout + --output file mode on explicit --target-dir with tags & format
    sample_dir = tmp_path / "sample"
    sample_dir.mkdir()
    (sample_dir / "app.py").write_text("print('bench')\n", encoding="utf-8")
    out_json_file = tmp_path / "compare_report.json"
    out_json_stdout = io.StringIO()
    err_json = io.StringIO()
    with patch("sys.stdout", out_json_stdout), patch("sys.stderr", err_json):
        rc_json = main(
            [
                "--backend",
                "compare",
                "--target-dir",
                str(sample_dir),
                "--format",
                "text",
                "--list-tags",
                "--tag",
                "python",
                "--json",
                "--output",
                str(out_json_file),
            ],
        )

    assert rc_json == 0
    assert out_json_file.is_file()
    payload = json.loads(out_json_stdout.getvalue())
    assert payload == json.loads(out_json_file.read_text(encoding="utf-8"))
    assert payload["measured_in"] == "subprocess"
    assert payload["rust_backend_status"] in {"native", "fallback"}
    assert len(payload["python_metrics"]) == 1
    assert len(payload["rust_metrics"]) == 1
    assert len(payload["comparisons"]) == 1
    comp = payload["comparisons"][0]
    assert comp["tier"] == "custom"
    assert comp["files_count"] == 1
    assert comp["throughput_speedup"] > 0.0
    assert comp["duration_speedup"] > 0.0
    assert "peak_rss_delta_mb" in comp


def test_compare_mode_error_paths_and_output_variants(tmp_path: Path) -> None:
    """Verify missing target-dir, output variants, and subprocess error handling."""
    # Missing target-dir returns 1
    err_missing = io.StringIO()
    with patch("sys.stderr", err_missing):
        assert main(["--backend", "compare", "--target-dir", str(tmp_path / "nope")]) == 1

    assert "does not exist" in err_missing.getvalue()

    parser = build_parser()
    fake_metric = BenchmarkMetric("custom", "/p", 4, 1, 0.01, 400.0, 100.0, 0.5, 512, 0.5, 20.0, "python")
    ok_proc = subprocess.CompletedProcess(
        args=["cmd"],
        returncode=0,
        stdout=json.dumps({"metrics": [fake_metric.to_dict()]}),
        stderr="",
    )
    args_native = parser.parse_args(["--backend", "compare", "--tier", "small", "--files", "4"])
    with (
        patch("tools.benchmark_backends.is_native_rust_find_available", return_value=True),
        patch("tools.benchmark_backends.subprocess.run", return_value=ok_proc),
    ):
        report = run_compare_mode(args_native)

    assert report is not None
    assert report.rust_backend_status == "native"

    # Output-only and JSON-only branches for compare mode
    only_out = tmp_path / "only_out.json"
    with patch.dict(main.__globals__, {"run_compare_mode": MagicMock(return_value=report)}):
        assert main(["--backend", "compare", "--output", str(only_out)]) == 0
        assert only_out.is_file()
        json_buf = io.StringIO()
        with patch("sys.stdout", json_buf):
            assert main(["--backend", "compare", "--json"]) == 0

        assert json.loads(json_buf.getvalue())["rust_backend_status"] == "native"

    # Subprocess non-zero exit code and malformed JSON handling
    args_sub = parser.parse_args(["--backend", "compare", "--files", "2"])
    bad_proc = subprocess.CompletedProcess(args=["cmd"], returncode=1, stdout="", stderr="boom")
    with (
        patch("tools.benchmark_backends.subprocess.run", return_value=bad_proc),
        pytest.raises(RuntimeError, match="Subprocess benchmark failed"),
    ):
        _measure_scenario_subprocess(tmp_path, "python", ("traversal", "small"), "python", args_sub)

    bad_json_proc = subprocess.CompletedProcess(args=["cmd"], returncode=0, stdout="{bad", stderr="")
    with (
        patch("tools.benchmark_backends.subprocess.run", return_value=bad_json_proc),
        pytest.raises(RuntimeError, match="Invalid JSON output"),
    ):
        _measure_scenario_subprocess(tmp_path, "python", ("traversal", "small"), "python", args_sub)

    err_sub = io.StringIO()
    with (
        patch.dict(main.__globals__, {"run_compare_mode": MagicMock(side_effect=RuntimeError("sub crash"))}),
        patch("sys.stderr", err_sub),
    ):
        assert main(["--backend", "compare", "--files", "2"]) == 1

    assert "sub crash" in err_sub.getvalue()


def test_compare_mode_rejects_baseline_and_isolates_formats(tmp_path: Path) -> None:
    """Verify baseline option rejection (exit 2) and per-format subprocess RSS isolation."""
    for bad_flag in (
        ["--save-baseline", str(tmp_path / "b.json")],
        ["--baseline", str(tmp_path / "b.json")],
        ["--threshold", "5.0"],
    ):
        err_base = io.StringIO()
        mock_run = MagicMock()
        with patch.dict(main.__globals__, {"run_compare_mode": mock_run}), patch("sys.stderr", err_base):
            assert main(["--backend", "compare", *bad_flag]) == 2
            mock_run.assert_not_called()

        assert "not supported with --backend compare" in err_base.getvalue()

    parser = build_parser()
    fake_metric = BenchmarkMetric("custom", "/p", 2, 1, 0.01, 200.0, 100.0, 0.5, 512, 0.5, 20.0, "python")
    ok_proc = subprocess.CompletedProcess(
        args=["cmd"],
        returncode=0,
        stdout=json.dumps({"metrics": [fake_metric.to_dict()]}),
        stderr="",
    )
    args_all_fmt = parser.parse_args(
        ["--backend", "compare", "--tier", "small", "--format", "all", "--files", "2"],
    )
    with (
        patch("tools.benchmark_backends.is_native_rust_find_available", return_value=True),
        patch("tools.benchmark_backends.subprocess.run", return_value=ok_proc) as mock_sub,
    ):
        all_fmt_report = run_compare_mode(args_all_fmt)

    assert all_fmt_report is not None
    assert mock_sub.call_count == 2 * len(ALL_FORMATS)
    invoked_cmds = [c.args[0] for c in mock_sub.call_args_list]
    assert len({cmd[cmd.index("--target-dir") + 1] for cmd in invoked_cmds}) == 1
    assert {cmd[cmd.index("--format") + 1] for cmd in invoked_cmds} == set(ALL_FORMATS)


def test_benchmark_script_bootstrap_and_empty_stream(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify empty streaming formatter latency and direct script sys.path bootstrap."""
    empty_dir = tmp_path / "empty_fmt"
    empty_dir.mkdir()
    empty_metric = measure_traversal(empty_dir, "empty_text", output_format="text")
    assert empty_metric.files_count == 0
    assert empty_metric.first_file_latency_ms == 0.0

    bench_script = Path(__file__).resolve().parents[2] / "tools" / "benchmark.py"
    repo_root_resolved = bench_script.parent.parent.resolve()
    monkeypatch.setattr(sys, "argv", ["benchmark.py", "--target-dir", str(empty_dir)])
    monkeypatch.setattr(
        sys,
        "path",
        [p for p in sys.path if Path(p).resolve() != repo_root_resolved],
    )
    monkeypatch.delitem(sys.modules, "tools", raising=False)
    monkeypatch.delitem(sys.modules, "tools.benchmark_backends", raising=False)
    with patch("sys.stdout", io.StringIO()), pytest.raises(SystemExit) as exc_info:
        runpy.run_path(str(bench_script), run_name="__main__")

    assert exc_info.value.code == 0
