"""Unit tests for the GIL-released native Rust directory walker in findfmt._rust_ext (#582)."""

from __future__ import annotations

import gc
import importlib
import os
import shutil
import subprocess
import sys
import warnings
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from findfmt import _fallback, core
from findfmt.exceptions import TraversalError
from findfmt.models import FileInfo, SortKey, TraversalConfig

if TYPE_CHECKING:
    import types


def _load_rust_ext() -> types.ModuleType:
    """Import compiled findfmt._rust_ext or skip when built with HATCH_MATURIN_DISABLE=1."""
    try:
        return importlib.import_module("findfmt._rust_ext")
    except ModuleNotFoundError:
        pytest.skip("findfmt._rust_ext is not compiled in this environment")


def test_find_files_rs_streaming_laziness_and_no_handle_leak(tmp_path: Path) -> None:
    """Verify find_files_rs returns a lazy Iterator[FileInfo] and leaks zero directory handles (#371, #582)."""
    rust_ext = _load_rust_ext()
    for idx in range(12):
        sub = tmp_path / f"dir_{idx:02d}"
        sub.mkdir()
        (sub / f"mod_{idx:02d}.py").write_text("x = 1\n", encoding="utf-8")

    cfg = TraversalConfig(root_paths=(tmp_path,))
    with warnings.catch_warnings():
        warnings.simplefilter("error", ResourceWarning)
        it = rust_ext.find_files_rs(cfg)
        assert isinstance(it, Iterator)
        assert iter(it) is it
        first = next(it)
        assert isinstance(first, FileInfo)
        assert first.relative_path == Path("dir_00/mod_00.py")
        del it
        gc.collect()

    all_rs = list(rust_ext.find_files_rs(cfg))
    all_alias = list(rust_ext.find_files(cfg))
    all_py = list(_fallback.find_files(cfg))
    assert all_rs == all_py
    assert all_alias == all_py


def test_find_files_rs_negative_bounds_and_fifo_root(tmp_path: Path) -> None:
    """Verify find_files_rs enforces TraversalError on negative bounds and skips FIFO roots."""
    rust_ext = _load_rust_ext()

    bad_depth = TraversalConfig(root_paths=(tmp_path,))
    object.__setattr__(bad_depth, "max_depth", -1)
    it_depth = rust_ext.find_files_rs(bad_depth)
    with pytest.raises(TraversalError, match="max_depth must be non-negative"):
        next(it_depth)

    bad_limit = TraversalConfig(root_paths=(tmp_path,))
    object.__setattr__(bad_limit, "file_limit", -2)
    it_limit = rust_ext.find_files_rs(bad_limit)
    with pytest.raises(TraversalError, match="file_limit must be non-negative"):
        next(it_limit)

    if hasattr(os, "mkfifo"):
        fifo_root = tmp_path / "root.fifo"
        os.mkfifo(fifo_root)
        fifo_cfg = TraversalConfig(root_paths=(fifo_root,))
        assert list(rust_ext.find_files_rs(fifo_cfg)) == []
        assert list(_fallback.find_files(fifo_cfg)) == []


def test_find_files_rs_worktree_gitdir_tilde_excludes_and_invalid_gitignore(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify worktree gitdir pointers, core.excludesFile tilde paths, and invalid gitignore parity."""
    rust_ext = _load_rust_ext()
    monkeypatch.delenv("FINDFMT_NO_EXTENSIONS", raising=False)
    monkeypatch.setattr(core, "_RUST_EXT", rust_ext)

    home_dir = tmp_path / "fake_home"
    home_dir.mkdir()
    (home_dir / "my_global.ign").write_text("*.tilde_ign\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("USERPROFILE", str(home_dir))

    real_git = tmp_path / "actual_git" / "modules" / "wt"
    (real_git / "info").mkdir(parents=True)
    (real_git / "info" / "exclude").write_text("*.wt_excl\n", encoding="utf-8")

    wt_repo = tmp_path / "wt_repo"
    wt_repo.mkdir()
    (wt_repo / ".git").write_text(f"gitdir: {real_git}\n", encoding="utf-8")
    (wt_repo / "keep.py").write_text("a = 1\n", encoding="utf-8")
    (wt_repo / "drop.wt_excl").write_text("excl\n", encoding="utf-8")

    # Malformed .gitignore inside a subdirectory is rejected identically to pathspec load_spec_file
    bad_sub = wt_repo / "bad_gi_sub"
    bad_sub.mkdir()
    (bad_sub / ".gitignore").write_text("*.py\n[z-a]\n", encoding="utf-8")
    (bad_sub / "inside.py").write_text("b = 2\n", encoding="utf-8")

    cfg = TraversalConfig(root_paths=(wt_repo,))
    assert list(rust_ext.find_files_rs(cfg)) == list(_fallback.find_files(cfg))

    if shutil.which("git") is not None:
        git_repo = tmp_path / "git_cfg_repo"
        git_repo.mkdir()
        subprocess.run(["git", "init", str(git_repo)], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(git_repo), "config", "core.excludesFile", "~/my_global.ign"],
            check=True,
            capture_output=True,
        )
        (git_repo / "kept.py").write_text("ok = 1\n", encoding="utf-8")
        (git_repo / "ignored.tilde_ign").write_text("ign\n", encoding="utf-8")
        monkeypatch.setattr(Path, "home", classmethod(lambda _cls: home_dir))
        git_cfg = TraversalConfig(root_paths=(git_repo,))
        rs_git_items = list(rust_ext.find_files_rs(git_cfg))
        py_git_items = list(_fallback.find_files(git_cfg))
        assert rs_git_items == py_git_items
        assert [i.relative_path.name for i in rs_git_items] == ["kept.py"]


@pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="POSIX chmod 0o000 required for unreadable subdirectory OSError test",
)
def test_find_files_rs_unreadable_subdir_and_prune_on_error_parity(tmp_path: Path) -> None:
    """Verify unreadable subdirectory OSError delivery during normal and --prune walks (#582)."""
    rust_ext = _load_rust_ext()

    (tmp_path / "a_first.py").write_text("x = 1\n", encoding="utf-8")
    locked = tmp_path / "m_locked"
    locked.mkdir()
    (locked / "hidden_inside.py").write_text("y = 2\n", encoding="utf-8")
    (tmp_path / "z_last.py").write_text("z = 3\n", encoding="utf-8")
    locked.chmod(0o000)

    try:
        for cfg in (
            TraversalConfig(root_paths=(tmp_path,), sort_by=SortKey.NAME),
            TraversalConfig(
                root_paths=(tmp_path,),
                dirs_only=True,
                prune_empty=True,
                include_tags=frozenset({"ruby"}),
            ),
        ):
            rs_errs: list[tuple[int | None, str | None]] = []
            py_errs: list[tuple[int | None, str | None]] = []
            rs_out = list(
                rust_ext.find_files_rs(cfg, on_error=lambda e, s=rs_errs: s.append((e.errno, e.filename))),
            )
            py_out = list(
                _fallback.find_files(cfg, on_error=lambda e, s=py_errs: s.append((e.errno, e.filename))),
            )
            assert rs_out == py_out
            assert rs_errs == py_errs
            assert len(rs_errs) == 1
            assert rs_errs[0][1] == str(locked.resolve())

        def _raising_on_error(err: OSError) -> None:
            msg = f"abort on {err.filename}"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="abort on"):
            list(rust_ext.find_files_rs(TraversalConfig(root_paths=(tmp_path,)), on_error=_raising_on_error))
    finally:
        locked.chmod(0o755)
