"""Entry point for python -m findfmt."""

from __future__ import annotations

from findfmt.cli import app

__all__: list[str] = []

if __name__ == "__main__":  # pragma: no cover
    app()
