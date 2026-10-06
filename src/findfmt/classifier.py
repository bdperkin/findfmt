"""File classification and content analysis engine."""

from __future__ import annotations

import mimetypes
import os
from typing import TYPE_CHECKING

import identify.identify as identify_engine

from findfmt.models import FileInfo

if TYPE_CHECKING:
    from pathlib import Path


def get_known_tags() -> frozenset[str]:
    """Retrieve all known format and type tags recognized by the engine.

    Returns:
        frozenset of all recognized string tags.
    """
    return frozenset(identify_engine.ALL_TAGS)


def extract_shebang(path: Path) -> str | None:
    """Extract the shebang interpreter from the top of an executable file.

    Args:
        path: Path to the target file.

    Returns:
        The raw shebang line string if present and readable, or None.
    """
    try:
        with path.open("rb") as f:
            first_line = f.readline(512)
            if first_line.startswith(b"#!"):
                return first_line.decode("utf-8", errors="replace").strip()
    except (OSError, UnicodeDecodeError):
        return None
    return None


def classify_file(path: Path, root_path: Path | None = None) -> FileInfo:
    """Classify a given file path by inspection of name, content, and metadata.

    Args:
        path: The path of the file to classify.
        root_path: Optional root directory used to compute relative_path.

    Returns:
        FileInfo containing metadata, identified tags, shebang, and MIME info.
    """
    str_path = str(path)
    is_symlink = path.is_symlink()
    stat_result: os.stat_result | None = None

    try:
        stat_result = path.lstat() if is_symlink else path.stat()
    except OSError:
        stat_result = None

    size_bytes = stat_result.st_size if stat_result else 0
    is_executable = os.access(path, os.X_OK) if path.exists() else False

    # Extract tags via identify engine with fallback handling
    tags: set[str] = set()
    try:
        if path.exists():
            tags.update(identify_engine.tags_from_path(str_path))
        else:
            tags.update(identify_engine.tags_from_filename(path.name))
    except (ValueError, OSError):
        # Fallback to pure filename-based detection if file cannot be read
        tags.update(identify_engine.tags_from_filename(path.name))

    # Shebang detection
    shebang: str | None = None
    if path.is_file() and not is_symlink:
        shebang = extract_shebang(path)
        if shebang:
            interpreter_parts = identify_engine.parse_shebang_from_file(str_path)
            for part in interpreter_parts:
                tags.update(identify_engine.tags_from_interpreter(part))

    # MIME type detection
    mime_type, _ = mimetypes.guess_type(str_path)
    if mime_type:
        tags.add(f"mime:{mime_type}")
        # Add primary MIME category tag (e.g., 'text' from 'text/plain')
        category = mime_type.split("/", 1)[0]
        tags.add(category)

    # Determine relative path
    relative_path: Path
    if root_path is not None:
        try:
            relative_path = path.resolve().relative_to(root_path.resolve())
        except ValueError:
            relative_path = path
    else:
        relative_path = path

    return FileInfo(
        path=path.resolve() if path.exists() else path,
        relative_path=relative_path,
        tags=frozenset(tags),
        shebang=shebang,
        mime_type=mime_type,
        is_executable=is_executable,
        is_symlink=is_symlink,
        size_bytes=size_bytes,
    )
