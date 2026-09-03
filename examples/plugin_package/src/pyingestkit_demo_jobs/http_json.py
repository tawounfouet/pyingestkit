from __future__ import annotations

from pyingestkit import (
    Dataset,
    DatasetContract,
    FieldContract,
    JsonParser,
    RunContext,
    ValidationResult,
    job,
    step,
)
from pyingestkit.artifacts import RawArtifact

from .http_common import reference_http_source

JSON_FIXTURE = b'[{"id":1,"name":"Alice","active":true},{"id":2,"name":"Bob","active":false}]'
JSON_CONTRACT = DatasetContract(
    fields=(
        FieldContract("id", nullable=False, expected_type=int, unique=True),
        FieldContract("name", nullable=False, expected_type=str),
        FieldContract("active", nullable=False, expected_type=bool),
    ),
    allow_extra_fields=False,
    min_rows=1,
)


@step(name="FetchHttpJson")
def fetch_http_json(context: RunContext) -> RawArtifact:
    return reference_http_source(
        context,
        fixture_content=JSON_FIXTURE,
        content_type="application/json",
        artifact_name="demo.json",
    ).fetch(context)


@step(name="ParseJson")
def parse_json(data: RawArtifact) -> Dataset:
    return JsonParser().parse(data)


@step(name="ValidateJsonDataset")
def validate_json_dataset(data: Dataset) -> ValidationResult:
    return JSON_CONTRACT.validate(data)


@job(
    id="demo.http_json",
    version="0.2.0",
    description="Reference HTTP -> RAW -> JSON -> Dataset -> validation vertical slice.",
)
def http_json_job() -> None:
    fetch_http_json()
    parse_json()
    validate_json_dataset()


job_definition = http_json_job
