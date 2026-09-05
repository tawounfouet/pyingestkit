from __future__ import annotations

import os

from sqlalchemy import BigInteger, Column, MetaData, Table, Text, create_engine
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION

from pyingestkit import (
    Dataset,
    DatasetContract,
    FieldContract,
    IdempotencyPolicy,
    LoadMode,
    NdjsonParser,
    PostgresTarget,
    RunContext,
    S3ArtifactStore,
    S3DatasetVersionStore,
    TargetLoadExecutor,
    TargetLoadRequest,
    job,
    step,
)
from pyingestkit.artifacts import RawArtifact
from pyingestkit.core.exceptions import ConfigurationError
from pyingestkit.diff import DatasetDiffer, DiffPolicy
from pyingestkit.metadata import PostgresMetadataStore, TargetLoadMetadataCapability
from pyingestkit.retry import RetryPolicy
from pyingestkit.sources.http import HttpRequest, HttpResponse, HttpSource

from .http_common import FixtureSequenceClient
from .quality_common import profiled_payload, validated_payload

DATASET_ID = "demo.versioned_s3"
ARTIFACT_NAME = "versioned-s3-people.ndjson"
SOURCE_URL = f"https://fixtures.pyingestkit.invalid/{ARTIFACT_NAME}"

REVISION_1 = (
    b'{"id":1,"name":"Alice","score":91.5}\n'
    b'{"id":2,"name":"Bob","score":87.0}\n'
    b'{"id":4,"name":"Dora","score":70.0}\n'
)
REVISION_2 = (
    b'{"id":1,"name":"Alice","score":92.0}\n'
    b'{"id":2,"name":"Bob","score":87.0}\n'
    b'{"id":3,"name":"Carla","score":80.0}\n'
)

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


class NetworkForbiddenClient:
    """Fail loudly if cross-host replay ever attempts live acquisition."""

    def send(self, request: HttpRequest) -> HttpResponse:
        raise AssertionError(f"Replay attempted a live HTTP request: {request.safe_url}")


def _fixture_payload(context: RunContext) -> bytes:
    revision = context.parameter("revision", 1)
    try:
        value = int(revision)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError("demo.versioned_s3 revision must be 1 or 2") from exc
    if value == 1:
        return REVISION_1
    if value == 2:
        return REVISION_2
    raise ConfigurationError("demo.versioned_s3 revision must be 1 or 2")


def _artifact_store(context: RunContext) -> S3ArtifactStore:
    store = context.artifact_store
    if not isinstance(store, S3ArtifactStore):
        raise ConfigurationError("demo.versioned_s3 requires an S3ArtifactStore")
    return store


def _metadata(context: RunContext) -> TargetLoadMetadataCapability:
    env_name = str(context.parameter("metadata_dsn_env", "PYINGEST_DATABASE_URL"))
    dsn = os.getenv(env_name)
    if not dsn:
        raise ConfigurationError(
            "demo.versioned_s3 expects PostgreSQL metadata DSN in environment "
            f"variable {env_name!r}"
        )
    metadata = PostgresMetadataStore(dsn)
    metadata.initialize()
    return metadata


def _target_parameters(context: RunContext) -> tuple[str, str, str | None, str]:
    target_id = str(context.parameter("target_id", "postgres.demo.versioned_s3"))
    table = str(context.parameter("target_table", "pyingestkit_demo_versioned_s3"))
    schema_value = context.parameter("target_schema", "public")
    schema = None if schema_value is None else str(schema_value)
    dsn_env = str(context.parameter("target_dsn_env", "PYINGEST_TARGET_DATABASE_URL"))
    if not target_id.strip() or not table.strip() or not dsn_env.strip():
        raise ConfigurationError("demo.versioned_s3 target parameters must not be empty")
    return target_id, table, schema, dsn_env


def _normalize_demo_postgres_dsn(dsn: str) -> str:
    if dsn.startswith("postgres://"):
        return "postgresql+psycopg://" + dsn.removeprefix("postgres://")
    if dsn.startswith("postgresql://"):
        return "postgresql+psycopg://" + dsn.removeprefix("postgresql://")
    return dsn


def _ensure_demo_target_table(dsn: str, table: str, schema: str | None) -> None:
    engine = create_engine(_normalize_demo_postgres_dsn(dsn), future=True)
    metadata = MetaData()
    demo_table = Table(
        table,
        metadata,
        Column("id", BigInteger, primary_key=True),
        Column("name", Text, nullable=False),
        Column("score", DOUBLE_PRECISION(), nullable=False),
        schema=schema,
    )
    try:
        metadata.create_all(engine, tables=[demo_table], checkfirst=True)
    finally:
        engine.dispose()


@step(name="FetchVersionedS3Ndjson")
def fetch_versioned_s3_ndjson(context: RunContext) -> RawArtifact:
    if context.replay is not None:
        return HttpSource(
            SOURCE_URL,
            client=NetworkForbiddenClient(),
            artifact_name=ARTIFACT_NAME,
        ).fetch(context)

    if not context.fixture_mode:
        raise ConfigurationError(
            "demo.versioned_s3 is an offline RC1 reference job and requires fixture_mode=true"
        )
    return HttpSource(
        SOURCE_URL,
        client=FixtureSequenceClient(_fixture_payload(context), "application/x-ndjson"),
        retry=RetryPolicy(
            max_attempts=2,
            initial_delay_seconds=0.0,
            max_delay_seconds=0.0,
            jitter=False,
        ),
        artifact_name=ARTIFACT_NAME,
    ).fetch(context)


@step(name="ParseVersionedS3Ndjson")
def parse_versioned_s3_ndjson(data: RawArtifact) -> Dataset:
    return NdjsonParser().parse(data)


@step(name="ValidateVersionedS3Dataset")
def validate_versioned_s3_dataset(data: Dataset) -> dict[str, object]:
    return validated_payload(data, CONTRACT)


@step(name="ProfileVersionedS3Dataset")
def profile_versioned_s3_dataset(data: dict[str, object]) -> dict[str, object]:
    return profiled_payload(data)


@step(name="VersionLoadPublishS3")
def version_load_publish_s3(
    context: RunContext,
    data: dict[str, object],
) -> dict[str, object]:
    dataset = data.get("dataset")
    if not isinstance(dataset, Dataset):
        raise TypeError("Versioned S3 reference payload is missing a Dataset")

    metadata = _metadata(context)
    version_store = S3DatasetVersionStore(
        _artifact_store(context),
        metadata_store=metadata,
    )
    previously_published = version_store.get_published(DATASET_ID)
    diff = None
    if previously_published is not None:
        previous = version_store.load_dataset(
            version_store.get_version(DATASET_ID, previously_published.version_id)
        )
        diff = DatasetDiffer(DiffPolicy(key_fields=("id",))).compare(previous, dataset)

    version = version_store.create_version(
        dataset,
        dataset_id=DATASET_ID,
        created_from_run_id=str(context.run_id),
        job_id=context.job_id,
        job_version=context.job_version,
        source_artifact_id=dataset.source_artifact_id,
        quality_reports=("reports/validation.json", "reports/profile.json"),
    )

    target_id, table, schema, dsn_env = _target_parameters(context)
    dsn = os.getenv(dsn_env)
    if not dsn:
        raise ConfigurationError(
            f"demo.versioned_s3 expects PostgreSQL target DSN in environment variable {dsn_env!r}"
        )
    if context.fixture_mode:
        _ensure_demo_target_table(dsn, table, schema)

    request = TargetLoadRequest(
        target_id=target_id,
        dataset_id=DATASET_ID,
        dataset_version_id=version.version_id,
        run_id=str(context.run_id),
        dataset=dataset,
        schema=schema,
        table=table,
        mode=LoadMode.REPLACE,
        key_fields=("id",),
        expected_row_count=dataset.row_count,
        idempotency_policy=IdempotencyPolicy.REQUIRE_VERSION,
    )
    with PostgresTarget(
        target_id=target_id,
        dsn=dsn,
        default_schema=schema,
    ) as target:
        load_result = TargetLoadExecutor(target=target, metadata_store=metadata).execute(request)

    if context.replay is None:
        published = version_store.publish(version, run_id=str(context.run_id))
    else:
        published = version_store.get_published(DATASET_ID)
        if published is None or published.version_id != version.version_id:
            raise ConfigurationError(
                "Replay reproduced a version that is not the currently published S3 dataset"
            )

    result: dict[str, object] = {
        **data,
        "version": version,
        "load_result": load_result,
        "published": published,
    }
    if diff is not None:
        result["diff"] = diff
    return result


@job(
    id=DATASET_ID,
    version="0.6.0",
    description=(
        "V0.6 stable remote RAW -> remote versions -> diff -> PostgreSQL -> publish -> "
        "cross-workspace strict replay -> idempotent SKIP reference slice."
    ),
    requires_artifacts="s3",
    requires_metadata="postgres",
)

def versioned_s3_job() -> None:
    fetch_versioned_s3_ndjson()
    parse_versioned_s3_ndjson()
    validate_versioned_s3_dataset()
    profile_versioned_s3_dataset()
    version_load_publish_s3()


job_definition = versioned_s3_job
