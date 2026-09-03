from __future__ import annotations

import mimetypes
from pathlib import Path

from pyingestkit.artifacts.raw import RawArtifact
from pyingestkit.core.context import RunContext
from pyingestkit.core.exceptions import FetchError

from .base import Source


class LocalSource(Source):
    def __init__(self, path: str | Path, *, artifact_name: str | None = None) -> None:
        self.path = Path(path)
        self.artifact_name = artifact_name or self.path.name

    def fetch(self, context: RunContext) -> RawArtifact:
        if not self.path.exists() or not self.path.is_file():
            raise FetchError(f"Local source not found: {self.path}")
        data = self.path.read_bytes()
        content_type, _ = mimetypes.guess_type(self.path.name)
        return context.artifact_store.write_raw(
            context.job_id,
            context.run_id,
            name=self.artifact_name,
            data=data,
            source_uri=self.path.resolve().as_uri(),
            content_type=content_type,
        )
