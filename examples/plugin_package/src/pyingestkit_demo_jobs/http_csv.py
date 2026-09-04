from __future__ import annotations

from pyingestkit import (
    CsvParser,
    Dataset,
    DatasetContract,
    FieldContract,
    RunContext,
    ValidationResult,
    job,
    step,
)
from pyingestkit.artifacts import RawArtifact

from .http_common import reference_http_source

CSV_FIXTURE = b"id,name,active\n001,Alice,true\n002,Bob,false\n"
CSV_CONTRACT = DatasetContract(
    fields=(
        FieldContract("id", nullable=False, expected_type=str, unique=True),
        FieldContract("name", nullable=False, expected_type=str),
        FieldContract("active", nullable=False, expected_type=str),
    ),
    allow_extra_fields=False,
    min_rows=1,
)


@step(name="FetchHttpCsv")
def fetch_http_csv(context: RunContext) -> RawArtifact:
    return reference_http_source(
        context,
        fixture_content=CSV_FIXTURE,
        content_type="text/csv; charset=utf-8",
        artifact_name="demo.csv",
    ).fetch(context)


@step(name="ParseCsv")
def parse_csv(data: RawArtifact) -> Dataset:
    return CsvParser().parse(data)


@step(name="ValidateCsvDataset")
def validate_csv_dataset(data: Dataset) -> ValidationResult:
    return CSV_CONTRACT.validate(data)


@job(
    id="demo.http_csv",
    version="0.4.0b2",
    description="Reference HTTP -> RAW -> CSV -> Dataset -> validation vertical slice.",
)
def http_csv_job() -> None:
    fetch_http_csv()
    parse_csv()
    validate_csv_dataset()


job_definition = http_csv_job
