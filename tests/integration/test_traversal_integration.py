"""Comprehensive integration tests for end-to-end traversal workflows."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_integration_traversal_boundaries_and_prune(tmp_path: Path) -> None:
    """Verify max depth, dirs only, and empty directory pruning via CLI subprocess."""
    deep_dir = tmp_path / "a" / "b" / "c"
    deep_dir.mkdir(parents=True)
    (deep_dir / "leaf.txt").write_text("leaf", encoding="utf-8")

    empty_dir = tmp_path / "a" / "empty"
    empty_dir.mkdir()

    # Max depth = 1 with dirs-only
    proc = subprocess.run(
        [sys.executable, "-m", "findfmt", str(tmp_path), "-d", "-L", "1"],
        capture_output=True,
        text=True,
        check=True,
    )
    stdout = proc.stdout.replace("\\", "/")
    assert "a" in stdout
    assert "a/b" not in stdout

    # Prune empty directory when filtering by .txt
    proc_prune = subprocess.run(
        [sys.executable, "-m", "findfmt", str(tmp_path), "--prune", "-P", "*.txt"],
        capture_output=True,
        text=True,
        check=True,
    )
    stdout_prune = proc_prune.stdout.replace("\\", "/")
    assert "empty" not in stdout_prune
    assert "leaf.txt" in stdout_prune


def test_integration_patterns_and_case_insensitivity(tmp_path: Path) -> None:
    """Verify glob inclusion, exclusion, and case-insensitivity combinations."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "Main.PY").write_text("print(1)", encoding="utf-8")
    (src_dir / "util.py").write_text("x = 1", encoding="utf-8")
    (src_dir / "notes.md").write_text("# doc", encoding="utf-8")
    (src_dir / "test.tmp").write_text("temp", encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "findfmt",
            str(tmp_path),
            "-P",
            "*.py|*.md",
            "-I",
            "*.tmp",
            "--ignore-case",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    stdout = proc.stdout.replace("\\", "/")
    assert "Main.PY" in stdout
    assert "util.py" in stdout
    assert "notes.md" in stdout
    assert "test.tmp" not in stdout


def test_integration_output_redirection_and_sorting(tmp_path: Path) -> None:
    """Verify direct file output redirection combined with structured sorting."""
    (tmp_path / "a.py").write_text("a", encoding="utf-8")
    (tmp_path / "b_large.py").write_text("bbbbbbbbbb", encoding="utf-8")
    out_file = tmp_path / "results.json"

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "findfmt",
            str(tmp_path),
            "-t",
            "python",
            "--sort",
            "size",
            "-f",
            "json",
            "-o",
            str(out_file),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.returncode == 0
    assert out_file.exists()

    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert len(data) == 2
    # Largest file first under size sorting
    assert "b_large.py" in data[0]["path"].replace("\\", "/")
    assert "a.py" in data[1]["path"].replace("\\", "/")


def test_integration_hidden_all_flag(tmp_path: Path) -> None:
    """Verify -a / --all and --no-all CLI flag handling via subprocess."""
    (tmp_path / ".secret.json").write_text("{}", encoding="utf-8")
    (tmp_path / "public.json").write_text("{}", encoding="utf-8")

    # Default ignores hidden
    proc_def = subprocess.run(
        [sys.executable, "-m", "findfmt", str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    stdout_def = proc_def.stdout.replace("\\", "/")
    assert ".secret.json" not in stdout_def
    assert "public.json" in stdout_def

    # -a includes hidden
    proc_a = subprocess.run(
        [sys.executable, "-m", "findfmt", str(tmp_path), "-a"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert ".secret.json" in proc_a.stdout.replace("\\", "/")

    # --all includes hidden
    proc_all = subprocess.run(
        [sys.executable, "-m", "findfmt", str(tmp_path), "--all"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert ".secret.json" in proc_all.stdout.replace("\\", "/")


def test_integration_from_file_and_offline(tmp_path: Path) -> None:
    """Verify input stream ingestion with offline mode via subprocess."""
    manifest = tmp_path / "manifest.txt"
    manifest.write_text(
        "src/app.py\nsrc/config.json\nsrc/link.py -> target.py\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "findfmt",
            "--from-file",
            str(manifest),
            "--offline",
            "-f",
            "json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert len(data) == 3
    paths = [item["relative_path"].replace("\\", "/") for item in data]
    assert "src/app.py" in paths
    assert "src/config.json" in paths
    assert "src/link.py" in paths
