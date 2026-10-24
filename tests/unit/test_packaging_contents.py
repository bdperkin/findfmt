"""Guard what the wheel and sdist select from the source tree (#495).

The wheel ships the compiled ``*.mo`` catalogs but not their ``*.po``/``*.pot`` sources, which are
never read at runtime. Both targets force-include the gitignored ``*.mo`` files; the sdist pattern
must be anchored to the package catalogs, or ``.mo`` files that ``make -C docs`` leaves under
``docs/`` leak into it. Files are selected by hatchling from a miniature tree that uses the real
``[tool.hatch]`` configuration, so no build backend plugins or network access are needed.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from hatchling.builders.sdist import SdistBuilder
from hatchling.builders.wheel import WheelBuilder

ROOT = Path(__file__).resolve().parents[2]
TREE = (
    "README.md",
    "LICENSE",
    "src/findfmt/__init__.py",
    "src/findfmt/py.typed",
    "src/findfmt/locale/findfmt.pot",
    "src/findfmt/locale/de/LC_MESSAGES/findfmt.po",
    "src/findfmt/locale/de/LC_MESSAGES/findfmt.mo",
    "docs/source/locale/de/LC_MESSAGES/index.po",
    "docs/source/locale/de/LC_MESSAGES/index.mo",
    "tools/i18n.py",
)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Return a miniature project using the real packaging configuration."""
    shutil.copy(ROOT / "pyproject.toml", tmp_path)
    (tmp_path / ".gitignore").write_text("*.mo\n", encoding="utf-8")
    for relative in TREE:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    return tmp_path


def _selected(builder: WheelBuilder | SdistBuilder) -> set[str]:
    return {f.distribution_path.replace("\\", "/") for f in builder.recurse_included_files()}


def test_wheel_ships_compiled_catalogs_only(project: Path) -> None:
    """The wheel holds the package, py.typed, and *.mo catalogs, but no catalog sources."""
    assert _selected(WheelBuilder(str(project))) == {
        "findfmt/__init__.py",
        "findfmt/py.typed",
        "findfmt/locale/de/LC_MESSAGES/findfmt.mo",
    }


def test_sdist_includes_only_package_catalog_artifacts(project: Path) -> None:
    """The sdist force-includes the package *.mo catalogs, not docs build output."""
    selected = _selected(SdistBuilder(str(project)))
    assert {path for path in selected if path.endswith(".mo")} == {
        "src/findfmt/locale/de/LC_MESSAGES/findfmt.mo",
    }
    for source in ("LICENSE", "src/findfmt/py.typed", "src/findfmt/locale/findfmt.pot"):
        assert source in selected
