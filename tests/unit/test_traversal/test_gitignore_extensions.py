"""Unit tests for ignore engine extensions (global gitignore and --gitignore-file)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from findfmt.models import TraversalConfig
from findfmt.traversal import (
    find_files,
    load_custom_gitignore_spec,
    load_global_gitignore_spec,
    traverse_directory,
)
from findfmt.traversal.boundaries import resolve_active_specs
from findfmt.traversal.ignore import (
    find_global_gitignore_path,
    load_ancestor_specs,
)


def test_find_global_gitignore_path_git_config_success(tmp_path: Path) -> None:
    """Verify detection when core.excludesFile is set and the file exists."""
    global_file = tmp_path / "global_ignore"
    global_file.write_text("*.log\n", encoding="utf-8")

    mock_proc = MagicMock(returncode=0, stdout=f"{global_file}\n")
    with (
        patch("shutil.which", return_value="/usr/bin/git"),
        patch("subprocess.run", return_value=mock_proc),
    ):
        assert find_global_gitignore_path() == global_file


def test_find_global_gitignore_path_git_config_missing_file() -> None:
    """Verify returns None when core.excludesFile is set but the file does not exist."""
    missing_file = "/path/to/nonexistent/ignore_file_12345"
    mock_proc = MagicMock(returncode=0, stdout=missing_file)
    with (
        patch("shutil.which", return_value="/usr/bin/git"),
        patch("subprocess.run", return_value=mock_proc),
    ):
        assert find_global_gitignore_path() is None


def test_find_global_gitignore_path_git_config_empty_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify fallback to standard paths when git returns empty stdout."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    xdg_file = tmp_path / ".config" / "git" / "ignore"
    xdg_file.parent.mkdir(parents=True)
    xdg_file.write_text("*.swp\n", encoding="utf-8")

    mock_proc = MagicMock(returncode=0, stdout="   \n")
    with (
        patch("shutil.which", return_value="/usr/bin/git"),
        patch("subprocess.run", return_value=mock_proc),
        patch.object(Path, "home", return_value=tmp_path),
    ):
        assert find_global_gitignore_path() == xdg_file


def test_find_global_gitignore_path_git_error_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify fallback to standard paths when git command fails or raises."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    xdg_file = tmp_path / ".config" / "git" / "ignore"
    xdg_file.parent.mkdir(parents=True)
    xdg_file.write_text("*.bak\n", encoding="utf-8")

    with (
        patch("shutil.which", return_value="/usr/bin/git"),
        patch("subprocess.run", side_effect=subprocess.SubprocessError("git error")),
        patch.object(Path, "home", return_value=tmp_path),
    ):
        assert find_global_gitignore_path() == xdg_file


def test_find_global_gitignore_path_xdg_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify discovery when XDG_CONFIG_HOME is set and git is not available."""
    xdg_dir = tmp_path / "custom_xdg"
    xdg_file = xdg_dir / "git" / "ignore"
    xdg_file.parent.mkdir(parents=True)
    xdg_file.write_text("*.tmp\n", encoding="utf-8")

    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_dir))
    with patch("shutil.which", return_value=None):
        assert find_global_gitignore_path() == xdg_file


def test_find_global_gitignore_path_xdg_env_missing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify returns None when XDG_CONFIG_HOME is set and git/ignore does not exist."""
    xdg_dir = tmp_path / "empty_xdg"
    xdg_dir.mkdir()
    legacy_file = tmp_path / ".gitignore"
    legacy_file.write_text("*.bak\n", encoding="utf-8")

    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_dir))
    with (
        patch("shutil.which", return_value=None),
        patch.object(Path, "home", return_value=tmp_path),
    ):
        assert find_global_gitignore_path() is None


def test_find_global_gitignore_path_home_missing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify returns None when XDG_CONFIG_HOME is unset and ~/.config/git/ignore is missing."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    with (
        patch("shutil.which", return_value=None),
        patch.object(Path, "home", return_value=tmp_path),
    ):
        assert find_global_gitignore_path() is None


def test_find_global_gitignore_path_home_exceptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify graceful handling when Path.home raises RuntimeError or OSError."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    with (
        patch("shutil.which", return_value=None),
        patch.object(Path, "home", side_effect=RuntimeError("No home dir")),
    ):
        assert find_global_gitignore_path() is None


def test_load_global_gitignore_spec(tmp_path: Path) -> None:
    """Verify load_global_gitignore_spec with explicit file and discovery."""
    ignore_file = tmp_path / "global.ignore"
    ignore_file.write_text("*.secret\n", encoding="utf-8")

    # Explicit spec file passed
    spec = load_global_gitignore_spec(ignore_file)
    assert spec is not None
    assert spec.match_file("test.secret")

    # Discovery fallback path
    with patch(
        "findfmt.traversal.ignore.find_global_gitignore_path",
        return_value=ignore_file,
    ):
        spec_discovered = load_global_gitignore_spec()
        assert spec_discovered is not None
        assert spec_discovered.match_file("test.secret")

    # Discovery returning None
    with patch("findfmt.traversal.ignore.find_global_gitignore_path", return_value=None):
        assert load_global_gitignore_spec() is None


def test_load_custom_gitignore_spec(tmp_path: Path) -> None:
    """Verify load_custom_gitignore_spec with valid, missing, and None paths."""
    assert load_custom_gitignore_spec(None) is None
    assert load_custom_gitignore_spec(tmp_path / "nonexistent.ignore") is None

    valid_file = tmp_path / "custom.ignore"
    valid_file.write_text("*.custom\n", encoding="utf-8")
    spec = load_custom_gitignore_spec(valid_file)
    assert spec is not None
    assert spec.match_file("file.custom")
    assert not spec.match_file("file.py")

    # Passing str instead of Path
    spec_str = load_custom_gitignore_spec(str(valid_file))
    assert spec_str is not None
    assert spec_str.match_file("file.custom")


def test_load_ancestor_specs_with_global_spec(tmp_path: Path) -> None:
    """Verify load_ancestor_specs incorporates global gitignore spec at root."""
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / ".gitignore").write_text("*.local\n", encoding="utf-8")

    global_spec_file = tmp_path / "global.ignore"
    global_spec_file.write_text("*.global\n", encoding="utf-8")

    with patch(
        "findfmt.traversal.ignore.find_global_gitignore_path",
        return_value=global_spec_file,
    ):
        specs = load_ancestor_specs(repo)
        assert len(specs) == 2
        # Global spec is at index 0 (lowest precedence)
        assert specs[0][0] == repo.resolve()
        assert specs[0][1].match_file("foo.global")
        # Local gitignore is at index 1
        assert specs[1][0] == repo.resolve()
        assert specs[1][1].match_file("foo.local")

    # Outside git repository
    outside = tmp_path / "outside"
    outside.mkdir()
    with patch(
        "findfmt.traversal.ignore.find_global_gitignore_path",
        return_value=global_spec_file,
    ):
        specs_outside = load_ancestor_specs(outside)
        assert len(specs_outside) == 1
        assert specs_outside[0][0] == outside.resolve()


def test_resolve_active_specs_with_gitignore_file(tmp_path: Path) -> None:
    """Verify resolve_active_specs incorporates custom gitignore file."""
    custom_ignore = tmp_path / "custom.ignore"
    custom_ignore.write_text("*.ignoreme\n", encoding="utf-8")

    with patch("findfmt.traversal.ignore.find_global_gitignore_path", return_value=None):
        # When respect_gitignore=False but gitignore_file is provided
        specs_no_git = resolve_active_specs(
            tmp_path,
            None,
            respect_gitignore=False,
            gitignore_file=custom_ignore,
        )
        assert len(specs_no_git) == 1
        assert specs_no_git[0][0] == tmp_path
        assert specs_no_git[0][1].match_file("file.ignoreme")

        # When active_specs is already provided, it is returned directly
        assert (
            resolve_active_specs(
                tmp_path,
                specs_no_git,
                respect_gitignore=True,
                gitignore_file=custom_ignore,
            )
            == specs_no_git
        )

        # When gitignore_file does not exist, custom_spec is None
        specs_missing = resolve_active_specs(
            tmp_path,
            None,
            respect_gitignore=False,
            gitignore_file=tmp_path / "missing.ignore",
        )
        assert specs_missing == ()


def test_find_files_with_gitignore_file(tmp_path: Path) -> None:
    """Verify find_files honors external gitignore file across directory descent."""
    custom_ignore = tmp_path / "custom.ignore"
    custom_ignore.write_text("*.skip\n/sub_skip/\n", encoding="utf-8")

    keep_file = tmp_path / "keep.txt"
    keep_file.write_text("content", encoding="utf-8")
    skip_file = tmp_path / "drop.skip"
    skip_file.write_text("content", encoding="utf-8")

    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    sub_keep = sub_dir / "sub_keep.txt"
    sub_keep.write_text("content", encoding="utf-8")
    sub_skip = sub_dir / "sub_drop.skip"
    sub_skip.write_text("content", encoding="utf-8")

    sub_skip_dir = tmp_path / "sub_skip"
    sub_skip_dir.mkdir()
    (sub_skip_dir / "nested.txt").write_text("content", encoding="utf-8")

    config = TraversalConfig(
        root_paths=(tmp_path,),
        gitignore_file=custom_ignore,
        respect_gitignore=False,
    )
    found = {f.path.name for f in find_files(config)}
    assert "keep.txt" in found
    assert "sub_keep.txt" in found
    assert "drop.skip" not in found
    assert "sub_drop.skip" not in found
    assert "nested.txt" not in found


def test_home_dot_gitignore_is_not_global(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify ~/.gitignore (e.g. dotfiles repo with '*') is never treated as global excludes."""
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    (home_dir / ".gitignore").write_text("*\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("USERPROFILE", str(home_dir))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / "visible.py").write_text("x = 1\n", encoding="utf-8")

    with patch.object(Path, "home", return_value=home_dir):
        assert find_global_gitignore_path(repo) is None
        found = [f.relative_path.name for f in traverse_directory(repo, TraversalConfig())]
        assert found == ["visible.py"]


def test_xdg_git_ignore_is_global_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify $XDG_CONFIG_HOME/git/ignore is applied as the global ignore default."""
    xdg_dir = tmp_path / "xdg"
    xdg_ignore = xdg_dir / "git" / "ignore"
    xdg_ignore.parent.mkdir(parents=True)
    xdg_ignore.write_text("*.xdg_ignored\n", encoding="utf-8")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_dir))

    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / "keep.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "drop.xdg_ignored").write_text("ignored\n", encoding="utf-8")

    found = [f.relative_path.name for f in traverse_directory(repo, TraversalConfig())]
    assert found == ["keep.py"]


@pytest.mark.skipif(shutil.which("git") is None, reason="git binary not available")
def test_core_excludesfile_resolved_relative_to_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify git -C <root> config is used even when process cwd is in a different repository."""
    other_repo = tmp_path / "other_repo"
    other_repo.mkdir()
    subprocess.run(["git", "init", str(other_repo)], check=True, capture_output=True)
    other_excl = other_repo / "other.excludes"
    other_excl.write_text("*.keep_in_target\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(other_repo), "config", "core.excludesFile", str(other_excl)],
        check=True,
        capture_output=True,
    )

    target_repo = tmp_path / "target_repo"
    target_repo.mkdir()
    subprocess.run(["git", "init", str(target_repo)], check=True, capture_output=True)
    target_excl = target_repo / ".git" / "custom.excludes"
    target_excl.write_text("*.target_excluded\n", encoding="utf-8")
    # Configure relative path in target_repo to verify both `git -C root` and relative resolution
    subprocess.run(
        ["git", "-C", str(target_repo), "config", "core.excludesFile", ".git/custom.excludes"],
        check=True,
        capture_output=True,
    )
    (target_repo / "file.keep_in_target").write_text("ok\n", encoding="utf-8")
    (target_repo / "file.target_excluded").write_text("skip\n", encoding="utf-8")

    monkeypatch.chdir(other_repo)
    assert find_global_gitignore_path(target_repo) == target_excl
    found = [f.relative_path.name for f in traverse_directory(target_repo, TraversalConfig())]
    assert found == ["file.keep_in_target"]


def test_no_ancestor_gitignore_outside_repo(tmp_path: Path) -> None:
    """Verify non-repo directory under a parent with .gitignore does not apply parent rules."""
    parent_dir = tmp_path / "parent_with_ignore"
    parent_dir.mkdir()
    (parent_dir / ".gitignore").write_text("*.parent_ignored\n", encoding="utf-8")

    non_repo = parent_dir / "non_repo_child"
    non_repo.mkdir()
    (non_repo / "kept.parent_ignored").write_text("keep\n", encoding="utf-8")
    (non_repo / ".gitignore").write_text("*.child_ignored\n", encoding="utf-8")
    (non_repo / "dropped.child_ignored").write_text("drop\n", encoding="utf-8")

    with patch("findfmt.traversal.ignore.find_git_repo_root", return_value=None):
        found = [f.relative_path.name for f in traverse_directory(non_repo, TraversalConfig())]
        assert found == ["kept.parent_ignored"]


@pytest.mark.skipif(shutil.which("git") is None, reason="git binary not available")
def test_matches_git_check_ignore(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify ignored file set matches `git check-ignore` on a fixture repository."""
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    # Dotfiles ~/.gitignore with '*' must be ignored by both git and findfmt
    (home_dir / ".gitignore").write_text("*\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("USERPROFILE", str(home_dir))

    xdg_dir = tmp_path / "xdg"
    xdg_ignore = xdg_dir / "git" / "ignore"
    xdg_ignore.parent.mkdir(parents=True)
    xdg_ignore.write_text("*.global_ign\n", encoding="utf-8")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_dir))

    repo = tmp_path / "fixture_repo"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    (repo / ".git" / "info" / "exclude").write_text("*.info_exc\n", encoding="utf-8")
    (repo / ".gitignore").write_text("*.log\n!important.log\nbuild/\n", encoding="utf-8")

    sub = repo / "sub"
    sub.mkdir()
    (sub / ".gitignore").write_text("*.sub_ign\n", encoding="utf-8")

    build = repo / "build"
    build.mkdir()

    candidate_rel_paths = [
        "app.py",
        "debug.log",
        "important.log",
        "secret.info_exc",
        "temp.global_ign",
        "build/artifact.bin",
        "sub/module.py",
        "sub/sub.log",
        "sub/local.sub_ign",
    ]
    for rel in candidate_rel_paths:
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("data\n", encoding="utf-8")

    with patch.object(Path, "home", return_value=home_dir):
        traversed_set = {
            f.relative_path.as_posix() for f in traverse_directory(repo, TraversalConfig())
        }

    findfmt_ignored = set(candidate_rel_paths) - traversed_set

    proc = subprocess.run(
        ["git", "-C", str(repo), "check-ignore", *candidate_rel_paths],
        capture_output=True,
        text=True,
        check=False,
    )
    git_ignored = {line.strip() for line in proc.stdout.splitlines() if line.strip()}
    assert findfmt_ignored == git_ignored
