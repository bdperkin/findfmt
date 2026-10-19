"""Unit tests for tools/benchmark_topologies.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from tools.benchmark_topologies import (
    count_directories,
    generate_synthetic_tree,
)


def test_count_directories(tmp_path: Path):
    """Test counting directories recursively."""
    assert count_directories(tmp_path) == 0
    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "c").mkdir()
    assert count_directories(tmp_path) == 3


def test_generate_synthetic_tree(tmp_path: Path):
    """Test synthetic directory tree generation and file template coverage."""
    files_created, dirs_created = generate_synthetic_tree(tmp_path, target_files=30, seed=42)
    assert files_created >= 30
    assert dirs_created > 0
    assert (tmp_path / ".gitignore").exists()
    assert (tmp_path / "scripts" / "worker").exists()
    assert (tmp_path / "scripts" / "deploy").exists()

    # Test chmod failure tolerance
    with patch("pathlib.Path.chmod", side_effect=OSError("Permission denied")):
        f2, _ = generate_synthetic_tree(tmp_path / "sub", target_files=5, seed=1)
        assert f2 >= 5


def test_generate_synthetic_tree_topologies(tmp_path: Path):
    """Verify tree generation across flat, deep, and real-world topologies."""
    # 1. Flat topology
    flat_root = tmp_path / "flat"
    f_flat, d_flat = generate_synthetic_tree(flat_root, target_files=20, topology="flat")
    assert f_flat >= 20
    assert d_flat == 0
    assert (flat_root / ".gitignore").exists()

    # 2. Deep topology
    deep_root = tmp_path / "deep"
    f_deep, d_deep = generate_synthetic_tree(deep_root, target_files=25, topology="deep")
    assert f_deep >= 25
    assert d_deep > 10
    assert (deep_root / ".gitignore").exists()

    # 3. Real-world topology
    rw_root = tmp_path / "real_world"
    f_rw, d_rw = generate_synthetic_tree(rw_root, target_files=30, topology="real-world")
    assert f_rw >= 30
    assert d_rw > 5
    assert (rw_root / ".gitignore").exists()
    assert (rw_root / "packages" / "core" / "src").exists()
    assert (rw_root / "node_modules" / "pkg_a").exists()
