from __future__ import annotations

from abc import ABC, abstractmethod

from .pipeline import Pipeline


class Job(ABC):
    """Identifiable ingestion unit. Scheduling is intentionally out of scope."""

    id: str
    version: str = "0.1.0"
    description: str = ""
    depends_on: tuple[str, ...] = ()
    requires_artifacts: str | None = None
    requires_metadata: str | None = None

    @abstractmethod
    def pipeline(self) -> Pipeline:
        raise NotImplementedError

    def validate_definition(self) -> None:
        if not self.id.strip():
            raise ValueError("Job.id must be a non-empty namespaced identifier")
        if "." not in self.id:
            raise ValueError("Job.id must be namespaced, e.g. 'public.postal_codes'")
        if not self.version.strip():
            raise ValueError("Job.version must be non-empty")
