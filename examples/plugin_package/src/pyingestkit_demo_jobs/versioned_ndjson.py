from __future__ import annotations

from pathlib import Path

from pyingestkit import Dataset, DatasetContract, FieldContract, NdjsonParser, RunContext, job, step
from pyingestkit.artifacts import RawArtifact, S3ArtifactStore
from pyingestkit.core.exceptions import ConfigurationError
from pyingestkit.diff import DatasetDiffer, DiffPolicy
from pyingestkit.metadata import SQLiteMetadataStore
from pyingestkit.retry import RetryPolicy
from pyingestkit.sources.http import HttpRequest, HttpResponse, HttpSource
from pyingestkit.versioning import (
    DatasetVersionStore,
    FilesystemDatasetVersionStore,
    S3DatasetVersionStore,
)

from .http_common import FixtureSequenceClient
from .quality_common import profiled_payload, validated_payload

DATASET_ID = "demo.versioned_ndjson"
ARTIFACT_NAME = "versioned-people.ndjson"
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
        raise ConfigurationError("demo.versioned_ndjson revision must be 1 or 2") from exc
    if value == 1:
        return REVISION_1
    if value == 2:
        return REVISION_2
    raise ConfigurationError("demo.versioned_ndjson revision must be 1 or 2")


def _version_store(context: RunContext) -> DatasetVersionStore:
    root = getattr(context.artifact_store, "root", None)
    if root is None:
        raise ConfigurationError("demo.versioned_ndjson requires an ArtifactStore workspace/cache")
    workspace = Path(root)
    metadata = SQLiteMetadataStore(workspace / "state" / "pyingest.sqlite3")
    metadata.initialize()
    if isinstance(context.artifact_store, S3ArtifactStore):
        return S3DatasetVersionStore(context.artifact_store, metadata_store=metadata)
    return FilesystemDatasetVersionStore(workspace, metadata_store=metadata)


@step(name="FetchVersionedNdjson")
def fetch_versioned_ndjson(context: RunContext) -> RawArtifact:
    if context.replay is not None:
        return HttpSource(
            SOURCE_URL,
            client=NetworkForbiddenClient(),
            artifact_name=ARTIFACT_NAME,
        ).fetch(context)

    if not context.fixture_mode:
        raise ConfigurationError(
            "demo.versioned_ndjson is an offline stable reference job and requires fixture_mode=true"
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


@step(name="ParseVersionedNdjson")
def parse_versioned_ndjson(data: RawArtifact) -> Dataset:
    return NdjsonParser().parse(data)


@step(name="ValidateVersionedDataset")
def validate_versioned_dataset(data: Dataset) -> dict[str, object]:
    return validated_payload(data, CONTRACT)


@step(name="ProfileVersionedDataset")
def profile_versioned_dataset(data: dict[str, object]) -> dict[str, object]:
    return profiled_payload(data)


@step(name="DiffVersionPublish")
def diff_version_publish(context: RunContext, data: dict[str, object]) -> dict[str, object]:
    dataset = data.get("dataset")
    if not isinstance(dataset, Dataset):
        raise TypeError("Versioned reference payload is missing a Dataset")

    store = _version_store(context)
    published = store.get_published(DATASET_ID)
    diff = None
    if published is not None:
        previous = store.load_dataset(store.get_version(DATASET_ID, published.version_id))
        diff = DatasetDiffer(DiffPolicy(key_fields=("id",))).compare(previous, dataset)

    version = store.create_version(
        dataset,
        dataset_id=DATASET_ID,
        created_from_run_id=str(context.run_id),
        job_id=context.job_id,
        job_version=context.job_version,
        source_artifact_id=dataset.source_artifact_id,
        quality_reports=("reports/validation.json", "reports/profile.json"),
    )
    current = store.publish(version, run_id=str(context.run_id))

    result: dict[str, object] = {**data, "version": version, "published": current}
    if diff is not None:
        result["diff"] = diff
    return result


@job(
    id=DATASET_ID,
    version="0.4.0",
    description="Stable V0.4 NDJSON V1 -> V2 -> diff -> version -> publish -> replay E2E slice.",
)
def versioned_ndjson_job() -> None:
    fetch_versioned_ndjson()
    parse_versioned_ndjson()
    validate_versioned_dataset()
    profile_versioned_dataset()
    diff_version_publish()


job_definition = versioned_ndjson_job
