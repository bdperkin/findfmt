"""Verify a release tag, fallback versions, and built distribution versions (#327, #609, #623).

The release workflow runs this twice: once before the quality gate to reject anything that is not a
``vMAJOR.MINOR.PATCH`` tag or has out-of-sync fallback versions, and once after ``uv build`` so a
mis-versioned build (for example a ``.devN`` version built from a branch) fails before anything is
published. Maintainers can also pass ``--write`` during release preparation to synchronize fallback
versions across ``pyproject.toml``, ``src/findfmt/__init__.py``, and ``SECURITY.md``.

Usage:
    python tools/verify_release_version.py --tag v1.2.0 --repo .
    python tools/verify_release_version.py --tag v1.2.0 --write
    python tools/verify_release_version.py --tag v1.2.0 --dist dist
"""

from __future__ import annotations

import argparse
import re
import sys
import tarfile
import zipfile
from email.parser import HeaderParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TAG_PATTERN = re.compile(r"v(\d+\.\d+\.\d+)")
PYPROJECT_FALLBACK_PATTERN = re.compile(
    r'^(version\.fallback-version\s*=\s*")([^"]+)(")',
    re.MULTILINE,
)
INIT_FALLBACK_PATTERN = re.compile(
    r'^(_FALLBACK_VERSION(?:\s*:\s*str)?\s*=\s*")([^"]+)(")',
    re.MULTILINE,
)
SECURITY_SUPPORTED_PATTERN = re.compile(
    r"^(\|\s*)(\d+\.\d+\.x)(\s*\|\s*:white_check_mark:\s*\|\s*\n\|\s*<\s*)(\d+\.\d+\.0)(\s*\|\s*:x:\s*\|)",
    re.MULTILINE,
)
SECURITY_ATTESTATION_PATTERN = re.compile(
    r"(ghcr\.io/bdperkin/findfmt:)(\d+\.\d+\.\d+)",
)


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


def _extract_fallback(path: Path, pattern: re.Pattern[str]) -> str | None:
    """Return the fallback version matched by ``pattern`` in ``path``, if present."""
    match = pattern.search(path.read_text(encoding="utf-8"))
    return str(match.group(2)) if match is not None else None


def _version_series(version: str) -> tuple[str, str]:
    """Return ``(major.minor.x, major.minor.0)`` for a ``MAJOR.MINOR.PATCH`` version."""
    major, minor, _ = version.split(".")
    return f"{major}.{minor}.x", f"{major}.{minor}.0"


def _check_security_versions(repo: Path, expected: str) -> list[str]:
    """Verify ``SECURITY.md`` supported version series if ``SECURITY.md`` exists in ``repo``."""
    security_path = repo / "SECURITY.md"
    if not security_path.is_file():
        return []

    expected_series, expected_floor = _version_series(expected)
    text = security_path.read_text(encoding="utf-8")
    match = SECURITY_SUPPORTED_PATTERN.search(text)
    if match is None:
        return ["SECURITY.md: missing Supported Versions table"]

    actual_series, actual_floor = str(match.group(2)), str(match.group(4))
    errors: list[str] = []
    if actual_series != expected_series:
        errors.append(
            f"SECURITY.md: supported version series {actual_series} != expected {expected_series}",
        )

    if actual_floor != expected_floor:
        errors.append(
            f"SECURITY.md: unsupported version floor {actual_floor} != expected {expected_floor}",
        )

    return errors


def _check_repo_fallbacks(repo: Path, expected: str) -> list[str]:
    """Verify fallback version declarations in ``repo`` match ``<expected>.dev0``."""
    expected_fallback = f"{expected}.dev0"
    targets = {
        "pyproject.toml": (repo / "pyproject.toml", PYPROJECT_FALLBACK_PATTERN),
        "src/findfmt/__init__.py": (
            repo / "src" / "findfmt" / "__init__.py",
            INIT_FALLBACK_PATTERN,
        ),
    }
    errors: list[str] = []
    for rel_path, (path, pattern) in targets.items():
        actual = _extract_fallback(path, pattern)
        if actual is None:
            errors.append(f"{rel_path}: missing fallback version declaration")
        elif actual != expected_fallback:
            errors.append(f"{rel_path}: fallback version {actual} != expected {expected_fallback}")

    errors.extend(_check_security_versions(repo, expected))
    return errors


def sync_fallback_versions(tag: str, repo: Path = REPO_ROOT) -> None:
    """Update fallback version declarations in ``repo`` to ``<tag_version>.dev0``.

    Args:
        tag: Release tag, for example ``v1.2.0``.
        repo: Repository root containing ``pyproject.toml``, ``src/findfmt/__init__.py``,
            and optionally ``SECURITY.md``.
    """
    expected = version_from_tag(tag)
    expected_fallback = f"{expected}.dev0"
    targets = (
        (repo / "pyproject.toml", PYPROJECT_FALLBACK_PATTERN),
        (repo / "src" / "findfmt" / "__init__.py", INIT_FALLBACK_PATTERN),
    )
    for path, pattern in targets:
        text = path.read_text(encoding="utf-8")
        updated = pattern.sub(rf"\g<1>{expected_fallback}\g<3>", text, count=1)
        path.write_text(updated, encoding="utf-8")

    security_path = repo / "SECURITY.md"
    if security_path.is_file():
        expected_series, expected_floor = _version_series(expected)
        sec_text = security_path.read_text(encoding="utf-8")
        sec_text = SECURITY_SUPPORTED_PATTERN.sub(
            rf"\g<1>{expected_series}\g<3>{expected_floor}\g<5>",
            sec_text,
            count=1,
        )
        sec_text = SECURITY_ATTESTATION_PATTERN.sub(rf"\g<1>{expected}", sec_text)
        security_path.write_text(sec_text, encoding="utf-8")


def _check_dist_artifacts(dist: Path, expected: str) -> list[str]:
    """Verify the built wheel and sdist in ``dist`` declare ``expected``."""
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


def check(tag: str, dist: Path | None = None, repo: Path | None = None) -> list[str]:
    """Return a list of problems with ``tag``, ``dist``, and ``repo`` fallback declarations.

    Args:
        tag: Release tag that triggered or was passed to the workflow.
        dist: Directory containing the built wheel and sdist, or ``None`` to skip artifact checks.
        repo: Repository root to check fallback versions, or ``None`` to skip fallback checks.

    Returns:
        Human-readable error messages; empty when everything matches.
    """
    try:
        expected = version_from_tag(tag)
    except ValueError as exc:
        return [str(exc)]

    errors: list[str] = []
    if repo is not None:
        errors.extend(_check_repo_fallbacks(repo, expected))

    if dist is not None:
        errors.extend(_check_dist_artifacts(dist, expected))

    return errors


def main(argv: list[str] | None = None) -> int:
    """Run the check or sync from the command line and return the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", required=True, help="release tag, for example v1.2.0")
    parser.add_argument("--dist", type=Path, help="directory with the built wheel and sdist")
    parser.add_argument(
        "--repo",
        type=Path,
        help="repository root to verify or update fallback version declarations",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="update fallback versions in pyproject.toml and src/findfmt/__init__.py to <tag>.dev0",
    )
    args = parser.parse_args(argv)

    repo = (args.repo or REPO_ROOT) if args.write else args.repo
    if args.write and TAG_PATTERN.fullmatch(args.tag) is not None:
        assert repo is not None
        sync_fallback_versions(args.tag, repo)

    errors = check(args.tag, args.dist, repo)
    for error in errors:
        sys.stderr.write(f"Error: {error}\n")

    if errors:
        return 1

    scope = f"tag and artifacts in {args.dist}" if args.dist else "tag"
    sys.stdout.write(f"OK: {scope} match version {version_from_tag(args.tag)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
