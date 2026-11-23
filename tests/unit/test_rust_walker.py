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


def test_find_files_rs_gitignore_slash_patterns_unicode_glob_and_sigma_sort(tmp_path: Path) -> None:
    """Verify ClusterFuzzLite */ gitignore patterns, Unicode ? globs, Unix C: dirs, and final-sigma sort."""
    rust_ext = _load_rust_ext()

    for pat in ("*/  \n", "*/\n!sub/\n", "**/\n", "/**/\n", "//\n", "/\n"):
        case_dir = tmp_path / f"gi_{abs(hash(pat))}"
        case_dir.mkdir(exist_ok=True)
        (case_dir / ".gitignore").write_text(pat, encoding="utf-8")
        (case_dir / "root.py").write_text("x = 1\n", encoding="utf-8")
        sub = case_dir / "sub"
        sub.mkdir(exist_ok=True)
        (sub / "nested.py").write_text("y = 2\n", encoding="utf-8")
        sym = case_dir / "symlink_dir"
        if not sym.exists() and not sym.is_symlink():
            sym.symlink_to(sub, target_is_directory=True)

        cfg = TraversalConfig(root_paths=(case_dir,), include_hidden=True, respect_gitignore=True)
        assert list(rust_ext.find_files_rs(cfg)) == list(_fallback.find_files(cfg))

    glob_dir = tmp_path / "unicode_glob"
    glob_dir.mkdir()
    (glob_dir / "é.txt").write_text("1\n", encoding="utf-8")
    (glob_dir / "ab.txt").write_text("2\n", encoding="utf-8")
    (glob_dir / "\u039f\u03a3").write_text("3\n", encoding="utf-8")
    (glob_dir / "\u039f\u03c2a").write_text("4\n", encoding="utf-8")
    if sys.platform != "win32":
        c_dir = glob_dir / "C:"
        c_dir.mkdir()
        (c_dir / "report.txt").write_text("5\n", encoding="utf-8")
        cfg_colon = TraversalConfig(root_paths=(glob_dir,), include_patterns=("/C:/report.txt",))
        assert list(rust_ext.find_files_rs(cfg_colon)) == list(_fallback.find_files(cfg_colon))

        raw_ff = os.fsdecode(os.fsencode(glob_dir) + b"/\xff.txt")
        Path(raw_ff).write_bytes(b"raw\n")
        (glob_dir / "\ufffd.txt").write_text("rep\n", encoding="utf-8")
        cfg_lossless = TraversalConfig(root_paths=(glob_dir,), exclude_patterns=("\ufffd.txt",))
        assert list(rust_ext.find_files_rs(cfg_lossless)) == list(_fallback.find_files(cfg_lossless))

        ver_dir = tmp_path / "ver_surrogate"
        ver_dir.mkdir()
        Path(os.fsdecode(os.fsencode(ver_dir) + b"/\xff_v2.py")).write_bytes(b"x = 1\n")
        (ver_dir / "\ue000_v2.py").write_text("x = 2\n", encoding="utf-8")
        cfg_ver = TraversalConfig(root_paths=(ver_dir,), sort_by=SortKey.VERSION)
        assert list(rust_ext.find_files_rs(cfg_ver)) == list(_fallback.find_files(cfg_ver))

    cfg_q = TraversalConfig(root_paths=(glob_dir,), include_patterns=("?.txt",))
    assert list(rust_ext.find_files_rs(cfg_q)) == list(_fallback.find_files(cfg_q))
    cfg_sigma = TraversalConfig(root_paths=(glob_dir,), sort_by=SortKey.NAME, ignore_case=True)
    assert list(rust_ext.find_files_rs(cfg_sigma)) == list(_fallback.find_files(cfg_sigma))


def test_find_files_rs_lazy_roots_depth_prune_memo_and_cyclic_gc(tmp_path: Path) -> None:
    """Verify lazy root resolution, depth-bounded symlink --prune memoization, and PyO3 cyclic GC."""
    rust_ext = _load_rust_ext()

    # 1. Lazy second root created after consuming from first root
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
    rest_items = list(it)
    assert [x.path.name for x in rest_items] == ["second.py"]

    # 2. Depth-limited symlink --prune memoization (p/a/link -> p/z with p/z/child/hit.txt)
    prune_root = tmp_path / "prune_depth"
    (prune_root / "a").mkdir(parents=True)
    (prune_root / "z" / "child").mkdir(parents=True)
    (prune_root / "z" / "child" / "hit.txt").write_text("ok\n", encoding="utf-8")
    (prune_root / "a" / "link").symlink_to(prune_root / "z", target_is_directory=True)
    for rev in (False, True):
        prune_cfg = TraversalConfig(
            root_paths=(prune_root,),
            dirs_only=True,
            prune_empty=True,
            follow_symlinks=True,
            max_depth=3,
            reverse_sort=rev,
        )
        rs_pruned = list(rust_ext.find_files_rs(prune_cfg))
        py_pruned = list(_fallback.find_files(prune_cfg))
        assert rs_pruned == py_pruned
        assert [x.relative_path.as_posix() for x in rs_pruned] == ["z", "z/child"]

    # 3. Cyclic GC collection of owner <-> iterator <-> bound callback cycle
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


@pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="POSIX chmod required for on_error sibling restoration test",
)
def test_find_files_rs_on_error_pauses_before_scanning_sibling_dir(tmp_path: Path) -> None:
    """Verify on_error runs before scanning sibling directories so restored siblings are traversed."""
    rust_ext = _load_rust_ext()
    dir_a = tmp_path / "a_blocked"
    dir_b = tmp_path / "b_restored"
    dir_a.mkdir()
    dir_b.mkdir()
    (dir_b / "recovered.py").write_text("ok = 1\n", encoding="utf-8")
    dir_a.chmod(0o000)
    dir_b.chmod(0o000)

    try:

        def _restore_b_on_a(err: OSError) -> None:
            if err.filename == str(dir_a.resolve()):
                dir_b.chmod(0o755)

        cfg = TraversalConfig(root_paths=(tmp_path,), sort_by=SortKey.NAME)
        rs_names = [x.path.name for x in rust_ext.find_files_rs(cfg, on_error=_restore_b_on_a)]
        dir_b.chmod(0o000)
        py_names = [x.path.name for x in _fallback.find_files(cfg, on_error=_restore_b_on_a)]
        assert rs_names == py_names == ["recovered.py"]
    finally:
        dir_a.chmod(0o755)
        dir_b.chmod(0o755)
