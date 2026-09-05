from __future__ import annotations

import re
from pathlib import PurePosixPath
from uuid import UUID

from pyingestkit.core.exceptions import StorageError

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_component(value: str) -> str:
    cleaned = _SAFE.sub("_", value).strip("._")
    return cleaned or "unnamed"


def job_parts(job_id: str) -> tuple[str, ...]:
    return tuple(safe_component(part) for part in job_id.split("."))


def relative_artifact_path(value: str) -> PurePosixPath:
    if not value or "\\" in value:
        raise StorageError(f"Invalid artifact relative path: {value!r}")
    path = PurePosixPath(value)
    if not path.parts or path.is_absolute() or any(part == ".." for part in path.parts):
        raise StorageError(f"Artifact path must stay inside the run workspace: {value!r}")
    return path


def run_relative_key(job_id: str, run_id: UUID, relative_path: str) -> str:
    relative = relative_artifact_path(relative_path)
    return str(PurePosixPath("runs", *job_parts(job_id), str(run_id), *relative.parts))
