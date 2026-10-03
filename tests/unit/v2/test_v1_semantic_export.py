from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pyingestkit.metadata.models import (
    ArtifactRecord,
    DatasetVersionRecord,
    PublishedDatasetRecord,
    ReplayRecord,
)
from pyingestkit.migration.v2 import V1SemanticExport, V1SemanticImporter


def test_v1_semantic_export_sanitizes_locator_secrets_before_bytes() -> None:
    run_id = str(uuid4())
    created_at = datetime(2026, 10, 3, 12, 30, tzinfo=UTC)
    artifact = ArtifactRecord(
        artifact_id="raw-1",
        run_id=run_id,
        kind="raw",
        path="/tmp/raw.csv",
        source_uri=(
            "https://user:password-secret@api.example.test/data.csv?token=query-secret&page=2"
        ),
        content_type="text/csv",
        size_bytes=12,
        sha256="a" * 64,
        created_at=created_at,
        resolved_url=("https://api.example.test/final.csv?x-amz-signature=redirect-secret&page=3"),
        status_code=200,
        etag='"v1"',
        last_modified="Wed, 02 Sep 2026 10:00:00 GMT",
        storage_uri="s3://bucket/runs/raw.csv",
    )

    export = V1SemanticExport.from_public_records(
        source_version="1.0.1",
        artifacts=(artifact,),
    )
    encoded = export.to_bytes()

    assert b"password-secret" not in encoded
    assert b"query-secret" not in encoded
    assert b"redirect-secret" not in encoded
    assert b"user:" not in encoded
    assert export.artifacts[0].source_uri == "https://api.example.test/data.csv?page=2"
    assert export.artifacts[0].resolved_url == ("https://api.example.test/final.csv?page=3")
    assert V1SemanticExport.from_bytes(encoded).to_bytes() == encoded


def test_v1_semantic_import_preserves_identity_without_promoting_source_url() -> None:
    run_id = str(uuid4())
    created_at = datetime(2026, 10, 3, 12, 30, tzinfo=UTC)
    version_id = "sha256-" + "b" * 64
    export = V1SemanticExport.from_public_records(
        source_version="1.0.1",
        artifacts=(
            ArtifactRecord(
                artifact_id="raw-1",
                run_id=run_id,
                kind="raw",
                path="/tmp/raw.csv",
                source_uri="https://api.example.test/data.csv?page=2",
                content_type="text/csv",
                size_bytes=12,
                sha256="a" * 64,
                created_at=created_at,
                storage_uri="s3://bucket/runs/raw.csv",
            ),
        ),
        dataset_versions=(
            DatasetVersionRecord(
                dataset_id="customer360.customers",
                version_id=version_id,
                fingerprint=version_id,
                snapshot_uri="s3://bucket/versions/customers/snapshot.json",
                created_from_run_id=run_id,
                job_id="demo.versioned",
                job_version="1.0.1",
                source_artifact_id="raw-1",
                source_raw_sha256="a" * 64,
                created_at=created_at,
            ),
        ),
        publications=(
            PublishedDatasetRecord(
                dataset_id="customer360.customers",
                version_id=version_id,
                published_from_run_id=run_id,
                published_at=created_at,
            ),
        ),
        replays=(
            ReplayRecord(
                run_id=str(uuid4()),
                source_run_id=run_id,
                source_job_id="demo.versioned",
                source_job_version="1.0.1",
                executed_job_version="1.0.1",
                verification_mode="strict",
                expected_fingerprint=version_id,
                actual_fingerprint=version_id,
                status="SUCCEEDED",
                created_at=created_at,
            ),
        ),
    )

    result = V1SemanticImporter().import_export(export)

    assert result.artifacts[0].artifact_id == "raw-1"
    assert result.artifacts[0].resource.locator == "s3://bucket/runs/raw.csv"
    assert "api.example.test" not in repr(result.artifacts[0])
    assert result.dataset_versions[0].identity == (
        "customer360.customers",
        version_id,
    )
    assert result.publications[0].version == result.dataset_versions[0]
    assert result.replays[0].source_run_id == run_id
    assert any(item.code == "artifact.source_locator.not_promoted" for item in result.report.issues)
    assert any(
        item.code == "replay.request.requires_definition_and_raw" for item in result.report.issues
    )
