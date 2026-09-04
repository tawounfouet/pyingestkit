from __future__ import annotations

import importlib
from io import BytesIO
from pathlib import Path
from typing import Any

from pyingestkit.artifacts import RawArtifact
from pyingestkit.core.exceptions import ConfigurationError, ParseError
from pyingestkit.dataset import Dataset

from .base import Parser


class ExcelParser(Parser):
    """Parse one XLSX worksheet structurally using the optional openpyxl extra.

    Cell values are preserved as returned by openpyxl. No trimming, renaming,
    formula evaluation, or business type coercion is performed.
    """

    def __init__(
        self,
        *,
        sheet: str | int = 0,
        header_row: int = 1,
        skip_empty_rows: bool = True,
        data_only: bool = True,
    ) -> None:
        if isinstance(sheet, int) and sheet < 0:
            raise ValueError("Excel sheet index must be >= 0")
        if not isinstance(sheet, (str, int)) or isinstance(sheet, bool):
            raise TypeError("Excel sheet must be a sheet name or zero-based index")
        if isinstance(sheet, str) and not sheet:
            raise ValueError("Excel sheet name must not be empty")
        if header_row < 1:
            raise ValueError("Excel header_row must be >= 1")
        self.sheet = sheet
        self.header_row = header_row
        self.skip_empty_rows = skip_empty_rows
        self.data_only = data_only

    def parse(self, artifact: RawArtifact) -> Dataset:
        try:
            data = Path(artifact.path).read_bytes()
        except OSError as exc:
            raise ParseError(f"Unable to read RAW artifact {artifact.path!r}") from exc
        return self.parse_bytes(data, source_artifact_id=artifact.artifact_id)

    def parse_bytes(self, data: bytes, *, source_artifact_id: str | None = None) -> Dataset:
        try:
            openpyxl = importlib.import_module("openpyxl")
        except ImportError as exc:  # pragma: no cover - depends on installed extras
            raise ConfigurationError(
                'Excel support requires the optional dependency: pip install "pyingestkit[excel]"'
            ) from exc

        try:
            workbook = openpyxl.load_workbook(
                BytesIO(data), read_only=True, data_only=self.data_only
            )
        except Exception as exc:  # noqa: BLE001 - optional parser backend boundary
            raise ParseError("Invalid XLSX payload") from exc

        try:
            worksheet = self._select_sheet(workbook)
            iterator = worksheet.iter_rows(values_only=True)
            header_values: tuple[Any, ...] | None = None
            for row_number, values in enumerate(iterator, start=1):
                if row_number == self.header_row:
                    header_values = tuple(values)
                    break
            if header_values is None:
                raise ParseError(f"Excel worksheet has no header row {self.header_row}")

            fields = self._header_fields(header_values)
            rows: list[dict[str, Any]] = []
            for values in iterator:
                normalized = tuple(values)
                if len(normalized) > len(fields) and any(
                    value is not None for value in normalized[len(fields) :]
                ):
                    raise ParseError("Excel data row contains values beyond the header width")
                normalized = normalized[: len(fields)] + (None,) * max(
                    0, len(fields) - len(normalized)
                )
                if self.skip_empty_rows and all(value is None for value in normalized):
                    continue
                rows.append(dict(zip(fields, normalized, strict=True)))
            return Dataset(rows, fields=fields, source_artifact_id=source_artifact_id)
        finally:
            workbook.close()

    def _select_sheet(self, workbook: Any) -> Any:
        if isinstance(self.sheet, str):
            if self.sheet not in workbook.sheetnames:
                raise ParseError(f"Excel worksheet {self.sheet!r} was not found")
            return workbook[self.sheet]
        if self.sheet >= len(workbook.worksheets):
            raise ParseError(f"Excel worksheet index {self.sheet} is out of range")
        return workbook.worksheets[self.sheet]

    @staticmethod
    def _header_fields(values: tuple[Any, ...]) -> tuple[str, ...]:
        trimmed = list(values)
        while trimmed and trimmed[-1] is None:
            trimmed.pop()
        if not trimmed:
            raise ParseError("Excel header row is empty")
        fields: list[str] = []
        for index, value in enumerate(trimmed, start=1):
            if value is None:
                raise ParseError(f"Excel header cell {index} is empty")
            if not isinstance(value, str):
                raise ParseError(f"Excel header cell {index} must be a string")
            if not value:
                raise ParseError(f"Excel header cell {index} is empty")
            fields.append(value)
        if len(fields) != len(set(fields)):
            raise ParseError("Excel header contains duplicate field names")
        return tuple(fields)
