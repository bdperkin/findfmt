"""File classification and content analysis engine."""

from __future__ import annotations

import io
import mimetypes
import os
import stat
from pathlib import Path

import identify.identify as identify_engine

from findfmt.metadata import extract_metadata
from findfmt.models import FileInfo
from findfmt.utils.strings import get_classification_indicator

__all__ = [
    "classify_file",
    "compute_relative_prefix",
    "extract_shebang",
    "extract_shebang_from_buffer",
    "get_known_tags",
]


def get_known_tags() -> frozenset[str]:
    """Retrieve all known format and type tags recognized by the engine.

    Returns:
        frozenset of all recognized string tags.
    """
    return frozenset(identify_engine.ALL_TAGS)


def extract_shebang_from_buffer(buffer: bytes) -> str | None:
    """Extract shebang interpreter line from a pre-read file buffer.

    Args:
        buffer: Initial bytes read from the file.

    Returns:
        The raw shebang line string if present and valid, or None.
    """
    if buffer.startswith(b"#!"):
        first_line = buffer.split(b"\n", 1)[0]
        return first_line.decode("utf-8", errors="replace").strip()

    return None


def extract_shebang(path: Path) -> str | None:
    """Extract the shebang interpreter from the top of an executable file.

    Args:
        path: Path to the target file.

    Returns:
        The raw shebang line string if present and readable, or None.
    """
    try:
        if not path.is_file():
            return None

        with path.open("rb") as f:
            return extract_shebang_from_buffer(f.readline(512))
    except (OSError, UnicodeDecodeError):
        return None


def compute_relative_prefix(root: Path) -> Path | None:
    """Compute relative prefix from an input root path.

    Args:
        root: Target search root path.

    Returns:
        Relative Path prefix to prepend, or None if no prefix is needed.
    """
    if root.is_absolute():
        try:
            rel = root.resolve().relative_to(Path.cwd().resolve())
            return rel if rel != Path() else None
        except ValueError:
            return root

    return root if root != Path() else None


def _resolve_relative(
    path: Path,
    root_path: Path | None,
    prefix: Path | None = None,
) -> Path:
    """Compute relative path from root_path if provided.

    Args:
        path: Target file path.
        root_path: Optional root directory path.
        prefix: Optional prefix to prepend to relative path.

    Returns:
        Relative path if root_path is given and matches, otherwise original path.
    """
    if root_path is None:
        return path

    try:
        rel = path.relative_to(root_path)
    except ValueError:
        try:
            rel_str = os.path.relpath(path, root_path)
            if rel_str.startswith(".."):
                return path

            rel = Path(rel_str)
        except (ValueError, OSError):
            return path

    if prefix is not None and prefix != Path():
        return prefix / rel

    return rel


def _read_initial_buffer(path: Path, max_bytes: int = 2048) -> bytes:
    """Read initial bytes once for shebang, encoding, and content checks.

    Args:
        path: Path to target file.
        max_bytes: Maximum number of bytes to read into memory.

    Returns:
        Bytes buffer if successfully read, otherwise empty bytes.
    """
    try:
        with path.open("rb") as f:
            return f.read(max_bytes)
    except OSError:
        return b""


def _identify_tags_from_buffer(
    name: str,
    buffer: bytes,
    *,
    is_executable: bool,
) -> set[str]:
    """Identify file tags directly from an in-memory buffer."""
    tags = {identify_engine.FILE}
    tags.add(
        identify_engine.EXECUTABLE if is_executable else identify_engine.NON_EXECUTABLE,
    )
    t = identify_engine.tags_from_filename(name)
    if t:
        tags.update(t)
    elif is_executable and buffer.startswith(b"#!"):
        parts = identify_engine.parse_shebang(io.BytesIO(buffer))
        if parts:
            tags.update(identify_engine.tags_from_interpreter(parts[0]))

    if not (identify_engine.ENCODING_TAGS & tags):
        if identify_engine.is_text(io.BytesIO(buffer)):
            tags.add(identify_engine.TEXT)
        else:
            tags.add(identify_engine.BINARY)

    return tags


def _identify_tags(  # noqa: PLR0913
    path: Path,
    str_path: str,
    *,
    exists: bool,
    is_regular_or_symlink: bool = True,
    buffer: bytes | None = None,
    is_executable: bool = False,
) -> set[str]:
    """Extract identify tags with fallback handling, using buffer if available.

    Args:
        path: Target file path.
        str_path: String representation of path.
        exists: Flag indicating whether path exists on disk.
        is_regular_or_symlink: Flag indicating whether path is regular file or symlink.
        buffer: Optional pre-read file content buffer.
        is_executable: Flag indicating whether file is executable.

    Returns:
        Set of tag strings identified for the file.
    """
    try:
        if not exists or not is_regular_or_symlink:
            return set(identify_engine.tags_from_filename(path.name))

        if buffer is not None:
            return _identify_tags_from_buffer(path.name, buffer, is_executable=is_executable)

        return set(identify_engine.tags_from_path(str_path))
    except (ValueError, OSError):
        return set(identify_engine.tags_from_filename(path.name))


def _shebang_info(
    path: Path,
    str_path: str,
    *,
    is_file: bool,
    is_symlink: bool,
    buffer: bytes | None = None,
) -> tuple[str | None, set[str]]:
    """Extract shebang and interpreter tags if applicable.

    Args:
        path: Target file path.
        str_path: String representation of path.
        is_file: Flag indicating whether path is a regular file.
        is_symlink: Flag indicating whether path is a symbolic link.
        buffer: Optional pre-read file content buffer.

    Returns:
        Tuple containing shebang string (or None) and set of tags.
    """
    if not (is_file and not is_symlink):
        return None, set()

    shebang = extract_shebang_from_buffer(buffer) if buffer is not None else extract_shebang(path)
    tags: set[str] = set()
    if shebang:
        parts = (
            identify_engine.parse_shebang(io.BytesIO(buffer))
            if buffer is not None
            else identify_engine.parse_shebang_from_file(str_path)
        )
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


def _check_executable(path: Path, *, exists: bool, shebang: str | None = None) -> bool:
    """Determine whether a file is executable across POSIX and Windows platforms.

    Args:
        path: File path to check.
        exists: Flag indicating whether path exists on disk.
        shebang: Optional shebang line string if detected.

    Returns:
        True if the file is considered executable on the host platform.
    """
    if not exists:
        return False

    if os.name == "nt":
        pathext = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD;.VBS;.JS;.WS;.MSC").split(";")
        has_pathext = any(path.name.upper().endswith(ext.upper()) for ext in pathext if ext)
        return has_pathext or bool(shebang)

    return os.access(path, os.X_OK)


def _inspect_entry_metadata(
    path: Path,
    entry: os.DirEntry[str],
) -> tuple[bool, bool, bool, int, os.stat_result | None]:
    """Inspect metadata from an os.DirEntry object."""
    try:
        is_symlink = entry.is_symlink()
    except OSError:
        is_symlink = False

    try:
        stat_result = entry.stat(follow_symlinks=not is_symlink)
        size_bytes = stat_result.st_size
        exists = True
        is_file = stat.S_ISREG(stat_result.st_mode)
    except OSError:
        stat_result = None
        size_bytes = 0
        exists = False
        is_file = False

    if is_symlink and exists:
        try:
            is_file = path.is_file()
        except OSError:
            is_file = False

    return is_symlink, exists, is_file, size_bytes, stat_result


def _inspect_path_metadata(
    path: Path,
) -> tuple[bool, bool, bool, int, os.stat_result | None]:
    """Inspect filesystem metadata directly from a Path object."""
    try:
        is_symlink = path.is_symlink()
    except OSError:
        is_symlink = False

    try:
        stat_result = path.lstat() if is_symlink else path.stat()
        size_bytes = stat_result.st_size
    except OSError:
        stat_result = None
        size_bytes = 0

    try:
        exists = path.exists()
        is_file = path.is_file() if exists else False
    except OSError:
        exists = False
        is_file = False

    return is_symlink, exists, is_file, size_bytes, stat_result


def _inspect_metadata(
    path: Path,
    entry: os.DirEntry[str] | None = None,
) -> tuple[bool, bool, bool, int, os.stat_result | None]:
    """Inspect filesystem metadata safely, reusing DirEntry when available.

    Args:
        path: File path to inspect.
        entry: Optional os.DirEntry from directory scanning.

    Returns:
        Tuple of (is_symlink, exists, is_file, size_bytes, stat_result).
    """
    if entry is not None:
        return _inspect_entry_metadata(path, entry)

    return _inspect_path_metadata(path)


def _adjust_nt_tags(tags: set[str], *, is_executable: bool) -> None:
    """Adjust executable tags on Windows platform.

    Args:
        tags: Set of tags to modify in place.
        is_executable: Flag indicating whether path is executable.
    """
    if os.name != "nt":
        return

    if is_executable:
        tags.discard("non-executable")
        tags.add("executable")
    else:
        tags.discard("executable")
        tags.add("non-executable")


def _extract_timestamps_and_indicator(  # noqa: PLR0913
    path: Path,
    stat_result: os.stat_result | None,
    *,
    exists: bool,
    is_file: bool,
    is_symlink: bool,
    is_executable: bool,
) -> tuple[float | None, float | None, str | None]:
    """Extract mtime, ctime, and classification indicator safely."""
    if stat_result is not None:
        mtime: float | None = stat_result.st_mtime
        ctime: float | None = stat_result.st_ctime
        is_dir = stat.S_ISDIR(stat_result.st_mode)
    else:
        mtime = None
        ctime = None
        is_dir = exists and not is_file and not is_symlink and path.is_dir()

    indicator = get_classification_indicator(
        is_dir=is_dir,
        is_symlink=is_symlink,
        is_executable=is_executable and not is_dir,
        stat_result=stat_result,
    )
    return mtime, ctime, indicator


def classify_file(
    path: Path,
    root_path: Path | None = None,
    prefix: Path | None = None,
    accumulated_size: int | None = None,
    *,
    entry: os.DirEntry[str] | None = None,
) -> FileInfo:
    """Classify a given file path by inspection of name, content, and metadata.

    Args:
        path: The path of the file to classify.
        root_path: Optional root directory used to compute relative_path.
        prefix: Optional prefix to prepend to relative_path.
        accumulated_size: Optional accumulated directory disk usage in bytes.
        entry: Optional os.DirEntry metadata from scandir.

    Returns:
        FileInfo containing metadata, identified tags, shebang, and MIME info.
    """
    str_path = str(path)
    is_symlink, exists, is_file, size_bytes, stat_result = _inspect_metadata(path, entry=entry)
    permissions_str, owner_user, owner_group, inode, device = extract_metadata(stat_result)

    buffer: bytes | None = None
    if exists and is_file and not is_symlink:
        buffer = _read_initial_buffer(path) if size_bytes > 0 else b""

    shebang, shebang_tags = _shebang_info(
        path,
        str_path,
        is_file=is_file,
        is_symlink=is_symlink,
        buffer=buffer,
    )
    is_executable = _check_executable(path, exists=exists, shebang=shebang)

    tags = _identify_tags(
        path,
        str_path,
        exists=exists,
        is_regular_or_symlink=is_file or is_symlink,
        buffer=buffer,
        is_executable=is_executable,
    )
    tags.update(shebang_tags)
    _adjust_nt_tags(tags, is_executable=is_executable)

    mime_type, mime_tags = _mime_info(str_path)
    tags.update(mime_tags)

    relative_path = _resolve_relative(path, root_path, prefix=prefix)
    resolved_path = path.resolve() if (is_symlink or entry is None) and exists else path
    effective_size = accumulated_size if accumulated_size is not None else size_bytes
    mtime, ctime, indicator = _extract_timestamps_and_indicator(
        path,
        stat_result,
        exists=exists,
        is_file=is_file,
        is_symlink=is_symlink,
        is_executable=is_executable,
    )

    return FileInfo(
        path=resolved_path,
        relative_path=relative_path,
        tags=frozenset(tags),
        shebang=shebang,
        mime_type=mime_type,
        is_executable=is_executable,
        is_symlink=is_symlink,
        size_bytes=effective_size,
        permissions_str=permissions_str,
        owner_user=owner_user,
        owner_group=owner_group,
        inode=inode,
        device=device,
        accumulated_size=accumulated_size,
        mtime=mtime,
        ctime=ctime,
        indicator=indicator,
    )
