from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from uuid import UUID

from .raw import RawArtifact


class ArtifactStore(ABC):
    @abstractmethod
    def prepare_run(self, job_id: str, run_id: UUID) -> Path:
        raise NotImplementedError

    @abstractmethod
    def write_raw(
        self,
        job_id: str,
        run_id: UUID,
        *,
        name: str,
        data: bytes,
        source_uri: str,
        content_type: str | None = None,
        resolved_url: str | None = None,
        status_code: int | None = None,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> RawArtifact:
        raise NotImplementedError

    @abstractmethod
    def write_json(self, job_id: str, run_id: UUID, relative_path: str, payload: Any) -> Path:
        raise NotImplementedError

    @abstractmethod
    def path_for(self, job_id: str, run_id: UUID, relative_path: str) -> Path:
        raise NotImplementedError
