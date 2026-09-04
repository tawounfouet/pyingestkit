from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pyingestkit.core.exceptions import ReplayError
from pyingestkit.core.result import RunResult

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_name(value: str) -> str:
    cleaned = _SAFE.sub("_", value).strip("._")
    return cleaned or "unnamed"


@dataclass(frozen=True, slots=True)
class ReplayRawArtifact:
    origin_run_id: str
    origin_artifact_id: str
    artifact_name: str
    origin_path: str
    source_uri: str
    content_type: str | None
    sha256: str
    origin_retrieved_at: datetime
    resolved_url: str | None = None
    status_code: int | None = None
    etag: str | None = None
    last_modified: str | None = None

    @classmethod
    def from_record(cls, record: Any) -> ReplayRawArtifact:
        return cls(
            origin_run_id=str(record.run_id),
            origin_artifact_id=str(record.artifact_id),
            artifact_name=Path(str(record.path)).name,
            origin_path=str(record.path),
            source_uri=str(record.source_uri),
            content_type=record.content_type,
            sha256=str(record.sha256),
            origin_retrieved_at=record.retrieved_at,
            resolved_url=record.resolved_url,
            status_code=record.status_code,
            etag=record.etag,
            last_modified=record.last_modified,
        )


@dataclass(frozen=True, slots=True)
class ReplayContext:
    source_run_id: str
    source_job_id: str
    source_job_version: str
    raw_artifacts: tuple[ReplayRawArtifact, ...]
    verification_mode: str
    verify_expected_fingerprint: str | None = None
    strict: bool = True

    def resolve_raw(self, artifact_name: str, source_uri: str) -> ReplayRawArtifact:
        safe_name = _safe_name(artifact_name)
        matches = [
            item
            for item in self.raw_artifacts
            if item.artifact_name == safe_name and item.source_uri == source_uri
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ReplayError(
                f"Replay RAW match is ambiguous for name={safe_name!r} source_uri={source_uri!r}"
            )
        if self.strict:
            raise ReplayError(
                f"Replay RAW not found for name={safe_name!r} source_uri={source_uri!r}; live fallback is disabled"
            )
        raise ReplayError("Non-strict live fallback is not implemented in V0.4")

    def as_manifest_dict(self, *, executed_job_version: str) -> dict[str, object]:
        return {
            "source_run_id": self.source_run_id,
            "source_job_id": self.source_job_id,
            "source_job_version": self.source_job_version,
            "executed_job_version": executed_job_version,
            "verification_mode": self.verification_mode,
            "expected_fingerprint": self.verify_expected_fingerprint,
            "actual_fingerprint": None,
            "matched": None,
        }


@dataclass(frozen=True, slots=True)
class ReplayResult:
    run: RunResult
    source_run_id: str
    source_job_version: str
    executed_job_version: str
    verification_mode: str
    expected_fingerprint: str | None
    actual_fingerprint: str | None
    matched: bool | None

    @property
    def succeeded(self) -> bool:
        return self.run.succeeded and self.matched is not False
