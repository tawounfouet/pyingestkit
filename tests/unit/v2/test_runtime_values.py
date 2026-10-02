from __future__ import annotations

from datetime import UTC, datetime

import pytest

from pyingestkit.domain.datasets import DatasetVersionReference
from pyingestkit.domain.runtime import (
    CorrelationContext,
    Diagnostic,
    DiagnosticSeverity,
    FailureCategory,
    FailureEvidence,
    IdempotencyReference,
    IngestionExecutionReference,
    IngestionStatus,
    OutcomeUncertainty,
    Retryability,
)
from pyingestkit.domain.shared import CorrelationId, IngestionRunId


def test_correlation_context_does_not_replace_native_run_identity() -> None:
    run_id = IngestionRunId.new()
    correlation_id = CorrelationId.new()
    context = CorrelationContext(
        correlation_id=correlation_id,
        ingestion_run_id=str(run_id),
    )

    assert context.correlation_id == correlation_id
    assert context.ingestion_run_id == str(run_id)
    assert str(run_id) != str(correlation_id)


def test_correlation_context_with_trace_preserves_correlation() -> None:
    context = CorrelationContext(causation_id="task-run-1")

    traced = context.with_trace(trace_id="trace-1", span_id="span-1")

    assert traced is not context
    assert traced.correlation_id == context.correlation_id
    assert traced.causation_id == "task-run-1"
    assert traced.trace_id == "trace-1"
    assert traced.span_id == "span-1"


def test_ingestion_status_preserves_uncertain_terminal_state() -> None:
    assert IngestionStatus.UNKNOWN_OUTCOME.terminal is True
    assert IngestionStatus.REQUIRES_RECONCILIATION.terminal is True
    assert IngestionStatus.RUNNING.terminal is False


def test_failure_evidence_preserves_unknown_outcome() -> None:
    evidence = FailureEvidence(
        error_code="publication.unknown_outcome",
        category=FailureCategory.UNKNOWN_OUTCOME,
        retryability=Retryability.RETRYABLE_AFTER_RECONCILIATION,
        uncertainty=OutcomeUncertainty.REQUIRES_RECONCILIATION,
        ingestion_run_id=IngestionRunId.new(),
        correlation_id=CorrelationId.new(),
        occurred_at=datetime(2026, 10, 2, tzinfo=UTC),
    )

    assert evidence.category is FailureCategory.UNKNOWN_OUTCOME
    assert evidence.uncertainty is OutcomeUncertainty.REQUIRES_RECONCILIATION


def test_failure_evidence_rejects_known_unknown_outcome() -> None:
    with pytest.raises(ValueError):
        FailureEvidence(
            error_code="publication.unknown_outcome",
            category=FailureCategory.UNKNOWN_OUTCOME,
            retryability=Retryability.UNKNOWN,
            uncertainty=OutcomeUncertainty.KNOWN,
            ingestion_run_id=IngestionRunId.new(),
            correlation_id=CorrelationId.new(),
        )


def test_diagnostic_is_structured_and_credential_safe() -> None:
    diagnostic = Diagnostic(
        code="decode.header_normalized",
        severity=DiagnosticSeverity.INFO,
        summary="Header names were normalized.",
        stage="decode",
        details=(("decoder", "csv"),),
    )

    assert diagnostic.portable is True
    assert diagnostic.stage == "decode"

    with pytest.raises(ValueError):
        Diagnostic(
            code="unsafe",
            severity=DiagnosticSeverity.ERROR,
            summary="unsafe",
            details=(("api_token", "secret"),),
        )


def test_idempotency_reference_requires_explicit_scope() -> None:
    key = IdempotencyReference(
        namespace="pyingestkit.publication",
        key="customers-2026-10-02",
        scope="customers-publication",
    )

    assert key.scope == "customers-publication"
    assert key.owner == "pyingestkit"


def test_execution_reference_requires_terminal_status_when_present() -> None:
    with pytest.raises(ValueError):
        IngestionExecutionReference(
            ingestion_run_id=IngestionRunId.new(),
            status=IngestionStatus.RUNNING,
        )


def test_execution_reference_can_carry_dataset_version() -> None:
    version = DatasetVersionReference(dataset_id="customers", version_id="v7")
    reference = IngestionExecutionReference(
        ingestion_run_id=IngestionRunId.new(),
        ingestion_definition_id="customers",
        output_dataset_version=version,
        status=IngestionStatus.SUCCEEDED,
    )

    assert reference.output_dataset_version is version
    assert reference.CONTRACT_ID == "pykit.ingestion_execution_reference"
