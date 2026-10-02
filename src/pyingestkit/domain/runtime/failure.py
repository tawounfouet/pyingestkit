"""Structured failure and uncertainty evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import ClassVar

from pyingestkit.domain.shared import CorrelationId, IngestionRunId
from pyingestkit.domain.shared.validation import (
    require_non_blank,
    validate_aware_datetime,
    validate_contract_version,
    validate_metadata,
    validate_optional_text,
)


class FailureCategory(StrEnum):
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    CAPABILITY = "capability"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    TRANSIENT = "transient"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    RATE_LIMITED = "rate_limited"
    INTEGRITY = "integrity"
    CONTRACT_VIOLATION = "contract_violation"
    SIDE_EFFECT_FAILED = "side_effect_failed"
    UNKNOWN_OUTCOME = "unknown_outcome"
    INTERNAL = "internal"
    EXTERNAL_PROVIDER = "external_provider"


class Retryability(StrEnum):
    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"
    UNKNOWN = "unknown"
    RETRYABLE_AFTER_RECONCILIATION = "retryable_after_reconciliation"


class OutcomeUncertainty(StrEnum):
    KNOWN = "known"
    UNKNOWN = "unknown"
    REQUIRES_RECONCILIATION = "requires_reconciliation"


@dataclass(frozen=True, slots=True)
class FailureEvidence:
    """Durable machine-readable evidence for one failed or uncertain ingestion."""

    CONTRACT_ID: ClassVar[str] = "pykit.failure_evidence"

    error_code: str
    category: FailureCategory
    retryability: Retryability
    uncertainty: OutcomeUncertainty
    ingestion_run_id: IngestionRunId
    correlation_id: CorrelationId
    source_framework: str = "pyingestkit"
    source_component: str | None = None
    provider_code: str | None = None
    message_summary: str | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    details: tuple[tuple[str, str], ...] = ()
    contract_version: str = "1"

    def __post_init__(self) -> None:
        require_non_blank(self.error_code, "FailureEvidence error_code")
        if not isinstance(self.category, FailureCategory):
            raise TypeError("FailureEvidence category must be a FailureCategory.")
        if not isinstance(self.retryability, Retryability):
            raise TypeError("FailureEvidence retryability must be a Retryability.")
        if not isinstance(self.uncertainty, OutcomeUncertainty):
            raise TypeError("FailureEvidence uncertainty must be an OutcomeUncertainty.")
        if not isinstance(self.ingestion_run_id, IngestionRunId):
            raise TypeError("FailureEvidence ingestion_run_id must be an IngestionRunId.")
        if not isinstance(self.correlation_id, CorrelationId):
            raise TypeError("FailureEvidence correlation_id must be a CorrelationId.")

        require_non_blank(self.source_framework, "FailureEvidence source_framework")
        validate_optional_text(
            self.source_component,
            "FailureEvidence source_component",
        )
        validate_optional_text(self.provider_code, "FailureEvidence provider_code")
        validate_optional_text(
            self.message_summary,
            "FailureEvidence message_summary",
        )
        validate_aware_datetime(self.occurred_at, "FailureEvidence occurred_at")
        validate_metadata(self.details, name="FailureEvidence details")
        validate_contract_version(self.contract_version)

        if (
            self.category is FailureCategory.UNKNOWN_OUTCOME
            and self.uncertainty is OutcomeUncertainty.KNOWN
        ):
            raise ValueError(
                "UNKNOWN_OUTCOME failure evidence cannot declare a known outcome."
            )

    @property
    def portable(self) -> bool:
        return True
