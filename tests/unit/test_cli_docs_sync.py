"""Keep every place that documents the CLI in step with the registered options (#494, #623).

The CLI reference, the ``--help-all`` manual, the README options table, the configuration guide, and
top-level architecture/governance Markdown documents each describe the command line and repository
layout. These tests fail when an option, config key, module path, or tool script drifts from code.
"""

from __future__ import annotations

import re
import shutil
import tomllib
from pathlib import Path

import pytest
from tools import sync_cli_docs
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


def test_every_canonical_config_key_is_documented() -> None:
    """Every canonical key in config_schema.py is documented in configuration.md (#623)."""
    documented = set(sync_cli_docs.extract_documented_config_table(ROOT))
    canonical = sync_cli_docs.get_canonical_config_keys()
    accepted = sync_cli_docs.get_all_accepted_config_keys()
    assert canonical <= documented, (
        f"Missing canonical config keys: {sorted(canonical - documented)}"
    )
    assert documented <= accepted, (
        f"Unknown documented config keys: {sorted(documented - accepted)}"
    )


def test_top_level_markdown_cli_flags_and_paths_in_sync(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify sync_cli_docs passes on the live repository (#623)."""
    assert sync_cli_docs.check_docs_sync(ROOT) == []
    assert sync_cli_docs.main(["--repo", str(ROOT)]) == 0
    assert "OK:" in capsys.readouterr().out


def test_sync_cli_docs_detects_drift(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify sync_cli_docs reports drift across flags, config keys, paths, and versions (#623)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    for rel in sync_cli_docs.TOP_LEVEL_CLI_DOCS:
        shutil.copy2(ROOT / rel, repo / rel)

    shutil.copy2(ROOT / "pyproject.toml", repo / "pyproject.toml")
    (repo / "docs" / "source" / "cli").mkdir(parents=True)
    (repo / "docs" / "source" / "guides").mkdir(parents=True)
    shutil.copy2(
        ROOT / "docs" / "source" / "cli" / "index.md",
        repo / "docs" / "source" / "cli" / "index.md",
    )
    shutil.copy2(
        ROOT / "docs" / "source" / "guides" / "configuration.md",
        repo / "docs" / "source" / "guides" / "configuration.md",
    )
    for subdir in ("src", "tools", "tests"):
        (repo / subdir).symlink_to(ROOT / subdir, target_is_directory=True)

    assert sync_cli_docs.check_docs_sync(repo) == []

    # Inject drift into ACCESSIBILITY.md, AGENTS.md, SECURITY.md, and configuration.md.
    (repo / "ACCESSIBILITY.md").write_text(
        (repo / "ACCESSIBILITY.md").read_text(encoding="utf-8")
        + "\nSupports `--nonexistent-flag` and `findfmt --bad-flag`.\n",
        encoding="utf-8",
    )
    (repo / "AGENTS.md").write_text(
        (repo / "AGENTS.md")
        .read_text(encoding="utf-8")
        .replace("`verify_quality.py`", "`ghost_tool.py`")
        + "\nSee `src/findfmt/diagnostics.py` and `src/findfmt/missing_mod.py`.\n",
        encoding="utf-8",
    )
    (repo / "SECURITY.md").write_text(
        (repo / "SECURITY.md")
        .read_text(encoding="utf-8")
        .replace("| 1.2.x", "| 0.8.x")
        .replace("| < 1.2.0", "| < 0.8.0"),
        encoding="utf-8",
    )
    (repo / "docs" / "source" / "guides" / "configuration.md").write_text(
        (repo / "docs" / "source" / "guides" / "configuration.md")
        .read_text(encoding="utf-8")
        .replace("| `locale`", "| `bogus_key`"),
        encoding="utf-8",
    )

    assert sync_cli_docs.main(["--repo", str(repo)]) == 1
    err = capsys.readouterr().err
    assert "--nonexistent-flag" in err
    assert "--bad-flag" in err
    assert "deprecated root shim `src/findfmt/diagnostics.py`" in err
    assert "referenced path `src/findfmt/missing_mod.py` does not exist" in err
    assert "missing tools/*.py scripts ['verify_quality.py']" in err
    assert "lists non-existent tools/*.py scripts ['ghost_tool.py']" in err
    assert "Supported Versions table missing series" in err
    assert "missing config keys ['locale']" in err
    assert "unknown config keys ['bogus_key']" in err
