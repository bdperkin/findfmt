"""Smoke-test an installed findfmt wheel in a clean environment (#496).

CI installs the built wheel into a fresh virtual environment on the minimum and maximum supported
Python on Linux, macOS, and Windows, then runs this script with that environment's interpreter.
It checks the installed package, not the source tree: the version matches the wheel, the console
scripts run, and the user-visible 1.1 behavior works without a traceback.

Usage:
    smoke_env/bin/python tools/smoke_wheel.py --wheel dist/findfmt-1.1.0-py3-none-any.whl
"""

from __future__ import annotations

import argparse
import gettext
import importlib.metadata
import platform
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import findfmt
from findfmt.i18n import _, get_current_translation, set_locale

if TYPE_CHECKING:
    from collections.abc import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
WHEEL_NAME_FIELDS = 5  # name-version-python-abi-platform.whl
WRAPPERS = ("findfilefmt", "findfilemime", "findfiles", "findfmt0", "findshebang", "findsummary")


class SmokeError(Exception):
    """A smoke check failed."""


def wheel_version(wheel: Path) -> str:
    """Return the version from a wheel file name (``name-version-tags.whl``)."""
    parts = wheel.name.split("-")
    if wheel.suffix != ".whl" or len(parts) < WHEEL_NAME_FIELDS:
        msg = f"{wheel.name} is not a wheel file name"
        raise SmokeError(msg)

    return parts[1]


def script(name: str) -> str:
    """Return the path of an installed console script next to this interpreter."""
    found = shutil.which(name, path=sysconfig.get_path("scripts"))
    if found is None:
        msg = f"console script {name!r} is not installed"
        raise SmokeError(msg)

    return found


def run(name: str, *args: str, expect: int = 0) -> str:
    """Run an installed console script and return its standard output.

    Raises:
        SmokeError: On an unexpected exit status, or if a traceback is printed.
    """
    result = subprocess.run(  # noqa: PLW1510 - the exit status is checked below
        [script(name), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    command = " ".join([name, *args])
    if "Traceback" in result.stdout + result.stderr:
        msg = f"{command} printed a traceback:\n{result.stderr}"
        raise SmokeError(msg)

    if result.returncode != expect:
        msg = f"{command} exited {result.returncode}, expected {expect}:\n{result.stderr}"
        raise SmokeError(msg)

    return result.stdout


def check_installed(version: str | None, *, allow_source: bool) -> None:
    """Check that findfmt is imported from the environment, with the expected version."""
    location = Path(findfmt.__file__).resolve()
    if not allow_source and location.is_relative_to(REPO_ROOT / "src"):
        msg = f"findfmt was imported from the source tree ({location}), not the installed wheel"
        raise SmokeError(msg)

    installed = importlib.metadata.version("findfmt")
    if version is not None and installed != version:
        msg = f"installed findfmt is {installed}, expected {version}"
        raise SmokeError(msg)

    if installed not in run("findfmt", "--version"):
        msg = f"findfmt --version does not report {installed}"
        raise SmokeError(msg)


def check_commands(tree: Path) -> None:
    """Run the CLI and every wrapper against a small tree."""
    (tree / "script.py").write_text("print('hi')\n", encoding="utf-8")
    (tree / "blob.bin").write_bytes(b"\0" * 2048)
    run("findfmt", "--help")
    if f"Python: {platform.python_version()}" not in run("findfmt", "--diagnostics"):
        msg = "findfmt --diagnostics does not report the running Python"
        raise SmokeError(msg)

    if run("findfmt", "-t", "python", "-l", str(tree)).split() != ["script.py"]:
        msg = "findfmt -t python did not list exactly script.py"
        raise SmokeError(msg)

    if "[2.0 KiB] blob.bin" not in run("findfmt", "-h", "-l", str(tree)):
        msg = "findfmt -h does not print IEC size labels"
        raise SmokeError(msg)

    run("findfmt", "-t", "no-such-tag", "--exit-status", str(tree), expect=1)
    for wrapper in WRAPPERS:
        run(wrapper, "--help")

    run("findfiles", "-t", "no-such-tag", "--exit-status", str(tree), expect=1)


def check_translations() -> None:
    """Check that the compiled message catalogs shipped in the wheel load."""
    try:
        if set_locale("de") != "de" or not isinstance(
            get_current_translation(),
            gettext.GNUTranslations,
        ):
            msg = "the German message catalog is not installed"
            raise SmokeError(msg)

        if _("not installed") != "nicht installiert":
            msg = "the German message catalog does not translate"
            raise SmokeError(msg)
    finally:
        set_locale("C")


def main(argv: list[str] | None = None) -> int:
    """Run every smoke check and return the exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--wheel", type=Path, help="wheel that was installed (checks its version)")
    parser.add_argument(
        "--allow-source",
        action="store_true",
        help="accept findfmt imported from the source tree (development installs)",
    )
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory() as tree:
        checks: list[tuple[str, Callable[[], None]]] = [
            (
                "installed package",
                lambda: check_installed(
                    wheel_version(args.wheel) if args.wheel else None,
                    allow_source=args.allow_source,
                ),
            ),
            ("console scripts", lambda: check_commands(Path(tree))),
            ("translations", check_translations),
        ]
        try:
            for name, check in checks:
                check()
                print(f"ok: {name}")
        except SmokeError as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1

    print(f"findfmt wheel smoke test passed on Python {platform.python_version()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
