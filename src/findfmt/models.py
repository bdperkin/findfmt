"""Core data models and configurations for findfmt."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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

    def to_dict(self, *, absolute: bool = False) -> dict[str, Any]:
        """Serialize file attributes to a dictionary representation.

        Args:
            absolute: Whether the 'path' entry contains the absolute path.

        Returns:
            Dictionary mapping attribute names to serialized values.
        """
        return {
            "path": str(self.path if absolute else self.relative_path),
            "relative_path": str(self.relative_path),
            "tags": sorted(self.tags),
            "shebang": self.shebang,
            "mime_type": self.mime_type,
            "is_executable": self.is_executable,
            "is_symlink": self.is_symlink,
            "size_bytes": self.size_bytes,
        }


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
        output_format: Requested output serialization format.
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
    output_format: str = "text"
