"""Runtime dispatch gateway between findfmt._rust_ext and pure-Python fallback (#578)."""

from __future__ import annotations

import importlib
import os
from typing import TYPE_CHECKING, Literal

from findfmt import _fallback

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator
    from pathlib import Path
    from types import ModuleType

    from findfmt.models import FileInfo, TraversalConfig

__all__ = [
    "classify_file",
    "find_files",
    "get_active_backend",
    "is_rust_backend_active",
]

_DISABLE_ENV_VAR = "FINDFMT_NO_EXTENSIONS"
_TRUTHY_ENV_VALUES: frozenset[str] = frozenset({"1", "true", "yes", "on"})


def _are_extensions_disabled() -> bool:
    """Return True when native extensions are disabled via FINDFMT_NO_EXTENSIONS."""
    return os.environ.get(_DISABLE_ENV_VAR, "").strip().lower() in _TRUTHY_ENV_VALUES


def _import_rust_ext() -> ModuleType | None:
    """Import findfmt._rust_ext unless disabled via environment or unavailable."""
    if _are_extensions_disabled():
        return None

    try:
        return importlib.import_module("findfmt._rust_ext")
    except ImportError:
        return None


_RUST_EXT: ModuleType | None = _import_rust_ext()


def _get_rust_ext() -> ModuleType | None:
    """Return the active native extension module when loaded and enabled."""
    if _are_extensions_disabled():
        return None

    return _RUST_EXT


def _is_rust_panic(exc: BaseException) -> bool:
    """Return True when exc is a PyO3 Rust panic exception (pyo3_runtime.PanicException)."""
    cls = type(exc)
    return cls.__name__ == "PanicException" and cls.__module__.startswith("pyo3_runtime")


def is_rust_backend_active() -> bool:
    """Return True when the native findfmt._rust_ext backend is loaded and enabled."""
    return _get_rust_ext() is not None


def get_active_backend() -> Literal["rust", "python"]:
    """Return the active runtime backend identifier ('rust' or 'python')."""
    return "rust" if is_rust_backend_active() else "python"


def classify_file(  # noqa: PLR0913 - public API signature parity
    path: Path,
    root_path: Path | None = None,
    prefix: Path | None = None,
    accumulated_size: int | None = None,
    *,
    entry: os.DirEntry[str] | None = None,
    follow_symlinks: bool = False,
) -> FileInfo:
    """Classify a file via findfmt._rust_ext when available, falling back to pure Python."""
    rust_ext = _get_rust_ext()
    rust_classify: Callable[..., FileInfo] | None = (
        getattr(rust_ext, "classify_file", None) if rust_ext is not None else None
    )
    if rust_classify is not None:
        try:
            return rust_classify(
                path,
                root_path,
                prefix,
                accumulated_size,
                entry=entry,
                follow_symlinks=follow_symlinks,
            )
        except BaseException as exc:
            if not _is_rust_panic(exc):
                raise

    return _fallback.classify_file(
        path,
        root_path,
        prefix,
        accumulated_size,
        entry=entry,
        follow_symlinks=follow_symlinks,
    )


def find_files(
    config: TraversalConfig,
    *,
    on_error: Callable[[OSError], None] | None = None,
) -> Iterator[FileInfo]:
    """Discover and classify files via findfmt._rust_ext when available, falling back to pure Python."""
    rust_ext = _get_rust_ext()
    rust_find: Callable[..., Iterable[FileInfo]] | None = (
        getattr(rust_ext, "find_files", None) if rust_ext is not None else None
    )
    if rust_find is not None:
        yielded_paths: set[Path] = set()
        try:
            for file_info in rust_find(config, on_error=on_error):
                yielded_paths.add(file_info.path)
                yield file_info
        except BaseException as exc:
            if not _is_rust_panic(exc):
                raise

            for file_info in _fallback.find_files(config, on_error=on_error):
                if file_info.path not in yielded_paths:
                    yield file_info

            return
        else:
            return

    yield from _fallback.find_files(config, on_error=on_error)
