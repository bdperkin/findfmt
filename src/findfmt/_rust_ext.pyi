import os
from collections.abc import Iterable
from pathlib import Path

from findfmt.models import FileInfo

def backend_name() -> str: ...
def rust_ext_version() -> str: ...
def classify_file_rs(
    path: Path,
    root_path: Path | None = None,
    prefix: Path | None = None,
    accumulated_size: int | None = None,
    *,
    entry: os.DirEntry[str] | None = None,
    follow_symlinks: bool = False,
) -> FileInfo: ...
def classify_file(
    path: Path,
    root_path: Path | None = None,
    prefix: Path | None = None,
    accumulated_size: int | None = None,
    *,
    entry: os.DirEntry[str] | None = None,
    follow_symlinks: bool = False,
) -> FileInfo: ...
def classify_batch_rs(
    candidates: Iterable[tuple[Path, os.DirEntry[str] | None, int | None]],
    *,
    root_path: Path | None = None,
    prefix: Path | None = None,
    follow_symlinks: bool = False,
    include_tags: Iterable[str] | None = None,
    exclude_tags: Iterable[str] | None = None,
    all_tags: bool = False,
    shebang_filter: str | None = None,
) -> list[FileInfo]: ...
