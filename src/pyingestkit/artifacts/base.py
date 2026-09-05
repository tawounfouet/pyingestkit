from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from uuid import UUID

from pyingestkit.core.exceptions import StorageError
from pyingestkit.provenance.hashing import sha256_bytes

from .raw import RawArtifact
from .uri import ArtifactURI


class ArtifactStore(ABC):
    """Run-artifact persistence contract.

    V0.6 separates a durable storage URI from the local materialization path.
    Existing third-party stores remain source-compatible because URI/read/materialize
    methods have conservative local-file defaults rather than new abstract methods.
    """

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

    def uri_for(self, job_id: str, run_id: UUID, relative_path: str) -> ArtifactURI:
        """Return the canonical storage URI for an artifact path.

        V0.5-compatible stores automatically get a ``file://`` implementation.
        Remote stores override this without changing callers.
        """

        return ArtifactURI.from_path(self.path_for(job_id, run_id, relative_path))

    def read_bytes(self, uri: ArtifactURI | str) -> bytes:
        """Read persisted bytes by canonical URI.

        The default implementation intentionally supports local ``file://`` only.
        Remote backends opt in by overriding this method.
        """

        location = uri if isinstance(uri, ArtifactURI) else ArtifactURI(uri)
        if not location.is_local:
            raise StorageError(
                f"Artifact store cannot read remote URI scheme {location.scheme!r}"
            )
        path = location.as_path()
        try:
            return path.read_bytes()
        except OSError as exc:
            raise StorageError(f"Unable to read artifact URI {location}") from exc

    def materialize_raw(self, artifact: RawArtifact) -> Path:
        """Ensure RAW is present at its local materialization path and verify SHA-256."""

        local_path = artifact.local_path
        if local_path.is_file():
            try:
                data = local_path.read_bytes()
            except OSError as exc:
                raise StorageError(f"Unable to read RAW materialization {local_path}") from exc
        else:
            data = self.read_bytes(artifact.location_uri)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            temp = local_path.with_name(f".{local_path.name}.materializing")
            try:
                temp.write_bytes(data)
                temp.replace(local_path)
            except OSError as exc:
                temp.unlink(missing_ok=True)
                raise StorageError(f"Unable to materialize RAW artifact at {local_path}") from exc

        actual = sha256_bytes(data)
        if actual != artifact.sha256:
            raise StorageError(
                "RAW materialization SHA-256 mismatch: "
                f"expected {artifact.sha256}, got {actual}"
            )
        return local_path
