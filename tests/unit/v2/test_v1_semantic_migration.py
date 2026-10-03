from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from pyingestkit.config import PyIngestKitConfig
from pyingestkit.domain.targets import TargetLoadModeV2
from pyingestkit.metadata.models import (
    ArtifactRecord,
    DatasetVersionRecord,
    PublishedDatasetRecord,
)
from pyingestkit.migration import (
    MigrationDispositionV2,
    assess_v1_plugin_entry_point,
    migrate_v1_artifact_record,
    migrate_v1_dataset_version_record,
    migrate_v1_postgres_target_config,
    migrate_v1_published_dataset_record,
    plan_v1_config_migration,
)


def test_local_v1_config_maps_supported_backends_and_postgres_target() -> None:
    config = PyIngestKitConfig.model_validate(
        {
            "runtime": {"workspace": ".legacy-workspace"},
            "targets": {
                "warehouse": {
                    "type": "postgres",
                    "target_id": "postgres.warehouse",
                    "dsn_env": "WAREHOUSE_DSN",
                    "schema": "analytics",
                    "table": "customers",
                    "load_mode": "truncate_load",
                }
            },
        }
    )

    plan = plan_v1_config_migration(config)

    assert plan.can_materialize_supported_backends is True
    assert plan.blocked == ()
    assert plan.postgres_targets[0].target_id == "postgres.warehouse"
    assert plan.postgres_targets[0].dsn_env == "WAREHOUSE_DSN"
    assert plan.postgres_targets[0].mode is TargetLoadModeV2.TRUNCATE_LOAD
    assert plan.postgres_targets[0].environment_variables == ("WAREHOUSE_DSN",)
    assert any(
        item.subject == "artifacts"
        and item.disposition is MigrationDispositionV2.AUTOMATIC
        and item.target_contract == "FileArtifactStore + FileDatasetVersionStore"
        for item in plan.decisions
    )
    assert any(
        item.subject == "metadata"
        and item.disposition is MigrationDispositionV2.RETAINED_V1_ONLY
        for item in plan.decisions
    )


def test_s3_v1_config_keeps_only_environment_reference_not_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "PYINGEST_S3_ENDPOINT_URL",
        "https://user:actual-secret@example.invalid",
    )
    config = PyIngestKitConfig.model_validate(
        {
            "artifacts": {
                "backend": "s3",
                "s3": {
                    "bucket": "migration-bucket",
                    "prefix": "legacy",
                    "region_name": "eu-west-3",
                    "endpoint_url_env": "PYINGEST_S3_ENDPOINT_URL",
                },
            }
        }
    )

    plan = plan_v1_config_migration(config)
    artifact = next(item for item in plan.decisions if item.subject == "artifacts")
    rendered = repr(plan)

    assert artifact.disposition is MigrationDispositionV2.AUTOMATIC
    assert ("bucket", "migration-bucket") in artifact.metadata
    assert ("endpoint_url_env", "PYINGEST_S3_ENDPOINT_URL") in artifact.metadata
    assert "actual-secret" not in rendered
    assert "user:" not in rendered


def test_s3_v1_config_without_bucket_is_blocked() -> None:
    config = PyIngestKitConfig.model_validate({"artifacts": {"backend": "s3"}})

    plan = plan_v1_config_migration(config)

    assert plan.can_materialize_supported_backends is False
    assert len(plan.blocked) == 1
    assert plan.blocked[0].subject == "artifacts"


def test_fixture_mode_and_free_form_parameters_require_explicit_rewrite() -> None:
    config = PyIngestKitConfig.model_validate(
        {
            "runtime": {
                "fixture_mode": True,
                "parameters": {"source_path": "customers.csv"},
            }
        }
    )

    plan = plan_v1_config_migration(config)

    assert {item.subject for item in plan.rewrite_required} == {
        "runtime.fixture_mode",
        "runtime.parameters",
    }


def test_postgres_target_migration_preserves_secret_reference_not_value() -> None:
    config = PyIngestKitConfig.model_validate(
        {
            "targets": {
                "warehouse": {
                    "target_id": "warehouse",
                    "dsn_env": "WAREHOUSE_SECRET_DSN",
                    "table": "customers",
                    "load_mode": "replace",
                }
            }
        }
    )

    migrated = migrate_v1_postgres_target_config(config.targets["warehouse"])

    assert migrated.target_id == "warehouse"
    assert migrated.dsn_env == "WAREHOUSE_SECRET_DSN"
    assert migrated.mode is TargetLoadModeV2.REPLACE


def test_v1_plugin_assessment_never_claims_automatic_code_translation() -> None:
    assessment = assess_v1_plugin_entry_point(
        "demo-versioned-s3",
        "pyingestkit_demo_jobs.versioned_s3:job_definition",
    )

    assert assessment.disposition is MigrationDispositionV2.REWRITE_REQUIRED
    assert assessment.target_contract.startswith("IngestionDefinition")
    assert "auto-translate" in assessment.reason


def test_v1_artifact_record_migrates_identity_and_ignores_source_secret() -> None:
    created_at = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)
    record = ArtifactRecord(
        artifact_id="raw-1",
        run_id=str(uuid4()),
        kind="raw",
        path="/tmp/cache/raw.csv",
        source_uri="https://api.example.test/data.csv?token=must-not-survive",
        content_type="text/csv",
        size_bytes=12,
        sha256="a" * 64,
        created_at=created_at,
        storage_uri="s3://bucket/runs/raw.csv",
    )

    reference = migrate_v1_artifact_record(record)

    assert reference.artifact_id == "raw-1"
    assert reference.kind == "raw"
    assert reference.resource.locator == "s3://bucket/runs/raw.csv"
    assert reference.checksum == "a" * 64
    assert reference.checksum_algorithm == "sha256"
    assert "must-not-survive" not in repr(reference)
    assert "source_uri" not in repr(reference)


def test_v1_dataset_and_publication_records_migrate_to_v2_references() -> None:
    run_id = str(uuid4())
    created_at = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)
    version_record = DatasetVersionRecord(
        dataset_id="customer360.customers",
        version_id="sha256-" + "b" * 64,
        fingerprint="sha256-" + "b" * 64,
        snapshot_uri="s3://bucket/versions/customer360/customers/snapshot.json",
        created_from_run_id=run_id,
        job_id="demo.versioned",
        job_version="1.0.0",
        source_artifact_id="raw-1",
        source_raw_sha256="c" * 64,
        created_at=created_at,
    )
    publication_record = PublishedDatasetRecord(
        dataset_id=version_record.dataset_id,
        version_id=version_record.version_id,
        published_from_run_id=run_id,
        published_at=created_at,
    )

    version = migrate_v1_dataset_version_record(version_record)
    published = migrate_v1_published_dataset_record(
        publication_record,
        version=version,
    )

    assert version.identity == (
        "customer360.customers",
        "sha256-" + "b" * 64,
    )
    assert version.content_fingerprint == version_record.fingerprint
    assert version.locator is not None
    assert version.locator.locator == version_record.snapshot_uri
    assert published.version == version
    assert str(published.published_from_run_id) == run_id


def test_v1_publication_with_non_uuid_run_id_fails_closed() -> None:
    created_at = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)
    version_record = DatasetVersionRecord(
        dataset_id="demo.dataset",
        version_id="sha256-" + "d" * 64,
        fingerprint="sha256-" + "d" * 64,
        snapshot_uri="versions/demo/snapshot.json",
        created_from_run_id=str(uuid4()),
        job_id="demo",
        job_version="1.0.0",
        source_artifact_id=None,
        source_raw_sha256=None,
        created_at=created_at,
    )
    publication = PublishedDatasetRecord(
        dataset_id=version_record.dataset_id,
        version_id=version_record.version_id,
        published_from_run_id="legacy-non-uuid",
        published_at=created_at,
    )

    with pytest.raises(ValueError, match="must be a UUID"):
        migrate_v1_published_dataset_record(
            publication,
            version=migrate_v1_dataset_version_record(version_record),
        )
