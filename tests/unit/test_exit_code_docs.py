"""The exit-code tables in ``--help-all`` and the CLI reference match the actual behavior (#493).

``findfmt`` exits 0 when nothing matches unless ``--exit-status`` is given, in which case no matches
means exit status 1. Both tables used to say 0 meant "matching files found".
"""

from __future__ import annotations

from pathlib import Path

from findfmt.cli.help import get_help_all

CLI_REFERENCE = Path(__file__).resolve().parents[2] / "docs" / "source" / "cli" / "index.md"


def _section(text: str, start: str, end: str) -> str:
    """Return the text between ``start`` and the next ``end`` marker."""
    assert start in text, f"missing {start!r}"
    return text.split(start, 1)[1].split(end, 1)[0]


def test_help_all_exit_codes_describe_exit_status() -> None:
    """The --help-all Exit Codes table explains the no-match, --exit-status, and SIGINT cases."""
    table = _section(get_help_all(), "Exit Codes:\n", "\n\n")
    assert "--exit-status" in table
    assert "SIGINT" in table
    assert "matching files found" not in table
    assert {line.split()[0] for line in table.splitlines() if line.strip()} == {
        "0",
        "1",
        "2",
        "130",
    }


def test_cli_reference_exit_status_section_describes_exit_status() -> None:
    """The CLI reference's Exit Status section documents codes 0, 1, 2, and 130."""
    section = _section(CLI_REFERENCE.read_text(encoding="utf-8"), "## 7. Exit Status", "\n## ")
    assert "--exit-status" in section
    assert "SIGPIPE" in section
    assert "SIGINT" in section
    assert "matching files found" not in section
    for code in ("`0`", "`1`", "`2`", "`130`"):
        assert code in section

    readme = (CLI_REFERENCE.parents[3] / "README.md").read_text(encoding="utf-8")
    assert "cli/index.html#exit-status" in readme
