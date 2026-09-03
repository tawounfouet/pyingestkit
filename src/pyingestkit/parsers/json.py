from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from pyingestkit.artifacts import RawArtifact
from pyingestkit.core.exceptions import ParseError
from pyingestkit.dataset import Dataset

from .base import Parser

JsonPathPart = str | int


class JsonParser(Parser):
    """Parse JSON records without flattening, coercion, renaming, or enrichment."""

    def __init__(
        self,
        *,
        records_path: Sequence[JsonPathPart] = (),
        allow_single_object: bool = True,
    ) -> None:
        self.records_path = tuple(records_path)
        self.allow_single_object = allow_single_object

    def parse(self, artifact: RawArtifact) -> Dataset:
        try:
            data = Path(artifact.path).read_bytes()
        except OSError as exc:
            raise ParseError(f"Unable to read RAW artifact {artifact.path!r}") from exc
        return self.parse_bytes(data, source_artifact_id=artifact.artifact_id)

    def parse_bytes(self, data: bytes, *, source_artifact_id: str | None = None) -> Dataset:
        try:
            payload: Any = json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ParseError("Invalid JSON payload") from exc

        selected = self._select_records(payload)
        if isinstance(selected, Mapping):
            if not self.allow_single_object:
                raise ParseError("JSON dataset must resolve to an array of objects")
            rows = [self._as_row(selected, index=0)]
        elif isinstance(selected, list):
            rows = [self._as_row(item, index=index) for index, item in enumerate(selected)]
        else:
            raise ParseError("JSON dataset must resolve to an object or an array of objects")

        return Dataset(rows, source_artifact_id=source_artifact_id)

    def _select_records(self, payload: Any) -> Any:
        current = payload
        for part in self.records_path:
            if isinstance(part, str):
                if not isinstance(current, Mapping) or part not in current:
                    raise ParseError(f"JSON records_path key {part!r} was not found")
                current = current[part]
                continue
            if not isinstance(current, list):
                raise ParseError(f"JSON records_path index {part} requires an array")
            try:
                current = current[part]
            except IndexError as exc:
                raise ParseError(f"JSON records_path index {part} is out of range") from exc
        return current

    @staticmethod
    def _as_row(value: Any, *, index: int) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise ParseError(f"JSON record at index {index} is not an object")
        if any(not isinstance(key, str) for key in value):
            raise ParseError(f"JSON record at index {index} contains a non-string field name")
        return value
