"""PyIngestKit 2.0 runtime API."""

from pyingestkit.application.runtime import IngestionRuntime
from pyingestkit.domain.runtime import (
    CorrelationContext,
    Diagnostic,
    DiagnosticSeverity,
    FailureCategory,
    FailureEvidence,
    IdempotencyReference,
    IngestionExecutionReference,
    IngestionResult,
    IngestionRun,
    IngestionStatus,
    OutcomeUncertainty,
    Retryability,
)
from pyingestkit.domain.shared import CorrelationId, IngestionRunId

__all__ = [
    "CorrelationContext",
    "CorrelationId",
    "Diagnostic",
    "DiagnosticSeverity",
    "FailureCategory",
    "FailureEvidence",
    "IdempotencyReference",
    "IngestionExecutionReference",
    "IngestionResult",
    "IngestionRun",
    "IngestionRunId",
    "IngestionRuntime",
    "IngestionStatus",
    "OutcomeUncertainty",
    "Retryability",
]
