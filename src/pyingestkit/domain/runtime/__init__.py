"""Portable runtime identity and evidence contracts."""

from pyingestkit.domain.runtime.context import CorrelationContext
from pyingestkit.domain.runtime.diagnostics import (
    Diagnostic,
    DiagnosticSeverity,
)
from pyingestkit.domain.runtime.execution import IngestionResult, IngestionRun
from pyingestkit.domain.runtime.failure import (
    FailureCategory,
    FailureEvidence,
    OutcomeUncertainty,
    Retryability,
)
from pyingestkit.domain.runtime.idempotency import IdempotencyReference
from pyingestkit.domain.runtime.references import IngestionExecutionReference
from pyingestkit.domain.runtime.status import IngestionStatus
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
    "IngestionStatus",
    "OutcomeUncertainty",
    "Retryability",
]
