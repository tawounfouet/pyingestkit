from __future__ import annotations

from collections.abc import Iterable

from .job import Job


class JobRegistry:
    """Explicit registry of job definitions. No global runtime state."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def register(self, job: Job, *, replace: bool = False) -> None:
        job.validate_definition()
        if job.id in self._jobs and not replace:
            raise ValueError(f"Job already registered: {job.id}")
        self._jobs[job.id] = job

    def register_many(self, jobs: Iterable[Job], *, replace: bool = False) -> None:
        for job in jobs:
            self.register(job, replace=replace)

    def get(self, job_id: str) -> Job:
        try:
            return self._jobs[job_id]
        except KeyError as exc:
            raise KeyError(f"Unknown job: {job_id}") from exc

    def list(self) -> tuple[Job, ...]:
        return tuple(self._jobs[key] for key in sorted(self._jobs))

    def __len__(self) -> int:
        return len(self._jobs)
