"""Rich visual terminal formatters and layout components."""

from __future__ import annotations

import io
import sys
from typing import TYPE_CHECKING, TextIO

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

from rich import box
from rich.panel import Panel
from rich.table import Table

from findfmt.formatters.badges import format_tag_badge
from findfmt.formatters.base import Formatter
from findfmt.formatters.glyphs import CP437_BOX
from findfmt.formatters.tree import RichTreeFormatter
from findfmt.metadata import format_metadata_parts
from findfmt.sizes import format_size
from findfmt.terminal import get_console
from findfmt.utils.strings import format_display_path

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


def format_summary_panel(match_count: int, tag_counter: Counter[str]) -> Panel:
    """Format execution statistics into a styled Rich Panel."""
    body_lines = [f"[bold]Matched files:[/] [cyan]{match_count}[/]"]
    if tag_counter:
        body_lines.append("")
        body_lines.append("[bold]Top tags:[/]")
        for tag, count in tag_counter.most_common(10):
            badge = format_tag_badge(tag)
            body_lines.append(f"  {badge}: [green]{count}[/]")

    return Panel(
        "\n".join(body_lines),
        title="--- findfmt summary ---",
        border_style="blue",
        expand=False,
    )


class UnsupportedBoxStyleError(ValueError):
    """Raised when an unsupported table border style is requested."""

    def __init__(self, table_style: str, valid_styles: str) -> None:
        """Initialize UnsupportedBoxStyleError."""
        super().__init__(
            f"Unsupported table style: '{table_style}'. Expected one of: {valid_styles}",
        )


class RichTableFormatter(Formatter):
    """Rich visual table serializer supporting customizable borders and tag badges."""

    def __init__(  # noqa: PLR0913
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
        self.show_permissions = show_permissions
        self.show_user = show_user
        self.show_group = show_group
        self.show_inodes = show_inodes
        self.show_device = show_device
        self.show_size = show_size
        self.human_readable = human_readable
        self.show_si = show_si
        self.accumulate_size = accumulate_size
        self.show_mtime = show_mtime
        self.show_ctime = show_ctime
        self.time_format = time_format
        self.classify = classify
        self.hide_control_chars = hide_control_chars
        self.literal = literal
        self.quote_name = quote_name

    def _setup_columns(self, table: Table) -> None:
        """Configure table columns including optional metadata columns."""
        if self.show_inodes:
            table.add_column("Inode", justify="right")

        if self.show_device:
            table.add_column("Device", justify="right")

        if self.show_permissions:
            table.add_column("Permissions", style="dim")

        if self.show_user:
            table.add_column("User")

        if self.show_group:
            table.add_column("Group")

        if self.show_mtime:
            table.add_column("Modified", style="blue")
        elif self.show_ctime:
            table.add_column("Status Changed", style="blue")

        table.add_column("Path", style="cyan", no_wrap=True)
        table.add_column("Tags", no_wrap=False)
        table.add_column("MIME Type", style="magenta")
        table.add_column("Size", justify="right", style="green")
        table.add_column("Executable", justify="center")
        table.add_column("Symlink", justify="center")
        table.add_column("Shebang", style="dim")

    def _format_row(self, file_info: FileInfo) -> list[str]:
        """Format an individual file record as a table row sequence."""
        row = format_metadata_parts(
            file_info,
            show_inodes=self.show_inodes,
            show_device=self.show_device,
            show_permissions=self.show_permissions,
            show_user=self.show_user,
            show_group=self.show_group,
            show_mtime=self.show_mtime,
            show_ctime=self.show_ctime,
            time_format=self.time_format,
        )
        formatted_sz = format_size(
            file_info.size_bytes,
            human_readable=self.human_readable,
            si=self.show_si,
            exact=self.show_size,
        )
        raw_path = str(file_info.path if self.absolute else file_info.relative_path)
        indicator = file_info.indicator if self.classify else None
        display_path = format_display_path(
            raw_path,
            quote_name=self.quote_name,
            hide_control_chars=self.hide_control_chars,
            literal=self.literal,
            indicator=indicator,
        )
        row.extend(
            [
                display_path,
                " ".join(format_tag_badge(t) for t in sorted(file_info.tags)),
                file_info.mime_type or "",
                formatted_sz,
                "[green]✓[/]" if file_info.is_executable else "[dim]-[/]",
                "[yellow]✓[/]" if file_info.is_symlink else "[dim]-[/]",
                file_info.shebang or "",
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
        table = self._build_table(files)
        get_console(stream, width=self.console_width, force_color=self.force_color).print(table)
