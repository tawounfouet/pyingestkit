from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pyingestkit.artifacts import RawArtifact
from pyingestkit.core.exceptions import ParseError
from pyingestkit.dataset import Dataset

from .base import Parser


class NdjsonParser(Parser):
    """Parse newline-delimited JSON objects without business normalization."""

    def __init__(self, *, encoding: str = "utf-8-sig", allow_blank_lines: bool = True) -> None:
        self.encoding = encoding
        self.allow_blank_lines = allow_blank_lines

    def parse(self, artifact: RawArtifact) -> Dataset:
        try:
            data = Path(artifact.path).read_bytes()
        except OSError as exc:
            raise ParseError(f"Unable to read RAW artifact {artifact.path!r}") from exc
        return self.parse_bytes(data, source_artifact_id=artifact.artifact_id)

    def parse_bytes(self, data: bytes, *, source_artifact_id: str | None = None) -> Dataset:
        try:
            text = data.decode(self.encoding)
        except UnicodeDecodeError as exc:
            raise ParseError(f"NDJSON payload is not valid {self.encoding}") from exc

        rows: list[Mapping[str, Any]] = []
        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            if not raw_line.strip():
                if self.allow_blank_lines:
                    continue
                raise ParseError(f"NDJSON line {line_number} is blank")
            try:
                value: Any = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ParseError(f"Invalid NDJSON object at line {line_number}") from exc
            if not isinstance(value, Mapping):
                raise ParseError(f"NDJSON record at line {line_number} is not an object")
            if any(not isinstance(key, str) for key in value):
                raise ParseError(f"NDJSON record at line {line_number} has a non-string field name")
            rows.append(value)

        return Dataset(rows, source_artifact_id=source_artifact_id)
