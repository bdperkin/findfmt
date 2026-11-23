"""Unit tests for native Rust batch traversal, live MIME refresh, and chunking (#583)."""

from __future__ import annotations

import contextlib
import contextvars
import importlib
import mimetypes
import os
import stat
import types
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from findfmt import _fallback, classifier, core
from findfmt.models import FileInfo, TraversalConfig
from findfmt.traversal._batch_dispatch import RUST_BATCH_CHUNK_SIZE
from findfmt.traversal._pruning import ACTIVE_RUST_BATCH_HOOKS

if TYPE_CHECKING:
    from collections.abc import Callable


def _load_rust_ext() -> types.ModuleType:
    """Import compiled findfmt._rust_ext or skip when built with HATCH_MATURIN_DISABLE=1."""
    try:
        return importlib.import_module("findfmt._rust_ext")
    except ModuleNotFoundError:
        pytest.skip("findfmt._rust_ext is not compiled in this environment")


def _make_rust_panic_cls() -> type[BaseException]:
    """Create a synthetic PyO3 PanicException subclassing BaseException in pyo3_runtime."""
    return type("PanicException", (BaseException,), {"__module__": "pyo3_runtime"})


def test_combined_traversal_batch_filtering_and_gateway_fallbacks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify combined GIL-released batch pass parity and gateway fallback branches (#583)."""
    py_script = tmp_path / "tool"
    py_script.write_text("#!/usr/bin/env -S python3 -u\nprint('hi')\n", encoding="utf-8")
    py_script.chmod(py_script.stat().st_mode | stat.S_IXUSR)
    rs_file = tmp_path / "lib.rs"
    rs_file.write_text("pub fn run() {}\n", encoding="utf-8")
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("hello\n", encoding="utf-8")

    configs = [
        TraversalConfig(root_paths=(tmp_path,)),
        TraversalConfig(root_paths=(tmp_path,), include_tags=frozenset({"python"})),
        TraversalConfig(
            root_paths=(tmp_path,),
            include_tags=frozenset({"python", "executable"}),
            all_tags=True,
            shebang_filter="python3",
        ),
        TraversalConfig(
            root_paths=(tmp_path,),
            include_tags=frozenset({"text"}),
            exclude_tags=frozenset({"rust"}),
            include_patterns=("*.txt",),
        ),
    ]
    monkeypatch.delenv("FINDFMT_NO_EXTENSIONS", raising=False)
    with contextlib.suppress(ModuleNotFoundError):
        monkeypatch.setattr(core, "_RUST_EXT", importlib.import_module("findfmt._rust_ext"))

    for cfg in configs:
        rust_results = list(core.find_files(cfg))
        py_results = list(_fallback.find_files(cfg))
        assert rust_results == py_results

    # Non-native DirEntry (MagicMock) falls back to pure-Python classifier cleanly
    mock_entry = MagicMock(spec=os.DirEntry)
    mock_entry.is_symlink.return_value = False
    mock_entry.stat.return_value = txt_file.stat()
    info_mock = core.classify_file(txt_file, root_path=tmp_path, entry=mock_entry)
    assert "text" in info_mock.tags

    # PanicException in classify_batch_rs falls back seamlessly; non-panic propagates
    panic_cls = _make_rust_panic_cls()

    class _BatchExt(types.ModuleType):
        classify_batch_rs: Callable[..., list[FileInfo]]
        classify_file: Callable[..., FileInfo]

    batch_ext = _BatchExt("findfmt._rust_ext")
    monkeypatch.setattr(core, "_RUST_EXT", batch_ext)
    cfg_all = TraversalConfig(root_paths=(tmp_path,), include_patterns=("*.rs", "*.txt"))

    raw_items = list(_fallback.find_files(TraversalConfig(root_paths=(tmp_path,))))
    batch_ext.classify_batch_rs = lambda *_a, **_kw: raw_items
    batch_ext.classify_file = classifier.classify_file
    assert list(core.find_files(cfg_all)) == list(_fallback.find_files(cfg_all))
    cfg_prune = TraversalConfig(
        root_paths=(tmp_path,),
        dirs_only=True,
        prune_empty=True,
        include_tags=frozenset({"rust"}),
    )
    assert list(core.find_files(cfg_prune)) == list(_fallback.find_files(cfg_prune))

    def _panic_batch(*_args: object, **_kwargs: object) -> list[FileInfo]:
        msg = "simulated batch panic"
        raise panic_cls(msg)

    batch_ext.classify_batch_rs = _panic_batch
    assert list(core.find_files(cfg_all)) == list(_fallback.find_files(cfg_all))

    def _error_batch(*_args: object, **_kwargs: object) -> list[FileInfo]:
        msg = "unexpected batch runtime error"
        raise RuntimeError(msg)

    batch_ext.classify_batch_rs = _error_batch
    with pytest.raises(RuntimeError, match="unexpected batch runtime error"):
        list(core.find_files(cfg_all))


def test_live_mime_refresh_and_uri_schemes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify runtime mimetypes.add_type, directory-MIME filter parity, and scheme-prefixed names."""
    rust_ext = _load_rust_ext()
    monkeypatch.delenv("FINDFMT_NO_EXTENSIONS", raising=False)
    monkeypatch.setattr(core, "_RUST_EXT", rust_ext)

    warmup = tmp_path / "warmup.py"
    warmup.write_text("x = 1\n", encoding="utf-8")
    _ = rust_ext.classify_file_rs(warmup, root_path=tmp_path)

    custom_file = tmp_path / "sample.examplefmt583"
    custom_file.write_text("payload\n", encoding="utf-8")
    dir_mime_file = tmp_path / "card.dirfmt583"
    dir_mime_file.write_text("BEGIN:VCARD\n", encoding="utf-8")
    extless_file = tmp_path / "EXTLESS583"
    extless_file.write_text("plain\n", encoding="utf-8")
    upper_py = tmp_path / "upper.PY"
    upper_py.write_text("x = 2\n", encoding="utf-8")
    db = getattr(mimetypes, "_db", None)
    strict_map = db.types_map[True] if db is not None else {}
    had_empty = "" in strict_map
    prev_empty = strict_map.get("")
    try:
        mimetypes.add_type("application/x-example583", ".examplefmt583")
        mimetypes.add_type("directory/x-dirfmt583", ".dirfmt583")
        mimetypes.add_type("application/x-extless583", "")
        strict_map[".PY"] = "text/x-custom-upper-py"
        for target in (custom_file, extless_file, upper_py):
            assert rust_ext.classify_file_rs(target, root_path=tmp_path) == classifier.classify_file(
                target,
                root_path=tmp_path,
            )

        sb_cfg = TraversalConfig(root_paths=(tmp_path,), shebang_filter="nonexistent_interp")
        assert list(core.find_files(sb_cfg)) == list(_fallback.find_files(sb_cfg))
    finally:
        strict_map.pop(".examplefmt583", None)
        strict_map.pop(".dirfmt583", None)
        strict_map.pop(".PY", None)
        if had_empty and prev_empty is not None:
            strict_map[""] = prev_empty
        else:
            strict_map.pop("", None)

    if os.name == "posix":
        uri_dir = tmp_path / "uris"
        uri_dir.mkdir()
        monkeypatch.chdir(uri_dir)
        for name in ("data:,hello", "data:hello", "http:report.py;v=1", " https:report.py?download=1"):
            p = Path(name)
            p.write_text("body\n", encoding="utf-8")
            assert rust_ext.classify_file_rs(p) == classifier.classify_file(p)


def test_bounded_chunk_batch_emission_and_context_isolation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify bounded-chunk streaming and ContextVar hook reset across paused core.find_files yields."""
    rust_ext = _load_rust_ext()
    monkeypatch.delenv("FINDFMT_NO_EXTENSIONS", raising=False)
    monkeypatch.setattr(core, "_RUST_EXT", rust_ext)

    chunk_dir = tmp_path / "chunked"
    chunk_dir.mkdir()
    total = RUST_BATCH_CHUNK_SIZE + 10
    for idx in range(total):
        (chunk_dir / f"f_{idx:04d}.py").write_text("x = 1\n", encoding="utf-8")

    chunk_sizes: list[int] = []
    orig_batch = rust_ext.classify_batch_rs

    def _recording_batch(candidates: list[object], *args: object, **kwargs: object) -> list[FileInfo]:
        chunk_sizes.append(len(candidates))
        raw = orig_batch(candidates, *args, **kwargs)
        assert isinstance(raw, list)
        return [item for item in raw if isinstance(item, FileInfo)]

    class _ClassifierOnlyExt(types.ModuleType):
        classify_file_rs: Callable[..., FileInfo]
        classify_file: Callable[..., FileInfo]
        classify_batch_rs: Callable[..., list[FileInfo]]

    cls_only_ext = _ClassifierOnlyExt("findfmt._rust_ext")
    cls_only_ext.classify_file_rs = rust_ext.classify_file_rs
    cls_only_ext.classify_file = rust_ext.classify_file
    cls_only_ext.classify_batch_rs = _recording_batch
    monkeypatch.setattr(core, "_RUST_EXT", cls_only_ext)

    chunk_cfg = TraversalConfig(root_paths=(chunk_dir,), include_tags=frozenset({"python"}))
    it = core.find_files(chunk_cfg)
    first_item = next(it)
    assert ACTIVE_RUST_BATCH_HOOKS.get() is None
    assert first_item.relative_path == Path("f_0000.py")
    assert chunk_sizes == [RUST_BATCH_CHUNK_SIZE]
    rest = list(it)
    assert len(rest) == total - 1
    assert chunk_sizes == [RUST_BATCH_CHUNK_SIZE, 10]

    # Closing a paused core.find_files iterator from a separate ContextVar Context never raises ValueError
    paused_it = core.find_files(chunk_cfg)
    assert isinstance(paused_it, types.GeneratorType)
    _ = next(paused_it)
    contextvars.copy_context().run(paused_it.close)

    # Full native walker streaming parity over > RUST_BATCH_CHUNK_SIZE files
    monkeypatch.setattr(core, "_RUST_EXT", rust_ext)
    native_it = core.find_files(chunk_cfg)
    assert next(native_it).relative_path == Path("f_0000.py")
    assert len(list(native_it)) == total - 1
