from __future__ import annotations

import os
from pathlib import Path

from pyingestkit import (
    Dataset,
    DatasetContract,
    FieldContract,
    IdempotencyPolicy,
    LoadMode,
    NdjsonParser,
    PostgresTarget,
    RunContext,
    TargetLoadExecutor,
    TargetLoadRequest,
    job,
    step,
)
from pyingestkit.artifacts import RawArtifact
from pyingestkit.core.exceptions import ConfigurationError
from pyingestkit.diff import DatasetDiffer, DiffPolicy
from pyingestkit.metadata import (
    PostgresMetadataStore,
    SQLiteMetadataStore,
    TargetLoadMetadataCapability,
)
from pyingestkit.retry import RetryPolicy
from pyingestkit.sources.http import HttpRequest, HttpResponse, HttpSource
from pyingestkit.versioning import FilesystemDatasetVersionStore

from .http_common import FixtureSequenceClient
from .quality_common import profiled_payload, validated_payload

DATASET_ID = "demo.versioned_postgres"
ARTIFACT_NAME = "versioned-postgres-people.ndjson"
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
    """Fail loudly if a replay ever attempts a live HTTP request."""

    def send(self, request: HttpRequest) -> HttpResponse:
        raise AssertionError(f"Replay attempted a live HTTP request: {request.safe_url}")


def _fixture_payload(context: RunContext) -> bytes:
    revision = context.parameter("revision", 1)
    try:
        value = int(revision)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError("demo.versioned_postgres revision must be 1 or 2") from exc
    if value == 1:
        return REVISION_1
    if value == 2:
        return REVISION_2
    raise ConfigurationError("demo.versioned_postgres revision must be 1 or 2")


def _workspace(context: RunContext) -> Path:
    root = getattr(context.artifact_store, "root", None)
    if root is None:
        raise ConfigurationError(
            "demo.versioned_postgres requires the LocalArtifactStore workspace"
        )
    return Path(root)


def _metadata(context: RunContext) -> TargetLoadMetadataCapability:
    backend = str(context.parameter("metadata_backend", "sqlite")).lower()
    if backend == "sqlite":
        metadata = SQLiteMetadataStore(_workspace(context) / "state" / "pyingest.sqlite3")
    elif backend == "postgres":
        env_name = str(context.parameter("metadata_dsn_env", "PYINGEST_DATABASE_URL"))
        dsn = os.getenv(env_name)
        if not dsn:
            raise ConfigurationError(
                "demo.versioned_postgres expects PostgreSQL metadata DSN in environment "
                f"variable {env_name!r}"
            )
        metadata = PostgresMetadataStore(dsn)
    else:
        raise ConfigurationError(
            "demo.versioned_postgres metadata_backend must be 'sqlite' or 'postgres'"
        )
    metadata.initialize()
    return metadata


def _target_parameters(context: RunContext) -> tuple[str, str, str | None, str]:
    target_id = str(context.parameter("target_id", "postgres.demo.versioned"))
    table = str(context.parameter("target_table", "pyingestkit_demo_versioned"))
    schema_value = context.parameter("target_schema", "public")
    schema = None if schema_value is None else str(schema_value)
    dsn_env = str(context.parameter("target_dsn_env", "PYINGEST_TARGET_DATABASE_URL"))
    if not target_id.strip() or not table.strip() or not dsn_env.strip():
        raise ConfigurationError("demo.versioned_postgres target parameters must not be empty")
    return target_id, table, schema, dsn_env


@step(name="FetchVersionedPostgresNdjson")
def fetch_versioned_postgres_ndjson(context: RunContext) -> RawArtifact:
    if context.replay is not None:
        return HttpSource(
            SOURCE_URL,
            client=NetworkForbiddenClient(),
            artifact_name=ARTIFACT_NAME,
        ).fetch(context)

    if not context.fixture_mode:
        raise ConfigurationError(
            "demo.versioned_postgres is an offline stable reference job and requires fixture_mode=true"
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


@step(name="ParseVersionedPostgresNdjson")
def parse_versioned_postgres_ndjson(data: RawArtifact) -> Dataset:
    return NdjsonParser().parse(data)


@step(name="ValidateVersionedPostgresDataset")
def validate_versioned_postgres_dataset(data: Dataset) -> dict[str, object]:
    return validated_payload(data, CONTRACT)


@step(name="ProfileVersionedPostgresDataset")
def profile_versioned_postgres_dataset(data: dict[str, object]) -> dict[str, object]:
    return profiled_payload(data)


@step(name="VersionLoadPublishPostgres")
def version_load_publish_postgres(
    context: RunContext,
    data: dict[str, object],
) -> dict[str, object]:
    dataset = data.get("dataset")
    if not isinstance(dataset, Dataset):
        raise TypeError("Versioned PostgreSQL reference payload is missing a Dataset")

    metadata = _metadata(context)
    version_store = FilesystemDatasetVersionStore(
        _workspace(context),
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
            "demo.versioned_postgres expects PostgreSQL target DSN in environment variable "
            f"{dsn_env!r}"
        )

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
                "Replay reproduced a version that is not the currently published PostgreSQL dataset"
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
    version="0.5.0",
    description=(
        "V0.5 stable V1 -> V2 -> diff -> DatasetVersion -> PostgreSQL -> publish -> "
        "strict RAW replay -> idempotent SKIP reference slice."
    ),
)
def versioned_postgres_job() -> None:
    fetch_versioned_postgres_ndjson()
    parse_versioned_postgres_ndjson()
    validate_versioned_postgres_dataset()
    profile_versioned_postgres_dataset()
    version_load_publish_postgres()


job_definition = versioned_postgres_job
