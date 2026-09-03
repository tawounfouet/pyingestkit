from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from pyingestkit.artifacts import RawArtifact
from pyingestkit.core.exceptions import ParseError
from pyingestkit.dataset import Dataset

from .base import Parser


class CsvParser(Parser):
    """Parse a header-based CSV RAW artifact without business coercion."""

    def __init__(
        self,
        *,
        encoding: str = "utf-8-sig",
        delimiter: str = ",",
        quotechar: str = '"',
        strict: bool = True,
    ) -> None:
        if len(delimiter) != 1:
            raise ValueError("CSV delimiter must be exactly one character")
        if len(quotechar) != 1:
            raise ValueError("CSV quotechar must be exactly one character")
        self.encoding = encoding
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.strict = strict

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
            raise ParseError(f"CSV payload is not valid {self.encoding}") from exc

        try:
            reader = csv.reader(
                StringIO(text, newline=""),
                delimiter=self.delimiter,
                quotechar=self.quotechar,
                strict=self.strict,
            )
            header = next(reader, None)
            if header is None:
                raise ParseError("CSV payload must contain a header row")
            if len(header) != len(set(header)):
                raise ParseError("CSV header contains duplicate field names")
            rows: list[dict[str, str]] = []
            for line_number, values in enumerate(reader, start=2):
                if len(values) != len(header):
                    raise ParseError(
                        f"CSV row {line_number} has {len(values)} values; expected {len(header)}"
                    )
                rows.append(dict(zip(header, values, strict=True)))
        except csv.Error as exc:
            raise ParseError(f"Invalid CSV payload: {exc}") from exc

        return Dataset(rows, fields=header, source_artifact_id=source_artifact_id)
