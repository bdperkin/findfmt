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
    """Recorded line length or file line count violation."""

    file_path: Path
    line_number: int | None
    length: int
    threshold: int
    is_error: bool
    format_name: str
    violation_type: str = "line_length"


_t = Threshold
DEFAULT_LIMITS: dict[str, Threshold] = {
    "python": _t(300, 500),
    "markdown": _t(300, 600),
    "yaml": _t(150, 300),
    "json": _t(100, 250),
    "shell": _t(100, 200),
    "javascript": _t(300, 500),
    "typescript": _t(300, 500),
    "html": _t(250, 500),
    "css": _t(300, 500),
    "sql": _t(150, 300),
    "config": _t(80, 150),
    "dockerfile": _t(80, 150),
}

DEFAULT_FALLBACK_THRESHOLD = Threshold(warning=300, error=500)
DEFAULT_INCLUDE: tuple[str, ...] = ("**/*",)
DEFAULT_EXCLUDE: tuple[str, ...] = (
    "dist/**",
    "build/**",
    ".venv/**",
    ".git/**",
    ".clusterfuzzlite/**",
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
    """Determine format category for a file using findfmt classification."""
    tags = classify_file(path).tags
    for fmt_name, tag_set in TAG_FORMAT_MAPPINGS:
        if tags & tag_set:
            return fmt_name

    return "default"


def resolve_threshold(format_name: str, overrides: dict[str, Threshold]) -> Threshold:
    """Resolve warning and error thresholds for a given format."""
    fallback = overrides.get("default", DEFAULT_FALLBACK_THRESHOLD)
    return overrides.get(format_name, DEFAULT_LIMITS.get(format_name, fallback))


def _parse_patterns(raw_val: object, default: tuple[str, ...]) -> tuple[str, ...]:
    """Parse string list patterns from TOML config."""
    if isinstance(raw_val, list | tuple):
        return tuple(str(p) for p in raw_val)

    return default


def load_config(config_path: Path | None = None) -> LinterConfig:
    """Load line linter configuration from pyproject.toml."""
    resolved_path = config_path or Path("pyproject.toml")
    try:
        with resolved_path.open("rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return LinterConfig(include=DEFAULT_INCLUDE, exclude=DEFAULT_EXCLUDE, overrides={})

    tool_table = data.get("tool", {}).get("line-linter", {})
    include = _parse_patterns(tool_table.get("include"), DEFAULT_INCLUDE)
    exclude = _parse_patterns(tool_table.get("exclude"), DEFAULT_EXCLUDE)

    raw_overrides = tool_table.get("overrides", {})
    overrides: dict[str, Threshold] = {}
    if isinstance(raw_overrides, dict):
        for fmt, limits in raw_overrides.items():
            if isinstance(limits, dict):
                w, e = limits.get("warning"), limits.get("error")
                if isinstance(w, int) and isinstance(e, int):
                    overrides[fmt.lower()] = Threshold(warning=w, error=e)

    return LinterConfig(include=include, exclude=exclude, overrides=overrides)


def check_file(path: Path, config: LinterConfig) -> list[Violation]:
    """Check line lengths and total line count for a single file."""
    if not path.is_file() or "binary" in classify_file(path).tags:
        return []

    format_name = determine_format(path)
    threshold = resolve_threshold(format_name, config.overrides)
    violations: list[Violation] = []

    try:
        total_lines = 0
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for line_no, raw_line in enumerate(f, 1):
                total_lines = line_no
                line_len = len(raw_line.rstrip("\r\n"))
                if line_len > threshold.error or line_len > threshold.warning:
                    is_err = line_len > threshold.error
                    violations.append(
                        Violation(
                            file_path=path,
                            line_number=line_no,
                            length=line_len,
                            threshold=threshold.error if is_err else threshold.warning,
                            is_error=is_err,
                            format_name=format_name,
                            violation_type="line_length",
                        ),
                    )

        if total_lines > threshold.error or total_lines > threshold.warning:
            is_err = total_lines > threshold.error
            violations.append(
                Violation(
                    file_path=path,
                    line_number=total_lines,
                    length=total_lines,
                    threshold=threshold.error if is_err else threshold.warning,
                    is_error=is_err,
                    format_name=format_name,
                    violation_type="file_line_count",
                ),
            )
    except OSError:
        return []

    return violations


def _rel_str(path: Path, root: Path) -> str:
    """Return path relative to root as a POSIX string."""
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def discover_files(root: Path, config: LinterConfig) -> list[Path]:
    """Discover files to check based on include and exclude patterns."""
    exclude_spec = pathspec.PathSpec.from_lines("gitignore", config.exclude)
    candidate_files: set[Path] = set()
    for pattern in config.include:
        for p in root.glob(pattern):
            if p.is_file():
                candidate_files.add(p)

    return [p for p in sorted(candidate_files) if not exclude_spec.match_file(_rel_str(p, root))]


def _filter_explicit_files(
    files: Sequence[Path],
    config: LinterConfig,
    root: Path,
) -> list[Path]:
    """Filter explicit files against include and exclude patterns."""
    include_spec = pathspec.PathSpec.from_lines("gitignore", config.include)
    exclude_spec = pathspec.PathSpec.from_lines("gitignore", config.exclude)
    targets: list[Path] = []
    for f in files:
        p = f if f.is_absolute() else (root / f)
        rel = _rel_str(p, root)
        if not p.is_file() or exclude_spec.match_file(rel):
            continue

        if config.include != DEFAULT_INCLUDE and not include_spec.match_file(rel):
            continue

        targets.append(p)

    return targets


def _report_violations(all_violations: Sequence[Violation]) -> int:
    """Format and print all violation notices to stderr."""
    error_count = sum(1 for v in all_violations if v.is_error)
    warning_count = sum(1 for v in all_violations if not v.is_error)
    for v in all_violations:
        level = "ERROR" if v.is_error else "WARNING"
        if v.violation_type == "file_line_count":
            sys.stderr.write(
                f"{v.file_path}: {level}: File line count {v.length} "
                f"exceeds {level.lower()} limit ({v.threshold}) for {v.format_name}\n",
            )
        else:
            sys.stderr.write(
                f"{v.file_path}:{v.line_number}: {level}: Line length {v.length} "
                f"exceeds {level.lower()} limit ({v.threshold}) for {v.format_name}\n",
            )

    if all_violations:
        sys.stderr.write(
            f"\nLine length check found {error_count} error(s) and {warning_count} warning(s).\n",
        )

    return error_count


def run_linter(files: Sequence[Path] | None, config: LinterConfig, root: Path) -> int:
    """Execute line length enforcement and print notices to stderr."""
    targets = _filter_explicit_files(files, config, root) if files else discover_files(root, config)
    all_violations: list[Violation] = []
    for target in targets:
        all_violations.extend(check_file(target, config))

    return 1 if _report_violations(all_violations) > 0 else 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for the line length enforcement tool."""
    parser = argparse.ArgumentParser(description="Enforce format-specific file line length limits.")
    parser.add_argument("--config", type=Path, default=None, help="Path to config file.")
    parser.add_argument("files", nargs="*", type=Path, help="Explicit files to check.")
    args = parser.parse_args(argv)
    return run_linter(args.files, load_config(args.config), Path.cwd())


if __name__ == "__main__":
    sys.exit(main())
