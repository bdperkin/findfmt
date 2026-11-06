"""Unit and integration tests for tools/suppression_auditor.py."""

from __future__ import annotations

import runpy
from pathlib import Path
from unittest.mock import patch

import pytest
from tools.suppression_auditor import (
    GRAND_UNIFIED_SUPPRESSION_REGEX,
    AllowedSuppression,
    AuditorConfig,
    _parse_allowed_entries,
    _parse_str_tuple,
    _rel_posix,
    app,
    audit_file,
    discover_files,
    extract_comments,
    has_justification,
    is_whitelisted,
    load_config,
)
from typer.testing import CliRunner

runner = CliRunner()
BARE_NOQA = f"# {'noqa'}"
BARE_TYPE_IGNORE = f"# {'type'}: ignore"


def test_audit_clean_file(tmp_path: Path) -> None:
    """Ensure a file with regular comments and no suppressions passes successfully."""
    p = tmp_path / "clean.py"
    p.write_text("# Regular module comment\nx = 1\ny = 2\nprint(x + y)\n", encoding="utf-8")

    result = runner.invoke(app, [str(p)])
    assert result.exit_code == 0
    assert "Successfully audited" in result.output


def test_audit_justified_suppression(tmp_path: Path) -> None:
    """Ensure a suppression comment with an explicit justification passes."""
    p = tmp_path / "justified.py"
    p.write_text(
        "x = 1  # type: ignore[attr-defined] # Required because dynamic attributes are injected\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, [str(p)])
    assert result.exit_code == 0
    assert "Successfully audited" in result.output


def test_audit_unjustified_suppression(tmp_path: Path) -> None:
    """Ensure a bare/unjustified suppression comment fails with exit code 1."""
    p = tmp_path / "unjustified.py"
    p.write_text(f"x = 1  {BARE_TYPE_IGNORE}\n", encoding="utf-8")

    result = runner.invoke(app, [str(p)])
    assert result.exit_code == 1
    assert "Found 1 unjustified suppression" in result.output
    assert "unjustified.py" in result.output


def test_audit_multiple_mixed_suppressions(tmp_path: Path) -> None:
    """Test a file containing both valid/justified and invalid suppressions."""
    p = tmp_path / "mixed.py"
    p.write_text(
        f"# noqa: E501 # Legacy line length restriction exception\ny = 2  {BARE_NOQA}\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, [str(p)])
    assert result.exit_code == 1
    assert "Found 1 unjustified suppression" in result.output


def test_audit_whitelisted_suppression(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure an otherwise unjustified suppression passes if whitelisted in pyproject.toml."""
    pyproject_content = """
[tool.findfmt.suppression_auditor]
allowed = [
    { file = "target.py", line = 1, code = "type: ignore", reason = "Whitelisted in test" }
]
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")
    target_path = tmp_path / "target.py"
    target_path.write_text(f"x = 1  {BARE_TYPE_IGNORE}\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["target.py"])
    assert result.exit_code == 0
    assert "Successfully audited" in result.output


def test_audit_invalid_whitelist_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure that a mismatch in file name, line number, or code fails the audit."""
    pyproject_content = """
[tool.findfmt.suppression_auditor]
allowed = [
    { file = "other.py", line = 1 },
    { file = "target.py", line = 99 },
    { file = "target.py", line = 1, code = "noqa: F401" }
]
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")
    target_path = tmp_path / "target.py"
    target_path.write_text(f"x = 1  {BARE_TYPE_IGNORE}\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["target.py"])
    assert result.exit_code == 1
    assert "Found 1 unjustified suppression" in result.output


def test_audit_ignore_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure files matching ignore_paths patterns in pyproject.toml are skipped."""
    pyproject_content = """
[tool.findfmt.suppression_auditor]
ignore_paths = ["vendor/**"]
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")
    vendor_dir = tmp_path / "vendor"
    vendor_dir.mkdir()
    target_path = vendor_dir / "external.py"
    target_path.write_text(f"x = 1  {BARE_TYPE_IGNORE}\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, [str(target_path)])
    assert result.exit_code == 0
    assert "Successfully audited" in result.output


def test_audit_strict_config_parsing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure strict mode is correctly parsed from pyproject.toml configuration."""
    pyproject_content = """
[tool.findfmt.suppression_auditor]
strict = true
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")
    target_path = tmp_path / "target.py"
    target_path.write_text(f"x = 1  {BARE_NOQA}\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, [str(target_path)])
    assert result.exit_code == 1
    assert "Configured strict mode: True" in result.output


@pytest.mark.parametrize(
    "directive_comment",
    [
        "# noqa: E501",
        "# flake8: noqa",
        "# ruff: ignore[F841]",
        "# pylint: disable=protected-access",
        "# fmt: skip",
        "# yapf: disable",
        "# type: ignore[attr-defined]",
        "# mypy: ignore-errors",
        "# pyright: ignore[reportGeneralTypeIssues]",
        "# pytype: disable=attribute-error",
        "# pyre-ignore[16]",
        "# nosec B101",
        f"# {'pragma'}: no cover",
        f"# {'pragma'}: no branch",
        "# doctest: +SKIP",
    ],
)
def test_grand_unified_regex_matches_all_categories(directive_comment: str) -> None:
    """Verify GRAND_UNIFIED_SUPPRESSION_REGEX matches all 7 tool categories."""
    assert GRAND_UNIFIED_SUPPRESSION_REGEX.search(directive_comment) is not None
    assert not has_justification(directive_comment)
    assert has_justification(f"{directive_comment} - explicit justification text")


def test_config_parsing_edge_cases(tmp_path: Path) -> None:
    """Test load_config and helper parsers across corrupt, missing, and alternate tables."""
    assert load_config(tmp_path / "missing.toml") == AuditorConfig()

    corrupt = tmp_path / "corrupt.toml"
    corrupt.write_text("invalid = [toml", encoding="utf-8")
    assert load_config(corrupt) == AuditorConfig()

    alt_cfg = tmp_path / "alt.toml"
    alt_cfg.write_text(
        '[tool.suppression-auditor]\nstrict = true\ninclude = ["custom/**/*.py"]\n',
        encoding="utf-8",
    )
    loaded_alt = load_config(alt_cfg)
    assert loaded_alt.strict is True
    assert loaded_alt.include == ("custom/**/*.py",)

    non_dict_cfg = tmp_path / "nondict.toml"
    non_dict_cfg.write_text('[tool]\nsuppression-auditor = "invalid"\n', encoding="utf-8")
    assert load_config(non_dict_cfg) == AuditorConfig()

    assert _parse_str_tuple("not-a-list", ("default",)) == ("default",)
    assert _parse_allowed_entries("not-a-list") == ()
    parsed_allowed = _parse_allowed_entries(
        [
            "not-a-dict",
            {"file": ""},
            {"file": "a.py", "line": True, "code": "", "reason": 123},
            {"file": "b.py", "line": 10, "code": "E501", "reason": "  valid  "},
        ],
    )
    assert parsed_allowed == (
        AllowedSuppression(file="a.py", line=None, code=None, reason=""),
        AllowedSuppression(file="b.py", line=10, code="E501", reason="valid"),
    )


def test_extract_comments_and_audit_file_fallbacks(tmp_path: Path) -> None:
    """Test tokenize fallback on incomplete syntax, string literal safety, and OSError."""
    # String literals containing suppression tokens are ignored by tokenize
    str_literal_code = 'x = "# noqa: E501"\n'
    assert extract_comments(str_literal_code) == []

    # Incomplete multiline string triggers TokenError fallback
    broken_code = 'x = """unterminated\n# noqa: E501\n'
    comments = extract_comments(broken_code)
    assert comments == [(2, "# noqa: E501")]

    # Audit file OSError handling
    missing_file = tmp_path / "missing.py"
    checked, violations = audit_file(missing_file, AuditorConfig(), tmp_path)
    assert checked == 0
    assert violations == []

    # Out-of-bounds line_no fallback in audit_file
    valid_file = tmp_path / "valid.py"
    valid_file.write_text("x = 1\n", encoding="utf-8")
    with patch("tools.suppression_auditor.extract_comments", return_value=[(99, BARE_NOQA)]):
        checked_oob, violations_oob = audit_file(valid_file, AuditorConfig(), tmp_path)

    assert checked_oob == 1
    assert violations_oob[0].content == BARE_NOQA

    # _rel_posix fallback when path is outside root
    assert _rel_posix(Path("/outside/file.py"), tmp_path / "nested") == "/outside/file.py"
    assert is_whitelisted(
        valid_file,
        1,
        "noqa",
        (AllowedSuppression(file="valid.py"),),
        tmp_path,
    )


def test_discover_files_directories_and_default_globs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test discover_files with directory args, non-py files, and default repo globs."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    py_file = src_dir / "mod.py"
    py_file.write_text("x = 1  # noqa: F401 - intentional unused import\n", encoding="utf-8")
    txt_file = src_dir / "notes.txt"
    txt_file.write_text("hello\n", encoding="utf-8")

    cfg = AuditorConfig(include=("src/**", "src/**/*.py", "src/*.py"), ignore_paths=())
    assert discover_files([src_dir, txt_file], cfg, tmp_path) == [py_file]
    assert discover_files(None, cfg, tmp_path) == [py_file]

    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, [])
    assert result.exit_code == 0

    script_path = Path(__file__).resolve().parents[2] / "tools" / "suppression_auditor.py"
    with (
        patch("sys.argv", [str(script_path), str(py_file)]),
        pytest.raises(SystemExit) as exc_info,
    ):
        runpy.run_path(str(script_path), run_name="__main__")

    assert exc_info.value.code == 0
