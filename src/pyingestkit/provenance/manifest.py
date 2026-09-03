from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from pyingestkit.artifacts.raw import RawArtifact
from pyingestkit.core.result import RunResult, StepResult


def _machine_value(value: Any) -> Any:
    """Normalize manifest values to stable machine-readable JSON primitives."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _machine_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_machine_value(item) for item in value]
    return value


def _step_value(step: StepResult) -> dict[str, Any]:
    """Serialize step lifecycle metadata without arbitrary runtime outputs."""
    return {
        "step_name": step.step_name,
        "status": step.status.value,
        "started_at": step.started_at.isoformat(),
        "completed_at": step.completed_at.isoformat(),
        "duration_seconds": step.duration_seconds,
        "error": step.error,
        "warnings": list(step.warnings),
        "metrics": dict(step.metrics),
    }


@dataclass(slots=True)
class RunManifest:
    run_id: str
    job_id: str
    job_version: str
    started_at: datetime
    completed_at: datetime | None = None
    status: str = "RUNNING"
    artifacts: list[RawArtifact] = field(default_factory=list)
    steps: list[StepResult] = field(default_factory=list)
    validations: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, int | float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    def add_artifact(self, artifact: RawArtifact) -> None:
        self.artifacts.append(artifact)

    def finalize(self, result: RunResult) -> None:
        self.completed_at = result.completed_at
        self.status = result.status.value
        self.steps = list(result.steps)
        self.warnings.extend(result.warnings)
        self.error = result.error

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "job_id": self.job_id,
            "job_version": self.job_version,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "artifacts": [_machine_value(asdict(artifact)) for artifact in self.artifacts],
            "steps": [_step_value(step) for step in self.steps],
            "validations": _machine_value(self.validations),
            "metrics": dict(self.metrics),
            "warnings": list(self.warnings),
            "error": self.error,
        }
