"""Verify a release tag, and that the built distributions carry exactly that version (#327).

The release workflow runs this twice: once before the quality gate to reject anything that is not a
``vMAJOR.MINOR.PATCH`` tag, and once after ``uv build`` so a mis-versioned build (for example a
``.devN`` version built from a branch) fails before anything is published.

Usage:
    python tools/verify_release_version.py --tag v1.1.0
    python tools/verify_release_version.py --tag v1.1.0 --dist dist
"""

from __future__ import annotations

import argparse
import re
import sys
import tarfile
import zipfile
from email.parser import HeaderParser
from pathlib import Path

TAG_PATTERN = re.compile(r"v(\d+\.\d+\.\d+)")


def version_from_tag(tag: str) -> str:
    """Return the version for a ``vMAJOR.MINOR.PATCH`` release tag.

    Args:
        tag: Git tag name, for example ``v1.1.0``.

    Returns:
        The version without the leading ``v``.

    Raises:
        ValueError: If ``tag`` is not a ``vMAJOR.MINOR.PATCH`` tag.
    """
    match = TAG_PATTERN.fullmatch(tag)
    if match is None:
        msg = f"release tag {tag!r} is not a vMAJOR.MINOR.PATCH tag"
        raise ValueError(msg)

    return str(match.group(1))


def _metadata_version(text: str) -> str | None:
    """Return the ``Version`` header from core metadata text, if present."""
    return HeaderParser().parsestr(text).get("Version")


def _wheel_version(path: Path) -> str | None:
    """Return the version declared in a wheel's ``*.dist-info/METADATA``."""
    with zipfile.ZipFile(path) as zf:
        name = next(n for n in zf.namelist() if n.endswith(".dist-info/METADATA"))
        return _metadata_version(zf.read(name).decode("utf-8"))


def _sdist_version(path: Path) -> str | None:
    """Return the version declared in an sdist's top-level ``PKG-INFO``."""
    with tarfile.open(path, "r:gz") as tf:
        member = next(
            m for m in tf.getmembers() if m.name.count("/") == 1 and m.name.endswith("/PKG-INFO")
        )
        handle = tf.extractfile(member)
        assert handle is not None
        return _metadata_version(handle.read().decode("utf-8"))


def check(tag: str, dist: Path | None = None) -> list[str]:
    """Return a list of problems with ``tag`` and, if given, the artifacts in ``dist``.

    Args:
        tag: Release tag that triggered or was passed to the workflow.
        dist: Directory containing the built wheel and sdist, or ``None`` to check the tag only.

    Returns:
        Human-readable error messages; empty when everything matches.
    """
    try:
        expected = version_from_tag(tag)
    except ValueError as exc:
        return [str(exc)]

    if dist is None:
        return []

    errors: list[str] = []
    readers = {"*.whl": _wheel_version, "*.tar.gz": _sdist_version}
    for pattern, reader in readers.items():
        artifacts = sorted(dist.glob(pattern))
        if len(artifacts) != 1:
            errors.append(f"expected exactly one {pattern} in {dist}, found {len(artifacts)}")
            continue

        version = reader(artifacts[0])
        if version is None:
            errors.append(f"{artifacts[0].name}: metadata has no Version header")
        elif version != expected:
            errors.append(f"{artifacts[0].name}: built version {version} != tag version {expected}")

    return errors


def main(argv: list[str] | None = None) -> int:
    """Run the check from the command line and return the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", required=True, help="release tag, for example v1.1.0")
    parser.add_argument("--dist", type=Path, help="directory with the built wheel and sdist")
    args = parser.parse_args(argv)

    errors = check(args.tag, args.dist)
    for error in errors:
        sys.stderr.write(f"Error: {error}\n")

    if errors:
        return 1

    scope = f"tag and artifacts in {args.dist}" if args.dist else "tag"
    sys.stdout.write(f"OK: {scope} match version {version_from_tag(args.tag)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
