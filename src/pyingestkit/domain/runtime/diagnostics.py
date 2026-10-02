"""Structured ingestion diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar

from pyingestkit.domain.shared import CorrelationId, IngestionRunId
from pyingestkit.domain.shared.validation import (
    require_non_blank,
    validate_contract_version,
    validate_metadata,
    validate_optional_text,
)


class DiagnosticSeverity(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """Structured evidence explaining one ingestion decision or anomaly."""

    CONTRACT_ID: ClassVar[str] = "pykit.diagnostic"

    code: str
    severity: DiagnosticSeverity
    summary: str
    stage: str | None = None
    source_context: str | None = None
    target_context: str | None = None
    related_rule: str | None = None
    related_field: str | None = None
    details: tuple[tuple[str, str], ...] = ()
    ingestion_run_id: IngestionRunId | None = None
    correlation_id: CorrelationId | None = None
    source_framework: str = "pyingestkit"
    contract_version: str = "1"

    def __post_init__(self) -> None:
        require_non_blank(self.code, "Diagnostic code")
        if not isinstance(self.severity, DiagnosticSeverity):
            raise TypeError("Diagnostic severity must be a DiagnosticSeverity.")
        require_non_blank(self.summary, "Diagnostic summary")

        for name, value in (
            ("stage", self.stage),
            ("source_context", self.source_context),
            ("target_context", self.target_context),
            ("related_rule", self.related_rule),
            ("related_field", self.related_field),
        ):
            validate_optional_text(value, f"Diagnostic {name}")

        validate_metadata(self.details, name="Diagnostic details")
        if self.ingestion_run_id is not None and not isinstance(
            self.ingestion_run_id,
            IngestionRunId,
        ):
            raise TypeError("Diagnostic ingestion_run_id must be an IngestionRunId.")
        if self.correlation_id is not None and not isinstance(
            self.correlation_id,
            CorrelationId,
        ):
            raise TypeError("Diagnostic correlation_id must be a CorrelationId.")
        require_non_blank(self.source_framework, "Diagnostic source_framework")
        validate_contract_version(self.contract_version)

    @property
    def portable(self) -> bool:
        return True
