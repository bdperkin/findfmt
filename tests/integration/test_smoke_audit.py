"""Final smoke testing and edge-case quality audit test suite for v1.0.0 GA.

Validates extreme directory topologies, broken symlink cycles, massive ignored
trees, malformed input ingestion, and cross-platform path and executable semantics.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Iterator
from pathlib import Path, PureWindowsPath
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from findfmt import build_file_uri, find_files
from findfmt.classifier import _check_executable
from findfmt.cli import app
from findfmt.models import TraversalConfig
from findfmt.parsers.engine import classify_file_offline

runner = CliRunner()


@pytest.mark.parametrize(
    "fmt",
    ["text", "json", "yaml", "table", "tree", "csv-table", "xml", "html"],
)
def test_smoke_empty_directories_across_formats(tmp_path: Path, fmt: str) -> None:
    """Verify execution on empty directories produces clean outputs across all formats."""
    empty_dir = tmp_path / "empty_root"
    empty_dir.mkdir()

    res = runner.invoke(app, [str(empty_dir), "--format", fmt, "--no-pager"])
    assert res.exit_code == 0
    assert "Traceback" not in res.output

    if fmt in ("json", "yaml"):
        assert "[]" in res.output


def test_smoke_zero_matching_files_filter(tmp_path: Path) -> None:
    """Verify filtering yielding zero matching entries exits cleanly without tracebacks."""
    (tmp_path / "file1.txt").write_text("content", encoding="utf-8")
    (tmp_path / "file2.py").write_text("print(1)", encoding="utf-8")

    res = runner.invoke(
        app,
        [str(tmp_path), "-t", "nonexistent_tag", "--format", "json", "--no-pager"],
    )
    assert res.exit_code == 0
    assert "Traceback" not in res.output
    assert json.loads(res.output) == []

    res_pat = runner.invoke(
        app,
        [str(tmp_path), "-P", "*.nonexistent", "--format", "json", "--no-pager"],
    )
    assert res_pat.exit_code == 0
    assert "Traceback" not in res_pat.output
    assert json.loads(res_pat.output) == []


def test_smoke_unreadable_directory_resilience(tmp_path: Path) -> None:
    """Verify unreadable subdirectories are skipped gracefully and unreadable roots fail cleanly."""
    if sys.platform == "win32":
        pytest.skip("POSIX permissions (chmod 0o000) do not restrict directory reading on Windows")

    valid_file = tmp_path / "valid.txt"
    valid_file.write_text("ok", encoding="utf-8")

    unreadable_sub = tmp_path / "locked_dir"
    unreadable_sub.mkdir()
    try:
        unreadable_sub.chmod(0o000)
    except OSError:
        pytest.skip("Filesystem does not support permission changes")

    try:
        res = runner.invoke(app, [str(tmp_path), "--no-pager"])
        assert res.exit_code == 0
        assert "valid.txt" in res.output
        assert "Traceback" not in res.output

        res_root = runner.invoke(app, [str(unreadable_sub), "--no-pager"])
        assert res_root.exit_code == 2
        assert "Traceback" not in res_root.output
        assert "not readable" in res_root.output.lower()
    finally:
        unreadable_sub.chmod(0o755)


def test_smoke_permission_error_graceful(tmp_path: Path) -> None:
    """Verify PermissionError during directory scanning is handled without tracebacks."""
    (tmp_path / "valid.txt").write_text("ok", encoding="utf-8")
    with patch("os.scandir", side_effect=PermissionError("Access denied")):
        res = runner.invoke(app, [str(tmp_path), "--no-pager"])
        assert res.exit_code == 0
        assert "Traceback" not in res.output


def test_smoke_broken_symlinks_and_cycles(tmp_path: Path) -> None:
    """Verify broken symlinks, target loops, and cyclic references avoid recursion crashes."""
    (tmp_path / "valid.py").write_text("x = 1", encoding="utf-8")

    broken_file = tmp_path / "broken_file.py"
    broken_dir = tmp_path / "broken_dir"
    try:
        broken_file.symlink_to(tmp_path / "non_existent_file.py")
        broken_dir.symlink_to(tmp_path / "non_existent_dir", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Filesystem does not support symlinks")

    # Default traversal skips broken symlinks without error
    res_def = runner.invoke(app, [str(tmp_path), "--no-pager"])
    assert res_def.exit_code == 0
    assert "Traceback" not in res_def.output
    assert "valid.py" in res_def.output

    # --follow-symlinks does not crash on broken symlinks
    res_follow = runner.invoke(app, [str(tmp_path), "-l", "--no-pager"])
    assert res_follow.exit_code == 0
    assert "Traceback" not in res_follow.output
    assert "valid.py" in res_follow.output

    # Direct invocation on a broken symlink root
    res_direct = runner.invoke(app, [str(broken_file), "--no-pager"])
    assert res_direct.exit_code == 0
    assert "Traceback" not in res_direct.output

    # Symlink cycle detection (a -> b -> a)
    cycle_a = tmp_path / "cycle_a"
    cycle_b = tmp_path / "cycle_b"
    cycle_a.mkdir()
    cycle_b.mkdir()
    (cycle_a / "leaf_a.txt").write_text("a", encoding="utf-8")
    (cycle_b / "leaf_b.txt").write_text("b", encoding="utf-8")

    (cycle_a / "to_b").symlink_to(cycle_b, target_is_directory=True)
    (cycle_b / "to_a").symlink_to(cycle_a, target_is_directory=True)

    res_cycle = runner.invoke(app, [str(cycle_a), "-l", "--no-pager"])
    assert res_cycle.exit_code == 0
    assert "Traceback" not in res_cycle.output
    assert "leaf_a.txt" in res_cycle.output
    assert "leaf_b.txt" in res_cycle.output


def test_smoke_massive_ignored_trees_pruning(tmp_path: Path) -> None:
    """Verify that ignored directory hierarchies are pruned without descending into them."""
    (tmp_path / ".gitignore").write_text("node_modules/\n.venv/\nbuild/\n", encoding="utf-8")

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "index.js").write_text("console.log('hi');", encoding="utf-8")

    # Construct nested ignored tree with multiple levels and files
    ignored_root = tmp_path / "node_modules"
    curr = ignored_root
    for i in range(5):
        curr = curr / f"pkg_{i}"
        curr.mkdir(parents=True)
        for j in range(10):
            (curr / f"mod_{j}.js").write_text("// dummy", encoding="utf-8")

    scanned_paths: list[str] = []
    real_scandir = os.scandir

    def spy_scandir(path: str = ".") -> Iterator[os.DirEntry[str]]:
        scanned_paths.append(str(path))
        return real_scandir(path)

    with patch("os.scandir", side_effect=spy_scandir):
        cfg = TraversalConfig(root_paths=(tmp_path,), respect_gitignore=True)
        results = list(find_files(cfg))

    rel_results = [r.relative_path.as_posix() for r in results]
    assert "src/index.js" in rel_results
    assert not any("node_modules" in r for r in rel_results)

    # Verify scandir was NEVER called inside node_modules
    for scanned in scanned_paths:
        norm = scanned.replace("\\", "/")
        assert "/node_modules/" not in norm
        assert not norm.endswith("/node_modules")


def test_smoke_from_file_edge_cases_and_malformed_inputs(tmp_path: Path) -> None:
    """Verify --from-file and stdin ingestion handle malformed, empty, and mixed inputs."""
    # Empty stdin
    res_empty = runner.invoke(app, ["--from-file", "-", "--no-pager"], input="")
    assert res_empty.exit_code == 0
    assert res_empty.output == ""

    # Malformed flat listing with comments, Windows separators, relative prefixes, and quotes
    manifest = tmp_path / "manifest.txt"
    manifest.write_text(
        "# Header comment\n"
        "\n"
        "   \n"
        "./\n"
        ".\\\n"
        "src/app.py\n"
        ".\\src\\config.json\n"
        "lib/foo.so -> libfoo.so.1\n"
        'scripts/run.sh -> "target_script.sh"\n'
        "broken_link -> \n"
        "missing_target\n"
        "README.md\n",
        encoding="utf-8",
    )

    res_manifest = runner.invoke(
        app,
        ["--from-file", str(manifest), "--offline", "-f", "json", "--no-pager"],
    )
    assert res_manifest.exit_code == 0
    assert "Traceback" not in res_manifest.output
    items = json.loads(res_manifest.output)
    paths = [item["relative_path"].replace("\\", "/") for item in items]
    assert "src/app.py" in paths
    assert "src/config.json" in paths
    assert "lib/foo.so" in paths
    assert "README.md" in paths

    # Malformed outline hierarchy with mixed indentation and comments
    outline_input = (
        "# Project outline\n"
        "root\n"
        "    src\n"
        "\t\tmodule.py\n"
        "  \t  nested\n"
        "\t\t\tdeep.txt\n"
        "    docs\n"
        "        guide.md\n"
    )
    res_outline = runner.invoke(
        app,
        ["--from-file", "-", "--tree", "--no-pager"],
        input=outline_input,
    )
    assert res_outline.exit_code == 0
    assert "module.py" in res_outline.output
    assert "deep.txt" in res_outline.output
    assert "guide.md" in res_outline.output


def test_smoke_cross_platform_path_and_pathext(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify cross-platform path normalization, Windows PATHEXT, and file URIs."""
    # Windows PATHEXT variations with spaces and missing leading dots
    exe_file = Path("app.exe")
    bat_file = Path("script.bat")
    cmd_file = Path("tool.cmd")
    txt_file = Path("notes.txt")

    monkeypatch.setattr("os.name", "nt")
    monkeypatch.setenv("PATHEXT", " .EXE ; .BAT ; CMD; ")

    assert _check_executable(exe_file, exists=True) is True
    assert _check_executable(bat_file, exists=True) is True
    assert _check_executable(cmd_file, exists=True) is True
    assert _check_executable(txt_file, exists=True) is False

    info_exe = classify_file_offline(exe_file, relative_path=exe_file)
    info_bat = classify_file_offline(bat_file, relative_path=bat_file)
    info_cmd = classify_file_offline(cmd_file, relative_path=cmd_file)
    info_txt = classify_file_offline(txt_file, relative_path=txt_file)

    assert info_exe.is_executable is True
    assert "executable" in info_exe.tags
    assert info_bat.is_executable is True
    assert "executable" in info_bat.tags
    assert info_cmd.is_executable is True
    assert "executable" in info_cmd.tags
    assert info_txt.is_executable is False
    assert "non-executable" in info_txt.tags

    # OSC 8 terminal hyperlink URI schemes across platforms
    posix_uri = build_file_uri("/workspace/app.py")
    assert posix_uri == "file:///workspace/app.py"

    win_str_uri = build_file_uri(r"C:\workspace\app.py")
    assert win_str_uri == "file:///C:/workspace/app.py"

    win_pure_uri = build_file_uri(PureWindowsPath(r"D:\projects\code\main.py"))
    assert win_pure_uri == "file:///D:/projects/code/main.py"

    custom_schema_uri = build_file_uri(
        r"C:\workspace\app.py",
        schema="vscode://file/",
        authority="devbox",
    )
    assert custom_schema_uri == "vscode://devbox/file/C:/workspace/app.py"


def test_smoke_pattern_case_sensitivity(tmp_path: Path) -> None:
    """Verify wildcard pattern matching respects case-sensitive and case-insensitive flags."""
    (tmp_path / "Document.TXT").write_text("doc", encoding="utf-8")
    (tmp_path / "data.txt").write_text("data", encoding="utf-8")
    (tmp_path / "image.PNG").write_text("img", encoding="utf-8")

    # Default case-sensitive on POSIX: *.txt matches only lowercase
    res_sensitive = runner.invoke(app, [str(tmp_path), "-P", "*.txt", "--no-pager"])
    assert res_sensitive.exit_code == 0
    assert "data.txt" in res_sensitive.output
    if sys.platform != "win32":
        assert "Document.TXT" not in res_sensitive.output

    # Case-insensitive (--ignore-case): *.txt matches both .txt and .TXT
    res_insensitive = runner.invoke(
        app,
        [str(tmp_path), "-P", "*.txt", "--ignore-case", "--no-pager"],
    )
    assert res_insensitive.exit_code == 0
    assert "data.txt" in res_insensitive.output
    assert "Document.TXT" in res_insensitive.output
    assert "image.PNG" not in res_insensitive.output
