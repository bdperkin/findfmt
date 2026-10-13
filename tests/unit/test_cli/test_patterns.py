"""CLI integration tests for wildcard and glob pattern filtering options."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typer.testing import CliRunner

from findfmt.cli import app
from findfmt.models import TraversalConfig
from findfmt.traversal import find_files

if TYPE_CHECKING:
    from pathlib import Path


def test_cli_include_pattern_single_and_multiple(sample_repo: Path) -> None:
    """Verify -P and multiple -P flags include only matching files."""
    runner = CliRunner()

    # Single pattern
    res_py = runner.invoke(app, [str(sample_repo), "-P", "*.py"])
    assert res_py.exit_code == 0
    stdout_py = res_py.stdout.replace("\\", "/")
    assert "src/app.py" in stdout_py
    assert "README.md" not in stdout_py
    assert "src/config.json" not in stdout_py

    # Multiple -P patterns
    res_multi = runner.invoke(app, [str(sample_repo), "-P", "*.py", "-P", "*.md"])
    assert res_multi.exit_code == 0
    stdout_multi = res_multi.stdout.replace("\\", "/")
    assert "src/app.py" in stdout_multi
    assert "README.md" in stdout_multi
    assert "src/config.json" not in stdout_multi


def test_cli_include_pattern_pipe_alternation(sample_repo: Path) -> None:
    """Verify -P with '|' alternation matches any alternating pattern."""
    runner = CliRunner()
    res = runner.invoke(app, [str(sample_repo), "-P", "*.py|*.json"])
    assert res.exit_code == 0
    stdout = res.stdout.replace("\\", "/")
    assert "src/app.py" in stdout
    assert "src/config.json" in stdout
    assert "README.md" not in stdout


def test_cli_exclude_pattern_single_and_multiple(sample_repo: Path) -> None:
    """Verify -I and multiple -I flags exclude matching files."""
    runner = CliRunner()

    # Single exclusion
    res = runner.invoke(app, [str(sample_repo), "-I", "*.py"])
    assert res.exit_code == 0
    stdout = res.stdout.replace("\\", "/")
    assert "src/app.py" not in stdout
    assert "README.md" in stdout
    assert "src/config.json" in stdout

    # Multiple exclusions
    res_multi = runner.invoke(app, [str(sample_repo), "-I", "*.py", "-I", "*.md"])
    assert res_multi.exit_code == 0
    stdout_multi = res_multi.stdout.replace("\\", "/")
    assert "src/app.py" not in stdout_multi
    assert "README.md" not in stdout_multi
    assert "src/config.json" in stdout_multi


def test_cli_pattern_case_insensitivity(tmp_path: Path) -> None:
    """Verify --ignore-case matches patterns without regard to casing."""
    (tmp_path / "foo.PY").write_text("print('hello')\n")
    (tmp_path / "bar.py").write_text("print('world')\n")
    (tmp_path / "baz.txt").write_text("text\n")

    runner = CliRunner()

    # Case-sensitive without flag: *.py matches bar.py, not foo.PY
    res_sens = runner.invoke(app, [str(tmp_path), "-P", "*.py"])
    assert res_sens.exit_code == 0
    assert "bar.py" in res_sens.stdout
    assert "foo.PY" not in res_sens.stdout

    # Case-insensitive with flag: *.py matches both bar.py and foo.PY
    res_insens = runner.invoke(app, [str(tmp_path), "-P", "*.py", "--ignore-case"])
    assert res_insens.exit_code == 0
    assert "bar.py" in res_insens.stdout
    assert "foo.PY" in res_insens.stdout
    assert "baz.txt" not in res_insens.stdout

    # Case-insensitive exclusion
    res_ex = runner.invoke(app, [str(tmp_path), "-I", "*.PY", "--ignore-case"])
    assert res_ex.exit_code == 0
    assert "bar.py" not in res_ex.stdout
    assert "foo.PY" not in res_ex.stdout
    assert "baz.txt" in res_ex.stdout


def test_cli_match_dirs_inheritance(tmp_path: Path) -> None:
    """Verify --match-dirs inherits inclusion match to children of matching directories."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "code.py").write_text("pass\n")
    (src_dir / "asset.png").write_text("binary\n")

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "manual.txt").write_text("manual\n")
    (docs_dir / "extra.png").write_text("binary\n")

    runner = CliRunner()

    # Without --match-dirs: -P src* only matches items whose name or path starts with src*
    # asset.png in src matches because path is src/asset.png, but extra.png in docs does not
    res_no_match = runner.invoke(app, [str(tmp_path), "-P", "src*"])
    assert res_no_match.exit_code == 0
    assert "code.py" in res_no_match.stdout
    assert "asset.png" in res_no_match.stdout
    assert "manual.txt" not in res_no_match.stdout

    # With --match-dirs: pattern matching directory 'src' inherits to its children
    res_match = runner.invoke(app, [str(tmp_path), "-P", "src", "--match-dirs"])
    assert res_match.exit_code == 0
    assert "code.py" in res_match.stdout
    assert "asset.png" in res_match.stdout
    assert "manual.txt" not in res_match.stdout
    assert "extra.png" not in res_match.stdout


def test_cli_pattern_with_prune(tmp_path: Path) -> None:
    """Verify --prune works in combination with -P pattern matching."""
    sub_matched = tmp_path / "matched_dir"
    sub_matched.mkdir()
    (sub_matched / "file.py").write_text("code\n")

    sub_unmatched = tmp_path / "unmatched_dir"
    sub_unmatched.mkdir()
    (sub_unmatched / "file.txt").write_text("text\n")

    runner = CliRunner()
    res = runner.invoke(app, [str(tmp_path), "-P", "*.py", "-d", "--prune"])
    assert res.exit_code == 0
    assert "matched_dir" in res.stdout
    assert "unmatched_dir" not in res.stdout


def test_cli_pattern_dirs_only(tmp_path: Path) -> None:
    """Verify -d with -P and -I filters directories by name."""
    (tmp_path / "src_dir").mkdir()
    (tmp_path / "test_dir").mkdir()
    (tmp_path / "doc_dir").mkdir()

    runner = CliRunner()

    # -d with -P and --match-dirs
    res_inc = runner.invoke(app, [str(tmp_path), "-d", "-P", "src*", "--match-dirs"])
    assert res_inc.exit_code == 0
    assert "src_dir" in res_inc.stdout
    assert "test_dir" not in res_inc.stdout

    # -d with -I
    res_exc = runner.invoke(app, [str(tmp_path), "-d", "-I", "test*"])
    assert res_exc.exit_code == 0
    assert "src_dir" in res_exc.stdout
    assert "doc_dir" in res_exc.stdout
    assert "test_dir" not in res_exc.stdout


def test_find_files_single_file_with_patterns(tmp_path: Path) -> None:
    """Verify find_files evaluates pattern matching on direct file root targets."""
    py_file = tmp_path / "main.py"
    py_file.write_text("print('hello')\n")

    # Matched pattern
    cfg_inc = TraversalConfig(root_paths=(py_file,), include_patterns=("*.py",))
    res_inc = list(find_files(cfg_inc))
    assert len(res_inc) == 1
    assert res_inc[0].path == py_file.resolve()

    # Unmatched pattern
    cfg_miss = TraversalConfig(root_paths=(py_file,), include_patterns=("*.md",))
    res_miss = list(find_files(cfg_miss))
    assert len(res_miss) == 0

    # Excluded pattern
    cfg_ex = TraversalConfig(root_paths=(py_file,), exclude_patterns=("*.py",))
    res_ex = list(find_files(cfg_ex))
    assert len(res_ex) == 0
