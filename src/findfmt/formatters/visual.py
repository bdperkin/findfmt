"""Rich visual terminal formatters and layout components."""

from __future__ import annotations

import collections
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
from findfmt.formatters.glyphs import CP437_BOX, resolve_tree_guides
from findfmt.metadata import format_metadata_parts
from findfmt.sizes import format_size
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


def _format_file_label(  # noqa: PLR0913
    file_info: FileInfo,
    filename: str,
    *,
    show_permissions: bool = False,
    show_user: bool = False,
    show_group: bool = False,
    show_inodes: bool = False,
    show_device: bool = False,
    show_size: bool = False,
    human_readable: bool = False,
    show_si: bool = False,
) -> str:
    """Format Rich leaf node label for a file with badges and optional metadata."""
    meta_parts = format_metadata_parts(
        file_info,
        show_inodes=show_inodes,
        show_device=show_device,
        show_permissions=show_permissions,
        show_user=show_user,
        show_group=show_group,
    )
    prefix = f"[cyan][{' '.join(meta_parts)}][/] " if meta_parts else ""
    tags_list = " ".join(format_tag_badge(t) for t in sorted(file_info.tags))
    tags_part = f" {tags_list}" if file_info.tags else ""
    formatted_sz = format_size(
        file_info.size_bytes,
        human_readable=human_readable,
        si=show_si,
        exact=show_size,
    )
    size_part = f" [green]{formatted_sz}[/]"
    mime_part = f" [dim]{file_info.mime_type}[/]" if file_info.mime_type else ""
    return f"{prefix}📄 {filename}{size_part}{tags_part}{mime_part}"


def _traverse_tree_node(
    tree: Tree,
    dir_nodes: dict[tuple[str, ...], Tree],
    dir_parts: tuple[str, ...],
    *,
    dir_sizes: dict[tuple[str, ...], str] | None = None,
) -> Tree:
    """Traverse or create branch nodes in tree for directory parts."""
    curr_node = tree
    for i in range(1, len(dir_parts) + 1):
        sub_tuple = dir_parts[:i]
        if sub_tuple not in dir_nodes:
            size_suffix = (
                f" [green]{dir_sizes[sub_tuple]}[/]"
                if dir_sizes is not None and sub_tuple in dir_sizes
                else ""
            )
            node_label = f"[bold blue]📁 {dir_parts[i - 1]}[/]{size_suffix}"
            dir_nodes[sub_tuple] = curr_node.add(node_label)

        curr_node = dir_nodes[sub_tuple]

    return curr_node


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
        )
        formatted_sz = format_size(
            file_info.size_bytes,
            human_readable=self.human_readable,
            si=self.show_si,
            exact=self.show_size,
        )
        row.extend(
            [
                str(file_info.path if self.absolute else file_info.relative_path),
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


def _compute_tree_dir_sizes(
    sorted_files: list[FileInfo],
    *,
    absolute: bool,
    human_readable: bool,
    show_si: bool,
    show_size: bool,
) -> dict[tuple[str, ...], str]:
    """Compute formatted accumulated directory sizes for tree display."""
    dir_sizes_raw: dict[tuple[str, ...], int] = collections.defaultdict(int)
    for file_info in sorted_files:
        target_path = file_info.path if absolute else file_info.relative_path
        is_abs = target_path.is_absolute()
        parts = target_path.parts
        dir_parts = tuple(parts[1:-1] if is_abs else parts[:-1])
        for i in range(1, len(dir_parts) + 1):
            dir_sizes_raw[dir_parts[:i]] += file_info.size_bytes

    dir_sizes_formatted: dict[tuple[str, ...], str] = {}
    for sub_tup, raw_sz in dir_sizes_raw.items():
        dir_sizes_formatted[sub_tup] = format_size(
            raw_sz,
            human_readable=human_readable,
            si=show_si,
            exact=show_size,
        )

    return dir_sizes_formatted


class RichTreeFormatter(Formatter):
    """Hierarchical directory tree serializer using Rich."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        absolute: bool = False,
        console_width: int | None = None,
        force_color: bool | None = None,
        no_indent: bool = False,
        ansi_lines: bool = False,
        cp437: bool = False,
        show_permissions: bool = False,
        show_user: bool = False,
        show_group: bool = False,
        show_inodes: bool = False,
        show_device: bool = False,
        show_size: bool = False,
        human_readable: bool = False,
        show_si: bool = False,
        accumulate_size: bool = False,
    ) -> None:
        """Initialize RichTreeFormatter.

        Args:
            absolute: Whether to emit absolute paths.
            console_width: Optional terminal output column width override.
            force_color: Explicit color enable override flag.
            no_indent: Whether to suppress branch indentation lines.
            ansi_lines: Whether to use ANSI/VT100 escape sequences.
            cp437: Whether to use CP437 console characters.
            show_permissions: Whether to display permissions string in labels.
            show_user: Whether to display file owner user in labels.
            show_group: Whether to display file owner group in labels.
            show_inodes: Whether to display filesystem inode in labels.
            show_device: Whether to display filesystem device in labels.
            show_size: Whether to display exact byte size.
            human_readable: Whether to format sizes using binary units.
            show_si: Whether to format sizes using SI metric units.
            accumulate_size: Whether to accumulate recursive directory disk usage.
        """
        super().__init__(absolute=absolute)
        self.console_width = console_width
        self.force_color = force_color
        self.no_indent = no_indent
        self.ansi_lines = ansi_lines
        self.cp437 = cp437
        self.show_permissions = show_permissions
        self.show_user = show_user
        self.show_group = show_group
        self.show_inodes = show_inodes
        self.show_device = show_device
        self.show_size = show_size
        self.human_readable = human_readable
        self.show_si = show_si
        self.accumulate_size = accumulate_size

    def _build_tree(self, files: Iterable[FileInfo]) -> Tree:
        """Construct a nested Rich Tree populated with directory branches and files."""
        sorted_files = sorted(
            files,
            key=lambda f: str(f.path if self.absolute else f.relative_path),
        )

        root_label = "[bold]/[/]" if self.absolute else "[bold].[/]"
        tree = Tree(root_label)
        guides = resolve_tree_guides(
            no_indent=self.no_indent,
            ansi_lines=self.ansi_lines,
            cp437=self.cp437,
        )
        tree.TREE_GUIDES = [guides, guides, guides]
        tree.ASCII_GUIDES = guides
        dir_nodes: dict[tuple[str, ...], Tree] = {}

        dir_sizes_formatted: dict[tuple[str, ...], str] | None = None
        if self.accumulate_size:
            dir_sizes_formatted = _compute_tree_dir_sizes(
                sorted_files,
                absolute=self.absolute,
                human_readable=self.human_readable,
                show_si=self.show_si,
                show_size=self.show_size,
            )

        for file_info in sorted_files:
            target_path = file_info.path if self.absolute else file_info.relative_path
            is_abs = target_path.is_absolute()
            parts = target_path.parts

            dir_parts = tuple(parts[1:-1] if is_abs else parts[:-1])
            curr_node = _traverse_tree_node(
                tree,
                dir_nodes,
                dir_parts,
                dir_sizes=dir_sizes_formatted,
            )
            filename = parts[-1] if parts else str(target_path)
            curr_node.add(
                _format_file_label(
                    file_info,
                    filename,
                    show_permissions=self.show_permissions,
                    show_user=self.show_user,
                    show_group=self.show_group,
                    show_inodes=self.show_inodes,
                    show_device=self.show_device,
                    show_size=self.show_size,
                    human_readable=self.human_readable,
                    show_si=self.show_si,
                ),
            )

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
