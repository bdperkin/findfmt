"""Unit tests for structured formatters (JSON, JSONL, YAML, IPYNB)."""

from __future__ import annotations

import ast
import io
import json
from pathlib import Path

import pytest
import yaml

from findfmt.formatters import (
    IpynbFormatter,
    JsonFormatter,
    JsonlFormatter,
    YamlFormatter,
)
from findfmt.models import FileInfo


@pytest.fixture
def sample_files() -> list[FileInfo]:
    """Provide a diverse list of sample FileInfo objects for testing."""
    return [
        FileInfo(
            path=Path("/workspace/project/main.py"),
            relative_path=Path("main.py"),
            tags=frozenset({"python", "text"}),
            shebang="#!/usr/bin/env python3",
            mime_type="text/x-python",
            is_executable=True,
            is_symlink=False,
            size_bytes=1024,
        ),
        FileInfo(
            path=Path("/workspace/project/data.json"),
            relative_path=Path("data.json"),
            tags=frozenset({"json", "text"}),
            shebang=None,
            mime_type="application/json",
            is_executable=False,
            is_symlink=True,
            size_bytes=256,
        ),
    ]


def test_file_info_to_dict_relative(sample_files: list[FileInfo]) -> None:
    """Verify FileInfo.to_dict produces expected relative path representation."""
    d = sample_files[0].to_dict(absolute=False)
    assert d == {
        "path": "main.py",
        "relative_path": "main.py",
        "tags": ["python", "text"],
        "shebang": "#!/usr/bin/env python3",
        "mime_type": "text/x-python",
        "is_executable": True,
        "is_symlink": False,
        "size_bytes": 1024,
    }


def test_file_info_to_dict_absolute(sample_files: list[FileInfo]) -> None:
    """Verify FileInfo.to_dict produces expected absolute path representation."""
    d = sample_files[0].to_dict(absolute=True)
    assert d["path"] == str(sample_files[0].path)
    assert d["relative_path"] == "main.py"


def test_json_formatter_empty() -> None:
    """Verify JsonFormatter handles empty lists cleanly."""
    fmt = JsonFormatter()
    output = fmt.format([])
    assert output == "[]\n"
    assert json.loads(output) == []

    buf = io.StringIO()
    fmt.stream([], buf)
    assert buf.getvalue() == "[]\n"


def test_json_formatter_records(sample_files: list[FileInfo]) -> None:
    """Verify JsonFormatter produces valid JSON array with correct records."""
    fmt = JsonFormatter(absolute=False, indent=2)
    output = fmt.format(sample_files)
    data = json.loads(output)
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["path"] == "main.py"
    assert data[0]["tags"] == ["python", "text"]
    assert data[0]["is_executable"] is True
    assert data[1]["path"] == "data.json"
    assert data[1]["is_symlink"] is True

    buf = io.StringIO()
    fmt.stream(sample_files, buf)
    assert buf.getvalue() == output


def test_json_formatter_compact(sample_files: list[FileInfo]) -> None:
    """Verify JsonFormatter compact mode (indent=None)."""
    fmt = JsonFormatter(absolute=True, indent=None)
    output = fmt.format(sample_files)
    assert output.endswith("\n")
    data = json.loads(output)
    assert len(data) == 2
    assert data[0]["path"] == str(sample_files[0].path)


def test_jsonl_formatter_empty() -> None:
    """Verify JsonlFormatter returns empty string for no files."""
    fmt = JsonlFormatter()
    assert fmt.format([]) == ""

    buf = io.StringIO()
    fmt.stream([], buf)
    assert buf.getvalue() == ""


def test_jsonl_formatter_streaming(sample_files: list[FileInfo]) -> None:
    """Verify JsonlFormatter generates valid line-delimited records."""
    fmt = JsonlFormatter(absolute=False)
    output = fmt.format(sample_files)
    lines = [line for line in output.split("\n") if line]
    assert len(lines) == 2

    rec1 = json.loads(lines[0])
    rec2 = json.loads(lines[1])
    assert rec1["path"] == "main.py"
    assert rec1["mime_type"] == "text/x-python"
    assert rec2["path"] == "data.json"
    assert rec2["is_symlink"] is True

    buf = io.StringIO()
    fmt.stream(sample_files, buf)
    assert buf.getvalue() == output


def test_yaml_formatter_empty() -> None:
    """Verify YamlFormatter returns valid empty YAML document."""
    fmt = YamlFormatter()
    output = fmt.format([])
    assert output == "[]\n"
    assert yaml.safe_load(output) == []

    buf = io.StringIO()
    fmt.stream([], buf)
    assert buf.getvalue() == "[]\n"


def test_yaml_formatter_records(sample_files: list[FileInfo]) -> None:
    """Verify YamlFormatter produces valid block-style YAML."""
    fmt = YamlFormatter(absolute=False, indent=2)
    output = fmt.format(sample_files)
    parsed = yaml.safe_load(output)
    assert isinstance(parsed, list)
    assert len(parsed) == 2
    assert parsed[0]["path"] == "main.py"
    assert parsed[0]["tags"] == ["python", "text"]
    assert parsed[0]["shebang"] == "#!/usr/bin/env python3"
    assert parsed[1]["path"] == "data.json"
    assert parsed[1]["is_symlink"] is True

    buf = io.StringIO()
    fmt.stream(sample_files, buf)
    assert buf.getvalue() == output


def test_ipynb_formatter_empty() -> None:
    """Verify IpynbFormatter generates valid notebook with empty files."""
    fmt = IpynbFormatter()
    output = fmt.format([])
    nb = json.loads(output)
    assert nb["nbformat"] == 4
    assert nb["nbformat_minor"] == 5
    assert len(nb["cells"]) == 3

    code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    for cell in code_cells:
        code_text = "".join(cell["source"])
        ast.parse(code_text)

    buf = io.StringIO()
    fmt.stream([], buf)
    assert buf.getvalue() == output


def test_ipynb_formatter_records(sample_files: list[FileInfo]) -> None:
    """Verify IpynbFormatter embeds files manifest and valid Python code cells."""
    fmt = IpynbFormatter(absolute=True)
    output = fmt.format(sample_files)
    nb = json.loads(output)
    assert nb["nbformat"] == 4
    assert nb["metadata"]["language_info"]["name"] == "python"

    intro_cell = nb["cells"][0]
    assert intro_cell["cell_type"] == "markdown"
    assert "# findfmt File Discovery Report" in "".join(intro_cell["source"])

    data_cell = nb["cells"][1]
    assert data_cell["cell_type"] == "code"
    data_source = "".join(data_cell["source"])
    assert "import pandas as pd" in data_source
    assert "main.py" in data_source
    ast.parse(data_source)

    analysis_cell = nb["cells"][2]
    assert analysis_cell["cell_type"] == "code"
    analysis_source = "".join(analysis_cell["source"])
    assert "value_counts" in analysis_source
    ast.parse(analysis_source)

    buf = io.StringIO()
    fmt.stream(sample_files, buf)
    assert buf.getvalue() == output
