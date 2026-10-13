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
        if self.symlink_target is not None:
            result["symlink_target"] = self.symlink_target

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
