"""Core data models and configurations for findfmt."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


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
        size_bytes: File size in bytes.
    """

    path: Path
    relative_path: Path
    tags: frozenset[str] = field(default_factory=frozenset)
    shebang: str | None = None
    mime_type: str | None = None
    is_executable: bool = False
    is_symlink: bool = False
    size_bytes: int = 0


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
        include_hidden: Whether to inspect hidden files and directories.
        follow_symlinks: Whether to resolve and traverse symbolic links.
        relative_paths: Whether to output relative paths rather than absolute.
        null_delimited: Whether to delimit output paths with NUL bytes (\0).
        show_tags: Whether to print identified tags alongside file paths.
        show_summary: Whether to output summary statistics of matches.
    """

    root_paths: tuple[Path, ...] = field(default_factory=lambda: (Path(),))
    include_tags: frozenset[str] = field(default_factory=frozenset)
    exclude_tags: frozenset[str] = field(default_factory=frozenset)
    all_tags: bool = False
    shebang_filter: str | None = None
    respect_gitignore: bool = True
    include_hidden: bool = False
    follow_symlinks: bool = False
    relative_paths: bool = True
    null_delimited: bool = False
    show_tags: bool = False
    show_summary: bool = False
