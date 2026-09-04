from __future__ import annotations

from io import BytesIO

from pyingestkit import Dataset, DatasetContract, DatasetProfiler, RunContext
from pyingestkit.artifacts import RawArtifact
from pyingestkit.core.exceptions import ConfigurationError
from pyingestkit.validation import ValidationResult


def fixture_raw(
    context: RunContext,
    *,
    name: str,
    data: bytes,
    content_type: str,
) -> RawArtifact:
    if not context.fixture_mode:
        raise ConfigurationError(
            f"{context.job_id} is a deterministic reference job and requires fixture_mode=true"
        )
    return context.artifact_store.write_raw(
        context.job_id,
        context.run_id,
        name=name,
        data=data,
        source_uri=f"fixture://pyingestkit/{context.job_id}/{name}",
        content_type=content_type,
    )


def validated_payload(dataset: Dataset, contract: DatasetContract) -> dict[str, object]:
    validation: ValidationResult = contract.validate(dataset)
    return {"dataset": dataset, "validation": validation}


def profiled_payload(data: dict[str, object]) -> dict[str, object]:
    dataset = data.get("dataset")
    if not isinstance(dataset, Dataset):
        raise TypeError("Quality reference payload is missing a Dataset")
    return {**data, "profile": DatasetProfiler().profile(dataset)}


def excel_fixture_bytes() -> bytes:
    try:
        from openpyxl import Workbook
    except ImportError as exc:  # pragma: no cover - optional dependency boundary
        raise ConfigurationError(
            'Excel reference job requires: pip install "pyingestkit[excel]"'
        ) from exc

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "People"
    worksheet.append(("id", "name", "score"))
    worksheet.append((1, "Alice", 91.5))
    worksheet.append((2, "Bob", 87.0))
    buffer = BytesIO()
    try:
        workbook.save(buffer)
    finally:
        workbook.close()
    return buffer.getvalue()


def parquet_fixture_bytes() -> bytes:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - optional dependency boundary
        raise ConfigurationError(
            'Parquet reference job requires: pip install "pyingestkit[parquet]"'
        ) from exc

    table = pa.Table.from_pylist(
        [
            {"id": 1, "name": "Alice", "score": 91.5},
            {"id": 2, "name": "Bob", "score": 87.0},
        ]
    )
    buffer = BytesIO()
    pq.write_table(table, buffer)
    return buffer.getvalue()
