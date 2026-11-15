"""Schema validation and conversion rules for findfmt configuration files."""

from __future__ import annotations

import difflib
import warnings
from pathlib import Path
from typing import Any, NoReturn

import typer

from findfmt.formatters import OutputFormat
from findfmt.i18n import _

__all__ = [
    "ACCEPTED_CONFIG_KEYS",
    "CANONICAL_CONFIG_KEYS",
    "validate_and_convert_config",
]

_BOOL_KEYS: dict[str, tuple[str, bool]] = {
    "hidden": ("hidden", False),
    "all": ("hidden", False),
    "ignore": ("no_ignore", True),
    "no_ignore": ("no_ignore", False),
    "all_tags": ("all_tags", False),
    "reverse": ("reverse", False),
    "unsorted": ("unsorted", False),
    "dirs_first": ("dirs_first", False),
    "files_first": ("files_first", False),
    "follow_symlinks": ("follow_symlinks", False),
    "dirs_only": ("dirs_only", False),
    "one_file_system": ("one_file_system", False),
    "prune": ("prune", False),
    "ignore_case": ("ignore_case", False),
    "match_dirs": ("match_dirs", False),
    "absolute": ("absolute", False),
    "relative": ("relative", False),
    "print0": ("print0", False),
    "list_tags": ("list_tags", False),
    "summary": ("summary", False),
    "exit_status": ("exit_status", False),
    "permissions": ("permissions", False),
    "user": ("user", False),
    "group": ("group", False),
    "size": ("size", False),
    "human_readable": ("human_readable", False),
    "si": ("si", False),
    "du": ("du", False),
    "inodes": ("inodes", False),
    "device": ("device", False),
    "mtime": ("mtime", False),
    "ctime": ("ctime", False),
    "classify": ("classify", False),
    "hide_control_chars": ("hide_control_chars", False),
    "literal": ("literal", False),
    "quote_name": ("quote_name", False),
    "no_indent": ("no_indent", False),
    "ansi_lines": ("ansi_lines", False),
    "cp437": ("cp437", False),
    "hyperlink": ("hyperlink", False),
    "tree": ("tree", False),
    "json": ("json", False),
    "xml": ("xml", False),
    "no_links": ("no_links", False),
    "csv_safe": ("csv_safe", False),
    "allow_outside_root": ("allow_outside_root", False),
}

_DEPRECATED_FORMAT_BOOL_KEYS: frozenset[str] = frozenset({"tree", "json", "xml"})

_STR_LIST_KEYS: dict[str, str] = {
    "tags": "tags",
    "tag": "tags",
    "type": "tags",
    "exclude_tags": "exclude_tags",
    "exclude_tag": "exclude_tags",
    "exclude": "exclude_tags",
    "pattern": "pattern",
    "patterns": "pattern",
    "include_pattern": "pattern",
    "exclude_pattern": "exclude_pattern",
    "exclude_patterns": "exclude_pattern",
}

_STR_KEYS: dict[str, str] = {
    "table_style": "table_style",
    "sort": "sort",
    "shebang": "shebang",
    "time_format": "time_format",
    "title": "title",
    "hyperlink_schema": "hyperlink_schema",
    "hyperlink_authority": "hyperlink_authority",
    "locale": "locale",
    "html": "html",
}

_INT_KEYS: dict[str, str] = {
    "max_depth": "max_depth",
    "file_limit": "file_limit",
}

CANONICAL_CONFIG_KEYS: frozenset[str] = frozenset(
    (
        {"format", "color", "pager", "gitignore_file"}
        | {"ignore" if target == "no_ignore" else target for target, _ in _BOOL_KEYS.values()}
        | set(_STR_LIST_KEYS.values())
        | set(_STR_KEYS.values())
        | set(_INT_KEYS.values())
    )
    - _DEPRECATED_FORMAT_BOOL_KEYS,
)

ACCEPTED_CONFIG_KEYS: frozenset[str] = frozenset(
    {"format", "output_format", "color", "pager", "gitignore_file"}
    | set(_BOOL_KEYS)
    | set(_STR_LIST_KEYS)
    | set(_STR_KEYS)
    | set(_INT_KEYS),
)


def _extract_tool_section(data: dict[str, Any], path: Path) -> dict[str, Any]:
    """Extract settings from [tool.findfmt] in pyproject.toml or root of config.toml."""
    if path.name == "pyproject.toml":
        tool_section = data.get("tool")
        if isinstance(tool_section, dict):
            findfmt_section = tool_section.get("findfmt")
            if isinstance(findfmt_section, dict):
                return findfmt_section

        return {}

    tool_section = data.get("tool")
    if isinstance(tool_section, dict):
        findfmt_section = tool_section.get("findfmt")
        if isinstance(findfmt_section, dict):
            return findfmt_section

    findfmt_section = data.get("findfmt")
    if isinstance(findfmt_section, dict):
        return findfmt_section

    return data


def _describe_val(val: object) -> str:
    """Return a diagnostic representation of a value and its Python type name."""
    return f"{val!r} ({type(val).__name__})"


def _convert_format_val(key: str, val: object, path: Path) -> OutputFormat:
    """Validate and convert format setting string into canonical OutputFormat enum."""
    if not isinstance(val, str):
        msg = _("expected string format name, got {type_name}").format(
            type_name=_describe_val(val),
        )
        typer.echo(
            _("Error: Invalid value for '{key}' in '{path}': {error}").format(
                key=key,
                path=path,
                error=msg,
            ),
            err=True,
        )
        raise typer.Exit(code=2)

    cleaned = val.strip().lower()
    for member in OutputFormat:
        if member.value == cleaned or member.name.lower() == cleaned:
            return member

    valid = ", ".join(m.value for m in OutputFormat)
    msg = _("unsupported format '{val}'. Valid options: {valid}").format(
        val=f"{val} ({type(val).__name__})",
        valid=valid,
    )
    typer.echo(
        _("Error: Invalid value for '{key}' in '{path}': {error}").format(
            key=key,
            path=path,
            error=msg,
        ),
        err=True,
    )
    raise typer.Exit(code=2)


def _convert_tri_state(key: str, val: object, path: Path) -> bool | None:
    """Validate and convert tri-state flag (color/pager) to bool or None."""
    if isinstance(val, bool):
        return val

    if val is None:
        return None

    if isinstance(val, str):
        lowered = val.strip().lower()
        if lowered in ("always", "true", "yes", "on", "1"):
            return True

        if lowered in ("never", "false", "no", "off", "0"):
            return False

        if lowered == "auto":
            return None

    msg = _("expected 'auto', 'always', 'never', or boolean, got '{val}'").format(
        val=_describe_val(val),
    )
    typer.echo(
        _("Error: Invalid value for '{key}' in '{path}': {error}").format(
            key=key,
            path=path,
            error=msg,
        ),
        err=True,
    )
    raise typer.Exit(code=2)


def _convert_bool_val(key: str, val: object, path: Path, *, invert: bool = False) -> bool:
    """Validate boolean configuration value."""
    if not isinstance(val, bool):
        msg = _("expected boolean (true/false), got {type_name}").format(
            type_name=_describe_val(val),
        )
        typer.echo(
            _("Error: Invalid value for '{key}' in '{path}': {error}").format(
                key=key,
                path=path,
                error=msg,
            ),
            err=True,
        )
        raise typer.Exit(code=2)

    return not val if invert else val


def _convert_str_list(key: str, val: object, path: Path) -> list[str]:
    """Validate list of strings or single string value."""
    if isinstance(val, str):
        return [val]

    if isinstance(val, list) and all(isinstance(x, str) for x in val):
        return [str(x) for x in val]

    msg = _("expected string or list of strings, got {type_name}").format(
        type_name=_describe_val(val),
    )
    typer.echo(
        _("Error: Invalid value for '{key}' in '{path}': {error}").format(
            key=key,
            path=path,
            error=msg,
        ),
        err=True,
    )
    raise typer.Exit(code=2)


def _convert_int_val(key: str, val: object, path: Path) -> int:
    """Validate non-negative integer configuration value."""
    if not isinstance(val, int) or isinstance(val, bool) or val < 0:
        msg = _("expected non-negative integer, got {val}").format(val=_describe_val(val))
        typer.echo(
            _("Error: Invalid value for '{key}' in '{path}': {error}").format(
                key=key,
                path=path,
                error=msg,
            ),
            err=True,
        )
        raise typer.Exit(code=2)

    return val


def _convert_str_val(key: str, val: object, path: Path) -> str:
    """Validate string configuration value."""
    if not isinstance(val, str):
        msg = _("expected string, got {type_name}").format(type_name=_describe_val(val))
        typer.echo(
            _("Error: Invalid value for '{key}' in '{path}': {error}").format(
                key=key,
                path=path,
                error=msg,
            ),
            err=True,
        )
        raise typer.Exit(code=2)

    return val


def _warn_deprecated_format_bool(raw_key: str, canonical_key: str, path: Path) -> None:
    """Emit a deprecation warning for deprecated format boolean config keys (#457)."""
    msg = _(
        "Warning: Configuration key '{key}' in '{path}' is deprecated and will be removed "
        "in v2.0.0; use 'format = \"{fmt}\"' instead.",
    ).format(
        key=raw_key,
        path=path,
        fmt=canonical_key,
    )
    typer.echo(msg, err=True)
    warnings.warn(msg, DeprecationWarning, stacklevel=3)


def _report_unknown_key(raw_key: str, key: str, path: Path) -> NoReturn:
    """Emit an unknown configuration key error with an optional close-match suggestion."""
    matches = difflib.get_close_matches(key, sorted(ACCEPTED_CONFIG_KEYS), n=1, cutoff=0.6)
    if matches:
        msg = _(
            "Error: Unknown configuration key '{key}' in '{path}'. Did you mean '{suggestion}'?",
        ).format(
            key=raw_key,
            path=path,
            suggestion=matches[0],
        )
    else:
        msg = _("Error: Unknown configuration key '{key}' in '{path}'.").format(
            key=raw_key,
            path=path,
        )

    typer.echo(msg, err=True)
    raise typer.Exit(code=2)


def _convert_single_key(raw_key: str, key: str, val: object, path: Path) -> tuple[str, Any]:
    """Validate and convert a single configuration entry to (target_name, converted_val)."""
    if key in ("format", "output_format"):
        result: tuple[str, Any] = ("output_format", _convert_format_val(raw_key, val, path))
    elif key in ("color", "pager"):
        result = (key, _convert_tri_state(raw_key, val, path))
    elif key in _BOOL_KEYS:
        target_name, invert = _BOOL_KEYS[key]
        converted_val = _convert_bool_val(raw_key, val, path, invert=invert)
        if key in _DEPRECATED_FORMAT_BOOL_KEYS:
            _warn_deprecated_format_bool(raw_key, target_name, path)

        result = (target_name, converted_val)
    elif key in _STR_LIST_KEYS:
        result = (_STR_LIST_KEYS[key], _convert_str_list(raw_key, val, path))
    elif key in _STR_KEYS:
        result = (_STR_KEYS[key], _convert_str_val(raw_key, val, path))
    elif key in _INT_KEYS:
        result = (_INT_KEYS[key], _convert_int_val(raw_key, val, path))
    elif key == "gitignore_file":
        result = ("gitignore_file", Path(_convert_str_val(raw_key, val, path)))
    else:
        _report_unknown_key(raw_key, key, path)

    return result


def validate_and_convert_config(raw_data: dict[str, Any], path: Path) -> dict[str, Any]:
    """Validate configuration dictionary schema and map to CLI parameter defaults.

    Args:
        raw_data: Unvalidated settings dictionary from TOML file.
        path: Path to configuration file for diagnostic error reporting.

    Returns:
        Dictionary of validated option defaults ready for Click default_map.

    Raises:
        typer.Exit: On encountering unrecognized keys, alias collisions, or type mismatches.
    """
    converted: dict[str, Any] = {}
    seen_targets: dict[str, str] = {}
    had_error = False

    for raw_key, val in raw_data.items():
        key = raw_key.removeprefix("FINDFMT_").lower().replace("-", "_")
        try:
            target_name, converted_val = _convert_single_key(raw_key, key, val, path)
        except typer.Exit:
            had_error = True
            continue

        if target_name in seen_targets:
            typer.echo(
                _(
                    "Error: Conflicting configuration keys '{first}' and '{second}' in '{path}'.",
                ).format(
                    first=seen_targets[target_name],
                    second=raw_key,
                    path=path,
                ),
                err=True,
            )
            had_error = True
            continue

        seen_targets[target_name] = raw_key
        converted[target_name] = converted_val

    if had_error:
        raise typer.Exit(code=2)

    return converted
