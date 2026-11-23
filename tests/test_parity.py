"""Parameterized Rust (_rust_ext) vs. pure-Python (_fallback) parity suite (#584)."""

from __future__ import annotations

import contextlib
import os
import socket
import tempfile
import types
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from findfmt import _fallback
from findfmt.models import FileInfo, SortKey, TraversalConfig
from tests.test_parity_assertions import (
    ConfigOverrides,
    activate_rust_backend,
    assert_classify_path_parity,
    assert_file_info_parity,
    assert_traversal_parity,
    assert_traversal_parity_with_ext,
)
from tests.test_parity_fixtures import (
    build_classification_and_encoding_tree,
    build_gitignore_and_exclude_tree,
    build_sorting_tree,
    build_symlink_and_boundary_tree,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


@pytest.mark.parametrize(
    ("scenario", "cfg_kwargs"),
    [
        ("default_gitignore", {}),
        ("no_gitignore", {"respect_gitignore": False}),
        ("include_hidden", {"include_hidden": True}),
        ("hidden_no_ignore", {"include_hidden": True, "respect_gitignore": False}),
        ("dirs_only_all", {"dirs_only": True}),
        ("dirs_only_hidden", {"dirs_only": True, "include_hidden": True}),
        ("dirs_only_pruned", {"dirs_only": True, "prune_empty": True}),
        (
            "dirs_only_pruned_py",
            {"dirs_only": True, "prune_empty": True, "include_tags": frozenset({"python"})},
        ),
        ("glob_include_cfg_log", {"include_patterns": ("*.cfg", "*.log")}),
        ("glob_exclude_py", {"exclude_patterns": ("*.py",)}),
        (
            "glob_ignore_case",
            {"include_patterns": ("*.txt",), "ignore_case": True},
        ),
        (
            "glob_case_sensitive",
            {"include_patterns": ("*.txt",), "ignore_case": False},
        ),
        (
            "glob_match_dirs",
            {"include_patterns": ("sub",), "match_dirs": True},
        ),
        ("custom_gitignore_only", {"gitignore_file": Path("__CUSTOM__")}),
    ],
    ids=lambda val: val if isinstance(val, str) else None,
)
def test_parity_empty_dirs_and_gitignore_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario: str,
    cfg_kwargs: ConfigOverrides,
) -> None:
    """Verify 100% parity across empty dirs, nested .gitignore negations, spaces, and excludes."""
    repo, custom_ignore = build_gitignore_and_exclude_tree(tmp_path)
    resolved_kwargs: ConfigOverrides = {**cfg_kwargs}
    if resolved_kwargs.get("gitignore_file") == Path("__CUSTOM__"):
        resolved_kwargs["gitignore_file"] = custom_ignore

    cfg = TraversalConfig(root_paths=(repo,), **resolved_kwargs)
    items = assert_traversal_parity(cfg, monkeypatch)
    if scenario == "default_gitignore":
        rel_names = {item.relative_path.as_posix() for item in items}
        assert "root_keep.log" in rel_names
        assert "sub/nested_keep.log" in rel_names
        assert "sub/anchored.cfg" in rel_names
        assert "anchored.cfg" not in rel_names
        assert "leading.py" in rel_names
        assert " leading.py" not in rel_names
        assert "keep.gitexcl" in rel_names
        assert "skip.gitexcl" not in rel_names
        assert "skip.globalign" not in rel_names


@pytest.mark.parametrize(
    ("scenario", "cfg_kwargs"),
    [
        ("unfollowed_default", {"follow_symlinks": False}),
        ("followed_cycle_safe", {"follow_symlinks": True}),
        ("prune_followed_cycles", {"follow_symlinks": True, "dirs_only": True, "prune_empty": True}),
        (
            "prune_followed_rust_only",
            {
                "follow_symlinks": True,
                "dirs_only": True,
                "prune_empty": True,
                "include_tags": frozenset({"rust"}),
            },
        ),
        ("depth_zero", {"max_depth": 0}),
        ("depth_one", {"max_depth": 1}),
        ("depth_two", {"max_depth": 2}),
        ("depth_three_followed", {"max_depth": 3, "follow_symlinks": True}),
        ("filelimit_zero", {"file_limit": 0}),
        ("filelimit_two", {"file_limit": 2}),
        ("filelimit_three", {"file_limit": 3}),
        ("filelimit_ten", {"file_limit": 10}),
        ("accumulate_du_files", {"accumulate_size": True}),
        ("accumulate_du_dirs", {"dirs_only": True, "accumulate_size": True}),
        ("relative_prefix", {"relative_prefix": True}),
    ],
    ids=lambda val: val if isinstance(val, str) else None,
)
def test_parity_symlinks_cycles_and_boundaries_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario: str,
    cfg_kwargs: ConfigOverrides,
) -> None:
    """Verify 100% parity across symlink loops, broken links, --prune, -L, --filelimit, and --du."""
    root, symlinks_ok = build_symlink_and_boundary_tree(tmp_path)
    cfg = TraversalConfig(root_paths=(root,), **cfg_kwargs)
    items = assert_traversal_parity(cfg, monkeypatch)
    if scenario == "depth_zero":
        assert all(len(item.relative_path.parts) == 1 for item in items)
    elif scenario == "filelimit_three":
        assert all("crowded" not in item.relative_path.parts for item in items)

    if symlinks_ok and scenario == "unfollowed_default":
        rust_ext = activate_rust_backend(monkeypatch)
        assert_classify_path_parity(rust_ext, root / "links" / "broken.py", root)


def test_parity_multi_root_single_file_and_missing_root_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify multi-root, single-file root, missing-root on_error, and #582 walker hook parity."""
    root, symlinks_ok = build_symlink_and_boundary_tree(tmp_path)
    missing = tmp_path / "does_not_exist_root"
    single_file = root / "top.py"
    cfg = TraversalConfig(root_paths=(single_file, root / "sparse", missing))
    items = assert_traversal_parity(cfg, monkeypatch)
    assert any(item.path == single_file.resolve() for item in items)

    if symlinks_ok:
        link_root = root / "links" / "valid_script"
        link_items = assert_traversal_parity(
            TraversalConfig(root_paths=(link_root,), follow_symlinks=False),
            monkeypatch,
        )
        assert len(link_items) == 1
        assert link_items[0].is_symlink is True

    manifest = tmp_path / "parity_manifest.txt"
    manifest.write_text("src/app.py\nsrc/link.py -> target.py\n", encoding="utf-8")
    manifest_items = assert_traversal_parity(
        TraversalConfig(from_file=str(manifest), offline=True),
        monkeypatch,
    )
    assert len(manifest_items) == 2

    rust_ext = activate_rust_backend(monkeypatch)

    class _WalkerExt(types.ModuleType):
        find_files_rs: Callable[..., Iterator[FileInfo | None]]
        find_files: Callable[..., Iterator[FileInfo | None]]
        classify_file_rs: Callable[..., FileInfo]
        classify_file: Callable[..., FileInfo]

    synth = _WalkerExt("findfmt._rust_ext")
    synth.find_files_rs = _fallback.find_files
    synth.find_files = _fallback.find_files
    synth.classify_file_rs = rust_ext.classify_file_rs
    synth.classify_file = rust_ext.classify_file
    assert assert_traversal_parity_with_ext(cfg, synth, monkeypatch) == items

    bad_synth = _WalkerExt("findfmt._rust_ext")
    bad_synth.find_files_rs = lambda *_a, **_kw: iter([None, *items])
    bad_synth.classify_file_rs = rust_ext.classify_file_rs
    bad_synth.classify_file = rust_ext.classify_file
    with pytest.raises(AssertionError, match="Unexpected find_files_rs item"):
        assert_traversal_parity_with_ext(cfg, bad_synth, monkeypatch)


def test_parity_cross_device_one_file_system(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify -x (one_file_system) parity on same-device and real secondary-mount symlinks."""
    root = tmp_path / "xdev_root"
    (root / "local_sub").mkdir(parents=True)
    (root / "local_sub" / "local.py").write_text("local = 1\n", encoding="utf-8")

    root_dev = root.stat().st_dev
    candidate_mounts: list[Path] = [Path("/dev/shm")]
    if hasattr(os, "getuid"):
        candidate_mounts.append(Path(f"/run/user/{os.getuid()}"))

    with contextlib.ExitStack() as exit_stack:
        linked_secondary = False
        for mount in candidate_mounts:
            with contextlib.suppress(OSError):
                if mount.is_dir() and mount.stat().st_dev != root_dev:
                    sec_tmp = Path(
                        exit_stack.enter_context(
                            tempfile.TemporaryDirectory(dir=mount, prefix="findfmt_xdev_"),
                        ),
                    )
                    (sec_tmp / "foreign.py").write_text("foreign = 1\n", encoding="utf-8")
                    (root / "foreign_mount").symlink_to(sec_tmp, target_is_directory=True)
                    linked_secondary = True
                    break

        confined_items = assert_traversal_parity(
            TraversalConfig(root_paths=(root,), follow_symlinks=True, one_file_system=True),
            monkeypatch,
        )
        unconfined_items = assert_traversal_parity(
            TraversalConfig(root_paths=(root,), follow_symlinks=True, one_file_system=False),
            monkeypatch,
        )
        confined_rels = {item.relative_path.as_posix() for item in confined_items}
        assert "local_sub/local.py" in confined_rels
        assert "foreign_mount/foreign.py" not in confined_rels
        if linked_secondary:
            unconfined_rels = {item.relative_path.as_posix() for item in unconfined_items}
            assert "foreign_mount/foreign.py" in unconfined_rels


@pytest.mark.parametrize(
    "sort_by",
    [
        SortKey.NAME,
        SortKey.SIZE,
        SortKey.MTIME,
        SortKey.TIME,
        SortKey.CTIME,
        SortKey.VERSION,
        SortKey.NONE,
    ],
)
@pytest.mark.parametrize("reverse_sort", [False, True], ids=["asc", "rev"])
@pytest.mark.parametrize(
    "order_flags",
    [
        (False, False, False),
        (True, False, False),
        (False, True, True),
    ],
    ids=["interleaved", "dirs_first", "files_first_icase"],
)
def test_parity_all_sorting_modes_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sort_by: SortKey,
    *,
    reverse_sort: bool,
    order_flags: tuple[bool, bool, bool],
) -> None:
    """Verify 100% sequence parity across all SortKey modes, Unicode digits, dirs_first, and reverse."""
    dirs_first, files_first, ignore_case = order_flags
    root = build_sorting_tree(tmp_path)
    cfg = TraversalConfig(
        root_paths=(root,),
        sort_by=sort_by,
        reverse_sort=reverse_sort,
        dirs_first=dirs_first,
        files_first=files_first,
        ignore_case=ignore_case,
    )
    items = assert_traversal_parity(cfg, monkeypatch)
    assert len(items) >= 16


@pytest.mark.parametrize(
    ("scenario", "cfg_kwargs"),
    [
        ("all_visible", {}),
        ("all_with_hidden", {"include_hidden": True}),
        ("python_tag", {"include_tags": frozenset({"python"})}),
        ("binary_tag", {"include_tags": frozenset({"binary"})}),
        ("text_exclude_python", {"include_tags": frozenset({"text"}), "exclude_tags": frozenset({"python"})}),
        (
            "all_tags_exec_python",
            {"include_tags": frozenset({"python", "executable"}), "all_tags": True},
        ),
        ("shebang_python3", {"shebang_filter": "python3"}),
        ("shebang_env_s", {"shebang_filter": "env -S"}),
        ("shebang_ruby", {"shebang_filter": "ruby"}),
        ("plist_tag", {"include_tags": frozenset({"plist"})}),
        ("dockerfile_or_makefile", {"include_tags": frozenset({"dockerfile", "makefile"})}),
        ("followed_links_hidden", {"include_hidden": True, "follow_symlinks": True}),
    ],
    ids=lambda val: val if isinstance(val, str) else None,
)
def test_parity_non_utf8_bidi_magic_shebang_and_filters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario: str,
    cfg_kwargs: ConfigOverrides,
) -> None:
    """Verify 100% parity on non-UTF-8 surrogateescape, bidi/control names, magic bytes, and shebangs."""
    root, probe_paths = build_classification_and_encoding_tree(tmp_path)
    rust_ext = activate_rust_backend(monkeypatch)

    # Keep a live AF_UNIX socket bound inside an isolated subdirectory during POSIX classification
    with contextlib.ExitStack() as exit_stack:
        if os.name == "posix" and hasattr(os, "mkfifo"):
            live_sock_dir = root / "live_sk"
            live_sock_dir.mkdir()
            prev_cwd = Path.cwd()
            os.chdir(live_sock_dir)
            try:
                srv = exit_stack.enter_context(socket.socket(socket.AF_UNIX, socket.SOCK_STREAM))
                srv.bind("s.sock")
                probe_paths.append(live_sock_dir / "s.sock")
            finally:
                os.chdir(prev_cwd)

        cfg = TraversalConfig(root_paths=(root,), **cfg_kwargs)
        _ = assert_traversal_parity(cfg, monkeypatch)

        if scenario == "all_with_hidden":
            for probe in probe_paths:
                assert_classify_path_parity(rust_ext, probe, root, follow_symlinks=False)
                assert_classify_path_parity(rust_ext, probe, root, follow_symlinks=True)

            with os.scandir(root) as scan_it:
                for entry in scan_it:
                    ep = Path(entry.path)
                    py_entry_info = _fallback.classify_file(ep, root_path=root, entry=entry)
                    rs_entry_info = rust_ext.classify_file_rs(ep, root_path=root, entry=entry)
                    assert isinstance(rs_entry_info, FileInfo)
                    assert_file_info_parity(rs_entry_info, py_entry_info)
