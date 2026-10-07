"""Synchronize GitHub labels from .github/labels.yml using GitHub CLI."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml


class LabelSyncError(RuntimeError):
    """Base exception for label synchronization errors."""


class LabelFileNotFoundError(LabelSyncError):
    """Raised when labels configuration file is missing."""

    def __init__(self, path: Path) -> None:
        """Initialize error with missing file path."""
        super().__init__(f"Labels configuration file not found: {path}")


class InvalidSchemaError(LabelSyncError):
    """Raised when labels YAML is not a list."""

    def __init__(self) -> None:
        """Initialize error with explanation."""
        super().__init__("Invalid labels.yml schema: Expected a list of label definitions.")


def sync_labels(labels_file: Path, *, dry_run: bool = False) -> None:
    """Synchronize labels defined in labels_file to current GitHub repository.

    Args:
        labels_file: Path to YAML file defining labels.
        dry_run: When True, logs planned changes without applying them.
    """
    if not labels_file.exists():
        raise LabelFileNotFoundError(labels_file)

    with labels_file.open("r", encoding="utf-8") as f:
        labels_data = yaml.safe_load(f)

    if not isinstance(labels_data, list):
        raise InvalidSchemaError

    sys.stdout.write(f"Syncing {len(labels_data)} labels from {labels_file}...\n")

    for item in labels_data:
        name = item.get("name")
        color = str(item.get("color", "cccccc")).lstrip("#")
        desc = item.get("description", "")

        if not name:
            continue

        if dry_run:
            sys.stdout.write(f"[DRY-RUN] Would create/update label: {name} ({color})\n")
            continue

        # Use gh label create with --force to create or update existing label
        cmd = [
            "gh",
            "label",
            "create",
            name,
            "--color",
            color,
            "--description",
            desc,
            "--force",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            sys.stdout.write(f"[✓] Synced label: {name}\n")
        else:
            sys.stderr.write(f"[-] Failed to sync label {name}: {proc.stderr.strip()}\n")


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Command-line arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(description="Synchronize repository labels from labels.yml.")
    parser.add_argument(
        "--file",
        type=Path,
        default=Path(".github/labels.yml"),
        help="Path to labels YAML file (default: .github/labels.yml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate label synchronization without applying changes.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Command-line arguments.

    Returns:
        Exit code (0 on success, non-zero on failure).
    """
    args = parse_arguments(argv)
    try:
        sync_labels(args.file, dry_run=args.dry_run)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"Label synchronization failed: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
