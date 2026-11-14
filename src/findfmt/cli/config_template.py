"""TOML configuration formatting and template generation for findfmt (#310)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from findfmt.i18n import _

if TYPE_CHECKING:
    from pathlib import Path

__all__ = [
    "format_config_dump",
    "generate_reference_config",
    "generate_sample_config",
]

# Each entry is (key, concrete_default_or_none, example_toml_when_none, description).
_REFERENCE_SECTIONS: tuple[
    tuple[str, tuple[tuple[str, object, str, str], ...]],
    ...,
] = (
    (
        "1. Output Serialization & Styling",
        (
            (
                "format",
                "text",
                "",
                "Output format (text, table, tree, json, jsonl, yaml, ipynb, csv,\n"
                "# csv-table, tsv, markdown, rst, xml, html).",
            ),
            (
                "table_style",
                None,
                '"rounded"',
                "Table border style (rounded, simple, minimal, double, heavy,\n"
                "# markdown, ascii, cp437, square, grid).",
            ),
            (
                "color",
                "auto",
                "",
                'ANSI color policy ("auto", "always", "never", or boolean).',
            ),
            (
                "pager",
                "auto",
                "",
                'Terminal paging policy ("auto", "always", "never", or boolean).',
            ),
            (
                "no_indent",
                False,
                "",
                "Omit tree branch lines and strip whitespace in structured formats.",
            ),
            (
                "ansi_lines",
                False,
                "",
                "Use ANSI/VT100 line-drawing escapes for tree indentation lines.",
            ),
            (
                "cp437",
                False,
                "",
                "Use CP437 console graphics characters for tree indentation lines.",
            ),
            (
                "csv_safe",
                False,
                "",
                "Prefix formula triggers in CSV/TSV cells with a single quote.",
            ),
            (
                "html",
                None,
                '"https://example.com"',
                "Render HTML5 output with hyperlinks prefixed by BASEHREF.",
            ),
            (
                "title",
                None,
                '"Directory Tree"',
                "Custom <title> and <h1> heading for HTML document output.",
            ),
            (
                "no_links",
                False,
                "",
                "Suppress hyperlink anchors in HTML output, rendering plain paths.",
            ),
            (
                "hyperlink",
                False,
                "",
                "Wrap paths in OSC 8 clickable terminal hyperlink escape sequences.",
            ),
            (
                "hyperlink_schema",
                "file://",
                "",
                "URI schema prefix for terminal hyperlinks (e.g. vscode://file/).",
            ),
            (
                "hyperlink_authority",
                None,
                '"localhost"',
                "Optional authority or hostname component for terminal hyperlinks.",
            ),
        ),
    ),
    (
        "2. Traversal Scope & Boundaries",
        (
            ("hidden", False, "", "Include dotfiles and hidden directories in traversal."),
            (
                "ignore",
                True,
                "",
                "Respect .gitignore and global gitignore rules (false disables).",
            ),
            (
                "gitignore_file",
                None,
                '".gitignore"',
                "External .gitignore file path applied across the traversal scope.",
            ),
            ("follow_symlinks", False, "", "Follow symbolic links during traversal."),
            ("dirs_only", False, "", "Emit directories only and suppress regular files."),
            (
                "one_file_system",
                False,
                "",
                "Confine traversal to the starting directory filesystem device.",
            ),
            (
                "max_depth",
                None,
                "3",
                "Maximum directory descent depth limit (non-negative integer).",
            ),
            (
                "file_limit",
                None,
                "1000",
                "Skip directories containing more than this number of entries.",
            ),
            ("prune", False, "", "Omit directories containing zero matching items."),
            (
                "allow_outside_root",
                False,
                "",
                "Allow --from-file paths that resolve outside the traversal root.",
            ),
        ),
    ),
    (
        "3. Tag, Pattern & Shebang Filtering",
        (
            ("tags", [], "", 'Default classification tags to include (e.g. ["python"]).'),
            ("exclude_tags", [], "", 'Classification tags to exclude (e.g. ["binary"]).'),
            (
                "all_tags",
                False,
                "",
                "Require matching files to have ALL specified tags instead of ANY.",
            ),
            ("pattern", [], "", 'Wildcard filename include patterns (e.g. ["*.py"]).'),
            (
                "exclude_pattern",
                [],
                "",
                'Wildcard filename exclude patterns (e.g. ["*_pb2.py"]).',
            ),
            ("ignore_case", False, "", "Apply case-insensitive glob pattern matching."),
            (
                "match_dirs",
                False,
                "",
                "Match directory names against patterns and inherit to children.",
            ),
            (
                "shebang",
                None,
                '"python"',
                "Filter files whose #! shebang contains this interpreter pattern.",
            ),
        ),
    ),
    (
        "4. Sorting & Entry Ordering",
        (
            (
                "sort",
                "name",
                "",
                'Sort criterion ("name", "size", "mtime", "ctime", "version", "none").',
            ),
            ("unsorted", False, "", "Yield entries in raw filesystem order without sorting."),
            ("reverse", False, "", "Reverse the active sort order."),
            ("dirs_first", False, "", "Group directories before files within each level."),
            ("files_first", False, "", "Group files before directories within each level."),
        ),
    ),
    (
        "5. Path Display, Metadata & Diagnostics",
        (
            ("absolute", False, "", "Output absolute paths instead of relative paths."),
            ("relative", False, "", "Prepend input search path prefix to relative paths."),
            ("print0", False, "", r"Delimit paths with a NUL (\0) byte for xargs -0."),
            ("list_tags", False, "", "Display identified classification tags alongside paths."),
            ("summary", False, "", "Print match count and tag frequency statistics to stderr."),
            ("exit_status", False, "", "Exit with status code 1 when zero files match."),
            ("permissions", False, "", "Display file type and permissions in ls -l style."),
            ("user", False, "", "Display file owner username or numeric UID."),
            ("group", False, "", "Display file group name or numeric GID."),
            ("inodes", False, "", "Display filesystem inode number (st_ino)."),
            ("device", False, "", "Display filesystem device number (st_dev)."),
            ("size", False, "", "Display file size in bytes (st_size)."),
            ("human_readable", False, "", "Format file sizes using binary units (KiB, MiB)."),
            ("si", False, "", "Format file sizes using SI metric units (kB, MB)."),
            ("du", False, "", "Accumulate recursive directory disk usage."),
            ("mtime", False, "", "Display file last modification timestamp (st_mtime)."),
            ("ctime", False, "", "Display file status change timestamp (st_ctime)."),
            (
                "time_format",
                None,
                '"%Y-%m-%d %H:%M:%S"',
                "Custom strftime format string for timestamps.",
            ),
            ("classify", False, "", "Append file type indicator characters (/, *, @, =, |, >)."),
            (
                "hide_control_chars",
                False,
                "",
                "Replace non-printable control characters in filenames with '?'.",
            ),
            ("literal", False, "", "Print non-printable control characters literally."),
            ("quote_name", False, "", "Enclose filenames in double quotes."),
            (
                "locale",
                None,
                '"en_US"',
                'Display and translation locale override (e.g. "en_US", "de", "es").',
            ),
        ),
    ),
)


def _format_toml_value(val: object) -> str:
    """Format a Python value as a TOML scalar or list string."""
    if isinstance(val, bool):
        return "true" if val else "false"

    if isinstance(val, (int, float)):
        return str(val)

    if isinstance(val, list):
        items = ", ".join(f'"{x}"' if isinstance(x, str) else str(x) for x in val)
        return f"[{items}]"

    return f'"{val}"'


def format_config_dump(path: Path | None, config_dict: dict[str, Any]) -> str:
    """Format active configuration settings for diagnostic display.

    Args:
        path: Path of the active configuration file or None.
        config_dict: Dictionary of active configuration key-value pairs.

    Returns:
        Formatted multi-line diagnostic string ending in a newline.
    """
    active_label = str(path) if path is not None else _("(none)")
    if not config_dict:
        return _("Active configuration: {path} (using built-in defaults)\n").format(
            path=active_label,
        )

    lines = [_("Active configuration: {path}").format(path=active_label), "", "[tool.findfmt]"]
    for key in sorted(config_dict):
        val_str = _format_toml_value(config_dict[key])
        lines.append(f"{key} = {val_str}")

    return "\n".join(lines) + "\n"


def generate_sample_config() -> str:
    """Return a practical sample TOML configuration showcasing popular options."""
    return (
        "# Sample findfmt configuration (save to ~/.config/findfmt/config.toml\n"
        "# or .findfmt.toml, or copy [tool.findfmt] into pyproject.toml).\n\n"
        "[tool.findfmt]\n"
        'format = "table"\n'
        'table_style = "rounded"\n'
        'color = "auto"\n'
        'pager = "auto"\n'
        "hyperlink = true\n"
        "summary = true\n"
        "dirs_first = true\n"
        "dirs_only = false\n"
        "hidden = false\n"
        "ignore = true\n"
    )


def generate_reference_config() -> str:
    """Generate the comprehensive, annotated reference TOML configuration."""
    lines: list[str] = [
        "# =============================================================================",
        "# findfmt Annotated Reference Configuration",
        "#",
        "# Generate with: findfmt --generate-config > ~/.config/findfmt/config.toml",
        "# Precedence:    user < project (.findfmt.toml / pyproject.toml) < env < CLI",
        "# =============================================================================",
        "",
        "[tool.findfmt]",
    ]
    for section_title, entries in _REFERENCE_SECTIONS:
        lines.extend(
            [
                "",
                "# -----------------------------------------------------------------------------",
                f"# {section_title}",
                "# -----------------------------------------------------------------------------",
            ],
        )
        for key, default_val, example_when_none, description in entries:
            lines.append(f"\n# {description}")
            if default_val is None:
                lines.append(f"# {key} = {example_when_none}")
            else:
                lines.append(f"{key} = {_format_toml_value(default_val)}")

    return "\n".join(lines) + "\n"
