"""Regression test for ``tools/benchmark.py --keep-temp`` (#489)."""

from __future__ import annotations

import gc
import io
import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from tools.benchmark import BenchmarkMetric, _collect_metrics, build_parser, run_compare_mode


def test_collect_metrics_synthetic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """Test --keep-temp leaves the generated tree on disk and reports where it is (#489)."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    parser = build_parser()
    args = parser.parse_args(["--tier", "small", "--files", "10", "--keep-temp"])
    metrics, cleanups = _collect_metrics(args)
    gc.collect()  # a TemporaryDirectory finalizer would delete the tree here
    assert len(metrics) == 1
    assert metrics[0].tier == "small"
    assert len(cleanups) == 0  # keep-temp suppresses cleanup accumulation
    kept = sorted(tmp_path.glob("findfmt_bench_small_standard_*"))
    assert len(kept) == 1
    assert kept[0].is_dir()
    assert any(kept[0].rglob("*"))
    assert str(kept[0]) in capsys.readouterr().err


def test_compare_mode_keep_temp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify --keep-temp preserves the generated tree in --backend compare mode."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    parser = build_parser()
    args_keep = parser.parse_args(
        [
            "--backend",
            "compare",
            "--tier",
            "small",
            "--topology",
            "flat",
            "--format",
            "json",
            "--files",
            "4",
            "--keep-temp",
        ],
    )
    fake_metric = BenchmarkMetric("custom", "/p", 4, 1, 0.01, 400.0, 100.0, 0.5, 512, 0.5, 20.0, "python")
    ok_proc = subprocess.CompletedProcess(
        args=["cmd"],
        returncode=0,
        stdout=json.dumps({"metrics": [fake_metric.to_dict()]}),
        stderr="",
    )
    with (
        patch("tools.benchmark_backends.is_native_rust_find_available", return_value=True),
        patch("tools.benchmark_backends.subprocess.run", return_value=ok_proc),
        patch("sys.stderr", io.StringIO()) as err_keep,
    ):
        report = run_compare_mode(args_keep)

    gc.collect()
    assert report is not None
    assert report.rust_backend_status == "native"
    assert report.comparisons[0].tier == "small flat json"
    assert "Keeping benchmark tree:" in err_keep.getvalue()
    assert len(list(tmp_path.glob("findfmt_bench_small_flat_*"))) == 1
