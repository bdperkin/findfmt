"""Targeted PyO3 boundary and GC traversal tests for findfmt._rust_ext coverage (#590)."""

from __future__ import annotations

import gc
import inspect
import mimetypes
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from findfmt import _rust_ext
from findfmt.core import classify_file
from findfmt.models import TraversalConfig

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override


class _BadBoundValue:
    """Comparable object whose integer conversion fails with ValueError."""

    def __lt__(self, _other: object) -> bool:
        return False

    def __index__(self) -> int:
        msg = "bad bound index"
        raise ValueError(msg)


class _BrokenRootPath:
    """Path-like root object raising custom exceptions during root probing."""

    def __init__(self, raw: str, exc: Exception) -> None:
        self._raw = raw
        self._exc = exc

    def __fspath__(self) -> str:
        return self._raw

    def is_symlink(self) -> bool:
        raise self._exc

    def __lt__(self, other: _BrokenRootPath) -> bool:
        return self._raw < other._raw

    @override
    def __str__(self) -> str:
        return self._raw


def _lock_unreadable_dir(path: Path) -> None:
    """Deny directory listing while keeping directory metadata readable across OSs."""
    if sys.platform == "win32":
        subprocess.run(["icacls", str(path), "/deny", "*S-1-1-0:(RD)"], check=True, capture_output=True)
    else:
        path.chmod(0o000)


def _unlock_unreadable_dir(path: Path) -> None:
    """Restore directory permissions after an unreadable-directory test."""
    if sys.platform == "win32":
        subprocess.run(["icacls", str(path), "/remove:d", "*S-1-1-0"], check=False, capture_output=True)
    else:
        path.chmod(0o755)


def test_rust_file_iterator_gc_traverse_clear_and_exhaustion(tmp_path: Path) -> None:
    """Exercise RustFileIterator __traverse__, __clear__, and post-exhaustion __next__."""
    sub1 = tmp_path / "d1"
    sub2 = tmp_path / "d2"
    sub1.mkdir()
    sub2.mkdir()
    (sub1 / "a.py").write_text("x = 1\n", encoding="utf-8")
    (sub2 / "b.py").write_text("y = 2\n", encoding="utf-8")

    errors: list[OSError] = []

    def on_err(err: OSError) -> None:
        errors.append(err)

    cfg_multi = TraversalConfig(root_paths=(sub1, sub2))
    uninit_no_cb = _rust_ext.find_files_rs(cfg_multi)
    assert uninit_no_cb.__iter__() is uninit_no_cb
    assert cfg_multi in gc.get_referents(uninit_no_cb)

    uninit_it = _rust_ext.find_files_rs(cfg_multi, on_error=on_err)
    refs_uninit = gc.get_referents(uninit_it)
    assert cfg_multi in refs_uninit
    assert on_err in refs_uninit

    # Pure 2-object cycle (it1.pending_roots -> it2.config -> it1) so CPython calls __clear__.
    mut_roots: list[Any] = [sub1]
    cyc_cfg: Any = SimpleNamespace(
        max_depth=None,
        file_limit=None,
        from_file=None,
        respect_gitignore=False,
        gitignore_file=None,
        include_hidden=False,
        follow_symlinks=False,
        dirs_only=False,
        one_file_system=False,
        prune_empty=False,
        ignore_case=False,
        match_dirs=False,
        relative_prefix=False,
        accumulate_size=False,
        sort_by="none",
        reverse_sort=False,
        dirs_first=False,
        include_patterns=(),
        exclude_patterns=(),
        include_tags=frozenset(),
        exclude_tags=frozenset(),
        all_tags=False,
        shebang_filter=None,
        root_paths=mut_roots,
    )
    it1: Any = _rust_ext.find_files_rs(cyc_cfg)
    it2: Any = _rust_ext.find_files_rs(it1)
    mut_roots.append(it2)
    _ = next(it1)
    del mut_roots, cyc_cfg, it1, it2
    gc.collect()

    native_it = _rust_ext.find_files_rs(cfg_multi, on_error=on_err)
    first_item = next(native_it)
    assert first_item.path.name == "a.py"
    assert on_err in gc.get_referents(native_it)
    assert len(list(native_it)) == 1
    with pytest.raises(StopIteration):
        next(native_it)

    with pytest.raises(StopIteration):
        next(native_it)

    list_file = tmp_path / "paths.txt"
    list_file.write_text(f"{sub1 / 'a.py'}\n{sub2 / 'b.py'}\n", encoding="utf-8")
    delegated_cfg = TraversalConfig(root_paths=(tmp_path,), from_file=str(list_file))
    delegated_it = _rust_ext.find_files_rs(delegated_cfg)
    _ = next(delegated_it)
    assert any(inspect.isgenerator(r) for r in gc.get_referents(delegated_it))
    assert len(list(delegated_it)) == 1


def test_mimetypes_reinit_classify_batch_prefix_and_toctou_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover mimetypes._db lazy init, classify_batch_rs prefix, readonly mode, and TOCTOU refresh."""
    sample = tmp_path / "script.py"
    sample.write_text("x = 1\n", encoding="utf-8")
    sample.chmod(0o444)
    try:
        monkeypatch.setattr(mimetypes, "_db", None)
        info = classify_file(sample)
        assert "python" in info.tags

        monkeypatch.setattr(mimetypes, "_db", None)
        cfg_str_sort: Any = SimpleNamespace(
            max_depth=None,
            file_limit=None,
            from_file=None,
            respect_gitignore=False,
            gitignore_file=None,
            include_hidden=False,
            follow_symlinks=False,
            dirs_only=False,
            one_file_system=False,
            prune_empty=False,
            ignore_case=False,
            match_dirs=False,
            relative_prefix=False,
            accumulate_size=False,
            sort_by="size",
            reverse_sort=False,
            dirs_first=False,
            include_patterns=(),
            exclude_patterns=(),
            include_tags=frozenset(),
            exclude_tags=frozenset(),
            all_tags=False,
            shebang_filter=None,
            root_paths=(tmp_path,),
        )
        assert len(list(_rust_ext.find_files_rs(cfg_str_sort))) == 1

        bad_cfg: Any = SimpleNamespace(**{**cfg_str_sort.__dict__, "max_depth": _BadBoundValue()})
        bad_it = _rust_ext.find_files_rs(bad_cfg)
        with pytest.raises(ValueError, match="bad bound index"):
            next(bad_it)

        batch_res = _rust_ext.classify_batch_rs(
            [(sample, None, None)],
            root_path=tmp_path,
            prefix=Path("custom_pfx"),
        )
        assert batch_res[0].relative_path == Path("custom_pfx/script.py")
    finally:
        sample.chmod(0o644)

    # Mid-stream TOCTOU refresh: dir replaced with file under dirs_only & shebang removed
    d_dirs = tmp_path / "toctou_dirs"
    (d_dirs / "a_dir").mkdir(parents=True)
    (d_dirs / "b_dir").mkdir(parents=True)
    it_dirs = _rust_ext.find_files_rs(TraversalConfig(root_paths=(d_dirs,), dirs_only=True))
    _ = next(it_dirs)
    (d_dirs / "b_dir").rmdir()
    (d_dirs / "b_dir").write_text("swapped\n", encoding="utf-8")
    _ = list(it_dirs)

    d_sb = tmp_path / "toctou_sb"
    d_sb.mkdir()
    (d_sb / "a_run").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    (d_sb / "b_run").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    it_sb = _rust_ext.find_files_rs(TraversalConfig(root_paths=(d_sb,), shebang_filter="python"))
    _ = next(it_sb)
    (d_sb / "b_run").write_text("plain text\n", encoding="utf-8")
    _ = list(it_sb)


def test_root_probing_symlinks_global_ignore_and_walk_error_callbacks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover symlink roots, global gitignore fallbacks, and portable WalkEvent::Error callbacks."""
    target_file = tmp_path / "real.py"
    target_file.write_text("z = 3\n", encoding="utf-8")
    file_link = tmp_path / "link_to_file.py"
    broken_link = tmp_path / "broken_link"
    try:
        file_link.symlink_to(target_file)
        broken_link.symlink_to(tmp_path / "missing_target")
    except OSError:
        pass
    else:
        cfg_links = TraversalConfig(root_paths=(file_link, broken_link), follow_symlinks=True)
        found = list(_rust_ext.find_files_rs(cfg_links))
        assert [f.path.name for f in found] == ["link_to_file.py"]

    monkeypatch.setattr("findfmt.traversal.ignore._find_git_config_excludes_file", lambda _root=None: 12345)
    assert (
        len(list(_rust_ext.find_files_rs(TraversalConfig(root_paths=(tmp_path,), respect_gitignore=True))))
        >= 1
    )

    def _git_boom(_root: object = None) -> None:
        msg = "git config boom"
        raise RuntimeError(msg)

    monkeypatch.setattr("findfmt.traversal.ignore._find_git_config_excludes_file", _git_boom)
    assert (
        len(list(_rust_ext.find_files_rs(TraversalConfig(root_paths=(tmp_path,), respect_gitignore=True))))
        >= 1
    )

    captured: list[OSError] = []
    os_err_root: Any = _BrokenRootPath(str(tmp_path / "a_os_err"), OSError("nameless error"))
    named_os_err_root: Any = _BrokenRootPath(
        str(tmp_path / "b_named_err"),
        OSError(2, "named error", "/preset/filename"),
    )
    rt_err_root: Any = _BrokenRootPath(str(tmp_path / "c_rt_err"), RuntimeError("symlink loop"))
    cfg_errs: Any = TraversalConfig(root_paths=(os_err_root, named_os_err_root, rt_err_root))
    assert list(_rust_ext.find_files_rs(cfg_errs, on_error=captured.append)) == []
    assert [e.filename for e in captured] == [str(tmp_path / "a_os_err"), "/preset/filename"]

    val_err_root: Any = _BrokenRootPath(str(tmp_path / "val_err"), ValueError("unexpected"))
    with pytest.raises(ValueError, match="unexpected"):
        list(_rust_ext.find_files_rs(TraversalConfig(root_paths=(val_err_root,))))

    # Portable WalkEvent::Error delivery (no callback, re-entrant iter(), and raising callback)
    locked_dir = tmp_path / "locked_sub"
    locked_dir.mkdir()
    _lock_unreadable_dir(locked_dir)
    try:
        assert list(_rust_ext.find_files_rs(TraversalConfig(root_paths=(locked_dir,)))) == []

        reentrant_it: Any = None

        def _reentrant_iter_cb(_err: OSError) -> None:
            with pytest.raises(RuntimeError, match="Already mutably borrowed"):
                iter(reentrant_it)

        reentrant_it = _rust_ext.find_files_rs(
            TraversalConfig(root_paths=(locked_dir,)),
            on_error=_reentrant_iter_cb,
        )
        assert list(reentrant_it) == []

        def raise_in_cb(_err: OSError) -> None:
            msg = "abort on error"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="abort on error"):
            list(_rust_ext.find_files_rs(TraversalConfig(root_paths=(locked_dir,)), on_error=raise_in_cb))
    finally:
        _unlock_unreadable_dir(locked_dir)
