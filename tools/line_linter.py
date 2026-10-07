"""Enforce line length limits by file format and configuration."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import pathspec

if TYPE_CHECKING:
    from collections.abc import Sequence

_src_dir = Path(__file__).resolve().parent.parent / "src"
if _src_dir.is_dir() and str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from findfmt.classifier import classify_file  # noqa: E402


@dataclass(frozen=True)
class Threshold:
    """Warning and error line length thresholds in characters."""

    warning: int
    error: int


@dataclass(frozen=True)
class LinterConfig:
    """Configuration options for the line length enforcement linter."""

    include: tuple[str, ...]
    exclude: tuple[str, ...]
    overrides: dict[str, Threshold]


@dataclass(frozen=True)
class Violation:
    """Recorded line length violation."""

    file_path: Path
    line_number: int
    length: int
    threshold: int
    is_error: bool
    format_name: str


DEFAULT_LIMITS: dict[str, Threshold] = {
    "python": Threshold(warning=300, error=500),
    "markdown": Threshold(warning=300, error=600),
    "yaml": Threshold(warning=150, error=300),
    "json": Threshold(warning=100, error=250),
    "shell": Threshold(warning=100, error=200),
    "javascript": Threshold(warning=300, error=500),
    "typescript": Threshold(warning=300, error=500),
    "html": Threshold(warning=250, error=500),
    "css": Threshold(warning=300, error=500),
    "sql": Threshold(warning=150, error=300),
    "config": Threshold(warning=80, error=150),
    "dockerfile": Threshold(warning=80, error=150),
}

DEFAULT_FALLBACK_THRESHOLD = Threshold(warning=300, error=500)

DEFAULT_INCLUDE: tuple[str, ...] = ("**/*",)
DEFAULT_EXCLUDE: tuple[str, ...] = (
    "dist/**",
    "build/**",
    ".venv/**",
    ".git/**",
    ".github/styles/**",
    "docs/_build/**",
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".ruff_cache/**",
    "__pycache__/**",
    "*.lock",
    "uv.lock",
)

TAG_FORMAT_MAPPINGS: tuple[tuple[str, frozenset[str]], ...] = (
    ("python", frozenset({"python"})),
    ("markdown", frozenset({"markdown"})),
    ("yaml", frozenset({"yaml"})),
    ("json", frozenset({"json"})),
    ("shell", frozenset({"shell", "bash", "sh", "zsh"})),
    ("typescript", frozenset({"typescript", "ts"})),
    ("javascript", frozenset({"javascript", "js", "jsx", "tsx"})),
    ("html", frozenset({"html"})),
    ("css", frozenset({"css", "scss", "sass", "less"})),
    ("sql", frozenset({"sql"})),
    ("dockerfile", frozenset({"dockerfile"})),
    ("config", frozenset({"toml", "ini", "cfg", "conf", "config", "properties"})),
)


def determine_format(path: Path) -> str:
    """Determine format category for a file using findfmt classification.

    Args:
        path: Path to target file.

    Returns:
        Canonical format category name string.
    """
    info = classify_file(path)
    tags = info.tags

    for fmt_name, tag_set in TAG_FORMAT_MAPPINGS:
        if tags & tag_set:
            return fmt_name

    return "default"


def resolve_threshold(format_name: str, overrides: dict[str, Threshold]) -> Threshold:
    """Resolve the warning and error thresholds for a given format.

    Args:
        format_name: Canonical format category name.
        overrides: Format-specific threshold overrides.

    Returns:
        Effective Threshold with warning and error limits.
    """
    if format_name in overrides:
        return overrides[format_name]

    if format_name in DEFAULT_LIMITS:
        return DEFAULT_LIMITS[format_name]

    if "default" in overrides:
        return overrides["default"]

    return DEFAULT_FALLBACK_THRESHOLD


def _parse_patterns(raw_val: object, default: tuple[str, ...]) -> tuple[str, ...]:
    """Parse string list patterns from TOML config.

    Args:
        raw_val: Raw parsed TOML value.
        default: Fallback default tuple of pattern strings.

    Returns:
        Tuple of pattern strings.
    """
    if isinstance(raw_val, list | tuple):
        return tuple(str(p) for p in raw_val)

    return default


def load_config(config_path: Path | None = None) -> LinterConfig:
    """Load line linter configuration from pyproject.toml.

    Args:
        config_path: Optional explicit path to configuration TOML file.

    Returns:
        Parsed LinterConfig instance.
    """
    resolved_path = config_path or Path("pyproject.toml")
    if not resolved_path.is_file():
        return LinterConfig(
            include=DEFAULT_INCLUDE,
            exclude=DEFAULT_EXCLUDE,
            overrides={},
        )

    try:
        with resolved_path.open("rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return LinterConfig(
            include=DEFAULT_INCLUDE,
            exclude=DEFAULT_EXCLUDE,
            overrides={},
        )

    tool_table = data.get("tool", {}).get("line-linter", {})
    include = _parse_patterns(tool_table.get("include"), DEFAULT_INCLUDE)
    exclude = _parse_patterns(tool_table.get("exclude"), DEFAULT_EXCLUDE)

    raw_overrides = tool_table.get("overrides", {})
    overrides: dict[str, Threshold] = {}
    if isinstance(raw_overrides, dict):
        for fmt, limits in raw_overrides.items():
            if isinstance(limits, dict):
                warning_limit = limits.get("warning")
                error_limit = limits.get("error")
                if isinstance(warning_limit, int) and isinstance(error_limit, int):
                    overrides[fmt.lower()] = Threshold(
                        warning=warning_limit,
                        error=error_limit,
                    )

    return LinterConfig(
        include=include,
        exclude=exclude,
        overrides=overrides,
    )


def check_file(path: Path, config: LinterConfig) -> list[Violation]:
    """Check line lengths for a single file.

    Args:
        path: Path to the target file.
        config: Linter configuration containing threshold overrides.

    Returns:
        List of Violation instances discovered in the file.
    """
    if not path.is_file():
        return []

    info = classify_file(path)
    if "binary" in info.tags:
        return []

    format_name = determine_format(path)
    threshold = resolve_threshold(format_name, config.overrides)

    violations: list[Violation] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for line_no, raw_line in enumerate(f, 1):
                clean_line = raw_line.rstrip("\r\n")
                line_len = len(clean_line)
                if line_len > threshold.error:
                    violations.append(
                        Violation(
                            file_path=path,
                            line_number=line_no,
                            length=line_len,
                            threshold=threshold.error,
                            is_error=True,
                            format_name=format_name,
                        ),
                    )
                elif line_len > threshold.warning:
                    violations.append(
                        Violation(
                            file_path=path,
                            line_number=line_no,
                            length=line_len,
                            threshold=threshold.warning,
                            is_error=False,
                            format_name=format_name,
                        ),
                    )
    except OSError:
        return []

    return violations


def discover_files(root: Path, config: LinterConfig) -> list[Path]:
    """Discover files to check based on include and exclude patterns.

    Args:
        root: Root repository or directory path.
        config: Linter configuration with include and exclude patterns.

    Returns:
        Sorted list of candidate Path objects to lint.
    """
    exclude_spec = pathspec.PathSpec.from_lines("gitignore", config.exclude)

    candidate_files: set[Path] = set()
    for pattern in config.include:
        for path in root.glob(pattern):
            if path.is_file():
                candidate_files.add(path)

    filtered_files: list[Path] = []
    for path in sorted(candidate_files):
        try:
            rel_path = path.resolve().relative_to(root.resolve())
            rel_str = str(rel_path).replace("\\", "/")
        except ValueError:
            rel_str = str(path).replace("\\", "/")

        if not exclude_spec.match_file(rel_str):
            filtered_files.append(path)

    return filtered_files


def run_linter(files: Sequence[Path] | None, config: LinterConfig, root: Path) -> int:
    """Execute line length enforcement and print notices to stderr.

    Args:
        files: Optional explicit list of files to check.
        config: Loaded LinterConfig instance.
        root: Root directory for relative path calculations and fallback search.

    Returns:
        Status code 0 on success/warnings, or 1 when any error threshold is breached.
    """
    include_spec = pathspec.PathSpec.from_lines("gitignore", config.include)
    exclude_spec = pathspec.PathSpec.from_lines("gitignore", config.exclude)

    if files:
        target_files: list[Path] = []
        for file_path in files:
            p = file_path if file_path.is_absolute() else (root / file_path)
            try:
                rel_path = p.resolve().relative_to(root.resolve())
                rel_str = str(rel_path).replace("\\", "/")
            except ValueError:
                rel_str = str(file_path).replace("\\", "/")

            if not p.is_file():
                continue

            if exclude_spec.match_file(rel_str):
                continue

            if config.include != DEFAULT_INCLUDE and not include_spec.match_file(rel_str):
                continue

            target_files.append(p)
    else:
        target_files = discover_files(root, config)

    all_violations: list[Violation] = []
    for target in target_files:
        all_violations.extend(check_file(target, config))

    error_count = sum(1 for v in all_violations if v.is_error)
    warning_count = sum(1 for v in all_violations if not v.is_error)

    for v in all_violations:
        level = "ERROR" if v.is_error else "WARNING"
        sys.stderr.write(
            f"{v.file_path}:{v.line_number}: {level}: Line length {v.length} "
            f"exceeds {level.lower()} limit ({v.threshold}) for {v.format_name}\n",
        )

    if all_violations:
        sys.stderr.write(
            f"\nLine length check found {error_count} error(s) and {warning_count} warning(s).\n",
        )

    return 1 if error_count > 0 else 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for the line length enforcement tool.

    Args:
        argv: Command-line arguments sequence, or None for sys.argv[1:].

    Returns:
        Exit code 0 on clean/warnings, or 1 on error threshold violations.
    """
    parser = argparse.ArgumentParser(description="Enforce format-specific file line length limits.")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to pyproject.toml configuration file.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Optional explicit files to check (e.g. passed by pre-commit).",
    )

    args = parser.parse_args(argv)
    root = Path.cwd()
    config = load_config(args.config)
    return run_linter(args.files, config, root)


if __name__ == "__main__":
    sys.exit(main())
