"""Rich visual terminal formatters and layout components."""

from __future__ import annotations

import io
import sys
from typing import TYPE_CHECKING, TextIO

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

import rich.markup
from rich import box
from rich.panel import Panel
from rich.table import Table

from findfmt.cli.terminal import _reconfigure_cp437, get_console
from findfmt.exceptions import UnsupportedBoxStyleError
from findfmt.formatters.badges import format_tag_badge
from findfmt.formatters.base import _MetadataFormatterBase
from findfmt.formatters.glyphs import CP437_BOX
from findfmt.formatters.tree import RichTreeFormatter
from findfmt.i18n import _, format_integer, ngettext
from findfmt.sizes import format_size

if TYPE_CHECKING:
    from collections import Counter
    from collections.abc import Iterable

    from findfmt.models import FileInfo

__all__ = [
    "RICH_BOX_STYLES",
    "RichTableFormatter",
    "RichTreeFormatter",
    "UnsupportedBoxStyleError",
    "format_size",
    "format_summary_panel",
    "format_tag_badge",
]

RICH_BOX_STYLES: dict[str, box.Box] = {
    "ascii": box.ASCII,
    "cp437": CP437_BOX,
    "double": box.DOUBLE,
    "grid": box.SQUARE,
    "heavy": box.HEAVY,
    "markdown": box.MARKDOWN,
    "minimal": box.MINIMAL,
    "rounded": box.ROUNDED,
    "simple": box.SIMPLE,
    "square": box.SQUARE,
}


def format_summary_panel(
    match_count: int,
    tag_counter: Counter[str],
    *,
    total_bytes: int | None = None,
) -> Panel:
    """Format execution statistics into a styled Rich Panel."""
    count_str = format_integer(match_count, grouping=True)
    matched_label = ngettext(
        "[bold]Matched file:[/] [cyan]{count}[/]",
        "[bold]Matched files:[/] [cyan]{count}[/]",
        match_count,
    ).format(count=count_str)
    body_lines = [matched_label]
    if total_bytes is not None:
        size_str = format_size(total_bytes)
        body_lines.append(f"[bold]{_('Total size:')}[/] [cyan]{size_str}[/]")

    if tag_counter:
        body_lines.append("")
        body_lines.append(_("[bold]Top tags:[/]") or "[bold]Top tags:[/]")
        top_tags = sorted(tag_counter.items(), key=lambda item: (-item[1], item[0]))[:10]
        for tag, count in top_tags:
            badge = format_tag_badge(tag)
            tag_count_str = format_integer(count, grouping=True)
            body_lines.append(f"  {badge}: [green]{tag_count_str}[/]")

    return Panel(
        "\n".join(body_lines),
        title=_("--- findfmt summary ---"),
        border_style="blue",
        expand=False,
    )


class RichTableFormatter(_MetadataFormatterBase):
    """Rich visual table serializer supporting customizable borders and tag badges."""

    def __init__(  # noqa: PLR0913 - wide CLI/config signature
        self,
        *,
        absolute: bool = False,
        table_style: str = "rounded",
        console_width: int | None = None,
        force_color: bool | None = None,
        show_permissions: bool = False,
        show_user: bool = False,
        show_group: bool = False,
        show_inodes: bool = False,
        show_device: bool = False,
        show_size: bool = False,
        human_readable: bool = False,
        show_si: bool = False,
        accumulate_size: bool = False,
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
        """Initialize RichTableFormatter.

        Args:
            absolute: Whether to emit absolute paths.
            table_style: Border style name mapping to rich.box styles.
            console_width: Optional terminal output column width override.
            force_color: Explicit color enable override flag.
            show_permissions: Whether to display permissions column.
            show_user: Whether to display file owner user column.
            show_group: Whether to display file owner group column.
            show_inodes: Whether to display filesystem inode column.
            show_device: Whether to display filesystem device column.
            show_size: Whether to display exact byte size.
            human_readable: Whether to format sizes using binary units.
            show_si: Whether to format sizes using SI metric units.
            accumulate_size: Whether to accumulate recursive directory disk usage.
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

        Raises:
            UnsupportedBoxStyleError: If table_style is not recognized.
        """
        super().__init__(absolute=absolute)
        normalized = table_style.lower().strip()
        if normalized not in RICH_BOX_STYLES:
            valid_styles = ", ".join(sorted(RICH_BOX_STYLES.keys()))
            raise UnsupportedBoxStyleError(table_style, valid_styles)

        self.table_style = normalized
        self.box_style = RICH_BOX_STYLES[normalized]
        self.console_width = console_width
        self.force_color = force_color
        self._set_ownership_options(permissions=show_permissions, user=show_user, group=show_group)
        self._set_stat_options(inodes=show_inodes, device=show_device, mtime=show_mtime, ctime=show_ctime)
        self.time_format = time_format
        self._set_size_options(exact=show_size, human=human_readable, si=show_si, accum=accumulate_size)
        self._set_path_options(classify=classify, ctrl=hide_control_chars, literal=literal, quote=quote_name)
        self._set_hyperlink_options(link=hyperlink, schema=hyperlink_schema, authority=hyperlink_authority)

    def _setup_columns(self, table: Table) -> None:
        """Configure table columns including optional metadata columns."""
        if self.show_inodes:
            table.add_column(_("Inode"), justify="right")

        if self.show_device:
            table.add_column(_("Device"), justify="right")

        if self.show_permissions:
            table.add_column(_("Permissions"), style="dim")

        if self.show_user:
            table.add_column(_("User"))

        if self.show_group:
            table.add_column(_("Group"))

        if self.show_mtime:
            table.add_column(_("Modified"), style="blue")
        elif self.show_ctime:
            table.add_column(_("Status Changed"), style="blue")

        table.add_column(_("Path"), style="cyan", no_wrap=True)
        table.add_column(_("Tags"), no_wrap=False)
        table.add_column(_("MIME Type"), style="magenta")
        table.add_column(_("Size"), justify="right", style="green")
        table.add_column(_("Executable"), justify="center")
        table.add_column(_("Symlink"), justify="center")
        table.add_column(_("Shebang"), style="dim")

    def _format_row(self, file_info: FileInfo) -> list[str]:
        """Format an individual file record as a table row sequence."""
        row = self._format_stat_parts(file_info)
        formatted_sz = format_size(
            file_info.size_bytes,
            human_readable=self.human_readable,
            si=self.show_si,
            exact=self.show_size,
        )
        display_path = self._format_file_display_path(file_info, escape_markup=True)
        row = [rich.markup.escape(c) for c in row]
        mime_val = rich.markup.escape(file_info.mime_type or "")
        shebang_val = rich.markup.escape(file_info.shebang or "")
        row.extend(
            [
                display_path,
                " ".join(format_tag_badge(t) for t in sorted(file_info.tags)),
                mime_val,
                formatted_sz,
                "[green]✓[/]" if file_info.is_executable else "[dim]-[/]",
                "[yellow]✓[/]" if file_info.is_symlink else "[dim]-[/]",
                shebang_val,
            ],
        )
        return row

    def _build_table(self, files: Iterable[FileInfo]) -> Table:
        """Construct a configured Rich Table populated with file rows."""
        table = Table(
            box=self.box_style,
            show_header=True,
            header_style="bold cyan",
            title="findfmt Files",
        )
        self._setup_columns(table)
        for file_info in files:
            table.add_row(*self._format_row(file_info))

        return table

    @override
    def format(self, files: Iterable[FileInfo]) -> str:
        """Render files into a formatted string table."""
        table = self._build_table(files)
        buf = io.StringIO()
        width = self.console_width if self.console_width is not None else 120
        get_console(buf, width=width, force_color=self.force_color).print(table)
        return buf.getvalue()

    @override
    def stream(self, files: Iterable[FileInfo], stream: TextIO) -> None:
        """Stream formatted table directly to a text stream."""
        if self.table_style == "cp437":
            _reconfigure_cp437(stream)

        table = self._build_table(files)
        get_console(stream, width=self.console_width, force_color=self.force_color).print(table)
