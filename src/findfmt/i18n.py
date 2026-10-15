"""Internationalization (i18n) and localization (l10n) runtime engine for findfmt."""

from __future__ import annotations

import contextlib
import gettext
import locale
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator, Mapping

DEFAULT_DOMAIN: str = "findfmt"
DEFAULT_LOCALE_DIR: Path = Path(__file__).resolve().parent / "locale"

__all__ = [
    "DEFAULT_DOMAIN",
    "DEFAULT_LOCALE_DIR",
    "_",
    "detect_locale",
    "detect_locales",
    "format_integer",
    "format_number",
    "get_current_locale",
    "get_current_translation",
    "locale_callback",
    "ngettext",
    "override_locale",
    "reset_locale",
    "set_locale",
]

_current_locale: str = "C"
_current_translation: gettext.NullTranslations = gettext.NullTranslations()
_ISO_639_1_CODE_LEN: int = 2


def detect_locale(env: Mapping[str, str] | None = None) -> str:
    """Detect the active locale following POSIX precedence order.

    Order: LANGUAGE -> LC_ALL -> LC_MESSAGES -> LANG -> fallback 'C'.

    Args:
        env: Optional mapping of environment variables (defaults to os.environ).

    Returns:
        The highest-precedence detected locale code string, or 'C'.
    """
    mapping = os.environ if env is None else env
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        val = mapping.get(var)
        if val:
            for part in val.split(":"):
                cleaned = part.strip()
                if cleaned:
                    return cleaned

    return "C"


def detect_locales(env: Mapping[str, str] | None = None) -> list[str]:
    """Return a deduplicated list of preferred locale codes in order of precedence.

    Order: LANGUAGE (split by ':') -> LC_ALL -> LC_MESSAGES -> LANG -> fallback ['C'].

    Args:
        env: Optional mapping of environment variables (defaults to os.environ).

    Returns:
        List of preferred locale code strings.
    """
    mapping = os.environ if env is None else env
    locales: list[str] = []
    seen: set[str] = set()

    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        val = mapping.get(var)
        if val:
            for part in val.split(":"):
                cleaned = part.strip()
                if cleaned and cleaned not in seen:
                    locales.append(cleaned)
                    seen.add(cleaned)

    if not locales:
        locales.append("C")

    return locales


def get_current_locale() -> str:
    """Return the currently active locale identifier.

    Returns:
        Active locale string (e.g. 'en_US', 'es', 'C').
    """
    return _current_locale


def get_current_translation() -> gettext.NullTranslations:
    """Return the active gettext translation catalog object.

    Returns:
        Active gettext.NullTranslations or GNUTranslations instance.
    """
    return _current_translation


def _try_apply_locale_candidate(cand: str) -> bool:
    """Attempt to apply a locale candidate string to the system locale.

    Args:
        cand: The locale identifier candidate string.

    Returns:
        True if LC_ALL was successfully set, False otherwise.
    """
    try:
        locale.setlocale(locale.LC_ALL, cand)
    except (locale.Error, ValueError, OSError):
        with contextlib.suppress(locale.Error, ValueError, OSError):
            locale.setlocale(locale.LC_TIME, cand)

        with contextlib.suppress(locale.Error, ValueError, OSError):
            locale.setlocale(locale.LC_NUMERIC, cand)

        return False
    else:
        return True


def _sync_system_locale(locale_name: str | None) -> None:
    """Synchronize Python's standard locale with the target or environment settings."""
    if locale_name is None:
        with contextlib.suppress(locale.Error, ValueError, OSError):
            locale.setlocale(locale.LC_ALL, "")

        return

    if locale_name in ("C", "POSIX"):
        with contextlib.suppress(locale.Error, ValueError, OSError):
            locale.setlocale(locale.LC_ALL, "C")

        return

    candidates = [locale_name, f"{locale_name}.UTF-8", f"{locale_name}.utf8"]
    if len(locale_name) == _ISO_639_1_CODE_LEN:
        upper = locale_name.upper()
        candidates.extend(
            [
                f"{locale_name}_{upper}.UTF-8",
                f"{locale_name}_{upper}.utf8",
                f"{locale_name}_{upper}",
            ],
        )

    for cand in candidates:
        if _try_apply_locale_candidate(cand):
            return


def set_locale(
    locale_name: str | None = None,
    localedir: Path | str | None = None,
    domain: str = DEFAULT_DOMAIN,
) -> str:
    """Set the active translation locale and initialize the gettext catalog.

    If locale_name is None, detect_locales() will be called to resolve candidate
    languages from environment variables. If locale_name is 'C' or 'POSIX',
    NullTranslations is used. Otherwise, gettext.translation() attempts to load
    a catalog from localedir, falling back to NullTranslations if not found.

    Args:
        locale_name: Explicit locale identifier (e.g. 'es_ES', 'fr'), or None.
        localedir: Directory containing locale message catalogs.
        domain: Translation domain name (default: 'findfmt').

    Returns:
        The resolved active locale code.
    """
    global _current_locale, _current_translation  # noqa: PLW0603

    _sync_system_locale(locale_name)

    if locale_name is None:
        locales = detect_locales()
        locale_name = locales[0]
    else:
        locales = [locale_name]

    _current_locale = locale_name

    if locale_name in ("C", "POSIX"):
        _current_translation = gettext.NullTranslations()
        return _current_locale

    target_dir = Path(localedir) if localedir is not None else DEFAULT_LOCALE_DIR
    try:
        _current_translation = gettext.translation(
            domain=domain,
            localedir=str(target_dir),
            languages=locales,
            fallback=True,
        )
    except (OSError, ValueError, UnicodeDecodeError):  # pragma: no cover
        _current_translation = gettext.NullTranslations()

    return _current_locale


def reset_locale() -> str:
    """Reset locale and translation catalog based on current environment variables.

    Returns:
        The detected active locale code.
    """
    return set_locale(None)


@contextlib.contextmanager
def override_locale(
    locale_name: str | None,
    localedir: Path | str | None = None,
    domain: str = DEFAULT_DOMAIN,
) -> Generator[str, None, None]:
    """Context manager to temporarily override active locale and restore on exit.

    Args:
        locale_name: Target locale identifier to activate.
        localedir: Optional custom catalog directory.
        domain: Translation domain name.

    Yields:
        The activated locale name.
    """
    global _current_locale, _current_translation  # noqa: PLW0603
    saved_locale = _current_locale
    saved_translation = _current_translation
    saved_system_locale: str | None = None
    with contextlib.suppress(locale.Error, ValueError, OSError):
        saved_system_locale = locale.setlocale(locale.LC_ALL)

    try:
        active = set_locale(locale_name=locale_name, localedir=localedir, domain=domain)
        yield active
    finally:
        _current_locale = saved_locale
        _current_translation = saved_translation
        if saved_system_locale is not None:
            with contextlib.suppress(locale.Error, ValueError, OSError):
                locale.setlocale(locale.LC_ALL, saved_system_locale)


def locale_callback(value: str | None) -> str | None:
    """Typer/Click callback for --locale / --lang option.

    Args:
        value: Explicit locale override string, or None if omitted.

    Returns:
        The locale string value passed in.
    """
    if value is not None:
        set_locale(value)

    return value


def _(message: str) -> str:
    """Translate message string using the active gettext translation catalog.

    Args:
        message: The translatable text string.

    Returns:
        Translated string, or original message if no translation catalog exists.
    """
    return _current_translation.gettext(message)


def ngettext(singular: str, plural: str, n: int) -> str:
    """Translate singular or plural message string according to count n.

    Args:
        singular: Singular message template.
        plural: Plural message template.
        n: Quantity determining singular or plural form.

    Returns:
        Translated string matching plural rules for n.
    """
    return _current_translation.ngettext(singular, plural, n)


def format_number(value: float, decimals: int = 1) -> str:
    """Format a floating point number respecting LC_NUMERIC decimal separator.

    Args:
        value: Float or int value to format.
        decimals: Number of decimal places.

    Returns:
        Formatted number string.
    """
    try:
        return locale.format_string(f"%.{decimals}f", value, grouping=True)
    except (ValueError, TypeError):  # pragma: no cover
        return f"{value:.{decimals}f}"


def format_integer(value: int, *, grouping: bool = False) -> str:
    """Format an integer respecting LC_NUMERIC thousands separator if requested.

    Args:
        value: Integer value to format.
        grouping: Whether to insert thousands grouping separators.

    Returns:
        Formatted integer string.
    """
    if not grouping:
        return str(value)

    try:
        return locale.format_string("%d", value, grouping=True)
    except (ValueError, TypeError):  # pragma: no cover
        return str(value)


# Initialize default locale from environment
set_locale()
