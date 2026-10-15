"""Core data models and configurations for findfmt."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

__all__ = ["FileInfo", "SortKey", "TraversalConfig"]


class SortKey(str, Enum):
    """Sort criteria keys for directory traversal."""

    NAME = "name"
    VERSION = "version"
    TIME = "time"
    MTIME = "mtime"
    CTIME = "ctime"
    SIZE = "size"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class FileInfo:
    """Represents file metadata, classification tags, and content attributes.

    Attributes:
        path: Absolute path to the file.
        relative_path: Path relative to the traversal root.
        tags: Set of tags assigned by the classifier (e.g., 'python', 'text').
        shebang: Extracted shebang line if present, otherwise None.
        mime_type: Detected MIME type if available, otherwise None.
        is_executable: Whether the file has executable permissions.
        is_symlink: Whether the path is a symbolic link.
        symlink_target: Target path if the file is a symbolic link, otherwise None.
        size_bytes: File size in bytes.
        permissions_str: Formatted file mode in standard ls -l format (e.g. -rw-r--r--).
        owner_user: File owner username or UID if username is unavailable.
        owner_group: File owner group name or GID if group name is unavailable.
        inode: Filesystem inode number (st_ino).
        device: Filesystem device number (st_dev).
        accumulated_size: Accumulated directory disk usage in bytes if --du is active.
    """

    path: Path
    relative_path: Path
    tags: frozenset[str] = field(default_factory=frozenset)
    shebang: str | None = None
    mime_type: str | None = None
    is_executable: bool = False
    is_symlink: bool = False
    symlink_target: str | None = None
    size_bytes: int = 0
    permissions_str: str | None = None
    owner_user: str | None = None
    owner_group: str | None = None
    inode: int | None = None
    device: int | None = None
    accumulated_size: int | None = None
    mtime: float | None = None
    ctime: float | None = None
    indicator: str | None = None

    def to_dict(self, *, absolute: bool = False) -> dict[str, Any]:
        """Serialize file attributes to a dictionary representation.

        Args:
            absolute: Whether the 'path' entry contains the absolute path.

        Returns:
            Dictionary mapping attribute names to serialized values.
        """
        result: dict[str, Any] = {
            "path": str(self.path if absolute else self.relative_path),
            "relative_path": str(self.relative_path),
            "tags": sorted(self.tags),
            "shebang": self.shebang,
            "mime_type": self.mime_type,
            "is_executable": self.is_executable,
            "is_symlink": self.is_symlink,
            "size_bytes": self.size_bytes,
        }
        optional_fields: tuple[tuple[str, Any], ...] = (
            ("symlink_target", self.symlink_target),
            ("permissions_str", self.permissions_str),
            ("owner_user", self.owner_user),
            ("owner_group", self.owner_group),
            ("inode", self.inode),
            ("device", self.device),
            ("accumulated_size", self.accumulated_size),
            ("mtime", self.mtime),
            ("ctime", self.ctime),
            ("indicator", self.indicator),
        )
        result.update({k: v for k, v in optional_fields if v is not None})
        return result


@dataclass(frozen=True, slots=True)
class TraversalConfig:
    r"""Configuration options for repository traversal and format filtering.

    Attributes:
        root_paths: Roots from which to begin file discovery.
        include_tags: Tags that files must have to be included.
        exclude_tags: Tags that disqualify a file from inclusion.
        all_tags: If True, file must match all include_tags; if False, any tag.
        shebang_filter: Substring or interpreter name required in shebang.
        respect_gitignore: Whether to ignore paths matched by gitignore rules.
        gitignore_file: External gitignore file path to apply across traversal scope.
        include_hidden: Whether to inspect hidden files and directories.
        follow_symlinks: Whether to resolve and traverse symbolic links.
        dirs_only: Whether to list directories only, suppressing file entries.
        one_file_system: Whether to confine traversal to the root filesystem device.
        max_depth: Maximum directory descent depth, or None for unlimited.
        file_limit: Maximum directory entries threshold before skipping descent, or None.
        prune_empty: Whether to prune empty directories or directories with no matching files.
        include_patterns: Wildcard/glob patterns for including files (-P).
        exclude_patterns: Wildcard/glob patterns for excluding files (-I).
        ignore_case: Whether pattern comparisons are case-insensitive.
        match_dirs: Whether directory names are matched against patterns and inherit.
        relative_paths: Whether to output relative paths rather than absolute.
        relative_prefix: Whether to prepend input search path prefix to relative paths.
        null_delimited: Whether to delimit output paths with NUL bytes (\0).
        show_tags: Whether to print identified tags alongside file paths.
        show_summary: Whether to output summary statistics of matches.
        output_format: Requested output serialization format.
        sort_by: Criterion for ordering directory traversal entries.
        reverse_sort: Whether to invert the active sort order.
        dirs_first: Whether to list directories before files within directory levels.
        files_first: Whether to list files before directories within directory levels.
        from_file: Input file path or '-' for stdin to ingest directory structure from.
        offline: Whether to enforce extension-only classification without disk access.
        show_permissions: Whether to display file permissions in ls -l format.
        show_user: Whether to display file owner username or UID.
        show_group: Whether to display file owner group name or GID.
        show_inodes: Whether to display filesystem inode numbers.
        show_device: Whether to display filesystem device numbers.
        show_size: Whether to display file size in bytes.
        human_readable: Whether to format sizes using binary units (powers of 1024).
        show_si: Whether to format sizes using SI metric units (powers of 1000).
        accumulate_size: Whether to accumulate recursive directory disk usage.
        show_mtime: Whether to display file modification date/time.
        show_ctime: Whether to display inode status change date/time.
        time_format: Optional strftime format string for timestamps.
        classify: Whether to append file classification indicators.
        hide_control_chars: Whether to mask non-printable characters as '?'.
        literal: Whether to print non-printable characters verbatim.
        quote_name: Whether to enclose filenames in double quotes with backslash escaping.
        base_href: Optional base URL prefix for HTML hyperlinks.
        intro_file: Optional path to HTML fragment file prepended to directory listing.
        outro_file: Optional path to HTML fragment file appended to directory listing.
        html_title: Document title and heading for HTML output.
        no_links: Whether to suppress hyperlinks in HTML mode.
        xml: Whether XML output format flag is active.
        hyperlink: Whether to emit OSC 8 terminal hyperlinks for paths.
        hyperlink_schema: URI schema for terminal hyperlinks.
        hyperlink_authority: Optional URI authority component for terminal hyperlinks.
        locale: Optional locale string for translations and formatting.
    """

    root_paths: tuple[Path, ...] = field(default_factory=lambda: (Path(),))
    include_tags: frozenset[str] = field(default_factory=frozenset)
    exclude_tags: frozenset[str] = field(default_factory=frozenset)
    all_tags: bool = False
    shebang_filter: str | None = None
    respect_gitignore: bool = True
    gitignore_file: Path | None = None
    include_hidden: bool = False
    follow_symlinks: bool = False
    dirs_only: bool = False
    one_file_system: bool = False
    max_depth: int | None = None
    file_limit: int | None = None
    prune_empty: bool = False
    include_patterns: tuple[str, ...] = ()
    exclude_patterns: tuple[str, ...] = ()
    ignore_case: bool = False
    match_dirs: bool = False
    relative_paths: bool = True
    relative_prefix: bool = False
    null_delimited: bool = False
    show_tags: bool = False
    show_summary: bool = False
    output_format: str = "text"
    sort_by: SortKey = SortKey.NAME
    reverse_sort: bool = False
    dirs_first: bool = False
    files_first: bool = False
    from_file: str | None = None
    offline: bool = False
    show_permissions: bool = False
    show_user: bool = False
    show_group: bool = False
    show_inodes: bool = False
    show_device: bool = False
    show_size: bool = False
    human_readable: bool = False
    show_si: bool = False
    accumulate_size: bool = False
    show_mtime: bool = False
    show_ctime: bool = False
    time_format: str | None = None
    classify: bool = False
    hide_control_chars: bool = False
    literal: bool = False
    quote_name: bool = False
    base_href: str | None = None
    intro_file: Path | None = None
    outro_file: Path | None = None
    html_title: str | None = None
    no_links: bool = False
    xml: bool = False
    hyperlink: bool = False
    hyperlink_schema: str = "file://"
    hyperlink_authority: str | None = None
    locale: str | None = None
