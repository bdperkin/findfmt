"""End-to-end acceptance tests for Epic #384: Formatter Integrity & Encoding Robustness."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from findfmt.cli import app
from findfmt.formatters.markup import MarkdownFormatter
from findfmt.models import FileInfo


def test_epic_384_formatter_integrity_acceptance(tmp_path: Path) -> None:
    """Verify Epic #384 acceptance criteria across CLI formatters in a single workspace."""
    (tmp_path / "alpha.txt").write_text("a", encoding="utf-8")
    (tmp_path / "zeta.txt").write_text("z", encoding="utf-8")
    (tmp_path / "=SUM(A1).csv").write_text("1,2", encoding="utf-8")

    runner = CliRunner()

    # 1. Markdown escapes raw HTML tags in filenames (#333)
    html_file = FileInfo(
        path=Path("/workspace/<img src=x onerror=alert(1)>.md"),
        relative_path=Path("<img src=x onerror=alert(1)>.md"),
        tags=frozenset({"markdown", "text"}),
        size_bytes=5,
    )
    md_out = MarkdownFormatter().format([html_file])
    assert "&lt;img src=x onerror=alert(1)&gt;.md" in md_out
    assert "<img src=x onerror=alert(1)>.md" not in md_out

    # 2. --csv-safe neutralizes spreadsheet formula injection prefixes (#339)
    csv_res = runner.invoke(app, ["-f", "csv", "--csv-safe", str(tmp_path)])
    assert csv_res.exit_code == 0
    assert "'=SUM(A1).csv" in csv_res.stdout

    # 3. -f ipynb emits valid Python AST in code cells without JSON null/false NameError (#330)
    ipynb_res = runner.invoke(app, ["-f", "ipynb", str(tmp_path)])
    assert ipynb_res.exit_code == 0
    notebook = json.loads(ipynb_res.stdout)
    code_source = "".join(notebook["cells"][1]["source"])
    ast.parse(code_source)

    # 4. --sort name --reverse is respected across tree, HTML, and XML (#341)
    for fmt in ("tree", "html", "xml"):
        sorted_res = runner.invoke(
            app,
            ["-f", fmt, "--sort", "name", "--reverse", str(tmp_path)],
        )
        assert sorted_res.exit_code == 0
        assert sorted_res.stdout.index("zeta.txt") < sorted_res.stdout.index("alpha.txt")

    # 5. --tree --cp437 outputs CP437 box-drawing bytes without Latin-1 mojibake (#343)
    cp437_proc = subprocess.run(
        [sys.executable, "-m", "findfmt", "--tree", "--cp437", str(tmp_path)],
        capture_output=True,
        check=True,
    )
    decoded_cp437 = cp437_proc.stdout.decode("cp437")
    assert "├──" in decoded_cp437 or "└──" in decoded_cp437
    assert "Ã" not in decoded_cp437
    assert "Ä" not in decoded_cp437
