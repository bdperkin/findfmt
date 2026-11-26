"""Plain text and NUL-delimited output formatters."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, TextIO

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

from findfmt.formatters.base import _MetadataFormatterBase, write_stream_safe
from findfmt.utils.strings import (
    mask_control_characters,
    strip_ansi_escapes,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from findfmt.models import FileInfo

__all__ = ["TextFormatter"]


class TextFormatter(_MetadataFormatterBase):
    """Standard line-oriented or NUL-delimited plain text formatter."""

    def __init__(  # noqa: PLR0913 - wide CLI/config signature
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
        show_size: bool = False,
        human_readable: bool = False,
        show_si: bool = False,
        show_mtime: bool = False,
        show_ctime: bool = False,
        time_format: str | None = None,
        classify: bool = False,
        hide_control_chars: bool = False,
        literal: bool = False,
        quote_name: bool = False,
        hyperlink: bool = False,
        hyperlink_schema: str = "file://",
        hyperlink_authority: str | None = None,
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
            show_size: Whether to display exact byte size.
            human_readable: Whether to format sizes using binary units.
            show_si: Whether to format sizes using SI metric units.
            show_mtime: Whether to display file modification date/time.
            show_ctime: Whether to display last status change date/time.
            time_format: Optional strftime syntax format string for dates/times.
            classify: Whether to append file classification indicator characters.
            hide_control_chars: Whether to mask non-printable and bidirectional control
                characters with '?'.
            literal: Whether to emit literal control characters.
            quote_name: Whether to enclose filenames in double quotes.
            hyperlink: Whether to wrap paths in OSC 8 terminal hyperlink escapes.
            hyperlink_schema: URI schema for terminal hyperlinks.
            hyperlink_authority: Optional URI authority component for terminal hyperlinks.
        """
        super().__init__(absolute=absolute)
        if delimiter == "\0":
            literal = True
            hide_control_chars = False

        self.show_tags = show_tags
        self.delimiter = delimiter
        self._set_ownership_options(permissions=show_permissions, user=show_user, group=show_group)
        self._set_stat_options(inodes=show_inodes, device=show_device, mtime=show_mtime, ctime=show_ctime)
        self.time_format = time_format
        self._set_size_options(exact=show_size, human=human_readable, si=show_si)
        self._set_path_options(classify=classify, ctrl=hide_control_chars, literal=literal, quote=quote_name)
        self._set_hyperlink_options(link=hyperlink, schema=hyperlink_schema, authority=hyperlink_authority)

    def format_item(self, file_info: FileInfo) -> str:
        """Format an individual file record as a text line.

        Args:
            file_info: Classified file information.

        Returns:
            Formatted line string including trailing delimiter.
        """
        meta_parts = self._format_stat_parts(file_info, include_size=True)
        display_path = self._format_file_display_path(file_info)
        if not self.literal and meta_parts:
            meta_parts = [mask_control_characters(strip_ansi_escapes(p)) for p in meta_parts]

        prefix = f"[{' '.join(meta_parts)}] " if meta_parts else ""

        if self.show_tags:
            tags_repr = ", ".join(sorted(file_info.tags))
            if not self.literal:
                tags_repr = mask_control_characters(strip_ansi_escapes(tags_repr))

            return f"{prefix}{display_path} [{tags_repr}]{self.delimiter}"

        return f"{prefix}{display_path}{self.delimiter}"

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
        for file_info in files:
            write_stream_safe(stream, self.format_item(file_info))

        stream.flush()
