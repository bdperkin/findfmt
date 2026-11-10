"""findfmt: A .gitignore-aware file discovery and classification suite."""

from __future__ import annotations

import warnings
from importlib.metadata import PackageNotFoundError as _PackageNotFoundError
from importlib.metadata import version as _pkg_version

from findfmt.classifier import classify_file, get_known_tags
from findfmt.exceptions import (
    FindFmtError,
    InvalidSortCriteriaError,
    ParserError,
    TraversalError,
    UnsupportedBoxStyleError,
    UnsupportedFormatError,
    UnsupportedTableStyleError,
)
from findfmt.formatters import Formatter, OutputFormat, get_formatter
from findfmt.i18n import (
    detect_locale,
    detect_locales,
    get_current_locale,
    get_current_translation,
    ngettext,
    override_locale,
    reset_locale,
    set_locale,
)
from findfmt.metadata import extract_metadata, format_permissions
from findfmt.models import FileInfo, SortKey, TraversalConfig
from findfmt.sizes import (
    calculate_accumulated_sizes,
    format_size,
    format_size_binary,
    format_size_bytes,
    format_size_si,
)
from findfmt.traversal import find_files, traverse_directory
from findfmt.utils.hyperlinks import (
    build_file_uri,
    format_hyperlink,
    format_osc8_link,
    format_rich_link,
)
from findfmt.utils.strings import (
    format_display_path,
    format_timestamp,
    get_classification_indicator,
    mask_control_characters,
    quote_filename,
    strip_ansi_escapes,
)

_FALLBACK_VERSION: str = "1.1.5.dev0"


def get_version() -> str:
    """Retrieve package version or fallback string."""
    try:
        return _pkg_version("findfmt")
    except _PackageNotFoundError:
        return _FALLBACK_VERSION


__version__ = get_version()

__all__ = [
    "FileInfo",
    "FindFmtError",
    "Formatter",
    "InvalidSortCriteriaError",
    "OutputFormat",
    "ParserError",
    "SortKey",
    "TraversalConfig",
    "TraversalError",
    "UnsupportedBoxStyleError",
    "UnsupportedFormatError",
    "UnsupportedTableStyleError",
    "__version__",
    "build_file_uri",
    "calculate_accumulated_sizes",
    "classify_file",
    "detect_locale",
    "detect_locales",
    "extract_metadata",
    "find_files",
    "format_display_path",
    "format_hyperlink",
    "format_osc8_link",
    "format_permissions",
    "format_rich_link",
    "format_size",
    "format_size_binary",
    "format_size_bytes",
    "format_size_si",
    "format_timestamp",
    "get_classification_indicator",
    "get_current_locale",
    "get_current_translation",
    "get_formatter",
    "get_known_tags",
    "get_version",
    "mask_control_characters",
    "ngettext",
    "override_locale",
    "quote_filename",
    "reset_locale",
    "set_locale",
    "strip_ansi_escapes",
    "traverse_directory",
]

_DEPRECATED_CLI_ENTRYPOINTS: frozenset[str] = frozenset(
    {
        "main",
        "main_findfilefmt",
        "main_findfilemime",
        "main_findfiles",
        "main_findfmt0",
        "main_findshebang",
        "main_findsummary",
    },
)


def __getattr__(name: str) -> object:
    """Lazily resolve deprecated CLI entry points and gettext helper."""
    if name in _DEPRECATED_CLI_ENTRYPOINTS:
        warnings.warn(
            f"'findfmt.{name}' is deprecated and will be removed in v2.0; "
            f"import '{name}' from 'findfmt.cli' or 'findfmt.cli.entrypoints' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from findfmt.cli import entrypoints

        return getattr(entrypoints, name)

    if name == "_":
        warnings.warn(
            "'findfmt._' is deprecated and will be removed in v2.0; "
            "import '_' from 'findfmt.i18n' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from findfmt.i18n import _ as gettext_func

        return gettext_func

    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
