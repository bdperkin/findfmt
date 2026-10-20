"""Unit tests for file size formatting and disk usage accumulation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from findfmt.cli.main import app
from findfmt.formatters import RichTableFormatter, RichTreeFormatter, TextFormatter
from findfmt.i18n import format_integer, override_locale
from findfmt.metadata import format_metadata_parts
from findfmt.models import FileInfo
from findfmt.sizes import (
    calculate_accumulated_sizes,
    format_size,
    format_size_binary,
    format_size_bytes,
    format_size_si,
)


def test_format_size_bytes() -> None:
    """Verify format_size_bytes formats raw byte counts."""
    assert format_size_bytes(0) == "0 B"
    assert format_size_bytes(1) == "1 B"
    assert format_size_bytes(1024) == "1024 B"
    assert format_size_bytes(1048576) == "1048576 B"
    assert format_size_bytes(-50) == "-50 B"


def test_format_size_binary() -> None:
    """Verify format_size_binary formats sizes using powers of 1024."""
    assert format_size_binary(-10) == "-10 B"
    assert format_size_binary(0) == "0 B"
    assert format_size_binary(512) == "512 B"
    assert format_size_binary(1023) == "1023 B"
    assert format_size_binary(1024) == "1.0 K"
    assert format_size_binary(1536) == "1.5 K"
    assert format_size_binary(1024**2) == "1.0 M"
    assert format_size_binary(1024**3) == "1.0 G"
    assert format_size_binary(1024**4) == "1.0 T"
    assert format_size_binary(1024**5) == "1.0 P"
    assert format_size_binary(1024**6) == "1.0 E"
    # Over max unit
    assert format_size_binary(1024**7) == "1024.0 E"


def test_format_size_si() -> None:
    """Verify format_size_si formats sizes using metric powers of 1000."""
    assert format_size_si(-10) == "-10 B"
    assert format_size_si(0) == "0 B"
    assert format_size_si(500) == "500 B"
    assert format_size_si(999) == "999 B"
    assert format_size_si(1000) == "1.0 kB"
    assert format_size_si(1500) == "1.5 kB"
    assert format_size_si(1000**2) == "1.0 MB"
    assert format_size_si(1000**3) == "1.0 GB"
    assert format_size_si(1000**4) == "1.0 TB"
    assert format_size_si(1000**5) == "1.0 PB"
    assert format_size_si(1000**6) == "1.0 EB"
    # Over max unit
    assert format_size_si(1000**7) == "1000.0 EB"


def test_format_size_dispatch() -> None:
    """Verify format_size switches between exact, binary, SI, and default modes."""
    # exact
    assert format_size(1024, exact=True) == "1024 B"
    # human_readable
    assert format_size(1024, human_readable=True) == "1.0 K"
    # si
    assert format_size(1000, si=True) == "1.0 kB"
    # default
    assert format_size(500) == "500 B"
    assert format_size(1024) == "1.0 KB"
    assert format_size(1024 * 1024 * 1024) == "1.0 GB"
    # Default unit overflow
    assert format_size(1024**4) == "1024.0 GB"


def test_localized_size_formatting() -> None:
    """Verify format_size, format_size_bytes, and units respect regional locales."""
    # French: comma decimal separator, Mo/Ko unit names, octets 'o'
    with override_locale("fr"):
        assert format_size(int(12.4 * 1024 * 1024)) == "12,4 Mo"
        assert format_size(int(1.5 * 1024)) == "1,5 Ko"
        assert format_size(int(2.5 * 1024 * 1024 * 1024)) == "2,5 Go"
        assert format_size_bytes(1048576) == "1048576 o"
        assert format_integer(1048576, grouping=True) in ("1\u202f048\u202f576", "1 048 576")

    # German: comma decimal separator, MB/KB unit names, 'B'
    with override_locale("de"):
        assert format_size(int(12.4 * 1024 * 1024)) == "12,4 MB"
        assert format_size_bytes(1048576) == "1048576 B"
        assert format_integer(1048576, grouping=True) == "1.048.576"

    # Spanish: period-separated thousands, comma decimal
    with override_locale("es"):
        assert format_size(int(12.4 * 1024 * 1024)) == "12,4 MB"
        assert format_size_bytes(1048576) == "1048576 B"
        assert format_integer(1048576, grouping=True) == "1.048.576"

    # Hindi / South Asian: lakh/crore grouping
    with override_locale("hi"):
        assert format_size_bytes(1048576) == "1048576 B"
        assert format_integer(1048576, grouping=True) == "10,48,576"


def test_calculate_accumulated_sizes_file_root(tmp_path: Path) -> None:
    """Verify calculate_accumulated_sizes handles a file as root."""
    file_path = tmp_path / "single.txt"
    file_path.write_bytes(b"x" * 42)
    sizes = calculate_accumulated_sizes(file_path)
    assert sizes[file_path] == 42


def test_calculate_accumulated_sizes_tree(tmp_path: Path) -> None:
    """Verify calculate_accumulated_sizes computes correct post-order directory totals."""
    # Structure:
    # tmp_path/
    #   root_file.txt (10 bytes)
    #   sub1/
    #     child1.txt (20 bytes)
    #     nested/
    #       deep.txt (30 bytes)
    #   sub2/ (empty dir)
    #   .hidden_file (100 bytes)
    #   .hidden_dir/
    #     hidden_child.txt (200 bytes)
    (tmp_path / "root_file.txt").write_bytes(b"a" * 10)
    sub1 = tmp_path / "sub1"
    sub1.mkdir()
    (sub1 / "child1.txt").write_bytes(b"b" * 20)
    nested = sub1 / "nested"
    nested.mkdir()
    (nested / "deep.txt").write_bytes(b"c" * 30)
    sub2 = tmp_path / "sub2"
    sub2.mkdir()
    (tmp_path / ".hidden_file").write_bytes(b"h" * 100)
    hidden_dir = tmp_path / ".hidden_dir"
    hidden_dir.mkdir()
    (hidden_dir / "hidden_child.txt").write_bytes(b"x" * 200)

    # With hidden files included
    sizes = calculate_accumulated_sizes(tmp_path, include_hidden=True)
    assert sizes[nested] == 30
    assert sizes[sub1] == 50
    assert sizes[sub2] == 0
    assert sizes[hidden_dir] == 200
    assert sizes[tmp_path] == 360

    # With hidden files excluded
    sizes_no_hidden = calculate_accumulated_sizes(tmp_path, include_hidden=False)
    assert sizes_no_hidden[nested] == 30
    assert sizes_no_hidden[sub1] == 50
    assert sizes_no_hidden[sub2] == 0
    assert hidden_dir not in sizes_no_hidden
    assert sizes_no_hidden[tmp_path] == 60


def test_calculate_accumulated_sizes_symlinks(tmp_path: Path) -> None:
    """Verify calculate_accumulated_sizes respects symlink flags and prevents cycles."""
    ext_dir = tmp_path / "external"
    ext_dir.mkdir()
    (ext_dir / "data.bin").write_bytes(b"y" * 50)

    search_root = tmp_path / "search"
    search_root.mkdir()
    link_dir = search_root / "link_to_ext"
    link_dir.symlink_to(ext_dir, target_is_directory=True)

    # With follow_symlinks=False
    sizes_no_follow = calculate_accumulated_sizes(search_root, follow_symlinks=False)
    assert link_dir not in sizes_no_follow
    assert sizes_no_follow[search_root] == 0

    # With follow_symlinks=True
    sizes_follow = calculate_accumulated_sizes(search_root, follow_symlinks=True)
    assert sizes_follow[link_dir] == 50
    assert sizes_follow[search_root] == 50

    # Cycle test
    cycle_dir = tmp_path / "cycle_dir"
    cycle_dir.mkdir()
    (cycle_dir / "cycle_file.bin").write_bytes(b"z" * 25)
    loop_link = cycle_dir / "loop"
    loop_link.symlink_to(cycle_dir, target_is_directory=True)
    # Should not raise RecursionError or hang
    cycle_sizes = calculate_accumulated_sizes(cycle_dir, follow_symlinks=True)
    assert cycle_sizes[cycle_dir] == 25


def test_calculate_accumulated_sizes_visited_root(tmp_path: Path) -> None:
    """Verify calculate_accumulated_sizes returns empty dict if root is already visited."""
    visited = {tmp_path.resolve()}
    sizes = calculate_accumulated_sizes(tmp_path, visited=visited)
    assert sizes == {}


def test_calculate_accumulated_sizes_os_errors(tmp_path: Path) -> None:
    """Verify calculate_accumulated_sizes handles OS errors gracefully."""
    # Test root resolve error
    with patch.object(Path, "resolve", side_effect=OSError("Resolve error")):
        sizes = calculate_accumulated_sizes(tmp_path)
        assert sizes[tmp_path] == 0

    # Test root.is_dir() OSError
    with patch.object(Path, "is_dir", side_effect=OSError("is_dir error")):
        sizes = calculate_accumulated_sizes(tmp_path)
        assert sizes[tmp_path] == 0

    # Test not root.is_dir() with stat() OSError
    with (
        patch.object(Path, "is_dir", return_value=False),
        patch.object(Path, "stat", side_effect=OSError("stat error")),
    ):
        sizes = calculate_accumulated_sizes(tmp_path)
        assert sizes[tmp_path] == 0

    # Test os.scandir error
    with patch("os.scandir", side_effect=PermissionError("Permission denied")):
        sizes = calculate_accumulated_sizes(tmp_path)
        assert sizes[tmp_path] == 0

    # Test error inside scandir entry loop
    mock_entry = MagicMock()
    mock_entry.name = "error_child"
    mock_entry.is_dir.side_effect = OSError("Child error")
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = [mock_entry]
    mock_ctx.__exit__.return_value = None

    with patch("os.scandir", return_value=mock_ctx):
        sizes = calculate_accumulated_sizes(tmp_path)
        assert sizes[tmp_path] == 0


def test_format_metadata_parts_size() -> None:
    """Verify format_metadata_parts formats size correctly."""
    info = FileInfo(
        path=Path("main.py"),
        relative_path=Path("main.py"),
        size_bytes=2048,
    )
    # Default exact
    parts = format_metadata_parts(info, show_size=True)
    assert parts == ["2048 B"]

    # Binary human readable
    parts_h = format_metadata_parts(info, show_size=True, human_readable=True)
    assert parts_h == ["2.0 K"]

    # SI metric
    parts_si = format_metadata_parts(info, show_size=True, show_si=True)
    assert parts_si == ["2.0 kB"]


def test_text_formatter_sizes() -> None:
    """Verify TextFormatter integrates size formatting options."""
    files = [
        FileInfo(
            path=Path("app.py"),
            relative_path=Path("app.py"),
            size_bytes=1024,
        ),
    ]
    fmt_exact = TextFormatter(show_size=True)
    assert fmt_exact.format(files).strip() == "[1024 B] app.py"

    fmt_bin = TextFormatter(show_size=True, human_readable=True)
    assert fmt_bin.format(files).strip() == "[1.0 K] app.py"

    fmt_si = TextFormatter(show_size=True, show_si=True)
    assert fmt_si.format(files).strip() == "[1.0 kB] app.py"


def test_rich_table_formatter_sizes() -> None:
    """Verify RichTableFormatter formats the Size column based on active options."""
    files = [
        FileInfo(
            path=Path("module.py"),
            relative_path=Path("module.py"),
            size_bytes=2048,
        ),
    ]
    fmt_exact = RichTableFormatter(show_size=True)
    out = fmt_exact.format(files)
    assert "2048 B" in out

    fmt_bin = RichTableFormatter(show_size=True, human_readable=True)
    out_bin = fmt_bin.format(files)
    assert "2.0 K" in out_bin

    fmt_si = RichTableFormatter(show_size=True, show_si=True)
    out_si = fmt_si.format(files)
    assert "2.0 kB" in out_si


def test_rich_tree_formatter_sizes(tmp_path: Path) -> None:
    """Verify RichTreeFormatter displays leaf and accumulated sizes."""
    sub = tmp_path / "subdir"
    sub.mkdir()
    child = sub / "file.txt"
    child.write_bytes(b"z" * 1024)

    files = [
        FileInfo(
            path=child,
            relative_path=Path("subdir/file.txt"),
            size_bytes=1024,
        ),
    ]
    # Exact tree size
    fmt = RichTreeFormatter(show_size=True)
    out = fmt.format(files)
    assert "1024 B" in out

    # Human readable tree with accumulated sizes
    fmt_du = RichTreeFormatter(show_size=True, human_readable=True, accumulate_size=True)
    out_du = fmt_du.format(files)
    assert "1.0 K" in out_du


def test_cli_size_options(tmp_path: Path) -> None:
    """Verify CLI flags --size, -h, --si, and --du run without errors."""
    sub = tmp_path / "pkg"
    sub.mkdir()
    (sub / "test.py").write_text("print('test')\n", encoding="utf-8")

    runner = CliRunner(env={"NO_COLOR": "1", "TERM": "dumb"})

    # --size
    res_size = runner.invoke(app, [str(tmp_path), "--size"])
    assert res_size.exit_code == 0
    assert "B" in res_size.stdout

    # -h
    res_h = runner.invoke(app, [str(tmp_path), "--size", "-h"])
    assert res_h.exit_code == 0

    # --si
    res_si = runner.invoke(app, [str(tmp_path), "--size", "--si"])
    assert res_si.exit_code == 0

    # --du
    res_du = runner.invoke(app, [str(tmp_path), "--du"])
    assert res_du.exit_code == 0

    # --du with --tree
    res_du_tree = runner.invoke(app, [str(tmp_path), "--du", "--tree"])
    assert res_du_tree.exit_code == 0
