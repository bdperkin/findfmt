"""Unit and integration tests for tools/line_linter.py."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

from tools.line_linter import (
    DEFAULT_FALLBACK_THRESHOLD,
    DEFAULT_LIMITS,
    LinterConfig,
    Threshold,
    check_file,
    determine_format,
    discover_files,
    load_config,
    main,
    resolve_threshold,
    run_linter,
)


def test_determine_format_various_types(tmp_path: Path) -> None:
    """Test determine_format across various file formats and extensions."""
    test_cases = [
        ("test.py", "python"),
        ("test.md", "markdown"),
        ("test.yaml", "yaml"),
        ("test.json", "json"),
        ("test.sh", "shell"),
        ("test.ts", "typescript"),
        ("test.js", "javascript"),
        ("test.html", "html"),
        ("test.css", "css"),
        ("test.sql", "sql"),
        ("Dockerfile", "dockerfile"),
        ("config.toml", "config"),
        ("unknown.xyz", "default"),
    ]

    for filename, expected_fmt in test_cases:
        f = tmp_path / filename
        f.write_text("sample content\n", encoding="utf-8")
        assert determine_format(f) == expected_fmt


def test_resolve_threshold_overrides_and_defaults() -> None:
    """Test threshold resolution from defaults, overrides, and fallbacks."""
    overrides = {
        "python": Threshold(warning=200, error=400),
        "default": Threshold(warning=100, error=200),
    }

    # Format override match
    assert resolve_threshold("python", overrides) == Threshold(warning=200, error=400)

    # Default limits match
    assert resolve_threshold("yaml", overrides) == DEFAULT_LIMITS["yaml"]

    # Unknown format falls back to "default" override
    assert resolve_threshold("custom", overrides) == Threshold(warning=100, error=200)

    # Empty overrides fall back to DEFAULT_FALLBACK_THRESHOLD for unknown formats
    assert resolve_threshold("custom", {}) == DEFAULT_FALLBACK_THRESHOLD


def test_load_config_missing_and_corrupt_files(tmp_path: Path) -> None:
    """Test load_config when configuration file is missing or invalid TOML."""
    missing_path = tmp_path / "nonexistent.toml"
    config = load_config(missing_path)
    assert config.include == ("**/*",)
    assert config.overrides == {}

    corrupt_path = tmp_path / "corrupt.toml"
    corrupt_path.write_text("invalid = [toml content", encoding="utf-8")
    config_corrupt = load_config(corrupt_path)
    assert config_corrupt.include == ("**/*",)
    assert config_corrupt.overrides == {}


def test_load_config_valid(tmp_path: Path) -> None:
    """Test load_config successfully parsing include, exclude, and overrides."""
    config_file = tmp_path / "pyproject.toml"
    config_file.write_text(
        """
[tool.line-linter]
include = ["src/**/*.py", "*.md"]
exclude = ["build/**"]

[tool.line-linter.overrides]
python = { warning = 250, error = 450 }
yaml = { warning = 120, error = 250 }
invalid = "not-a-dict"
""",
        encoding="utf-8",
    )

    config = load_config(config_file)
    assert config.include == ("src/**/*.py", "*.md")
    assert config.exclude == ("build/**",)
    assert config.overrides["python"] == Threshold(warning=250, error=450)
    assert config.overrides["yaml"] == Threshold(warning=120, error=250)
    assert "invalid" not in config.overrides


def test_check_file_nonexistent_and_binary(tmp_path: Path) -> None:
    """Test check_file returns empty violations for missing or binary files."""
    config = LinterConfig(include=("**/*",), exclude=(), overrides={})

    assert check_file(tmp_path / "missing.txt", config) == []

    binary_file = tmp_path / "binary.bin"
    binary_file.write_bytes(b"\x00\x01\x02\x03\xff" * 200)
    assert check_file(binary_file, config) == []


def test_check_file_warnings_and_errors(tmp_path: Path) -> None:
    """Test check_file detects warning and error violations correctly."""
    py_file = tmp_path / "test.py"
    # Line 1: 50 chars (clean)
    # Line 2: 350 chars (warning for python: > 300, <= 500)
    # Line 3: 550 chars (error for python: > 500)
    content = "\n".join(
        [
            "#" * 50,
            "#" * 350,
            "#" * 550,
        ],
    )
    py_file.write_text(content, encoding="utf-8")

    config = LinterConfig(include=("**/*",), exclude=(), overrides={})
    violations = check_file(py_file, config)

    assert len(violations) == 2
    warn_violation = violations[0]
    assert not warn_violation.is_error
    assert warn_violation.line_number == 2
    assert warn_violation.length == 350
    assert warn_violation.threshold == 300

    err_violation = violations[1]
    assert err_violation.is_error
    assert err_violation.line_number == 3
    assert err_violation.length == 550
    assert err_violation.threshold == 500


def test_check_file_line_count_warning(tmp_path: Path) -> None:
    """Test check_file detects file line count warning violation."""
    py_file = tmp_path / "long_file.py"
    # 350 short lines (python warning is 300, error is 500)
    py_file.write_text("x = 1\n" * 350, encoding="utf-8")

    config = LinterConfig(include=("**/*",), exclude=(), overrides={})
    violations = check_file(py_file, config)

    assert len(violations) == 1
    v = violations[0]
    assert v.violation_type == "file_line_count"
    assert not v.is_error
    assert v.length == 350
    assert v.threshold == 300


def test_check_file_line_count_error(tmp_path: Path) -> None:
    """Test check_file detects file line count error violation."""
    py_file = tmp_path / "error_file.py"
    # 550 short lines (python error is 500)
    py_file.write_text("x = 1\n" * 550, encoding="utf-8")

    config = LinterConfig(include=("**/*",), exclude=(), overrides={})
    violations = check_file(py_file, config)

    assert len(violations) == 1
    v = violations[0]
    assert v.violation_type == "file_line_count"
    assert v.is_error
    assert v.length == 550
    assert v.threshold == 500


def test_run_linter_file_line_count_output(tmp_path: Path) -> None:
    """Test run_linter outputs formatted file line count errors to stderr."""
    py_file = tmp_path / "huge.py"
    py_file.write_text("x = 1\n" * 550, encoding="utf-8")

    config = LinterConfig(include=("**/*",), exclude=(), overrides={})
    stderr = io.StringIO()
    with patch("sys.stderr", stderr):
        exit_code = run_linter([py_file], config, tmp_path)

    assert exit_code == 1
    assert "ERROR: File line count 550 exceeds error limit (500) for python" in stderr.getvalue()


def test_check_file_os_error_handling(tmp_path: Path) -> None:
    """Test check_file handles OSError during file read gracefully."""
    py_file = tmp_path / "error.py"
    py_file.write_text("content\n", encoding="utf-8")

    config = LinterConfig(include=("**/*",), exclude=(), overrides={})
    with patch.object(Path, "open", side_effect=OSError("Read error")):
        assert check_file(py_file, config) == []


def test_discover_files_include_and_exclude(tmp_path: Path) -> None:
    """Test discover_files respects include and exclude glob patterns."""
    (tmp_path / "src").mkdir()
    (tmp_path / "dist").mkdir()

    f1 = tmp_path / "src" / "a.py"
    f2 = tmp_path / "dist" / "b.py"
    f3 = tmp_path / "notes.txt"

    f1.write_text("print(1)\n", encoding="utf-8")
    f2.write_text("print(2)\n", encoding="utf-8")
    f3.write_text("notes\n", encoding="utf-8")

    config = LinterConfig(
        include=("src/**/*.py", "dist/**/*.py"),
        exclude=("dist/**",),
        overrides={},
    )

    discovered = discover_files(tmp_path, config)
    assert discovered == [f1]


def test_run_linter_clean(tmp_path: Path) -> None:
    """Test run_linter returns exit code 0 when no violations exist."""
    py_file = tmp_path / "clean.py"
    py_file.write_text("print('hello')\n", encoding="utf-8")

    config = LinterConfig(include=("**/*",), exclude=(), overrides={})
    stderr = io.StringIO()
    with patch("sys.stderr", stderr):
        exit_code = run_linter([py_file], config, tmp_path)

    assert exit_code == 0
    assert stderr.getvalue() == ""


def test_run_linter_warnings_only(tmp_path: Path) -> None:
    """Test run_linter returns exit code 0 and logs notices when only warnings exist."""
    py_file = tmp_path / "warn.py"
    py_file.write_text("#" * 350 + "\n", encoding="utf-8")

    config = LinterConfig(include=("**/*",), exclude=(), overrides={})
    stderr = io.StringIO()
    with patch("sys.stderr", stderr):
        exit_code = run_linter([py_file], config, tmp_path)

    assert exit_code == 0
    output = stderr.getvalue()
    assert "WARNING: Line length 350 exceeds warning limit (300)" in output
    assert "Line length check found 0 error(s) and 1 warning(s)." in output


def test_run_linter_errors(tmp_path: Path) -> None:
    """Test run_linter returns exit code 1 when error violations exist."""
    py_file = tmp_path / "err.py"
    py_file.write_text("#" * 550 + "\n", encoding="utf-8")

    config = LinterConfig(include=("**/*",), exclude=(), overrides={})
    stderr = io.StringIO()
    with patch("sys.stderr", stderr):
        exit_code = run_linter([py_file], config, tmp_path)

    assert exit_code == 1
    output = stderr.getvalue()
    assert "ERROR: Line length 550 exceeds error limit (500)" in output
    assert "Line length check found 1 error(s) and 0 warning(s)." in output


def test_run_linter_filtering_positional_files(tmp_path: Path) -> None:
    """Test run_linter filters positional files by include and exclude rules."""
    included_file = tmp_path / "test.py"
    excluded_file = tmp_path / "excluded.py"
    ignored_include = tmp_path / "extra.txt"

    included_file.write_text("print(1)\n", encoding="utf-8")
    excluded_file.write_text("print(2)\n", encoding="utf-8")
    ignored_include.write_text("text\n", encoding="utf-8")

    config = LinterConfig(
        include=("*.py",),
        exclude=("excluded.py",),
        overrides={},
    )

    stderr = io.StringIO()
    with patch("sys.stderr", stderr):
        exit_code = run_linter(
            [included_file, excluded_file, ignored_include],
            config,
            tmp_path,
        )

    assert exit_code == 0


def test_main_cli_execution(tmp_path: Path) -> None:
    """Test main function CLI invocation with explicit config and files."""
    config_file = tmp_path / "pyproject.toml"
    config_file.write_text("[tool.line-linter]\n", encoding="utf-8")

    test_file = tmp_path / "main_test.py"
    test_file.write_text("print('test')\n", encoding="utf-8")

    stderr = io.StringIO()
    with patch("sys.stderr", stderr):
        exit_code = main(["--config", str(config_file), str(test_file)])

    assert exit_code == 0
