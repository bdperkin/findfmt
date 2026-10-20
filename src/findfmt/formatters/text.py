"""Plain text and NUL-delimited output formatters."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, TextIO

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

from findfmt.formatters.base import Formatter, write_stream_safe
from findfmt.metadata import format_metadata_parts
from findfmt.utils.hyperlinks import build_file_uri
from findfmt.utils.strings import (
    format_display_path,
    mask_control_characters,
    strip_ansi_escapes,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from findfmt.models import FileInfo

__all__ = ["TextFormatter"]


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
            hide_control_chars: Whether to mask non-printable characters with '?'.
            literal: Whether to emit literal control characters.
            quote_name: Whether to enclose filenames in double quotes.
            hyperlink: Whether to wrap paths in OSC 8 terminal hyperlink escapes.
            hyperlink_schema: URI schema for terminal hyperlinks.
            hyperlink_authority: Optional URI authority component for terminal hyperlinks.
        """
        super().__init__(absolute=absolute)
        self.show_tags = show_tags
        self.delimiter = delimiter
        self.show_permissions = show_permissions
        self.show_user = show_user
        self.show_group = show_group
        self.show_inodes = show_inodes
        self.show_device = show_device
        self.show_size = show_size
        self.human_readable = human_readable
        self.show_si = show_si
        self.show_mtime = show_mtime
        self.show_ctime = show_ctime
        self.time_format = time_format
        self.classify = classify
        self.hide_control_chars = hide_control_chars
        self.literal = literal
        self.quote_name = quote_name
        self.hyperlink = hyperlink
        self.hyperlink_schema = hyperlink_schema
        self.hyperlink_authority = hyperlink_authority

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
            show_size=self.show_size,
            human_readable=self.human_readable,
            show_si=self.show_si,
            show_mtime=self.show_mtime,
            show_ctime=self.show_ctime,
            time_format=self.time_format,
        )
        raw_path = str(file_info.path if self.absolute else file_info.relative_path)
        indicator = file_info.indicator if self.classify else None
        uri = (
            build_file_uri(
                file_info.path,
                schema=self.hyperlink_schema,
                authority=self.hyperlink_authority,
            )
            if self.hyperlink
            else None
        )
        display_path = format_display_path(
            raw_path,
            quote_name=self.quote_name,
            hide_control_chars=self.hide_control_chars,
            literal=self.literal,
            indicator=indicator,
            hyperlink=self.hyperlink,
            uri=uri,
        )
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
