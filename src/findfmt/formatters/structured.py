"""Structured data serializers (JSON, JSONL, YAML, IPYNB)."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, Any, TextIO

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override  # pragma: no cover

import yaml

from findfmt.formatters.base import Formatter

if TYPE_CHECKING:
    from collections.abc import Iterable

    from findfmt.models import FileInfo


class JsonFormatter(Formatter):
    """Deterministic JSON array formatter with configurable indentation."""

    def __init__(
        self,
        *,
        absolute: bool = False,
        indent: int | None = 2,
    ) -> None:
        """Initialize JsonFormatter.

        Args:
            absolute: Whether to emit absolute paths.
            indent: Indentation spaces for pretty-printing, or None for compact.
        """
        super().__init__(absolute=absolute)
        self.indent = indent

    @override
    def format(self, files: Iterable[FileInfo]) -> str:
        """Format FileInfo objects into a deterministic JSON array.

        Args:
            files: Iterable of classified file objects.

        Returns:
            JSON array string ending with a newline.
        """
        records = [f.to_dict(absolute=self.absolute) for f in files]
        return json.dumps(records, indent=self.indent, ensure_ascii=False) + "\n"


class JsonlFormatter(Formatter):
    """Line-delimited JSON (NDJSON) record serializer for streaming pipelines."""

    def __init__(self, *, absolute: bool = False) -> None:
        """Initialize JsonlFormatter.

        Args:
            absolute: Whether to emit absolute paths.
        """
        super().__init__(absolute=absolute)

    def format_item(self, file_info: FileInfo) -> str:
        """Serialize a single FileInfo item to a compact JSON line.

        Args:
            file_info: Classified file information.

        Returns:
            Single line JSON string ending with a newline.
        """
        data = file_info.to_dict(absolute=self.absolute)
        return json.dumps(data, ensure_ascii=False) + "\n"

    @override
    def format(self, files: Iterable[FileInfo]) -> str:
        """Format an iterable of FileInfo objects into line-delimited JSON.

        Args:
            files: Iterable of classified file objects.

        Returns:
            Concatenated JSON lines string.
        """
        return "".join(self.format_item(f) for f in files)

    @override
    def stream(self, files: Iterable[FileInfo], stream: TextIO) -> None:
        """Stream FileInfo records as JSON lines directly to the output stream.

        Args:
            files: Iterable of classified file objects.
            stream: Target text stream.
        """
        stream.writelines(self.format_item(file_info) for file_info in files)
        stream.flush()


class YamlFormatter(Formatter):
    """Block-style YAML document serializer using PyYAML."""

    def __init__(self, *, absolute: bool = False, indent: int = 2) -> None:
        """Initialize YamlFormatter.

        Args:
            absolute: Whether to emit absolute paths.
            indent: Indentation spaces for nested YAML structures.
        """
        super().__init__(absolute=absolute)
        self.indent = indent

    @override
    def format(self, files: Iterable[FileInfo]) -> str:
        """Format FileInfo objects into a clean YAML document string.

        Args:
            files: Iterable of classified file objects.

        Returns:
            YAML document string ending with a newline.
        """
        records = [f.to_dict(absolute=self.absolute) for f in files]
        return str(
            yaml.safe_dump(
                records,
                sort_keys=False,
                indent=self.indent,
                allow_unicode=True,
                default_flow_style=False,
            ),
        )


class IpynbFormatter(Formatter):
    """Jupyter Notebook v4 JSON serializer pre-populated with analysis code."""

    def __init__(self, *, absolute: bool = False) -> None:
        """Initialize IpynbFormatter.

        Args:
            absolute: Whether to emit absolute paths.
        """
        super().__init__(absolute=absolute)

    @override
    def format(self, files: Iterable[FileInfo]) -> str:
        """Format FileInfo objects into a valid Jupyter Notebook v4 JSON string.

        Args:
            files: Iterable of classified file objects.

        Returns:
            Formatted Jupyter Notebook JSON string.
        """
        records = [f.to_dict(absolute=self.absolute) for f in files]
        manifest_literal = json.dumps(records, indent=2, ensure_ascii=False)

        cells: list[dict[str, Any]] = [
            {
                "cell_type": "markdown",
                "id": "intro",
                "metadata": {},
                "source": [
                    "# findfmt File Discovery Report\n",
                    "\n",
                    "Discovered files manifest generated by `findfmt`.\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "manifest-data",
                "metadata": {},
                "outputs": [],
                "source": (
                    "import pandas as pd\n\n"
                    "# Discovered files manifest\n"
                    f"FILES = {manifest_literal}\n\n"
                    "# Ingest into pandas DataFrame\n"
                    "df = pd.DataFrame(FILES)\n\n"
                    "# Optional: Ingest into polars DataFrame\n"
                    "# import polars as pl\n"
                    "# pl_df = pl.DataFrame(FILES)\n\n"
                    "df.head()\n"
                ).splitlines(keepends=True),
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "analysis",
                "metadata": {},
                "outputs": [],
                "source": (
                    "# Summary statistics\n"
                    'print(f"Total matched files: {len(df)}")\n'
                    'if not df.empty and "tags" in df.columns:\n'
                    '    print("\\nTop classification tags:")\n'
                    '    print(df.explode("tags")["tags"].value_counts().head(10))\n'
                    'if not df.empty and "mime_type" in df.columns:\n'
                    '    print("\\nTop MIME types:")\n'
                    '    print(df["mime_type"].value_counts().head(10))\n'
                ).splitlines(keepends=True),
            },
        ]

        notebook: dict[str, Any] = {
            "cells": cells,
            "metadata": {
                "language_info": {
                    "name": "python",
                    "version": "3",
                },
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }

        return json.dumps(notebook, indent=1, ensure_ascii=False) + "\n"
