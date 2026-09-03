from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from pyingestkit.artifacts.raw import RawArtifact
from pyingestkit.core.result import RunResult, StepResult


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
        return asdict(self)
