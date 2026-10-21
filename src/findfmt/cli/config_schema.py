"""Schema validation and conversion rules for findfmt configuration files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from findfmt.formatters import OutputFormat
from findfmt.i18n import _

__all__ = [
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
}

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


def _convert_format_val(key: str, val: object, path: Path) -> OutputFormat:
    """Validate and convert format setting string into canonical OutputFormat enum."""
    if not isinstance(val, str):
        msg = _("expected string format name, got {type_name}").format(
            type_name=type(val).__name__,
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
        val=val,
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

    msg = _("expected 'auto', 'always', 'never', or boolean, got '{val}'").format(val=val)
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
            type_name=type(val).__name__,
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
        type_name=type(val).__name__,
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
        msg = _("expected non-negative integer, got {val}").format(val=val)
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
        msg = _("expected string, got {type_name}").format(type_name=type(val).__name__)
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


def validate_and_convert_config(raw_data: dict[str, Any], path: Path) -> dict[str, Any]:
    """Validate configuration dictionary schema and map to CLI parameter defaults.

    Args:
        raw_data: Unvalidated settings dictionary from TOML file.
        path: Path to configuration file for diagnostic error reporting.

    Returns:
        Dictionary of validated option defaults ready for Click default_map.

    Raises:
        typer.Exit: On encountering unrecognized keys or schema type mismatches.
    """
    converted: dict[str, Any] = {}

    for raw_key, val in raw_data.items():
        key = raw_key.replace("-", "_")

        if key in ("format", "output_format"):
            converted["output_format"] = _convert_format_val(raw_key, val, path)
        elif key in ("color", "pager"):
            converted[key] = _convert_tri_state(raw_key, val, path)
        elif key in _BOOL_KEYS:
            target_name, invert = _BOOL_KEYS[key]
            converted[target_name] = _convert_bool_val(raw_key, val, path, invert=invert)
        elif key in _STR_LIST_KEYS:
            target_name = _STR_LIST_KEYS[key]
            converted[target_name] = _convert_str_list(raw_key, val, path)
        elif key in _STR_KEYS:
            target_name = _STR_KEYS[key]
            converted[target_name] = _convert_str_val(raw_key, val, path)
        elif key in _INT_KEYS:
            target_name = _INT_KEYS[key]
            converted[target_name] = _convert_int_val(raw_key, val, path)
        elif key == "gitignore_file":
            str_val = _convert_str_val(raw_key, val, path)
            converted["gitignore_file"] = Path(str_val)
        else:
            typer.echo(
                _("Error: Unknown configuration key '{key}' in '{path}'.").format(
                    key=raw_key,
                    path=path,
                ),
                err=True,
            )
            raise typer.Exit(code=2)

    return converted
