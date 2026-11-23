"""Platform error, callback recovery, and surrogateescape tests for findfmt._rust_ext (#582)."""

from __future__ import annotations

import errno
import importlib
import os
import string
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from findfmt import _fallback
from findfmt.models import SortKey, TraversalConfig

if TYPE_CHECKING:
    import types
    from collections.abc import Callable, Iterator

    from findfmt.models import FileInfo


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


@pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="POSIX chmod required for mutating on_error bounded prune test",
)
def test_find_files_rs_mutating_on_error_invalidates_bounded_prune_memo(tmp_path: Path) -> None:
    """Verify bounded --prune --dirs-first does not reuse stale ancestor hits across on_error."""
    rust_ext = _load_rust_ext()

    def _run_once(backend_fn: Callable[..., Iterator[FileInfo]]) -> list[str]:
        root = tmp_path / ("rs_tree" if backend_fn is rust_ext.find_files_rs else "py_tree")
        drop_leaf = root / "a_drop" / "child"
        locked = root / "b_locked"
        keep_leaf = root / "c_keep" / "child"
        drop_leaf.mkdir(parents=True)
        locked.mkdir(parents=True)
        keep_leaf.mkdir(parents=True)
        hit = drop_leaf / "hit.txt"
        hit.write_text("drop\n", encoding="utf-8")
        (keep_leaf / "hit.txt").write_text("keep\n", encoding="utf-8")
        locked.chmod(0o000)

        def _mutate_on_err(err: OSError) -> None:
            if err.filename == str(locked.resolve()) and hit.exists():
                hit.unlink()
                drop_leaf.rmdir()

        cfg = TraversalConfig(
            root_paths=(root,),
            dirs_only=True,
            dirs_first=True,
            prune_empty=True,
            max_depth=3,
            sort_by=SortKey.NAME,
        )
        try:
            items = list(backend_fn(cfg, on_error=_mutate_on_err))
            return [str(x.relative_path.as_posix()) for x in items]
        finally:
            locked.chmod(0o755)

    rs_rels = _run_once(rust_ext.find_files_rs)
    py_rels = _run_once(_fallback.find_files)
    assert rs_rels == py_rels == ["a_drop/child", "c_keep/child", "c_keep"]


def test_find_files_rs_round4_unicode_case_cmd_mode_and_git_config_parity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Python re.I equivalences, wide ranges, .cmd DirEntry mode, and GIT_CONFIG parity."""
    rust_ext = _load_rust_ext()

    uni_dir = tmp_path / "uni_case"
    uni_dir.mkdir()
    (uni_dir / "\u017f.txt").write_text("long-s\n", encoding="utf-8")
    (uni_dir / "\u00d7.txt").write_text("times\n", encoding="utf-8")
    (uni_dir / "\u00e0.txt").write_text("a-grave\n", encoding="utf-8")
    for pat in ("[a-z].txt", "[\u00c0-\u0531].txt"):
        cfg_ci = TraversalConfig(root_paths=(uni_dir,), include_patterns=(pat,), ignore_case=True)
        assert list(rust_ext.find_files_rs(cfg_ci)) == list(_fallback.find_files(cfg_ci))

    cmd_dir = tmp_path / "cmd_mode"
    cmd_dir.mkdir()
    cmd_file = cmd_dir / "run.cmd"
    cmd_file.write_text("@echo off\r\n", encoding="utf-8")
    for roots in ((cmd_dir,), (cmd_file,)):
        cfg_cmd = TraversalConfig(root_paths=roots)
        assert list(rust_ext.find_files_rs(cfg_cmd)) == list(_fallback.find_files(cfg_cmd))

    repo = tmp_path / "git_cfg_repo"
    (repo / ".git").mkdir(parents=True)
    excl_file = tmp_path / "repo_excludes.ign"
    excl_file.write_text("report.txt\n", encoding="utf-8")
    (repo / ".git" / "config").write_text(
        f'[core]\n\texcludesFile = "{excl_file.as_posix()}"\n',
        encoding="utf-8",
    )
    (repo / "report.txt").write_text("visible\n", encoding="utf-8")
    empty_git_cfg = tmp_path / "empty_gitconfig"
    empty_git_cfg.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG", str(empty_git_cfg))
    cfg_git = TraversalConfig(root_paths=(repo,), respect_gitignore=True)
    assert list(rust_ext.find_files_rs(cfg_git)) == list(_fallback.find_files(cfg_git))

    if sys.platform != "win32":
        nl_dir = tmp_path / "nl_anchor"
        nl_dir.mkdir()
        try:
            (nl_dir / "note\n").write_text("1\n", encoding="utf-8")
            (nl_dir / "note\nmore").write_text("2\n", encoding="utf-8")
        except OSError:
            return

        cfg_nl = TraversalConfig(root_paths=(nl_dir,), include_patterns=("note",))
        rs_nl = list(rust_ext.find_files_rs(cfg_nl))
        py_nl = list(_fallback.find_files(cfg_nl))
        assert rs_nl == py_nl
        assert len(rs_nl) == 1


@pytest.mark.skipif(sys.platform != "win32", reason="Windows multi-volume symlink boundary test")
def test_find_files_rs_windows_cross_volume_unfollowed_symlink_parity(tmp_path: Path) -> None:
    """Verify -x with unfollowed symlink on root volume pointing to another volume matches fallback."""
    rust_ext = _load_rust_ext()
    root_dev = tmp_path.stat().st_dev
    other_target: Path | None = None
    for letter in string.ascii_uppercase:
        drive = Path(f"{letter}:\\")
        try:
            if drive.exists() and drive.stat().st_dev != root_dev:
                other_target = drive
                break
        except OSError:
            continue

    if other_target is None:
        pytest.skip("No secondary volume available on this Windows host")

    link_path = tmp_path / "cross_vol_link"
    try:
        link_path.symlink_to(other_target, target_is_directory=True)
    except OSError:
        pytest.skip("Windows symlink privilege not enabled")

    for follow in (False, True):
        cfg = TraversalConfig(
            root_paths=(tmp_path,),
            one_file_system=True,
            follow_symlinks=follow,
            max_depth=1,
        )
        rs_res = list(rust_ext.find_files_rs(cfg))
        py_res = list(_fallback.find_files(cfg))
        assert rs_res == py_res
        if not follow:
            assert [x.path.name for x in rs_res] == ["cross_vol_link"]
