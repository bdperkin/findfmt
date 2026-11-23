"""Unit tests for the GIL-released native Rust directory walker in findfmt._rust_ext (#582)."""

from __future__ import annotations

import gc
import importlib
import os
import shutil
import subprocess
import sys
import warnings
import weakref
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
    """Verify find_files_rs returns a lazy Iterator[FileInfo] without handle leaks (#371, #582)."""
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


def test_find_files_rs_gitignore_slash_patterns_unicode_glob_and_sigma_sort(tmp_path: Path) -> None:
    """Verify gitignore slash/bracket/whitespace rules, Unicode ? globs, and Tolong Siki/sigma sort."""
    rust_ext = _load_rust_ext()

    patterns = (
        "*/  \n",
        "*/\n!sub/\n",
        "/*\n!sub/\n",
        "/\n!sub/\n",
        "**\n!sub/\n",
        "*.py\n!sub/\n",
        "?*[!a-z]\n",
        "**[!a-z]\n",
        "sub[^0-9]\n",
        "/\u00a0\u00a0 \n",
        "/\t \n",
        "\\/\n*.py\n",
        "!\n*.py\n",
        r"[\]" + "\n",
        "**/\n",
        "/**/\n",
        "//\n",
        "/\n",
    )
    for idx, pat in enumerate(patterns):
        case_dir = tmp_path / f"gi_{idx}"
        case_dir.mkdir(exist_ok=True)
        (case_dir / ".gitignore").write_text(pat, encoding="utf-8")
        (case_dir / "root.py").write_text("x = 1\n", encoding="utf-8")
        sub = case_dir / "sub"
        sub.mkdir(exist_ok=True)
        (sub / "nested.py").write_text("y = 2\n", encoding="utf-8")
        sym = case_dir / "symlink_dir"
        if sys.platform != "win32" and not sym.exists() and not sym.is_symlink():
            sym.symlink_to(sub, target_is_directory=True)

        cfg = TraversalConfig(root_paths=(case_dir,), include_hidden=True, respect_gitignore=True)
        assert list(rust_ext.find_files_rs(cfg)) == list(_fallback.find_files(cfg))

    glob_dir = tmp_path / "unicode_glob"
    glob_dir.mkdir()
    (glob_dir / "é.txt").write_text("1\n", encoding="utf-8")
    (glob_dir / "ab.txt").write_text("2\n", encoding="utf-8")
    (glob_dir / "\u039f\u03a3").write_text("3\n", encoding="utf-8")
    (glob_dir / "\u039f\u03c2a").write_text("4\n", encoding="utf-8")
    (glob_dir / "tolong_\U00011de1\U00011de0.txt").write_text("5\n", encoding="utf-8")
    (glob_dir / "tolong_\U00011de2.txt").write_text("6\n", encoding="utf-8")
    if sys.platform != "win32":
        c_dir = glob_dir / "C:"
        c_dir.mkdir()
        (c_dir / "report.txt").write_text("7\n", encoding="utf-8")
        cfg_colon = TraversalConfig(root_paths=(glob_dir,), include_patterns=("/C:/report.txt",))
        assert list(rust_ext.find_files_rs(cfg_colon)) == list(_fallback.find_files(cfg_colon))

    cfg_q = TraversalConfig(root_paths=(glob_dir,), include_patterns=("?.txt",))
    assert list(rust_ext.find_files_rs(cfg_q)) == list(_fallback.find_files(cfg_q))
    cfg_sigma = TraversalConfig(root_paths=(glob_dir,), sort_by=SortKey.NAME, ignore_case=True)
    assert list(rust_ext.find_files_rs(cfg_sigma)) == list(_fallback.find_files(cfg_sigma))
    cfg_tolong = TraversalConfig(root_paths=(glob_dir,), sort_by=SortKey.VERSION)
    assert list(rust_ext.find_files_rs(cfg_tolong)) == list(_fallback.find_files(cfg_tolong))

    bad_pat_cfg = TraversalConfig(root_paths=(glob_dir,), include_patterns=("[z-a]",))
    with pytest.raises(ValueError, match=r"pattern|range"):
        list(rust_ext.find_files_rs(bad_pat_cfg))


def test_find_files_rs_lazy_roots_depth_prune_memo_and_cyclic_gc(tmp_path: Path) -> None:
    """Verify lazy root resolution, depth-bounded/aliased --prune memoization, and PyO3 cyclic GC."""
    rust_ext = _load_rust_ext()

    root_a = tmp_path / "lazy_a"
    root_b = tmp_path / "lazy_b"
    root_a.mkdir()
    (root_a / "first.py").write_text("a = 1\n", encoding="utf-8")
    lazy_cfg = TraversalConfig(root_paths=(root_a, root_b), sort_by=SortKey.NONE)
    it = rust_ext.find_files_rs(lazy_cfg)
    first_item = next(it)
    assert first_item.path.name == "first.py"
    root_b.mkdir()
    (root_b / "second.py").write_text("b = 2\n", encoding="utf-8")
    assert [x.path.name for x in it] == ["second.py"]

    # Cross-platform depth-bounded and match_dirs --prune parity (covers Windows & POSIX)
    base_prune = tmp_path / "prune_cross"
    (base_prune / "empty_branch" / "leaf").mkdir(parents=True)
    (base_prune / "match_branch" / "sub").mkdir(parents=True)
    (base_prune / "match_branch" / "sub" / "hit.txt").write_text("ok\n", encoding="utf-8")
    for depth_lim in (2, 3, None):
        cross_cfg = TraversalConfig(
            root_paths=(base_prune,),
            dirs_only=True,
            prune_empty=True,
            follow_symlinks=True,
            max_depth=depth_lim,
            match_dirs=True,
            include_patterns=("match_branch",),
        )
        assert list(rust_ext.find_files_rs(cross_cfg)) == list(_fallback.find_files(cross_cfg))

    if sys.platform != "win32":
        prune_root = tmp_path / "prune_depth"
        (prune_root / "a").mkdir(parents=True)
        (prune_root / "z" / "child").mkdir(parents=True)
        (prune_root / "z" / "child" / "hit.txt").write_text("ok\n", encoding="utf-8")
        (prune_root / "z" / "scoped.txt").write_text("ok2\n", encoding="utf-8")
        (prune_root / "a" / "link").symlink_to(prune_root / "z", target_is_directory=True)
        for rev in (False, True):
            prune_cfg = TraversalConfig(
                root_paths=(prune_root,),
                dirs_only=True,
                prune_empty=True,
                follow_symlinks=True,
                max_depth=3,
                include_patterns=("hit.txt",),
                reverse_sort=rev,
            )
            rs_pruned = list(rust_ext.find_files_rs(prune_cfg))
            assert rs_pruned == list(_fallback.find_files(prune_cfg))
            assert [x.relative_path.as_posix() for x in rs_pruned] == ["z", "z/child"]

        for max_d in (2, None):
            scoped_cfg = TraversalConfig(
                root_paths=(prune_root,),
                dirs_only=True,
                prune_empty=True,
                follow_symlinks=True,
                max_depth=max_d,
                include_patterns=("z/scoped.txt",),
            )
            rs_scoped = list(rust_ext.find_files_rs(scoped_cfg))
            assert rs_scoped == list(_fallback.find_files(scoped_cfg))
            assert [x.relative_path.as_posix() for x in rs_scoped] == ["z"]

    class _CycleOwner:
        def __init__(self, target_root: Path) -> None:
            self.it: Iterator[FileInfo] | None = rust_ext.find_files_rs(
                TraversalConfig(root_paths=(target_root,)),
                on_error=self.handle_err,
            )

        def handle_err(self, _err: OSError) -> None:
            pass

    owner = _CycleOwner(root_a)
    assert owner.it is not None
    _ = next(owner.it)
    ref = weakref.ref(owner)
    del owner
    gc.collect()
    assert ref() is None
