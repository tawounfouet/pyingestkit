from __future__ import annotations

import importlib
from collections.abc import Sequence
from io import BytesIO
from pathlib import Path
from typing import Any

from pyingestkit.artifacts import RawArtifact
from pyingestkit.core.exceptions import ConfigurationError, ParseError
from pyingestkit.dataset import Dataset

from .base import Parser


class ParquetParser(Parser):
    """Materialize a Parquet payload into the neutral Dataset contract.

    PyArrow is loaded lazily from the optional ``parquet`` extra. The parser is
    structural: it preserves values returned by PyArrow and performs no business
    coercion, renaming, enrichment, or dataframe conversion.
    """

    def __init__(
        self,
        *,
        columns: Sequence[str] | None = None,
        max_rows: int | None = None,
    ) -> None:
        normalized_columns = None if columns is None else tuple(columns)
        if normalized_columns is not None:
            if not normalized_columns:
                raise ValueError("Parquet columns must not be empty")
            if any(not isinstance(column, str) or not column for column in normalized_columns):
                raise ValueError("Parquet columns must be non-empty strings")
            if len(normalized_columns) != len(set(normalized_columns)):
                raise ValueError("Parquet columns must be unique")
        if max_rows is not None and max_rows < 0:
            raise ValueError("Parquet max_rows must be >= 0")
        self.columns = normalized_columns
        self.max_rows = max_rows

    def parse(self, artifact: RawArtifact) -> Dataset:
        try:
            data = Path(artifact.path).read_bytes()
        except OSError as exc:
            raise ParseError(f"Unable to read RAW artifact {artifact.path!r}") from exc
        return self.parse_bytes(data, source_artifact_id=artifact.artifact_id)

    def parse_bytes(self, data: bytes, *, source_artifact_id: str | None = None) -> Dataset:
        pq = self._parquet_module()
        buffer = BytesIO(data)
        try:
            parquet_file = pq.ParquetFile(buffer)
            metadata = parquet_file.metadata
            row_count = int(metadata.num_rows)
            if self.max_rows is not None and row_count > self.max_rows:
                raise ParseError(
                    f"Parquet payload has {row_count} rows; configured max_rows is {self.max_rows}"
                )
            buffer.seek(0)
            table = pq.read_table(buffer, columns=list(self.columns) if self.columns else None)
        except ParseError:
            raise
        except Exception as exc:  # noqa: BLE001 - optional parser backend boundary
            raise ParseError("Invalid Parquet payload") from exc

        fields = tuple(table.schema.names)
        if any(not isinstance(field, str) for field in fields):
            raise ParseError("Parquet schema contains a non-string field name")
        if len(fields) != len(set(fields)):
            raise ParseError("Parquet schema contains duplicate field names")

        try:
            rows: list[dict[str, Any]] = table.to_pylist()
        except Exception as exc:  # noqa: BLE001 - optional parser backend boundary
            raise ParseError("Unable to materialize Parquet rows") from exc
        return Dataset(rows, fields=fields, source_artifact_id=source_artifact_id)

    @staticmethod
    def _parquet_module() -> Any:
        try:
            return importlib.import_module("pyarrow.parquet")
        except ImportError as exc:
            message = (
                "Parquet support requires the optional dependency: "
                'pip install "pyingestkit[parquet]"'
            )
            raise ConfigurationError(message) from exc
