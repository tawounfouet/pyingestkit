from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from pyingestkit.artifacts.raw import RawArtifact
from pyingestkit.core.context import RunContext
from pyingestkit.core.exceptions import ReplayIntegrityError, StorageError
from pyingestkit.provenance.hashing import sha256_bytes

from .models import ReplayRawArtifact


def _historical_raw_bytes(context: RunContext, origin: ReplayRawArtifact) -> bytes:
    if origin.origin_storage_uri is not None:
        try:
            return context.artifact_store.read_bytes(origin.origin_storage_uri)
        except (StorageError, ValueError) as exc:
            raise ReplayIntegrityError(
                f"Historical RAW is not readable from {origin.origin_storage_uri}"
            ) from exc
    try:
        return Path(origin.origin_path).read_bytes()
    except OSError as exc:
        raise ReplayIntegrityError(f"Historical RAW is not readable: {origin.origin_path}") from exc


def materialize_replayed_raw(
    context: RunContext,
    origin: ReplayRawArtifact,
    *,
    name: str,
) -> RawArtifact:
    data = _historical_raw_bytes(context, origin)
    actual = sha256_bytes(data)
    if actual != origin.sha256:
        raise ReplayIntegrityError(
            f"Historical RAW SHA-256 mismatch for {origin.origin_artifact_id}: "
            f"expected {origin.sha256}, got {actual}"
        )
    artifact = context.artifact_store.write_raw(
        context.job_id,
        context.run_id,
        name=name,
        data=data,
        source_uri=origin.source_uri,
        content_type=origin.content_type,
        resolved_url=origin.resolved_url,
        status_code=origin.status_code,
        etag=origin.etag,
        last_modified=origin.last_modified,
    )
    if artifact.sha256 != origin.sha256:
        raise ReplayIntegrityError(
            f"Materialized replay RAW SHA-256 mismatch: expected {origin.sha256}, got {artifact.sha256}"
        )
    return replace(
        artifact,
        acquisition_mode="REPLAY",
        origin_run_id=origin.origin_run_id,
        origin_artifact_id=origin.origin_artifact_id,
        origin_retrieved_at=origin.origin_retrieved_at,
    )
