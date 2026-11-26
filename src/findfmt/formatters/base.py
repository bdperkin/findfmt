"""Base interfaces and protocols for output formatters."""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, TextIO

from findfmt.exceptions import UnsupportedFormatError
from findfmt.metadata import format_metadata_parts
from findfmt.utils.hyperlinks import build_file_uri
from findfmt.utils.strings import format_display_path

if TYPE_CHECKING:
    from collections.abc import Iterable

    from findfmt.models import FileInfo

__all__ = [
    "TABLE_FIELD_NAMES",
    "Formatter",
    "OutputFormat",
    "UnsupportedFormatError",
    "write_stream_safe",
]


class OutputFormat(enum.StrEnum):
    """Supported output serialization formats."""

    TEXT = "text"
    JSON = "json"
    JSONL = "jsonl"
    YAML = "yaml"
    IPYNB = "ipynb"
    CSV = "csv"
    TSV = "tsv"
    MARKDOWN = "markdown"
    MD = "md"
    RST = "rst"
    TABLE = "table"
    TREE = "tree"
    CSV_TABLE = "csv-table"
    NDJSON = "ndjson"
    XML = "xml"
    HTML = "html"


TABLE_FIELD_NAMES: tuple[str, ...] = (
    "path",
    "relative_path",
    "tags",
    "mime_type",
    "shebang",
    "is_executable",
    "is_symlink",
    "size_bytes",
)


def write_stream_safe(stream: TextIO, content: str) -> None:
    """Write text content to a text stream, handling surrogate escapes safely.

    If the target stream or its wrapper raises UnicodeEncodeError, this attempts
    to encode with errors='surrogateescape' and write directly to the stream's
    underlying binary buffer.

    Args:
        stream: Target text stream.
        content: String content potentially containing surrogate code points.
    """
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure) and getattr(stream, "encoding", None) != "cp437":
        reconfigure(errors="surrogateescape")

    try:
        stream.write(content)
    except UnicodeEncodeError:
        buffer = getattr(stream, "buffer", None)
        if buffer is not None:
            encoding = getattr(stream, "encoding", None) or "utf-8"
            buffer.write(content.encode(encoding, errors="surrogateescape"))
        else:
            raise


class Formatter(ABC):
    """Abstract base class for all findfmt output formatters."""

    def __init__(self, *, absolute: bool = False) -> None:
        """Initialize formatter.

        Args:
            absolute: Whether to format paths as absolute rather than relative.
        """
        self.absolute = absolute

    @abstractmethod
    def format(self, files: Iterable[FileInfo]) -> str:
        """Format an iterable of FileInfo instances into a string.

        Args:
            files: Iterable of classified file objects.

        Returns:
            Formatted string representation.
        """

    def stream(self, files: Iterable[FileInfo], stream: TextIO) -> None:
        """Stream formatted output directly to a text stream.

        Args:
            files: Iterable of classified file objects.
            stream: Target text output stream (e.g., sys.stdout).
        """
        write_stream_safe(stream, self.format(files))
        stream.flush()


class _MetadataFormatterBase(Formatter):
    """Internal base class for formatters supporting POSIX stat, size, and path display options."""

    show_permissions: bool
    show_user: bool
    show_group: bool
    show_inodes: bool
    show_device: bool
    show_mtime: bool
    show_ctime: bool
    time_format: str | None
    show_size: bool
    human_readable: bool
    show_si: bool
    accumulate_size: bool
    classify: bool
    hide_control_chars: bool
    literal: bool
    quote_name: bool
    hyperlink: bool
    hyperlink_schema: str
    hyperlink_authority: str | None

    def _set_ownership_options(
        self,
        *,
        permissions: bool = False,
        user: bool = False,
        group: bool = False,
    ) -> None:
        """Assign file permission, owner user, and owner group display options."""
        self.show_permissions = permissions
        self.show_user = user
        self.show_group = group

    def _set_stat_options(
        self,
        *,
        inodes: bool = False,
        device: bool = False,
        mtime: bool = False,
        ctime: bool = False,
    ) -> None:
        """Assign inode, device, modification, and status-change display options."""
        self.show_inodes = inodes
        self.show_device = device
        self.show_mtime = mtime
        self.show_ctime = ctime

    def _set_size_options(
        self,
        *,
        exact: bool = False,
        human: bool = False,
        si: bool = False,
        accum: bool = False,
    ) -> None:
        """Assign byte, binary, SI, and accumulated directory size display options."""
        self.show_size = exact
        self.human_readable = human
        self.show_si = si
        self.accumulate_size = accum

    def _set_path_options(
        self,
        *,
        classify: bool = False,
        ctrl: bool = False,
        literal: bool = False,
        quote: bool = False,
    ) -> None:
        """Assign classification indicator, control-character, and quoting display options."""
        self.classify = classify
        self.hide_control_chars = ctrl
        self.literal = literal
        self.quote_name = quote

    def _set_hyperlink_options(
        self,
        *,
        link: bool = False,
        schema: str = "file://",
        authority: str | None = None,
    ) -> None:
        """Assign OSC 8 terminal hyperlink display options."""
        self.hyperlink = link
        self.hyperlink_schema = schema
        self.hyperlink_authority = authority

    def _format_stat_parts(
        self,
        file_info: FileInfo,
        *,
        include_size: bool = False,
    ) -> list[str]:
        """Format enabled POSIX stat metadata fields for a file record."""
        return format_metadata_parts(
            file_info,
            show_inodes=self.show_inodes,
            show_device=self.show_device,
            show_permissions=self.show_permissions,
            show_user=self.show_user,
            show_group=self.show_group,
            show_size=self.show_size and include_size,
            human_readable=self.human_readable,
            show_si=self.show_si,
            show_mtime=self.show_mtime,
            show_ctime=self.show_ctime,
            time_format=self.time_format,
        )

    def _format_file_display_path(
        self,
        file_info: FileInfo,
        *,
        escape_markup: bool = False,
    ) -> str:
        """Format a file path with optional classification indicator and OSC 8 hyperlink."""
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
        return format_display_path(
            raw_path,
            quote_name=self.quote_name,
            hide_control_chars=self.hide_control_chars,
            literal=self.literal,
            indicator=indicator,
            hyperlink=self.hyperlink,
            uri=uri,
            escape_markup=escape_markup,
        )
