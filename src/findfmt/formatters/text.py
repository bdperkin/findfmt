"""Plain text and NUL-delimited output formatters."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, TextIO

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

from findfmt.formatters.base import Formatter
from findfmt.metadata import format_metadata_parts

if TYPE_CHECKING:
    from collections.abc import Iterable

    from findfmt.models import FileInfo


class TextFormatter(Formatter):
    """Standard line-oriented or NUL-delimited plain text formatter."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        absolute: bool = False,
        show_tags: bool = False,
        delimiter: str = "\n",
        show_permissions: bool = False,
        show_user: bool = False,
        show_group: bool = False,
        show_inodes: bool = False,
        show_device: bool = False,
    ) -> None:
        r"""Initialize TextFormatter.

        Args:
            absolute: Whether to emit absolute paths.
            show_tags: Whether to append classification tags.
            delimiter: Line terminator string (typically '\n' or '\0').
            show_permissions: Whether to display permissions string in ls -l style.
            show_user: Whether to display file owner username or UID.
            show_group: Whether to display file owner group name or GID.
            show_inodes: Whether to display filesystem inode number.
            show_device: Whether to display filesystem device number.
        """
        super().__init__(absolute=absolute)
        self.show_tags = show_tags
        self.delimiter = delimiter
        self.show_permissions = show_permissions
        self.show_user = show_user
        self.show_group = show_group
        self.show_inodes = show_inodes
        self.show_device = show_device

    def format_item(self, file_info: FileInfo) -> str:
        """Format an individual file record as a text line.

        Args:
            file_info: Classified file information.

        Returns:
            Formatted line string including trailing delimiter.
        """
        meta_parts = format_metadata_parts(
            file_info,
            show_inodes=self.show_inodes,
            show_device=self.show_device,
            show_permissions=self.show_permissions,
            show_user=self.show_user,
            show_group=self.show_group,
        )
        path_str = str(file_info.path if self.absolute else file_info.relative_path)
        prefix = f"[{' '.join(meta_parts)}] " if meta_parts else ""

        if self.show_tags:
            tags_repr = ", ".join(sorted(file_info.tags))
            return f"{prefix}{path_str} [{tags_repr}]{self.delimiter}"

        return f"{prefix}{path_str}{self.delimiter}"

    @override
    def format(self, files: Iterable[FileInfo]) -> str:
        """Format all files into a concatenated text string.

        Args:
            files: Iterable of classified file objects.

        Returns:
            Concatenated formatted text string.
        """
        return "".join(self.format_item(f) for f in files)

    @override
    def stream(self, files: Iterable[FileInfo], stream: TextIO) -> None:
        """Stream formatted text items directly to the output stream.

        Args:
            files: Iterable of classified file objects.
            stream: Target text stream.
        """
        stream.writelines(self.format_item(file_info) for file_info in files)
        stream.flush()
