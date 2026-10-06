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


def _resolve_relative(path: Path, root_path: Path | None) -> Path:
    """Compute relative path from root_path if provided.

    Args:
        path: Target file path.
        root_path: Optional root directory path.

    Returns:
        Relative path if root_path is given and matches, otherwise original path.
    """
    if root_path is None:
        return path
    try:
        return path.resolve().relative_to(root_path.resolve())
    except ValueError:
        return path


def _identify_tags(path: Path, str_path: str, *, exists: bool) -> set[str]:
    """Extract identify tags with fallback handling.

    Args:
        path: Target file path.
        str_path: String representation of path.
        exists: Flag indicating whether path exists on disk.

    Returns:
        Set of tag strings identified for the file.
    """
    try:
        if exists:
            return set(identify_engine.tags_from_path(str_path))
        return set(identify_engine.tags_from_filename(path.name))
    except (ValueError, OSError):
        return set(identify_engine.tags_from_filename(path.name))


def _shebang_info(
    path: Path, str_path: str, *, is_file: bool, is_symlink: bool
) -> tuple[str | None, set[str]]:
    """Extract shebang and interpreter tags if applicable.

    Args:
        path: Target file path.
        str_path: String representation of path.
        is_file: Flag indicating whether path is a regular file.
        is_symlink: Flag indicating whether path is a symbolic link.

    Returns:
        Tuple containing shebang string (or None) and set of tags.
    """
    if not (is_file and not is_symlink):
        return None, set()

    shebang = extract_shebang(path)
    tags: set[str] = set()
    if shebang:
        parts = identify_engine.parse_shebang_from_file(str_path)
        for part in parts:
            tags.update(identify_engine.tags_from_interpreter(part))
    return shebang, tags


def _mime_info(str_path: str) -> tuple[str | None, set[str]]:
    """Extract MIME type and MIME-derived tags.

    Args:
        str_path: String representation of the file path.

    Returns:
        Tuple containing MIME type string (or None) and set of MIME tags.
    """
    mime_type, _ = mimetypes.guess_type(str_path)
    tags: set[str] = set()
    if mime_type:
        tags.add(f"mime:{mime_type}")
        category = mime_type.split("/", 1)[0]
        tags.add(category)
    return mime_type, tags


def classify_file(path: Path, root_path: Path | None = None) -> FileInfo:
    """Classify a given file path by inspection of name, content, and metadata.

    Args:
        path: The path of the file to classify.
        root_path: Optional root directory used to compute relative_path.

    Returns:
        FileInfo containing metadata, identified tags, shebang, and MIME info.
    """
    str_path = str(path)
    try:
        is_symlink = path.is_symlink()
    except OSError:
        is_symlink = False

    stat_result: os.stat_result | None = None
    try:
        stat_result = path.lstat() if is_symlink else path.stat()
    except OSError:
        stat_result = None

    size_bytes = stat_result.st_size if stat_result else 0

    try:
        exists = path.exists()
    except OSError:
        exists = False

    is_executable = os.access(path, os.X_OK) if exists else False
    is_file = path.is_file() if exists else False

    tags = _identify_tags(path, str_path, exists=exists)
    shebang, shebang_tags = _shebang_info(path, str_path, is_file=is_file, is_symlink=is_symlink)
    tags.update(shebang_tags)

    mime_type, mime_tags = _mime_info(str_path)
    tags.update(mime_tags)

    relative_path = _resolve_relative(path, root_path)
    resolved_path = path.resolve() if exists else path

    return FileInfo(
        path=resolved_path,
        relative_path=relative_path,
        tags=frozenset(tags),
        shebang=shebang,
        mime_type=mime_type,
        is_executable=is_executable,
        is_symlink=is_symlink,
        size_bytes=size_bytes,
    )
