"""Audit Python source files for inline linter and type-checker suppression comments."""

from __future__ import annotations

import io
import re
import tokenize
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import pathspec
import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "DEFAULT_IGNORE_PATHS",
    "DEFAULT_INCLUDE_PATTERNS",
    "GRAND_UNIFIED_SUPPRESSION_REGEX",
    "AllowedSuppression",
    "AuditorConfig",
    "SuppressionViolation",
    "app",
    "audit",
    "audit_file",
    "console",
    "discover_files",
    "extract_comments",
    "has_justification",
    "is_whitelisted",
    "load_config",
]
app = typer.Typer(help="Audit and verify inline linter and type-checker suppression comments.")
console = Console(width=200)
MIN_JUSTIFICATION_WORDS = 2
DEFAULT_INCLUDE_PATTERNS: tuple[str, ...] = ("src/**/*.py", "tests/**/*.py", "tools/**/*.py")
DEFAULT_IGNORE_PATHS: tuple[str, ...] = (
    "dist/**",
    "build/**",
    "vendor/**",
    ".venv/**",
    ".git/**",
    "__pycache__/**",
)
GRAND_UNIFIED_SUPPRESSION_REGEX = re.compile(
    r"""
    \#\s*(?P<directive>
        (?:flake8:\s*noqa|ruff:\s*(?:noqa|ignore|disable|enable|no-qa)(?:\[[^\]]*\])?)|
        \bnoqa\b(?::\s*[A-Za-z0-9_]+(?:\s*,\s*[A-Za-z0-9_]+)*)?|
        pylint:\s*(?:disable|enable)(?:=[A-Za-z0-9_-]+(?:\s*,\s*[A-Za-z0-9_-]+)*)?|
        (?:fmt|yapf):\s*(?:skip|off|on|disable|enable)\b|
        type:\s*ignore(?:\[[^\]]*\])?|mypy:\s*ignore-errors\b|pyright:\s*ignore(?:\[[^\]]*\])?|
        pytype:\s*disable=[A-Za-z0-9_-]+(?:\s*,\s*[A-Za-z0-9_-]+)*|pyre-(?:ignore|fixme)(?:\[\d+\])?\b|
        nosec\b(?:\s+[A-Za-z0-9_]+(?:\s*,\s*[A-Za-z0-9_]+)*)?|
        pragma:\s*no\s+(?:cover|branch)\b|pragma:\s*[A-Za-z0-9_-]+|doctest:\s*[+\-][A-Za-z0-9_]+
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)


@dataclass(frozen=True)
class AllowedSuppression:
    """Whitelisted inline suppression entry configured in pyproject.toml."""

    file: str
    line: int | None = None
    code: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class AuditorConfig:
    """Configuration options for the inline suppression auditor."""

    strict: bool = False
    include: tuple[str, ...] = DEFAULT_INCLUDE_PATTERNS
    ignore_paths: tuple[str, ...] = DEFAULT_IGNORE_PATHS
    allowed: tuple[AllowedSuppression, ...] = ()


@dataclass(frozen=True)
class SuppressionViolation:
    """Recorded unjustified inline suppression comment."""

    file: str
    line: int
    content: str
    directive: str


def _parse_str_tuple(raw_val: object, default: tuple[str, ...]) -> tuple[str, ...]:
    """Parse a list of string patterns from TOML configuration."""
    return tuple(str(item) for item in raw_val) if isinstance(raw_val, list | tuple) else default


def _parse_allowed_entries(raw_allowed: object) -> tuple[AllowedSuppression, ...]:
    """Parse allowed suppression table entries from TOML configuration."""
    if not isinstance(raw_allowed, list):
        return ()
    entries: list[AllowedSuppression] = []
    for item in raw_allowed:
        if not isinstance(item, dict):
            continue
        file_val = item.get("file")
        if not isinstance(file_val, str) or not file_val:
            continue
        raw_line, raw_code, raw_reason = item.get("line"), item.get("code"), item.get("reason")
        line_int = (
            raw_line if isinstance(raw_line, int) and not isinstance(raw_line, bool) else None
        )
        code_str = str(raw_code) if isinstance(raw_code, str) and raw_code else None
        reason_str = str(raw_reason).strip() if isinstance(raw_reason, str) else ""
        entries.append(AllowedSuppression(file_val, line_int, code_str, reason_str))
    return tuple(entries)


def load_config(config_path: Path | None = None) -> AuditorConfig:
    """Load suppression auditor configuration from pyproject.toml if available."""
    pyproject_path = config_path or Path("pyproject.toml")
    if not pyproject_path.is_file():
        return AuditorConfig()
    try:
        with pyproject_path.open("rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        console.print(f"[yellow]Warning: Failed to parse {pyproject_path}: {exc}[/yellow]")
        return AuditorConfig()

    tool_section = data.get("tool", {})
    raw_cfg = tool_section.get("findfmt", {}).get("suppression_auditor")
    if not isinstance(raw_cfg, dict):
        raw_cfg = tool_section.get("suppression-auditor", {})
    if not isinstance(raw_cfg, dict):
        return AuditorConfig()

    return AuditorConfig(
        strict=bool(raw_cfg.get("strict", False)),
        include=_parse_str_tuple(raw_cfg.get("include"), DEFAULT_INCLUDE_PATTERNS),
        ignore_paths=_parse_str_tuple(raw_cfg.get("ignore_paths"), DEFAULT_IGNORE_PATHS),
        allowed=_parse_allowed_entries(raw_cfg.get("allowed")),
    )


def has_justification(comment_text: str) -> bool:
    """Check whether a comment containing a suppression directive includes a justification."""
    remaining = GRAND_UNIFIED_SUPPRESSION_REGEX.sub("", comment_text)
    return len(remaining.lstrip(" \t#-—:;").strip().split()) >= MIN_JUSTIFICATION_WORDS


def _rel_posix(path: Path, root: Path) -> str:
    """Return path relative to root as a normalized POSIX string when possible."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def is_whitelisted(
    file_path: Path,
    line_no: int,
    directive: str,
    allowed: Sequence[AllowedSuppression],
    root: Path,
) -> bool:
    """Check whether a specific file, line, and directive match an allowed entry."""
    resolved_target = file_path.resolve()
    rel_target = _rel_posix(file_path, root)
    for entry in allowed:
        if (root / entry.file).resolve() != resolved_target and entry.file != rel_target:
            continue
        if entry.line is not None and entry.line != line_no:
            continue
        if entry.code is not None and entry.code.lower() not in directive.lower():
            continue
        return True
    return False


def extract_comments(content: str) -> list[tuple[int, str]]:
    """Extract (line_number, comment_text) pairs from Python source using tokenize."""
    reader = io.StringIO(content).readline
    try:
        return [
            (tok.start[0], tok.string)
            for tok in tokenize.generate_tokens(reader)
            if tok.type == tokenize.COMMENT
        ]
    except (tokenize.TokenError, IndentationError):
        return [
            (line_no, line[line.find("#") :])
            for line_no, line in enumerate(content.splitlines(), start=1)
            if "#" in line
        ]


def audit_file(
    file_path: Path,
    config: AuditorConfig,
    root: Path,
) -> tuple[int, list[SuppressionViolation]]:
    """Audit a single Python file and return (checked_count, violations)."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        console.print(f"[red]Error reading {file_path}: {exc}[/red]")
        return 0, []

    lines = content.splitlines()
    checked = 0
    violations: list[SuppressionViolation] = []
    for line_no, comment_text in extract_comments(content):
        match = GRAND_UNIFIED_SUPPRESSION_REGEX.search(comment_text)
        if not match:
            continue
        checked += 1
        directive = match.group("directive").strip()
        if is_whitelisted(file_path, line_no, directive, config.allowed, root):
            continue
        if not has_justification(comment_text):
            raw_line = lines[line_no - 1].strip() if 1 <= line_no <= len(lines) else comment_text
            violations.append(SuppressionViolation(str(file_path), line_no, raw_line, directive))
    return checked, violations


def discover_files(
    explicit_files: Sequence[Path] | None,
    config: AuditorConfig,
    root: Path,
) -> list[Path]:
    """Resolve target Python files from explicit arguments or repository globs."""
    ignore_spec = pathspec.PathSpec.from_lines("gitignore", config.ignore_paths)
    candidates: list[Path] = []
    if explicit_files is not None and len(explicit_files) > 0:
        for item in explicit_files:
            if item.is_dir():
                candidates.extend(sorted(item.rglob("*.py")))
            elif item.is_file() and item.suffix == ".py":
                candidates.append(item)
    else:
        seen: set[Path] = set()
        for pattern in config.include:
            for match_path in sorted(root.glob(pattern)):
                if match_path.is_file() and match_path.suffix == ".py" and match_path not in seen:
                    seen.add(match_path)
                    candidates.append(match_path)
    return [
        p
        for p in candidates
        if not ignore_spec.match_file(_rel_posix(p, root))
        and not ignore_spec.match_file(p.as_posix())
    ]


@app.command()
def audit(
    files: Annotated[list[Path] | None, typer.Argument(help="Python files to audit.")] = None,
    *,
    strict: Annotated[bool | None, typer.Option("--strict/--no-strict")] = None,
    config_file: Annotated[Path | None, typer.Option("--config")] = None,
) -> None:
    """Scan Python files for unjustified inline suppression comments."""
    root = Path.cwd()
    config = load_config(config_file)
    is_strict = strict if strict is not None else config.strict
    violations: list[SuppressionViolation] = []
    total_checked = 0
    for file_path in discover_files(files, config, root):
        checked, file_violations = audit_file(file_path, config, root)
        total_checked += checked
        violations.extend(file_violations)

    if violations:
        console.print(f"\n[bold red]Found {len(violations)} unjustified suppression(s):[/bold red]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("File", overflow="fold")
        table.add_column("Line")
        table.add_column("Suppression Line", overflow="fold")
        for violation in violations:
            table.add_row(escape(violation.file), str(violation.line), escape(violation.content))
        console.print(table)
        console.print(f"\n[yellow]Configured strict mode: {is_strict}[/yellow]")
        console.print("[yellow]Action required: Add inline reason or pyproject.toml rule.[/yellow]")
        raise typer.Exit(code=1)

    console.print(
        f"[bold green]Successfully audited {total_checked} suppression(s). "
        "All checks passed![/bold green]",
    )
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
