"""Integration test verifying that built wheels properly package and load translation catalogs."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.slow
def test_built_wheel_loads_german_catalog(tmp_path: Path) -> None:
    """Verify wheel built in isolation includes valid gettext catalogs and translates strings."""
    dist_dir = tmp_path / "dist"
    venv_dir = tmp_path / "venv"

    # Build wheel using uv build in isolation
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(dist_dir)],
        check=True,
        capture_output=True,
    )
    wheels = list(dist_dir.glob("*.whl"))
    assert len(wheels) == 1
    wheel_path = wheels[0]

    # Create temporary virtual environment
    subprocess.run(
        ["uv", "venv", str(venv_dir)],
        check=True,
        capture_output=True,
    )

    if sys.platform == "win32":
        python_bin = venv_dir / "Scripts" / "python.exe"
    else:
        python_bin = venv_dir / "bin" / "python"

    # Install built wheel into temporary venv
    subprocess.run(
        ["uv", "pip", "install", "--python", str(python_bin), str(wheel_path)],
        check=True,
        capture_output=True,
    )

    # Verify set_locale("de") loads German catalog and translates
    script = (
        "import gettext;"
        "from findfmt.i18n import set_locale, get_current_translation, _;"
        "active = set_locale('de');"
        "assert active == 'de';"
        "trans = get_current_translation();"
        "assert isinstance(trans, gettext.GNUTranslations);"
        "translated = _('not installed');"
        "assert translated == 'nicht installiert', f'Unexpected: {translated}';"
        "print('SUCCESS')"
    )
    result = subprocess.run(
        [str(python_bin), "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "SUCCESS" in result.stdout
