from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pyingestkit.provenance.hashing import sha256_bytes

from .base import ArtifactStore
from .raw import RawArtifact

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe(value: str) -> str:
    cleaned = _SAFE.sub("_", value).strip("._")
    return cleaned or "unnamed"


class LocalArtifactStore(ArtifactStore):
    def __init__(self, root: str | Path = ".pyingest") -> None:
        self.root = Path(root)

    def _job_parts(self, job_id: str) -> tuple[str, ...]:
        return tuple(_safe(part) for part in job_id.split("."))

    def run_root(self, job_id: str, run_id: UUID) -> Path:
        return self.root / "runs" / Path(*self._job_parts(job_id)) / str(run_id)

    def prepare_run(self, job_id: str, run_id: UUID) -> Path:
        run_root = self.run_root(job_id, run_id)
        for name in ("raw", "staging", "candidate", "reports"):
            (run_root / name).mkdir(parents=True, exist_ok=True)
        return run_root

    def path_for(self, job_id: str, run_id: UUID, relative_path: str) -> Path:
        path = self.run_root(job_id, run_id) / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def write_raw(
        self,
        job_id: str,
        run_id: UUID,
        *,
        name: str,
        data: bytes,
        source_uri: str,
        content_type: str | None = None,
    ) -> RawArtifact:
        self.prepare_run(job_id, run_id)
        digest = sha256_bytes(data)
        path = self.path_for(job_id, run_id, f"raw/{_safe(name)}")
        path.write_bytes(data)
        return RawArtifact(
            artifact_id=str(uuid4()),
            source_uri=source_uri,
            retrieved_at=datetime.now(timezone.utc),
            content_type=content_type,
            size_bytes=len(data),
            sha256=digest,
            path=str(path),
        )

    def write_json(self, job_id: str, run_id: UUID, relative_path: str, payload: Any) -> Path:
        path = self.path_for(job_id, run_id, relative_path)
        temp = path.with_name(f".{path.name}.tmp")
        temp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
        temp.replace(path)
        return path
