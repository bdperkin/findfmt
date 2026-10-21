"""Unit tests for the Git ignore and ancestor repository discovery engine."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pathspec
import pytest
from typer.testing import CliRunner

from findfmt.cli import app
from findfmt.models import TraversalConfig
from findfmt.traversal import find_files
from findfmt.traversal.ignore import (
    PathSpecType,
    find_git_repo_root,
    is_path_ignored,
    load_ancestor_specs,
    load_child_specs,
    load_git_exclude_spec,
    load_gitignore_spec,
    load_spec_file,
)


def test_load_spec_file_valid_and_empty(tmp_path: Path) -> None:
    spec_path = tmp_path / ".gitignore"
    spec_path.write_text("*.log\n# comment\n\ntarget/\n", encoding="utf-8")
    spec = load_spec_file(spec_path)
    assert spec is not None
    assert spec.match_file("test.log")
    assert not spec.match_file("test.py")

    empty_path = tmp_path / "empty.txt"
    empty_path.write_text("# only comments\n   \n", encoding="utf-8")
    assert load_spec_file(empty_path) is None
    assert load_spec_file(tmp_path / "missing.txt") is None


def test_load_spec_file_exceptions(tmp_path: Path) -> None:
    bad_spec = tmp_path / "bad.txt"
    bad_spec.write_text("\\\n", encoding="utf-8")
    assert load_spec_file(bad_spec) is None

    err_file = tmp_path / "err.txt"
    err_file.write_text("*.tmp", encoding="utf-8")
    with patch.object(Path, "open", side_effect=OSError("Read error")):
        assert load_spec_file(err_file) is None


def test_load_gitignore_spec(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("*.bin\n", encoding="utf-8")
    spec = load_gitignore_spec(tmp_path)
    assert spec is not None
    assert spec.match_file("data.bin")

    assert load_gitignore_spec(tmp_path / "subdir") is None


def test_load_git_exclude_spec_directory(tmp_path: Path) -> None:
    exclude_dir = tmp_path / ".git" / "info"
    exclude_dir.mkdir(parents=True)
    (exclude_dir / "exclude").write_text("*.custom\n", encoding="utf-8")

    spec = load_git_exclude_spec(tmp_path)
    assert spec is not None
    assert spec.match_file("foo.custom")

    # Missing exclude file
    assert load_git_exclude_spec(tmp_path / "other") is None


def test_load_git_exclude_spec_pointer_file(tmp_path: Path) -> None:
    # Submodule / worktree .git pointer file
    real_git_dir = tmp_path / "real_git" / "modules" / "sub"
    (real_git_dir / "info").mkdir(parents=True)
    (real_git_dir / "info" / "exclude").write_text("*.submod\n", encoding="utf-8")

    sub_worktree = tmp_path / "worktree"
    sub_worktree.mkdir()
    git_file = sub_worktree / ".git"
    git_file.write_text(f"gitdir: {real_git_dir}\n", encoding="utf-8")

    spec = load_git_exclude_spec(sub_worktree)
    assert spec is not None
    assert spec.match_file("file.submod")

    # Non-gitdir pointer file
    bad_git_file = tmp_path / "bad_git"
    bad_git_file.mkdir()
    (bad_git_file / ".git").write_text("invalid content\n", encoding="utf-8")
    assert load_git_exclude_spec(bad_git_file) is None

    # OSError on read
    with patch.object(Path, "read_text", side_effect=OSError("Read failed")):
        assert load_git_exclude_spec(sub_worktree) is None


def test_find_git_repo_root(tmp_path: Path) -> None:
    repo = tmp_path / "my_repo"
    (repo / ".git").mkdir(parents=True)
    sub = repo / "a" / "b"
    sub.mkdir(parents=True)

    assert find_git_repo_root(sub) == repo.resolve()
    assert find_git_repo_root(repo) == repo.resolve()

    # Outside any repository
    outside = tmp_path / "outside"
    outside.mkdir()
    with patch.object(Path, "exists", return_value=False):
        assert find_git_repo_root(outside) is None

    # OSError during resolve
    expected_repo = repo.resolve()
    orig_resolve = Path.resolve

    def mock_resolve(self: Path) -> Path:
        if self == sub:
            raise OSError

        return orig_resolve(self)

    with patch.object(Path, "resolve", autospec=True, side_effect=mock_resolve):
        assert find_git_repo_root(sub) == expected_repo

    # OSError during exists check
    orig_exists = Path.exists

    def mock_exists(self: Path) -> bool:
        if self.name == ".git":
            raise OSError

        return orig_exists(self)

    with patch.object(Path, "exists", autospec=True, side_effect=mock_exists):
        assert find_git_repo_root(sub) is None


def test_load_ancestor_specs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git" / "info").mkdir(parents=True)
    (repo / ".git" / "info" / "exclude").write_text("*.exc\n", encoding="utf-8")
    (repo / ".gitignore").write_text("*.log\n", encoding="utf-8")

    pkg = repo / "pkg"
    pkg.mkdir()
    # pkg has no .gitignore

    sub = pkg / "sub"
    sub.mkdir()
    (sub / ".gitignore").write_text("!keep.log\n", encoding="utf-8")

    specs = load_ancestor_specs(sub)
    # Expected: exclude at repo root, .gitignore at repo root, .gitignore at sub
    assert len(specs) == 3
    assert specs[0][0] == repo.resolve()
    assert specs[1][0] == repo.resolve()
    assert specs[2][0] == sub.resolve()

    # Outside git repository
    outside = tmp_path / "non_repo" / "child"
    outside.mkdir(parents=True)
    (outside.parent / ".gitignore").write_text("*.tmp\n", encoding="utf-8")
    with patch("findfmt.traversal.ignore.find_git_repo_root", return_value=None):
        specs_outside = load_ancestor_specs(outside)
        assert any(base == outside.parent.resolve() for base, _ in specs_outside)

    # OSError during root.resolve()
    with patch.object(Path, "resolve", side_effect=OSError("Error")):
        specs_err = load_ancestor_specs(sub)
        assert len(specs_err) >= 1


def test_load_child_specs(tmp_path: Path) -> None:
    parent_specs: tuple[tuple[Path, PathSpecType], ...] = ()
    child = tmp_path / "child"
    child.mkdir()
    (child / ".gitignore").write_text("*.child\n", encoding="utf-8")

    specs = load_child_specs(child, parent_specs)
    assert len(specs) == 1
    assert specs[0][0] == child

    # Child directory with no gitignore and no nested git
    plain_child = tmp_path / "plain"
    plain_child.mkdir()
    assert load_child_specs(plain_child, specs) == specs

    # Nested git repo submodule
    submod = tmp_path / "submodule"
    (submod / ".git" / "info").mkdir(parents=True)
    (submod / ".git" / "info" / "exclude").write_text("*.submodeleted\n", encoding="utf-8")
    (submod / ".gitignore").write_text("*.submodfile\n", encoding="utf-8")

    submod_specs = load_child_specs(submod, specs)
    assert len(submod_specs) == 3

    # Nested git repo without exclude file
    submod_no_exc = tmp_path / "submod_no_exc"
    (submod_no_exc / ".git").mkdir(parents=True)
    (submod_no_exc / ".gitignore").write_text("*.sample\n", encoding="utf-8")
    assert len(load_child_specs(submod_no_exc, specs)) == 2

    # OSError during git_marker.exists()
    orig_exists2 = Path.exists

    def mock_exists2(self: Path) -> bool:
        if self.name == ".git":
            raise OSError

        return orig_exists2(self)

    with patch.object(Path, "exists", autospec=True, side_effect=mock_exists2):
        specs_err = load_child_specs(child, parent_specs)
        assert len(specs_err) == 1


def test_is_path_ignored_precedence_and_negation(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    sub = repo / "sub"
    sub.mkdir(parents=True)

    repo_spec = pathspec.PathSpec.from_lines("gitignore", ["*.log", "__pycache__/"])
    sub_spec = pathspec.PathSpec.from_lines("gitignore", ["!important.log"])

    specs = ((repo, repo_spec), (sub, sub_spec))

    # Child negation overrides parent ignore
    assert not is_path_ignored(sub / "important.log", is_dir=False, specs=specs)

    # Parent rule matches non-negated file
    assert is_path_ignored(sub / "debug.log", is_dir=False, specs=specs)

    # Directory match with trailing slash
    assert is_path_ignored(sub / "__pycache__", is_dir=True, specs=specs)

    # Clean file not ignored
    assert not is_path_ignored(sub / "app.py", is_dir=False, specs=specs)

    # Path unrelated to base_dir
    unrelated = Path("/some/unrelated/file.log")
    assert not is_path_ignored(unrelated, is_dir=False, specs=specs)

    # Path exactly matching base_dir itself
    assert not is_path_ignored(sub, is_dir=True, specs=specs)


def test_cli_subdir_respects_ancestor_gitignore(
    sample_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CliRunner()
    monkeypatch.chdir(sample_repo)

    res = runner.invoke(app, ["--no-summary", "src/nested/"])
    assert res.exit_code == 0
    stdout = res.stdout.replace("\\", "/")
    assert "nested.py" in stdout
    assert "ignored.nestedignore" not in stdout

    res_src = runner.invoke(app, ["--no-summary", "src/"])
    assert res_src.exit_code == 0
    stdout_src = res_src.stdout.replace("\\", "/")
    assert "app.py" in stdout_src
    assert "config.json" in stdout_src
    assert "ignored.nestedignore" not in stdout_src

    res_no_ign = runner.invoke(app, ["--no-summary", "--no-ignore", "src/nested/"])
    assert res_no_ign.exit_code == 0
    stdout_no_ign = res_no_ign.stdout.replace("\\", "/")
    assert "ignored.nestedignore" in stdout_no_ign


def test_traversal_nested_repo_and_submodule(tmp_path: Path) -> None:
    outer = tmp_path / "outer"
    (outer / ".git").mkdir(parents=True)
    (outer / ".gitignore").write_text("*.outer_ignore\n", encoding="utf-8")

    sub = outer / "nested_repo"
    (sub / ".git" / "info").mkdir(parents=True)
    (sub / ".git" / "info" / "exclude").write_text("*.nested_exc\n", encoding="utf-8")
    (sub / ".gitignore").write_text("*.nested_ign\n", encoding="utf-8")

    (sub / "good.py").write_text("a = 1\n", encoding="utf-8")
    (sub / "bad.outer_ignore").write_text("x = 1\n", encoding="utf-8")
    (sub / "bad.nested_exc").write_text("y = 1\n", encoding="utf-8")
    (sub / "bad.nested_ign").write_text("z = 1\n", encoding="utf-8")

    config = TraversalConfig(root_paths=(outer,))
    results = list(find_files(config))
    names = [r.path.name for r in results]

    assert "good.py" in names
    assert "bad.outer_ignore" not in names
    assert "bad.nested_exc" not in names
    assert "bad.nested_ign" not in names


def test_gitignore_significant_whitespace(tmp_path: Path) -> None:
    """Verify gitignore parser preserves leading and escaped trailing whitespace."""
    spec_path = tmp_path / ".gitignore"
    spec_path.write_bytes(
        b" leading.txt\r\n"
        b"trailing\\ \r\n"
        b"trailing_multi\\   \r\n"
        b"unescaped   \r\n"
        b"# comment\r\n"
        b" # not a comment\r\n"
        b"\\#escaped_hash\r\n"
        b"   \r\n"
        b"crlf.txt\r\n"
        b"cr_only.txt\r",
    )
    spec = load_spec_file(spec_path)
    assert spec is not None

    # Leading space: matches ' leading.txt', but not 'leading.txt'
    assert spec.match_file(" leading.txt")
    assert not spec.match_file("leading.txt")

    # Escaped trailing space: matches 'trailing ', but not 'trailing'
    assert spec.match_file("trailing ")
    assert not spec.match_file("trailing")

    # Escaped space followed by unescaped spaces: matches 'trailing_multi '
    assert spec.match_file("trailing_multi ")
    assert not spec.match_file("trailing_multi")

    # Unescaped trailing space: matches 'unescaped', but not 'unescaped   '
    assert spec.match_file("unescaped")
    assert not spec.match_file("unescaped   ")

    # Indented line is not a comment, matches ' # not a comment'
    assert spec.match_file(" # not a comment")
    assert not spec.match_file("# not a comment")

    # Escaped hash matches '#escaped_hash'
    assert spec.match_file("#escaped_hash")

    # Carriage return variants match cleanly
    assert spec.match_file("crlf.txt")
    assert spec.match_file("cr_only.txt")

    # End-to-end traversal test with find_files
    (tmp_path / " leading.txt").write_text("1", encoding="utf-8")
    (tmp_path / "leading.txt").write_text("2", encoding="utf-8")
    (tmp_path / "trailing ").write_text("3", encoding="utf-8")
    (tmp_path / "trailing").write_text("4", encoding="utf-8")

    config = TraversalConfig(root_paths=(tmp_path,))
    results = [r.path.name for r in find_files(config)]
    assert "leading.txt" in results
    assert " leading.txt" not in results
    assert "trailing" in results
    assert "trailing " not in results
