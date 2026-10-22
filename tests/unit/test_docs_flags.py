"""Keep documented option declarations aligned with the registered command."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from typer.main import get_command

from findfmt.cli import app

DOCS = Path(__file__).resolve().parents[2] / "docs" / "source"


@pytest.fixture
def cli_options():
    command = get_command(app)
    context = command.context_class(command)
    return {
        option.name: set(option.opts + getattr(option, "secondary_opts", []))
        for option in command.get_params(context)
        if any(name.startswith("-") for name in option.opts)
    }


def _flags(declaration):
    return re.findall(r"(?<![\w/-])--?[A-Za-z0-9][\w-]*", declaration)


def _configuration_declarations():
    text = (DOCS / "guides" / "configuration.md").read_text(encoding="utf-8")
    return {
        cells[1].strip(" `"): cells[3]
        for line in text.splitlines()
        if line.startswith("| `")
        if len(cells := line.split("|")) > 4
    }


def _cli_declarations():
    text = (DOCS / "cli" / "index.md").read_text(encoding="utf-8")
    options = text.split("## 3. Options\n", 1)[1].split("\n## 4.", 1)[0]
    return [
        " ".join(re.findall(r"`([^`]+)`", paragraph.split(" : ", 1)[0]))
        for block in options.split("\n\n")
        if re.match(r"(?:- )?`-", paragraph := " ".join(block.splitlines()))
    ]


@pytest.mark.parametrize("document", ["cli/index.md", "guides/configuration.md"])
def test_documented_flags_exist(cli_options, document):
    registered = set().union(*cli_options.values())
    assert registered
    declarations = (
        _cli_declarations()
        if document == "cli/index.md"
        else list(_configuration_declarations().values())
    )
    assert declarations, document
    for declaration in declarations:
        flags = _flags(declaration)
        assert flags, (document, declaration)
        assert len(flags) == len(set(flags)), (document, "duplicate flags", flags)
        assert set(flags) <= registered, (document, "unknown flags", set(flags) - registered)


def test_follow_symlinks_documented_flags(cli_options):
    declaration = _configuration_declarations()["follow_symlinks"]
    flags = set(_flags(declaration))
    assert flags <= cli_options["follow_symlinks"], ("follow_symlinks", declaration)
    assert "-l" in flags


@pytest.mark.parametrize(
    ("declaration", "expected"),
    [
        ("-L, --max-depth LEVEL", ["-L", "--max-depth"]),
        ("--follow-links / --no-follow-links", ["--follow-links", "--no-follow-links"]),
        ("--help", ["--help"]),
        ("PATH *.py /tmp/a-file", []),
    ],
)
def test_option_declaration_tokens(declaration, expected):
    assert _flags(declaration) == expected
