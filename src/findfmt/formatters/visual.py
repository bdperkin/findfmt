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
from rich.tree import Tree

from findfmt.formatters.base import Formatter
from findfmt.terminal import get_console

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

_KIB = 1024
_MIB = 1024 * 1024
_GIB = 1024 * 1024 * 1024

RICH_BOX_STYLES: dict[str, box.Box] = {
    "ascii": box.ASCII,
    "double": box.DOUBLE,
    "grid": box.SQUARE,
    "heavy": box.HEAVY,
    "markdown": box.MARKDOWN,
    "minimal": box.MINIMAL,
    "rounded": box.ROUNDED,
    "simple": box.SIMPLE,
    "square": box.SQUARE,
}

TAG_COLOR_MAP: dict[str, str] = {
    "binary": "red",
    "c": "bright_cyan",
    "cpp": "blue",
    "executable": "yellow",
    "json": "cyan",
    "markdown": "bright_magenta",
    "python": "bright_blue",
    "rust": "bright_red",
    "shell": "bright_yellow",
    "text": "green",
    "yaml": "magenta",
}


def format_size(size_bytes: int) -> str:
    """Format byte count into human-readable representation."""
    if size_bytes < _KIB:
        return f"{size_bytes} B"

    if size_bytes < _MIB:
        return f"{size_bytes / _KIB:.1f} KB"

    if size_bytes < _GIB:
        return f"{size_bytes / _MIB:.1f} MB"

    return f"{size_bytes / _GIB:.1f} GB"


def format_tag_badge(tag: str) -> str:
    """Render a colorful tag pill badge in Rich markup format."""
    color = TAG_COLOR_MAP.get(tag.lower(), "cyan")
    return f"[black on {color}] {tag} [/]"


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


def _format_file_label(file_info: FileInfo, filename: str) -> str:
    """Format Rich leaf node label for a file with badges."""
    tags_list = " ".join(format_tag_badge(t) for t in sorted(file_info.tags))
    tags_part = f" {tags_list}" if file_info.tags else ""
    size_part = f" [green]{format_size(file_info.size_bytes)}[/]"
    mime_part = f" [dim]{file_info.mime_type}[/]" if file_info.mime_type else ""
    return f"📄 {filename}{size_part}{tags_part}{mime_part}"


def _traverse_tree_node(
    tree: Tree,
    dir_nodes: dict[tuple[str, ...], Tree],
    dir_parts: tuple[str, ...],
) -> Tree:
    """Traverse or create branch nodes in tree for directory parts."""
    curr_node = tree
    for i in range(1, len(dir_parts) + 1):
        sub_tuple = dir_parts[:i]
        if sub_tuple not in dir_nodes:
            dir_nodes[sub_tuple] = curr_node.add(f"[bold blue]📁 {dir_parts[i - 1]}[/]")

        curr_node = dir_nodes[sub_tuple]

    return curr_node


class RichTableFormatter(Formatter):
    """Rich visual table serializer supporting customizable borders and tag badges."""

    def __init__(
        self,
        *,
        absolute: bool = False,
        table_style: str = "rounded",
        console_width: int | None = None,
        force_color: bool | None = None,
    ) -> None:
        """Initialize RichTableFormatter.

        Args:
            absolute: Whether to emit absolute paths.
            table_style: Border style name mapping to rich.box styles.
            console_width: Optional terminal output column width override.
            force_color: Explicit color enable override flag.

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

    def _build_table(self, files: Iterable[FileInfo]) -> Table:
        """Construct a configured Rich Table populated with file rows."""
        table = Table(
            box=self.box_style,
            show_header=True,
            header_style="bold cyan",
            title="findfmt Files",
        )
        table.add_column("Path", style="cyan", no_wrap=True)
        table.add_column("Tags", no_wrap=False)
        table.add_column("MIME Type", style="magenta")
        table.add_column("Size", justify="right", style="green")
        table.add_column("Executable", justify="center")
        table.add_column("Symlink", justify="center")
        table.add_column("Shebang", style="dim")

        for file_info in files:
            table.add_row(
                str(file_info.path if self.absolute else file_info.relative_path),
                " ".join(format_tag_badge(t) for t in sorted(file_info.tags)),
                file_info.mime_type or "",
                format_size(file_info.size_bytes),
                "[green]✓[/]" if file_info.is_executable else "[dim]-[/]",
                "[yellow]✓[/]" if file_info.is_symlink else "[dim]-[/]",
                file_info.shebang or "",
            )

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


class RichTreeFormatter(Formatter):
    """Hierarchical directory tree serializer using Rich."""

    def __init__(
        self,
        *,
        absolute: bool = False,
        console_width: int | None = None,
        force_color: bool | None = None,
    ) -> None:
        """Initialize RichTreeFormatter.

        Args:
            absolute: Whether to emit absolute paths.
            console_width: Optional terminal output column width override.
            force_color: Explicit color enable override flag.
        """
        super().__init__(absolute=absolute)
        self.console_width = console_width
        self.force_color = force_color

    def _build_tree(self, files: Iterable[FileInfo]) -> Tree:
        """Construct a nested Rich Tree populated with directory branches and files."""
        sorted_files = sorted(
            files,
            key=lambda f: str(f.path if self.absolute else f.relative_path),
        )

        root_label = "[bold]/[/]" if self.absolute else "[bold].[/]"
        tree = Tree(root_label)
        dir_nodes: dict[tuple[str, ...], Tree] = {}

        for file_info in sorted_files:
            target_path = file_info.path if self.absolute else file_info.relative_path
            is_abs = target_path.is_absolute()
            parts = target_path.parts

            dir_parts = tuple(parts[1:-1] if is_abs else parts[:-1])
            curr_node = _traverse_tree_node(tree, dir_nodes, dir_parts)
            filename = parts[-1] if parts else str(target_path)
            curr_node.add(_format_file_label(file_info, filename))

        return tree

    @override
    def format(self, files: Iterable[FileInfo]) -> str:
        """Render files into a formatted string tree."""
        tree = self._build_tree(files)
        buf = io.StringIO()
        width = self.console_width if self.console_width is not None else 120
        get_console(buf, width=width, force_color=self.force_color).print(tree)
        return buf.getvalue()

    @override
    def stream(self, files: Iterable[FileInfo], stream: TextIO) -> None:
        """Stream formatted tree directly to a text stream."""
        tree = self._build_tree(files)
        get_console(stream, width=self.console_width, force_color=self.force_color).print(tree)
