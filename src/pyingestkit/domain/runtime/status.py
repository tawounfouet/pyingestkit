"""Typed PyIngestKit V2 execution status values."""

from __future__ import annotations

from enum import StrEnum


class IngestionStatus(StrEnum):
    """Lifecycle state for one semantic ingestion execution."""

    CREATED = "created"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    UNKNOWN_OUTCOME = "unknown_outcome"
    REQUIRES_RECONCILIATION = "requires_reconciliation"
    PARTIAL = "partial"

    @property
    def terminal(self) -> bool:
        return self in {
            IngestionStatus.SUCCEEDED,
            IngestionStatus.FAILED,
            IngestionStatus.CANCELLED,
            IngestionStatus.TIMED_OUT,
            IngestionStatus.UNKNOWN_OUTCOME,
            IngestionStatus.REQUIRES_RECONCILIATION,
            IngestionStatus.PARTIAL,
        }
