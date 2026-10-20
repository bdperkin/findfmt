"""Unit tests for timestamp formatting, classification indicators, and path quoting."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from findfmt.classifier import classify_file
from findfmt.cli.config import build_traversal_config
from findfmt.cli.main import app
from findfmt.formatters import OutputFormat, get_formatter
from findfmt.formatters.text import TextFormatter
from findfmt.formatters.visual import RichTableFormatter, RichTreeFormatter
from findfmt.metadata import format_metadata_parts
from findfmt.models import FileInfo
from findfmt.parsers.engine import classify_file_offline
from findfmt.utils.strings import (
    format_display_path,
    format_timestamp,
    get_classification_indicator,
    mask_control_characters,
    quote_filename,
)

runner = CliRunner()


def test_mask_control_characters() -> None:
    """Verify masking of ASCII control characters while preserving printable text."""
    # Control chars 0-31 and 127
    raw = "hello\x00\x07\x08\t\n\x1bworld\x7f!"
    masked = mask_control_characters(raw)
    assert masked == "hello??????world?!"

    # Printable ASCII and Unicode remain untouched
    clean = "regular-file_01.txt (unicode: \u2713 \u00e9)"
    assert mask_control_characters(clean) == clean


def test_quote_filename() -> None:
    """Verify double-quoting with backslash and internal quote escaping."""
    assert quote_filename("simple.txt") == '"simple.txt"'
    assert quote_filename('file "with" quotes') == r'"file \"with\" quotes"'
    assert quote_filename(r"path\with\backslashes") == r'"path\\with\\backslashes"'
    assert quote_filename(r"both \" mixed") == r'"both \\\" mixed"'


def test_format_display_path() -> None:
    """Verify combined path formatting with masking, quoting, and indicators."""
    # Baseline passthrough without flags
    assert format_display_path("plain.txt") == "plain.txt"

    # Masking only
    assert format_display_path("bad\x07name.txt", hide_control_chars=True) == "bad?name.txt"

    # Literal mode without masking
    raw_bad = "bad\x07name.txt"
    assert format_display_path(raw_bad, hide_control_chars=False, literal=True) == raw_bad

    # hide_control_chars active under literal
    assert format_display_path(raw_bad, hide_control_chars=True, literal=True) == "bad?name.txt"

    # Quoting only
    assert format_display_path("space name.txt", quote_name=True) == '"space name.txt"'

    # Indicator only
    assert format_display_path("script.sh", indicator="*") == "script.sh*"

    # Indicator with directory
    assert format_display_path("subdir", indicator="/") == "subdir/"

    # Combined quoting and indicator: indicator must be OUTSIDE quotes
    assert format_display_path("script.sh", quote_name=True, indicator="*") == '"script.sh"*'
    assert format_display_path("subdir", quote_name=True, indicator="/") == '"subdir"/'

    # Combined masking, quoting, and indicator
    assert (
        format_display_path(
            'my\x00"dir"',
            quote_name=True,
            hide_control_chars=True,
            indicator="/",
        )
        == r'"my?\"dir\""/'
    )


def test_format_timestamp() -> None:
    """Verify timestamp formatting including default format, custom format, and error handling."""
    # None timestamp returns '-'
    assert format_timestamp(None) == "-"

    # Valid timestamp with default format
    ts = 1700000000.0
    formatted_default = format_timestamp(ts)
    assert formatted_default != "-"
    assert len(formatted_default) > 0

    # Custom format
    formatted_custom = format_timestamp(ts, fmt="%Y-%m-%d")
    assert formatted_custom.startswith("2023-11-")

    # Overflow/invalid timestamp returns '-'
    assert format_timestamp(1e25) == "-"


def test_get_classification_indicator() -> None:
    """Verify POSIX classification indicator characters."""
    # Directory
    assert get_classification_indicator(is_dir=True) == "/"
    assert get_classification_indicator(is_dir=True, is_executable=True) == "/"

    # Symlink
    assert get_classification_indicator(is_symlink=True) == "@"
    assert get_classification_indicator(is_symlink=True, is_executable=True) == "@"

    # Executable
    assert get_classification_indicator(is_executable=True) == "*"

    # Regular file
    assert get_classification_indicator() is None

    # Stat result with socket
    mock_stat_sock = MagicMock(spec=os.stat_result)
    mock_stat_sock.st_mode = stat.S_IFSOCK | 0o755
    assert get_classification_indicator(stat_result=mock_stat_sock) == "="

    # Stat result with FIFO
    mock_stat_fifo = MagicMock(spec=os.stat_result)
    mock_stat_fifo.st_mode = stat.S_IFIFO | 0o644
    assert get_classification_indicator(stat_result=mock_stat_fifo) == "|"

    # Stat result with Door (if supported or simulated)
    mock_stat_door = MagicMock(spec=os.stat_result)
    door_mode = 0xD000 | 0o644
    mock_stat_door.st_mode = door_mode
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(stat, "S_ISDOOR", lambda mode: mode == door_mode, raising=False)
        assert get_classification_indicator(stat_result=mock_stat_door) == ">"

    # Regular file with stat_result
    mock_stat_reg = MagicMock(spec=os.stat_result)
    mock_stat_reg.st_mode = stat.S_IFREG | 0o644
    assert get_classification_indicator(stat_result=mock_stat_reg) is None


def test_format_metadata_parts_timestamps() -> None:
    """Verify format_metadata_parts integration with show_mtime and show_ctime."""
    info = FileInfo(
        path=Path("sample.py"),
        relative_path=Path("sample.py"),
        mtime=1700000000.0,
        ctime=1700001000.0,
    )

    # Neither time requested
    parts_none = format_metadata_parts(info)
    assert len(parts_none) == 0

    # Modification time requested
    parts_mtime = format_metadata_parts(info, show_mtime=True, time_format="%Y-%m-%d")
    assert len(parts_mtime) == 1
    assert parts_mtime[0].startswith("2023-11-")

    # Status change time requested
    parts_ctime = format_metadata_parts(info, show_ctime=True, time_format="%Y-%m-%d")
    assert len(parts_ctime) == 1
    assert parts_ctime[0].startswith("2023-11-")

    # Timestamp is None
    info_no_time = FileInfo(path=Path("none.py"), relative_path=Path("none.py"))
    parts_missing = format_metadata_parts(info_no_time, show_mtime=True)
    assert parts_missing == ["-"]


def test_classifier_and_parser_indicators(tmp_path: Path) -> None:
    """Verify classifier and offline parser populate indicators, mtime, and ctime."""
    # Test directory
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    dir_info = classify_file(sub_dir, root_path=tmp_path)
    assert dir_info.indicator == "/"
    assert dir_info.mtime is not None
    assert dir_info.ctime is not None

    # Test executable script
    script_file = tmp_path / "run.sh"
    script_file.write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
    script_file.chmod(0o755)
    script_info = classify_file(script_file, root_path=tmp_path)
    assert script_info.is_executable is True
    assert script_info.indicator == "*"
    assert script_info.mtime is not None

    # Test symlink
    link_file = tmp_path / "link_to_run"
    link_file.symlink_to("run.sh")
    link_info = classify_file(link_file, root_path=tmp_path)
    assert link_info.is_symlink is True
    assert link_info.indicator == "@"

    # Test offline classification
    test_exe = Path("test.exe")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(os, "name", "nt")
        offline_exec = classify_file_offline(test_exe, relative_path=test_exe)
        assert offline_exec.indicator == "*"

    offline_link = classify_file_offline(Path("link"), relative_path=Path("link"), is_symlink=True)
    assert offline_link.indicator == "@"

    offline_reg = classify_file_offline(Path("doc.md"), relative_path=Path("doc.md"))
    assert offline_reg.indicator is None


def test_text_formatter_presentation() -> None:
    """Verify TextFormatter with timestamp, classification, and quoting."""
    info = FileInfo(
        path=Path("/tmp/root/script.sh"),
        relative_path=Path("script.sh"),
        is_executable=True,
        indicator="*",
        mtime=1700000000.0,
    )

    # Classify & quoting
    fmt = TextFormatter(classify=True, quote_name=True)
    out = fmt.format_item(info)
    assert out == '"script.sh"*\n'

    # With timestamps
    fmt_time = TextFormatter(
        show_mtime=True,
        time_format="%Y-%m-%d",
        classify=True,
        quote_name=True,
    )
    out_time = fmt_time.format_item(info)
    assert out_time.startswith("[2023-11-")
    assert out_time.endswith('] "script.sh"*\n')

    # Masking control chars
    bad_info = FileInfo(
        path=Path("/tmp/root/bad\x07file.txt"),
        relative_path=Path("bad\x07file.txt"),
    )
    fmt_mask = TextFormatter(hide_control_chars=True)
    assert fmt_mask.format_item(bad_info) == "bad?file.txt\n"

    # Literal mode without masking
    fmt_literal = TextFormatter(hide_control_chars=False, literal=True)
    assert fmt_literal.format_item(bad_info) == "bad\x07file.txt\n"

    # hide_control_chars active under literal
    fmt_mask_literal = TextFormatter(hide_control_chars=True, literal=True)
    assert fmt_mask_literal.format_item(bad_info) == "bad?file.txt\n"


def test_rich_table_formatter_presentation() -> None:
    """Verify RichTableFormatter columns and row formatting with presentation options."""
    info = FileInfo(
        path=Path("/tmp/root/app.py"),
        relative_path=Path("app.py"),
        tags=frozenset({"python"}),
        mime_type="text/x-python",
        is_executable=True,
        indicator="*",
        mtime=1700000000.0,
        ctime=1700001000.0,
    )

    # Table with modification time
    tbl_mtime = RichTableFormatter(
        show_mtime=True,
        time_format="%Y-%m-%d",
        classify=True,
        quote_name=True,
    )
    rendered_mtime = tbl_mtime.format([info])
    assert "Modified" in rendered_mtime
    assert '"app.py"*' in rendered_mtime

    # Table with status change time
    tbl_ctime = RichTableFormatter(
        show_ctime=True,
        time_format="%Y-%m-%d",
        classify=True,
    )
    rendered_ctime = tbl_ctime.format([info])
    assert "Status Changed" in rendered_ctime
    assert "app.py*" in rendered_ctime


def test_rich_tree_formatter_presentation() -> None:
    """Verify RichTreeFormatter with classification, quoting, and timestamps."""
    info = FileInfo(
        path=Path("/tmp/root/pkg/main.py"),
        relative_path=Path("pkg/main.py"),
        tags=frozenset({"python"}),
        is_executable=True,
        indicator="*",
        mtime=1700000000.0,
    )

    # Tree with classify and quoting
    tree_fmt = RichTreeFormatter(
        classify=True,
        quote_name=True,
        show_mtime=True,
        time_format="%Y-%m-%d",
    )
    rendered = tree_fmt.format([info])
    # Root should be quoted with / indicator
    assert '"."' in rendered
    # Branch should be quoted with / indicator
    assert '"pkg"/' in rendered
    # Leaf should be quoted with * indicator
    assert '"main.py"*' in rendered
    # Label should contain the timestamp
    assert "2023-11-" in rendered


def test_get_formatter_forwarding() -> None:
    """Verify get_formatter passes presentation flags to formatters."""
    fmt_text = get_formatter(OutputFormat.TEXT, show_mtime=True, classify=True, quote_name=True)
    assert isinstance(fmt_text, TextFormatter)
    assert fmt_text.show_mtime is True
    assert fmt_text.classify is True
    assert fmt_text.quote_name is True

    fmt_table = get_formatter(OutputFormat.TABLE, show_ctime=True, classify=True, quote_name=True)
    assert isinstance(fmt_table, RichTableFormatter)
    assert fmt_table.show_ctime is True
    assert fmt_table.classify is True
    assert fmt_table.quote_name is True

    fmt_tree = get_formatter(
        OutputFormat.TREE,
        show_mtime=True,
        time_format="%Y-%m-%d",
        classify=True,
    )
    assert isinstance(fmt_tree, RichTreeFormatter)
    assert fmt_tree.show_mtime is True
    assert fmt_tree.time_format == "%Y-%m-%d"
    assert fmt_tree.classify is True


def test_cli_config_presentation_options() -> None:
    """Verify build_traversal_config correctly builds TraversalConfig with presentation flags."""
    # -D / mtime
    cfg_mtime = build_traversal_config(
        paths=None,
        tags=None,
        exclude_tags=None,
        all_tags=False,
        shebang=None,
        no_ignore=False,
        hidden=False,
        follow_symlinks=False,
        dirs_only=False,
        one_file_system=False,
        max_depth=None,
        file_limit=None,
        prune=False,
        pattern=None,
        exclude_pattern=None,
        ignore_case=False,
        match_dirs=False,
        absolute=False,
        relative=False,
        print0=False,
        list_tags=False,
        summary=False,
        output_format="text",
        mtime=True,
        classify=True,
        quote_name=True,
    )
    assert cfg_mtime.show_mtime is True
    assert cfg_mtime.show_ctime is False
    assert cfg_mtime.classify is True
    assert cfg_mtime.quote_name is True

    # --time-format implies -D unless --ctime
    cfg_timefmt = build_traversal_config(
        paths=None,
        tags=None,
        exclude_tags=None,
        all_tags=False,
        shebang=None,
        no_ignore=False,
        hidden=False,
        follow_symlinks=False,
        dirs_only=False,
        one_file_system=False,
        max_depth=None,
        file_limit=None,
        prune=False,
        pattern=None,
        exclude_pattern=None,
        ignore_case=False,
        match_dirs=False,
        absolute=False,
        relative=False,
        print0=False,
        list_tags=False,
        summary=False,
        output_format="text",
        time_format="%Y-%m-%d",
    )
    assert cfg_timefmt.show_mtime is True
    assert cfg_timefmt.show_ctime is False
    assert cfg_timefmt.time_format == "%Y-%m-%d"

    # --time-format with --ctime keeps show_ctime and does not force show_mtime
    cfg_ctime = build_traversal_config(
        paths=None,
        tags=None,
        exclude_tags=None,
        all_tags=False,
        shebang=None,
        no_ignore=False,
        hidden=False,
        follow_symlinks=False,
        dirs_only=False,
        one_file_system=False,
        max_depth=None,
        file_limit=None,
        prune=False,
        pattern=None,
        exclude_pattern=None,
        ignore_case=False,
        match_dirs=False,
        absolute=False,
        relative=False,
        print0=False,
        list_tags=False,
        summary=False,
        output_format="text",
        ctime=True,
        time_format="%Y-%m-%d",
    )
    assert cfg_ctime.show_mtime is False
    assert cfg_ctime.show_ctime is True


def test_cli_presentation_flags_execution(tmp_path: Path) -> None:
    """Verify execution of findfmt CLI with presentation flags via CliRunner."""
    (tmp_path / "hello.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (tmp_path / "hello.sh").chmod(0o755)

    # -F / --classify
    res_f = runner.invoke(app, ["-F", str(tmp_path)])
    assert res_f.exit_code == 0
    assert "hello.sh*" in res_f.stdout

    # -Q / --quote-name
    res_q = runner.invoke(app, ["-Q", str(tmp_path)])
    assert res_q.exit_code == 0
    assert '"hello.sh"' in res_q.stdout

    # -F -Q combined
    res_fq = runner.invoke(app, ["-F", "-Q", str(tmp_path)])
    assert res_fq.exit_code == 0
    assert '"hello.sh"*' in res_fq.stdout

    # -D / --mtime
    res_d = runner.invoke(app, ["-D", str(tmp_path)])
    assert res_d.exit_code == 0
    assert "[" in res_d.stdout

    # --ctime
    res_ctime = runner.invoke(app, ["--ctime", str(tmp_path)])
    assert res_ctime.exit_code == 0
    assert "[" in res_ctime.stdout

    # --time-format
    res_tfmt = runner.invoke(app, ["--time-format", "%Y", str(tmp_path)])
    assert res_tfmt.exit_code == 0
    assert "[" in res_tfmt.stdout

    # -q / --hide-control-chars
    res_mask = runner.invoke(app, ["-q", str(tmp_path)])
    assert res_mask.exit_code == 0

    # -N / --literal
    res_lit = runner.invoke(app, ["-N", str(tmp_path)])
    assert res_lit.exit_code == 0
