from __future__ import annotations

from pyingestkit import Dataset, DatasetContract, FieldContract, NdjsonParser, RunContext, job, step
from pyingestkit.artifacts import RawArtifact

from .quality_common import fixture_raw, profiled_payload, validated_payload

NDJSON_FIXTURE = b'{"id":1,"name":"Alice","score":91.5}\n{"id":2,"name":"Bob","score":87.0}\n'
CONTRACT = DatasetContract(
    fields=(
        FieldContract("id", nullable=False, expected_type=int, unique=True, min_value=1),
        FieldContract("name", nullable=False, expected_type=str, min_length=1),
        FieldContract(
            "score",
            nullable=False,
            expected_type=(int, float),
            min_value=0,
            max_value=100,
        ),
    ),
    allow_extra_fields=False,
    min_rows=1,
    primary_key=("id",),
)


@step(name="FetchNdjsonFixture")
def fetch_ndjson(context: RunContext) -> RawArtifact:
    return fixture_raw(
        context,
        name="people.ndjson",
        data=NDJSON_FIXTURE,
        content_type="application/x-ndjson",
    )


@step(name="ParseNdjson")
def parse_ndjson(data: RawArtifact) -> Dataset:
    return NdjsonParser().parse(data)


@step(name="ValidateNdjsonDataset")
def validate_ndjson(data: Dataset) -> dict[str, object]:
    return validated_payload(data, CONTRACT)


@step(name="ProfileNdjsonDataset")
def profile_ndjson(data: dict[str, object]) -> dict[str, object]:
    return profiled_payload(data)


@job(
    id="demo.ndjson_quality",
    version="0.4.0rc1",
    description="Reference NDJSON -> Dataset -> Contract V2 -> profile -> quality reports slice.",
)
def ndjson_quality_job() -> None:
    fetch_ndjson()
    parse_ndjson()
    validate_ndjson()
    profile_ndjson()


job_definition = ndjson_quality_job
