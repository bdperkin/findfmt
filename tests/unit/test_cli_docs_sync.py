"""Keep every place that documents the CLI in step with the registered options (#494).

The CLI reference, the ``--help-all`` manual, and the README options table each describe the command
line. These tests fail when an option is added without documenting it, or when documentation names a
flag that does not exist. ``test_docs_flags.py`` checks the reference page in the other direction.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
from typer.main import get_command

from findfmt.cli import app
from findfmt.cli.help import get_help_all

ROOT = Path(__file__).resolve().parents[2]
FLAG = re.compile(r"(?<![\w/-])--?[A-Za-z0-9][\w-]*")


def _options() -> dict[str, set[str]]:
    """Return ``{parameter name: all of its flags}`` for every registered option."""
    command = get_command(app)
    context = command.context_class(command)
    return {
        param.name or "": set(param.opts) | set(getattr(param, "secondary_opts", []))
        for param in command.get_params(context)
        if any(name.startswith("-") for name in param.opts)
    }


def _readme_options_table() -> str:
    """Return the README "CLI Options" section."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    return readme.split("## 4. CLI Options", 1)[1].split("\n## ", 1)[0]


DOCUMENTS = {
    "CLI reference": lambda: (ROOT / "docs" / "source" / "cli" / "index.md").read_text(
        encoding="utf-8",
    ),
    "--help-all": get_help_all,
    "README options table": _readme_options_table,
}


@pytest.mark.parametrize("document", sorted(DOCUMENTS))
def test_every_option_is_documented(document: str) -> None:
    """Every registered option has at least one of its flags in the document."""
    mentioned = set(FLAG.findall(DOCUMENTS[document]()))
    missing = sorted(name for name, flags in _options().items() if not flags & mentioned)
    assert not missing, f"{document} does not document: {missing}"


@pytest.mark.parametrize("document", ["--help-all", "README options table"])
def test_documented_flags_exist(document: str) -> None:
    """Every flag named in the document is a registered option (``--`` ends option parsing)."""
    registered = set().union(*_options().values()) | {"--"}
    # Text after a POSIX `--` terminator is paths (e.g. `findfmt -- -hyphen-dir/`), not flags.
    lines = [line.split(" -- ", 1)[0] for line in DOCUMENTS[document]().splitlines()]
    unknown = sorted(set(FLAG.findall("\n".join(lines))) - registered)
    assert not unknown, f"{document} names unregistered flags: {unknown}"


@pytest.mark.parametrize("document", sorted(DOCUMENTS))
def test_every_wrapper_command_is_documented(document: str) -> None:
    """Every console script from pyproject.toml is described in the document."""
    with (ROOT / "pyproject.toml").open("rb") as f:
        scripts = set(tomllib.load(f)["project"]["scripts"]) - {"findfmt"}

    text = (
        DOCUMENTS[document]()
        if document != "README options table"
        else ((ROOT / "README.md").read_text(encoding="utf-8"))
    )
    missing = sorted(script for script in scripts if script not in text)
    assert not missing, f"{document} does not mention: {missing}"
