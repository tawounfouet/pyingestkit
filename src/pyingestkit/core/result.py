from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class RunStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class StepResult:
    step_name: str
    status: RunStatus
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    output: Any = None
    error: str | None = None
    warnings: tuple[str, ...] = ()
    metrics: dict[str, int | float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RunResult:
    run_id: str
    job_id: str
    job_version: str
    status: RunStatus
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    steps: tuple[StepResult, ...] = ()
    error: str | None = None
    warnings: tuple[str, ...] = ()

    @property
    def succeeded(self) -> bool:
        return self.status is RunStatus.SUCCESS
