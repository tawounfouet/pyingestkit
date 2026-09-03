from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pyingestkit.core.exceptions import StorageError
from pyingestkit.provenance.hashing import sha256_bytes

from .base import ArtifactStore
from .raw import RawArtifact

logger = logging.getLogger(__name__)

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
        resolved_url: str | None = None,
        status_code: int | None = None,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> RawArtifact:
        self.prepare_run(job_id, run_id)
        digest = sha256_bytes(data)
        path = self.path_for(job_id, run_id, f"raw/{_safe(name)}")
        try:
            with path.open("xb") as handle:
                handle.write(data)
        except FileExistsError as exc:
            raise StorageError(
                f"RAW artifacts are immutable: refusing to overwrite existing path {path}"
            ) from exc
        logger.debug("RAW artifact written path=%s bytes=%d sha256=%s", path, len(data), digest)
        return RawArtifact(
            artifact_id=str(uuid4()),
            source_uri=source_uri,
            retrieved_at=datetime.now(UTC),
            content_type=content_type,
            size_bytes=len(data),
            sha256=digest,
            path=str(path),
            resolved_url=resolved_url,
            status_code=status_code,
            etag=etag,
            last_modified=last_modified,
        )

    def write_json(self, job_id: str, run_id: UUID, relative_path: str, payload: Any) -> Path:
        path = self.path_for(job_id, run_id, relative_path)
        temp = path.with_name(f".{path.name}.tmp")
        temp.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
        )
        temp.replace(path)
        logger.debug("JSON artifact written path=%s", path)
        return path
