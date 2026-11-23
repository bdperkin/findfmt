"""Platform error, callback recovery, and surrogateescape tests for findfmt._rust_ext (#582)."""

from __future__ import annotations

import errno
import importlib
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from findfmt import _fallback
from findfmt.models import SortKey, TraversalConfig

if TYPE_CHECKING:
    import types


def _load_rust_ext() -> types.ModuleType:
    """Import compiled findfmt._rust_ext or skip when built with HATCH_MATURIN_DISABLE=1."""
    try:
        return importlib.import_module("findfmt._rust_ext")
    except ModuleNotFoundError:
        pytest.skip("findfmt._rust_ext is not compiled in this environment")


def test_find_files_rs_missing_root_on_error_and_interrupt_propagation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify cross-platform on_error subclass/errno parity and BaseException propagation (#582)."""
    rust_ext = _load_rust_ext()
    missing_root = tmp_path / "missing_dir_target"

    rs_captured: list[tuple[type[OSError], int | None, str | None]] = []
    py_captured: list[tuple[type[OSError], int | None, str | None]] = []
    cfg = TraversalConfig(root_paths=(missing_root,))

    assert (
        list(
            rust_ext.find_files_rs(
                cfg,
                on_error=lambda e: rs_captured.append((type(e), e.errno, e.filename)),
            ),
        )
        == []
    )
    assert (
        list(
            _fallback.find_files(
                cfg,
                on_error=lambda e: py_captured.append((type(e), e.errno, e.filename)),
            ),
        )
        == []
    )
    assert rs_captured == py_captured
    assert rs_captured == [(FileNotFoundError, errno.ENOENT, str(missing_root))]

    def _raise_keyboard_interrupt(*_args: object, **_kwargs: object) -> str | None:
        raise KeyboardInterrupt

    monkeypatch.setattr("findfmt.traversal.ignore.shutil.which", _raise_keyboard_interrupt)
    live_cfg = TraversalConfig(root_paths=(tmp_path,), respect_gitignore=True)
    with pytest.raises(KeyboardInterrupt):
        list(rust_ext.find_files_rs(live_cfg))


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX surrogateescape byte filenames required")
def test_find_files_rs_surrogateescape_lossless_glob_and_version_sort(tmp_path: Path) -> None:
    """Verify lossless PEP 383 surrogateescape matching and natural version sort without error masking."""
    rust_ext = _load_rust_ext()

    glob_dir = tmp_path / "raw_glob"
    glob_dir.mkdir()
    ver_dir = tmp_path / "raw_ver"
    ver_dir.mkdir()

    try:
        Path(os.fsdecode(os.fsencode(glob_dir) + b"/\xff.txt")).write_bytes(b"raw\n")
        Path(os.fsdecode(os.fsencode(ver_dir) + b"/\xff_v2.py")).write_bytes(b"x = 1\n")
    except OSError:
        pytest.skip("Filesystem rejects non-UTF-8 raw byte filenames (e.g., macOS APFS)")

    (glob_dir / "\ufffd.txt").write_text("rep\n", encoding="utf-8")
    (ver_dir / "\ue000_v2.py").write_text("x = 2\n", encoding="utf-8")

    cfg_lossless = TraversalConfig(root_paths=(glob_dir,), exclude_patterns=("\ufffd.txt",))
    rs_lossless = list(rust_ext.find_files_rs(cfg_lossless))
    py_lossless = list(_fallback.find_files(cfg_lossless))
    assert rs_lossless == py_lossless
    assert len(rs_lossless) == 1

    cfg_ver = TraversalConfig(root_paths=(ver_dir,), sort_by=SortKey.VERSION)
    assert list(rust_ext.find_files_rs(cfg_ver)) == list(_fallback.find_files(cfg_ver))


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
            rs_errs: list[tuple[type[OSError], int | None, str | None]] = []
            py_errs: list[tuple[type[OSError], int | None, str | None]] = []
            rs_out = list(
                rust_ext.find_files_rs(
                    cfg,
                    on_error=lambda e, s=rs_errs: s.append((type(e), e.errno, e.filename)),
                ),
            )
            py_out = list(
                _fallback.find_files(
                    cfg,
                    on_error=lambda e, s=py_errs: s.append((type(e), e.errno, e.filename)),
                ),
            )
            assert rs_out == py_out
            assert rs_errs == py_errs
            assert len(rs_errs) == 1
            assert rs_errs[0] == (PermissionError, errno.EACCES, str(locked.resolve()))

        def _raising_on_error(err: OSError) -> None:
            msg = f"abort on {err.filename}"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="abort on"):
            list(rust_ext.find_files_rs(TraversalConfig(root_paths=(tmp_path,)), on_error=_raising_on_error))
    finally:
        locked.chmod(0o755)


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

        dir_b.chmod(0o000)
        prune_cfg = TraversalConfig(
            root_paths=(tmp_path,),
            dirs_only=True,
            prune_empty=True,
            sort_by=SortKey.NAME,
        )
        rs_dirs = [x.path.name for x in rust_ext.find_files_rs(prune_cfg, on_error=_restore_b_on_a)]
        dir_b.chmod(0o000)
        py_dirs = [x.path.name for x in _fallback.find_files(prune_cfg, on_error=_restore_b_on_a)]
        assert rs_dirs == py_dirs == ["b_restored"]
    finally:
        dir_a.chmod(0o755)
        dir_b.chmod(0o755)
