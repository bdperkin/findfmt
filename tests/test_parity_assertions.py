"""Assertion helpers and typed config overrides for findfmt Rust-vs-Python parity tests (#584)."""

from __future__ import annotations

import importlib
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

import pytest

from findfmt import _fallback, core
from findfmt.models import FileInfo, TraversalConfig

if TYPE_CHECKING:
    import types

_FILE_INFO_FIELDS = (
    "path",
    "relative_path",
    "tags",
    "shebang",
    "mime_type",
    "is_executable",
    "is_symlink",
    "symlink_target",
    "size_bytes",
    "permissions_str",
    "owner_user",
    "owner_group",
    "inode",
    "device",
    "accumulated_size",
    "mtime",
    "ctime",
    "indicator",
)


class ConfigOverrides(TypedDict, total=False):
    """Typed TraversalConfig keyword overrides for parameterized parity matrices."""

    include_tags: frozenset[str]
    exclude_tags: frozenset[str]
    all_tags: bool
    shebang_filter: str | None
    respect_gitignore: bool
    gitignore_file: Path | None
    include_hidden: bool
    follow_symlinks: bool
    dirs_only: bool
    one_file_system: bool
    max_depth: int | None
    file_limit: int | None
    prune_empty: bool
    include_patterns: tuple[str, ...]
    exclude_patterns: tuple[str, ...]
    ignore_case: bool
    match_dirs: bool
    relative_prefix: bool
    accumulate_size: bool


def activate_rust_backend(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Import findfmt._rust_ext (skipping if unbuilt) and force it active on findfmt.core."""
    try:
        rust_ext = importlib.import_module("findfmt._rust_ext")
    except ModuleNotFoundError:
        pytest.skip("findfmt._rust_ext is not compiled in this environment")

    monkeypatch.delenv("FINDFMT_NO_EXTENSIONS", raising=False)
    monkeypatch.setattr(core, "_RUST_EXT", rust_ext)
    return rust_ext


def assert_file_info_parity(rust_info: FileInfo, py_info: FileInfo) -> None:
    """Assert 100% field-by-field and dictionary serialization parity between two FileInfo items."""
    for field_name in _FILE_INFO_FIELDS:
        rs_val = getattr(rust_info, field_name)
        py_val = getattr(py_info, field_name)
        assert rs_val == py_val, (
            f"Field {field_name!r} mismatch for {py_info.path!r}: rust={rs_val!r} != python={py_val!r}"
        )

    assert rust_info == py_info
    assert rust_info.to_dict(absolute=False) == py_info.to_dict(absolute=False)
    assert rust_info.to_dict(absolute=True) == py_info.to_dict(absolute=True)


def assert_classify_path_parity(
    rust_ext: types.ModuleType,
    target: Path,
    root_path: Path,
    *,
    follow_symlinks: bool = False,
) -> None:
    """Assert direct classify_file_rs, classify_file, and core.classify_file match _fallback."""
    for follow in {False, follow_symlinks}:
        expected = _fallback.classify_file(
            target,
            root_path=root_path,
            prefix=Path("pfx"),
            accumulated_size=4096,
            follow_symlinks=follow,
        )
        rs_direct = rust_ext.classify_file_rs(
            target,
            root_path=root_path,
            prefix=Path("pfx"),
            accumulated_size=4096,
            follow_symlinks=follow,
        )
        rs_alias = rust_ext.classify_file(
            target,
            root_path=root_path,
            prefix=Path("pfx"),
            accumulated_size=4096,
            follow_symlinks=follow,
        )
        rs_gateway = core.classify_file(
            target,
            root_path=root_path,
            prefix=Path("pfx"),
            accumulated_size=4096,
            follow_symlinks=follow,
        )
        assert isinstance(rs_direct, FileInfo)
        assert isinstance(rs_alias, FileInfo)
        assert_file_info_parity(rs_direct, expected)
        assert_file_info_parity(rs_alias, expected)
        assert_file_info_parity(rs_gateway, expected)


def _verify_direct_walker_parity(
    rust_ext: types.ModuleType,
    config: TraversalConfig,
    py_items: list[FileInfo],
    py_errors: list[tuple[int | None, str | None]],
) -> None:
    """Verify exported _rust_ext walker functions directly without dropping unexpected items."""
    for walker_attr in ("find_files_rs", "find_files"):
        walker_fn = getattr(rust_ext, walker_attr, None)
        assert callable(walker_fn), f"Missing required callable {walker_attr!r} on findfmt._rust_ext"

        direct_errors: list[tuple[int | None, str | None]] = []
        direct_raw = walker_fn(
            config,
            on_error=lambda e, sink=direct_errors: sink.append((e.errno, e.filename)),
        )
        assert isinstance(direct_raw, Iterable), f"Expected iterable from {walker_attr}"
        direct_items: list[FileInfo] = []
        for raw_item in direct_raw:
            assert isinstance(raw_item, FileInfo), f"Unexpected {walker_attr} item: {raw_item!r}"
            direct_items.append(raw_item)

        assert direct_errors == py_errors
        for d_item, py_item in zip(direct_items, py_items, strict=True):
            assert_file_info_parity(d_item, py_item)


def assert_traversal_parity_with_ext(
    config: TraversalConfig,
    rust_ext: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> list[FileInfo]:
    """Compare _fallback.find_files against core.find_files and optional _rust_ext walker symbols."""
    monkeypatch.delenv("FINDFMT_NO_EXTENSIONS", raising=False)
    monkeypatch.setattr(core, "_RUST_EXT", rust_ext)

    py_errors: list[tuple[int | None, str | None]] = []
    rs_errors: list[tuple[int | None, str | None]] = []

    py_items = list(
        _fallback.find_files(config, on_error=lambda e: py_errors.append((e.errno, e.filename))),
    )
    rs_items = list(
        core.find_files(config, on_error=lambda e: rs_errors.append((e.errno, e.filename))),
    )
    assert rs_errors == py_errors
    assert len(rs_items) == len(py_items)
    for rs_item, py_item in zip(rs_items, py_items, strict=True):
        assert_file_info_parity(rs_item, py_item)

    _verify_direct_walker_parity(rust_ext, config, py_items, py_errors)

    default_root = config.root_paths[0] if config.root_paths else Path.cwd()
    for py_item in py_items[:12]:
        assert_classify_path_parity(
            rust_ext,
            py_item.path,
            default_root,
            follow_symlinks=config.follow_symlinks,
        )

    return py_items


def assert_traversal_parity(
    config: TraversalConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> list[FileInfo]:
    """Assert 100% FileInfo sequence, metadata, and error parity between Rust and _fallback."""
    rust_ext = activate_rust_backend(monkeypatch)
    return assert_traversal_parity_with_ext(config, rust_ext, monkeypatch)
