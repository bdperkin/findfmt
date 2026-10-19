"""Exception hierarchy for the findfmt package."""

from __future__ import annotations

from findfmt.i18n import _

__all__ = [
    "FindFmtError",
    "InvalidSortCriteriaError",
    "ParserError",
    "TraversalError",
    "UnsupportedBoxStyleError",
    "UnsupportedFormatError",
    "UnsupportedTableStyleError",
]


class FindFmtError(Exception):
    """Base exception for all findfmt library errors.

    Downstream callers can catch this exception to handle any findfmt-specific
    failure without having to catch generic exceptions.
    """


class UnsupportedFormatError(FindFmtError, ValueError):
    """Raised when an unsupported output format is requested."""

    def __init__(self, format_type: str, valid_formats: str) -> None:
        """Initialize UnsupportedFormatError.

        Args:
            format_type: The invalid format requested.
            valid_formats: Comma-separated list of valid formats.
        """
        self.format_type = format_type
        self.valid_formats = valid_formats
        super().__init__(
            _("Unsupported output format: '{format}'. Expected one of: {valid_formats}").format(
                format=format_type,
                valid_formats=valid_formats,
            ),
        )


class UnsupportedTableStyleError(FindFmtError, ValueError):
    """Raised when an unsupported table border style is requested in RST formatter."""

    def __init__(self, table_style: str) -> None:
        """Initialize UnsupportedTableStyleError.

        Args:
            table_style: The invalid table style requested.
        """
        self.table_style = table_style
        super().__init__(
            _("Unsupported RST table style: '{style}'. Expected 'grid' or 'simple'.").format(
                style=table_style,
            ),
        )


class UnsupportedBoxStyleError(FindFmtError, ValueError):
    """Raised when an unsupported table border style is requested in Rich table formatters."""

    def __init__(self, table_style: str, valid_styles: str) -> None:
        """Initialize UnsupportedBoxStyleError.

        Args:
            table_style: The invalid table style requested.
            valid_styles: Comma-separated list of valid box styles.
        """
        self.table_style = table_style
        self.valid_styles = valid_styles
        super().__init__(
            _("Unsupported table style: '{style}'. Expected one of: {valid_styles}").format(
                style=table_style,
                valid_styles=valid_styles,
            ),
        )


class InvalidSortCriteriaError(FindFmtError, ValueError):
    """Raised when an invalid sort criteria is passed to resolve_sort_key."""

    def __init__(self, criteria: str) -> None:
        """Initialize InvalidSortCriteriaError.

        Args:
            criteria: The invalid sort criteria value.
        """
        self.criteria = criteria
        super().__init__(
            _(
                "Invalid sort criteria '{criteria}'. "
                "Choose from: name, version, time, mtime, ctime, size, none.",
            ).format(criteria=criteria),
        )


class TraversalError(FindFmtError):
    """Base exception for directory traversal errors."""


class ParserError(FindFmtError, ValueError):
    """Base exception for external input parsing and outline ingestion errors."""
