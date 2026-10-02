"""Portable execution-correlation context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from pyingestkit.domain.shared import CorrelationId
from pyingestkit.domain.shared.validation import (
    validate_contract_version,
    validate_optional_text,
)


@dataclass(frozen=True, slots=True)
class CorrelationContext:
    """Portable cross-boundary correlation metadata."""

    CONTRACT_ID: ClassVar[str] = "pykit.correlation_context"

    correlation_id: CorrelationId = field(default_factory=CorrelationId.new)
    causation_id: str | None = None
    parent_execution_id: str | None = None
    workflow_run_id: str | None = None
    task_run_id: str | None = None
    task_attempt_id: str | None = None
    ingestion_run_id: str | None = None
    transformation_execution_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    contract_version: str = "1"

    def __post_init__(self) -> None:
        if not isinstance(self.correlation_id, CorrelationId):
            raise TypeError("correlation_id must be a CorrelationId.")
        for name, value in (
            ("causation_id", self.causation_id),
            ("parent_execution_id", self.parent_execution_id),
            ("workflow_run_id", self.workflow_run_id),
            ("task_run_id", self.task_run_id),
            ("task_attempt_id", self.task_attempt_id),
            ("ingestion_run_id", self.ingestion_run_id),
            ("transformation_execution_id", self.transformation_execution_id),
            ("trace_id", self.trace_id),
            ("span_id", self.span_id),
        ):
            validate_optional_text(value, name)
        validate_contract_version(self.contract_version)

    @property
    def portable(self) -> bool:
        return True

    def with_trace(
        self,
        *,
        trace_id: str,
        span_id: str | None = None,
    ) -> CorrelationContext:
        """Return a copy carrying explicit trace context."""
        return CorrelationContext(
            correlation_id=self.correlation_id,
            causation_id=self.causation_id,
            parent_execution_id=self.parent_execution_id,
            workflow_run_id=self.workflow_run_id,
            task_run_id=self.task_run_id,
            task_attempt_id=self.task_attempt_id,
            ingestion_run_id=self.ingestion_run_id,
            transformation_execution_id=self.transformation_execution_id,
            trace_id=trace_id,
            span_id=span_id,
            contract_version=self.contract_version,
        )
