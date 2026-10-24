"""Print the CHANGELOG.md section for a release tag, as the GitHub Release notes (#498).

The release workflow runs this before the quality gate, so a release whose changelog was not
prepared fails before anything is built or published, and again to fill in the GitHub Release.

Usage:
    python tools/release_notes.py --tag v1.1.0
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TAG_PATTERN = re.compile(r"v(\d+\.\d+\.\d+)")
TRAILER = re.compile(r"\s*|\[[^\]]+\]: \S+|<!--.*-->")
CHANGELOG = Path(__file__).resolve().parents[1] / "CHANGELOG.md"


def release_notes(changelog: str, tag: str) -> str:
    """Return the body of the ``## [X.Y.Z] - YYYY-MM-DD`` section for ``tag``.

    Args:
        changelog: CHANGELOG.md text.
        tag: Release tag, for example ``v1.1.0``.

    Returns:
        The section body, without its heading, up to the next ``## `` heading.

    Raises:
        ValueError: If the tag is not ``vMAJOR.MINOR.PATCH``, or the section is missing or empty.
    """
    match = TAG_PATTERN.fullmatch(tag)
    if match is None:
        msg = f"release tag {tag!r} is not a vMAJOR.MINOR.PATCH tag"
        raise ValueError(msg)

    version = match.group(1)
    heading = re.compile(rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$", re.MULTILINE)
    found = heading.search(changelog)
    if found is None:
        msg = f"CHANGELOG.md has no '## [{version}] - YYYY-MM-DD' section"
        raise ValueError(msg)

    rest = changelog[found.end() :]
    following = re.search(r"^## ", rest, re.MULTILINE)
    lines = (rest[: following.start()] if following else rest).strip().splitlines()
    # The link reference definitions and comments at the end of the file belong to no section.
    while lines and TRAILER.fullmatch(lines[-1]):
        lines.pop()

    body = "\n".join(lines).strip()
    if not body:
        msg = f"the CHANGELOG.md section for {version} is empty"
        raise ValueError(msg)

    return body + "\n"


def main(argv: list[str] | None = None) -> int:
    """Print the release notes for ``--tag``; return 1 if they are missing."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", required=True, help="release tag, for example v1.1.0")
    parser.add_argument("--changelog", type=Path, default=CHANGELOG, help="path to CHANGELOG.md")
    args = parser.parse_args(argv)
    try:
        notes = release_notes(args.changelog.read_text(encoding="utf-8"), args.tag)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
