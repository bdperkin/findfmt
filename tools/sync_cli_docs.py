"""Verify synchronization between CLI/config Source of Truth and static Markdown docs (#623).

Usage:
    python tools/sync_cli_docs.py
    python tools/sync_cli_docs.py --repo .
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

from typer.main import get_command

from findfmt import _FALLBACK_VERSION
from findfmt.cli import app, config_schema
from findfmt.cli.help import get_help_all

REPO_ROOT = Path(__file__).resolve().parents[1]
FLAG_PATTERN = re.compile(r"(?<![\w/-])--?[A-Za-z0-9][\w-]*")
CODE_SPAN_PATTERN = re.compile(r"`([^`\n]+)`")
FINDFMT_INVOCATION_PATTERN = re.compile(r"\bfindfmt\s+([^\n`|;&>#]+)")
REPO_PATH_PATTERN = re.compile(r"^(?:src/findfmt|tools|tests)(?:/[\w.*-]+)+/?$")
DEPRECATED_ROOT_SHIMS = frozenset(
    {
        "src/findfmt/diagnostics.py",
        "src/findfmt/entrypoints.py",
        "src/findfmt/summary.py",
        "src/findfmt/terminal.py",
    },
)
TOP_LEVEL_CLI_DOCS = (
    "ACCESSIBILITY.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "README.md",
    "SECURITY.md",
    "SUPPORT.md",
)


def get_registered_cli_options() -> dict[str, set[str]]:
    """Return ``{param_name: set_of_flags}`` for every registered CLI option."""
    command = get_command(app)
    context = command.context_class(command)
    return {
        param.name or "": set(param.opts) | set(getattr(param, "secondary_opts", []))
        for param in command.get_params(context)
        if any(name.startswith("-") for name in param.opts)
    }


def get_canonical_config_keys() -> set[str]:
    """Return the set of canonical configuration keys accepted by ``config_schema``."""
    return set(config_schema.CANONICAL_CONFIG_KEYS)


def get_all_accepted_config_keys() -> set[str]:
    """Return all primary and alias configuration keys accepted by ``config_schema``."""
    return set(config_schema.ACCEPTED_CONFIG_KEYS)


MIN_CONFIG_TABLE_CELLS = 5


def extract_documented_config_table(repo: Path = REPO_ROOT) -> dict[str, str]:
    """Return ``{setting_key: cli_equivalent_cell}`` from ``configuration.md``."""
    text = (repo / "docs" / "source" / "guides" / "configuration.md").read_text(encoding="utf-8")
    return {
        cells[1].strip(" `"): cells[3].strip()
        for line in text.splitlines()
        if line.startswith("| `") and len(cells := line.split("|")) >= MIN_CONFIG_TABLE_CELLS
    }


def _check_cli_options_parity(repo: Path, options: dict[str, set[str]]) -> list[str]:
    """Verify every registered CLI option is documented across help, README, and CLI docs."""
    readme_text = (repo / "README.md").read_text(encoding="utf-8")
    readme_table = readme_text.split("## 4. CLI Options", 1)[1].split("\n## ", 1)[0]
    cli_ref_text = (repo / "docs" / "source" / "cli" / "index.md").read_text(encoding="utf-8")
    documents = {
        "--help-all": get_help_all(),
        "README.md (## 4. CLI Options)": readme_table,
        "docs/source/cli/index.md": cli_ref_text,
    }
    registered_flags = set().union(*options.values()) | {"--"}
    errors: list[str] = []

    for doc_name, content in documents.items():
        mentioned = set(FLAG_PATTERN.findall(content))
        missing = sorted(name for name, flags in options.items() if not flags & mentioned)
        if missing:
            errors.append(f"{doc_name}: missing registered CLI options {missing}")

    for doc_name in ("--help-all", "README.md (## 4. CLI Options)"):
        lines = [line.split(" -- ", 1)[0] for line in documents[doc_name].splitlines()]
        unknown = sorted(set(FLAG_PATTERN.findall("\n".join(lines))) - registered_flags)
        if unknown:
            errors.append(f"{doc_name}: names unregistered flags {unknown}")

    with (repo / "pyproject.toml").open("rb") as f:
        scripts = set(tomllib.load(f)["project"]["scripts"]) - {"findfmt"}

    for doc_name, full_text in (
        ("--help-all", documents["--help-all"]),
        ("README.md", readme_text),
        ("docs/source/cli/index.md", cli_ref_text),
    ):
        missing_scripts = sorted(s for s in scripts if s not in full_text)
        if missing_scripts:
            errors.append(f"{doc_name}: missing wrapper commands {missing_scripts}")

    return errors


def _check_config_docs_parity(repo: Path, options: dict[str, set[str]]) -> list[str]:
    """Verify ``docs/source/guides/configuration.md`` documents all canonical config keys."""
    documented = extract_documented_config_table(repo)
    canonical = get_canonical_config_keys()
    accepted = get_all_accepted_config_keys()
    registered_flags = set().union(*options.values())
    errors: list[str] = []

    missing_keys = sorted(canonical - set(documented))
    if missing_keys:
        errors.append(f"docs/source/guides/configuration.md: missing config keys {missing_keys}")

    unknown_keys = sorted(set(documented) - accepted)
    if unknown_keys:
        errors.append(f"docs/source/guides/configuration.md: unknown config keys {unknown_keys}")

    for key, cli_cell in documented.items():
        flags = FLAG_PATTERN.findall(cli_cell)
        unknown_flags = sorted(set(flags) - registered_flags)
        if unknown_flags:
            errors.append(
                f"docs/source/guides/configuration.md ({key}): unknown CLI flags {unknown_flags}",
            )

    return errors


def _check_top_level_markdown_flags(repo: Path, options: dict[str, set[str]]) -> list[str]:
    """Verify inline ``findfmt`` flags in top-level Markdown files exist in ``options.py``."""
    registered_flags = set().union(*options.values()) | {"--"}
    errors: list[str] = []

    for filename in TOP_LEVEL_CLI_DOCS:
        path = repo / filename
        text = path.read_text(encoding="utf-8")
        # 1. Check flags in `findfmt ...` command invocations.
        for match in FINDFMT_INVOCATION_PATTERN.finditer(text):
            head = match.group(1).split(" -- ", 1)[0]
            unknown = sorted(set(FLAG_PATTERN.findall(head)) - registered_flags)
            if unknown:
                errors.append(f"{filename}: unknown flags in findfmt invocation: {unknown}")

        # 2. Check standalone flag code spans in architecture/security/accessibility/support docs.
        if filename in ("ACCESSIBILITY.md", "AGENTS.md", "SECURITY.md", "SUPPORT.md"):
            for span in CODE_SPAN_PATTERN.findall(text):
                stripped = span.strip()
                if stripped.startswith("-") and not stripped.startswith(("-rw", "->", "-s,")):
                    head = stripped.split(" -- ", 1)[0]
                    flags = FLAG_PATTERN.findall(head)
                    unknown = sorted(set(flags) - registered_flags)
                    if unknown:
                        errors.append(f"{filename}: unknown flag in `{span}`: {unknown}")

    return errors


def _check_module_paths_and_tools_inventory(repo: Path) -> list[str]:
    """Verify referenced module paths exist on disk and ``tools/*.py`` is cataloged in AGENTS.md."""
    errors: list[str] = []
    for filename in ("AGENTS.md", "SECURITY.md"):
        text = (repo / filename).read_text(encoding="utf-8")
        for span in CODE_SPAN_PATTERN.findall(text):
            candidate = span.strip()
            if not REPO_PATH_PATTERN.match(candidate) or "*" in candidate:
                continue

            normalized = candidate.rstrip("/")
            if normalized in DEPRECATED_ROOT_SHIMS:
                errors.append(f"{filename}: references deprecated root shim `{candidate}`")
            elif not (repo / normalized).exists():
                errors.append(f"{filename}: referenced path `{candidate}` does not exist")

    agents_text = (repo / "AGENTS.md").read_text(encoding="utf-8")
    tools_section = agents_text.split("- `tools/`:", 1)[1].split("\n- `tests/`:", 1)[0]
    documented_tools = {
        span for span in CODE_SPAN_PATTERN.findall(tools_section) if span.endswith(".py")
    }
    actual_tools = {p.name for p in (repo / "tools").glob("*.py")}
    missing_tools = sorted(actual_tools - documented_tools)
    extra_tools = sorted(documented_tools - actual_tools)
    if missing_tools:
        errors.append(f"AGENTS.md: missing tools/*.py scripts {missing_tools}")

    if extra_tools:
        errors.append(f"AGENTS.md: lists non-existent tools/*.py scripts {extra_tools}")

    return errors


def _check_security_supported_version_sync(repo: Path) -> list[str]:
    """Verify ``SECURITY.md`` Supported Versions table matches ``_FALLBACK_VERSION`` series."""
    base_version = _FALLBACK_VERSION.removesuffix(".dev0")
    major, minor, _ = base_version.split(".")
    expected_series = f"{major}.{minor}.x"
    expected_floor = f"{major}.{minor}.0"
    security_text = (repo / "SECURITY.md").read_text(encoding="utf-8")
    errors: list[str] = []
    if f"| {expected_series}" not in security_text:
        errors.append(f"SECURITY.md: Supported Versions table missing series {expected_series}")

    if f"| < {expected_floor}" not in security_text:
        errors.append(f"SECURITY.md: Supported Versions table missing floor < {expected_floor}")

    return errors


def check_docs_sync(repo: Path = REPO_ROOT) -> list[str]:
    """Run all Source-of-Truth documentation synchronization checks on ``repo``."""
    options = get_registered_cli_options()
    return [
        *_check_cli_options_parity(repo, options),
        *_check_config_docs_parity(repo, options),
        *_check_top_level_markdown_flags(repo, options),
        *_check_module_paths_and_tools_inventory(repo),
        *_check_security_supported_version_sync(repo),
    ]


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for Source-of-Truth documentation synchronization checks."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--repo",
        type=Path,
        default=REPO_ROOT,
        help="repository root directory to audit (default: current repository)",
    )
    args = parser.parse_args(argv)
    errors = check_docs_sync(args.repo)
    for error in errors:
        sys.stderr.write(f"Error: {error}\n")

    if errors:
        return 1

    sys.stdout.write("OK: all CLI, configuration, and Markdown docs match Source of Truth.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
