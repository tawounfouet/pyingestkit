from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from .runner import Runner as Runner

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


def __getattr__(name: str) -> object:
    if name == "Runner":
        from .runner import Runner

        return Runner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
