from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from pyingestkit.domain.datasets.publication import PublishedDataset
from pyingestkit.domain.datasets.references import DatasetVersionReference
from pyingestkit.domain.runtime import (
    CorrelationContext,
    FailureCategory,
    FailureEvidence,
    IngestionResult,
    IngestionRun,
    IngestionStatus,
    OutcomeUncertainty,
    Retryability,
)
from pyingestkit.domain.shared import IngestionRunId


def _run(
    status: IngestionStatus,
    *,
    started: bool = False,
    ended: bool = False,
) -> IngestionRun:
    run_id = IngestionRunId.new()
    created_at = datetime(2026, 10, 3, 8, 0, tzinfo=UTC)
    started_at = created_at + timedelta(seconds=1) if started else None
    ended_at = created_at + timedelta(seconds=2) if ended else None
    return IngestionRun(
        ingestion_run_id=run_id,
        ingestion_definition_name="demo.reference",
        definition_fingerprint="sha256:abc123",
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
        status=status,
        created_at=created_at,
        started_at=started_at,
        ended_at=ended_at,
    )


def _failure(run: IngestionRun) -> FailureEvidence:
    return FailureEvidence(
        error_code="ingestion.failed",
        category=FailureCategory.INTERNAL,
        retryability=Retryability.NON_RETRYABLE,
        uncertainty=OutcomeUncertainty.KNOWN,
        ingestion_run_id=run.ingestion_run_id,
        correlation_id=run.correlation.correlation_id,
        source_component="LOT-09-test",
    )


def test_created_run_has_no_execution_timestamps() -> None:
    run = _run(IngestionStatus.CREATED)

    assert run.terminal is False
    assert run.started_at is None
    assert run.ended_at is None


def test_running_run_requires_started_at() -> None:
    with pytest.raises(ValueError, match="RUNNING"):
        _run(IngestionStatus.RUNNING)


def test_terminal_run_requires_ended_at() -> None:
    with pytest.raises(ValueError, match="Terminal"):
        _run(IngestionStatus.SUCCEEDED, started=True)


def test_run_rejects_backwards_timestamps() -> None:
    run_id = IngestionRunId.new()
    created_at = datetime(2026, 10, 3, 8, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="started_at cannot precede"):
        IngestionRun(
            ingestion_run_id=run_id,
            ingestion_definition_name="demo.reference",
            definition_fingerprint="sha256:abc123",
            correlation=CorrelationContext(ingestion_run_id=str(run_id)),
            status=IngestionStatus.RUNNING,
            created_at=created_at,
            started_at=created_at - timedelta(seconds=1),
        )


def test_success_result_cannot_contain_failure() -> None:
    run = _run(IngestionStatus.SUCCEEDED, started=True, ended=True)

    with pytest.raises(ValueError, match="Successful"):
        IngestionResult(run=run, failure=_failure(run))


def test_failure_result_requires_matching_failure_evidence() -> None:
    run = _run(IngestionStatus.FAILED, started=True, ended=True)

    with pytest.raises(ValueError, match="requires FailureEvidence"):
        IngestionResult(run=run)


def test_published_output_must_match_dataset_version() -> None:
    run = _run(IngestionStatus.SUCCEEDED, started=True, ended=True)
    version = DatasetVersionReference(
        dataset_id="demo.reference",
        version_id="sha256-" + "a" * 64,
        schema_fingerprint="schema-a",
        content_fingerprint="sha256-" + "a" * 64,
    )
    other = DatasetVersionReference(
        dataset_id="demo.reference",
        version_id="sha256-" + "b" * 64,
        schema_fingerprint="schema-b",
        content_fingerprint="sha256-" + "b" * 64,
    )
    published = PublishedDataset(
        dataset_id="demo.reference",
        version=other,
        published_at=datetime(2026, 10, 3, 8, 5, tzinfo=UTC),
        published_from_run_id=run.ingestion_run_id,
    )

    with pytest.raises(ValueError, match="identity mismatch"):
        IngestionResult(
            run=run,
            dataset_version=version,
            published_dataset=published,
        )


def test_success_result_exposes_terminal_run_identity() -> None:
    run = _run(IngestionStatus.SUCCEEDED, started=True, ended=True)
    result = IngestionResult(run=run)

    assert result.succeeded is True
    assert result.status is IngestionStatus.SUCCEEDED
    assert result.ingestion_run_id == run.ingestion_run_id
