"""Plain text and NUL-delimited output formatters."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, TextIO

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

from findfmt.formatters.base import Formatter

if TYPE_CHECKING:
    from collections.abc import Iterable

    from findfmt.models import FileInfo


class TextFormatter(Formatter):
    """Standard line-oriented or NUL-delimited plain text formatter."""

    def __init__(
        self,
        *,
        absolute: bool = False,
        show_tags: bool = False,
        delimiter: str = "\n",
    ) -> None:
        r"""Initialize TextFormatter.

        Args:
            absolute: Whether to emit absolute paths.
            show_tags: Whether to append classification tags.
            delimiter: Line terminator string (typically '\n' or '\0').
        """
        super().__init__(absolute=absolute)
        self.show_tags = show_tags
        self.delimiter = delimiter

    def format_item(self, file_info: FileInfo) -> str:
        """Format an individual file record as a text line.

        Args:
            file_info: Classified file information.

        Returns:
            Formatted line string including trailing delimiter.
        """
        path_str = str(file_info.path if self.absolute else file_info.relative_path)
        if self.show_tags:
            tags_repr = ", ".join(sorted(file_info.tags))
            return f"{path_str} [{tags_repr}]{self.delimiter}"

        return f"{path_str}{self.delimiter}"

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
