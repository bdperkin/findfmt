"""Regression test for ``tools/benchmark.py --keep-temp`` (#489)."""

from __future__ import annotations

import gc
import tempfile
from pathlib import Path

import pytest
from tools.benchmark import _collect_metrics, build_parser


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
