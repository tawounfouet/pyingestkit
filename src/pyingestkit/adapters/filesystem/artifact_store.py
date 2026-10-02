"""Create-once local ArtifactStore for the V2 reference profile."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname
from uuid import uuid4

from pyingestkit.domain.artifacts import (
    ArtifactIntegrityError,
    ArtifactKind,
    ArtifactPutStatus,
    ArtifactReference,
    PutArtifactRequest,
    PutArtifactResult,
    RawArtifactEvidence,
)
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import (
    Diagnostic,
    DiagnosticSeverity,
    FailureCategory,
    FailureEvidence,
    OutcomeUncertainty,
    Retryability,
)
from pyingestkit.ports.artifacts import ArtifactReader


@dataclass(frozen=True, slots=True)
class FileArtifactReader:
    """Reader that verifies durable file bytes against ArtifactReference evidence."""

    reference: ArtifactReference
    path: Path

    def read(self) -> bytes:
        if self.path.is_symlink():
            raise ArtifactIntegrityError("Artifact path must not be a symbolic link.")
        try:
            data = self.path.read_bytes()
        except OSError as exc:
            raise ArtifactIntegrityError("Unable to read durable artifact bytes.") from exc

        if self.reference.checksum_algorithm != "sha256" or self.reference.checksum is None:
            raise ArtifactIntegrityError("FileArtifactReader requires SHA-256 reference evidence.")
        actual = hashlib.sha256(data).hexdigest()
        if actual != self.reference.checksum:
            raise ArtifactIntegrityError(
                "Artifact SHA-256 mismatch: durable bytes no longer match the reference."
            )
        if self.reference.size_bytes is not None and self.reference.size_bytes != len(data):
            raise ArtifactIntegrityError(
                "Artifact size mismatch: durable bytes no longer match the reference."
            )
        return data


class FileArtifactStore:
    """Filesystem ArtifactStore with atomic create-only artifact publication.

    Construction performs no filesystem I/O. A successful put writes exact bytes
    to a temporary file, fsyncs them, then creates the final immutable path using
    a hard link so an existing artifact is never overwritten.
    """

    def __init__(self, *, root: str | Path) -> None:
        self._root = Path(root)

    @property
    def root(self) -> Path:
        return self._root

    def put(self, request: PutArtifactRequest) -> PutArtifactResult:
        if not isinstance(request, PutArtifactRequest):
            raise TypeError("FileArtifactStore.put expects PutArtifactRequest.")

        digest = hashlib.sha256(request.content).hexdigest()
        if (
            request.expected_checksum_algorithm is not None
            and request.expected_checksum != digest
        ):
            return self._failed(
                request,
                status=ArtifactPutStatus.FAILED,
                code="artifact.integrity.source_checksum_mismatch",
                category=FailureCategory.INTEGRITY,
                retryability=Retryability.NON_RETRYABLE,
                summary="Acquired bytes do not match the expected SHA-256 checksum.",
            )

        path = self._path_for(request)
        try:
            self._write_create_once(path, request.content)
        except FileExistsError:
            return self._failed(
                request,
                status=ArtifactPutStatus.CONFLICT,
                code="artifact.file.immutable_conflict",
                category=FailureCategory.CONFLICT,
                retryability=Retryability.NON_RETRYABLE,
                summary="Artifact path already exists; immutable artifact was not overwritten.",
            )
        except OSError:
            return self._failed(
                request,
                status=ArtifactPutStatus.FAILED,
                code="artifact.file.write_failed",
                category=FailureCategory.EXTERNAL_PROVIDER,
                retryability=Retryability.UNKNOWN,
                summary="Artifact persistence failed during filesystem I/O.",
            )

        persisted_at = datetime.now(UTC)
        resolved = path.resolve(strict=True)
        uri = resolved.as_uri()
        resource = ResourceReference(
            namespace="pyingestkit.artifact.file",
            resource_id=_resource_id(uri),
            locator=uri,
            media_type=request.media_type,
            format=resolved.suffix.lstrip(".").lower() or None,
        )
        reference = ArtifactReference(
            artifact_id=_artifact_id(request, digest),
            kind=request.kind.value,
            resource=resource,
            checksum=digest,
            checksum_algorithm="sha256",
            media_type=request.media_type,
            size_bytes=len(request.content),
            created_at=persisted_at,
            metadata=request.metadata,
        )
        raw_evidence = None
        if request.kind is ArtifactKind.RAW:
            if request.source_resource is None or request.source_acquired_at is None:
                raise AssertionError("RAW request invariants were not preserved.")
            raw_evidence = RawArtifactEvidence(
                reference=reference,
                source_resource=request.source_resource,
                ingestion_run_id=request.ingestion_run_id,
                acquired_at=request.source_acquired_at,
                persisted_at=persisted_at,
                retention=request.retention,
                manifest_artifact_id=request.manifest_artifact_id,
            )

        diagnostic = Diagnostic(
            code="artifact.file.persisted",
            severity=DiagnosticSeverity.INFO,
            summary="Artifact bytes were durably persisted.",
            stage="persist_raw" if request.kind is ArtifactKind.RAW else "persist_artifact",
            target_context="file-artifact-store",
            details=(
                ("artifact_id", reference.artifact_id),
                ("checksum_algorithm", "sha256"),
                ("size_bytes", str(len(request.content))),
            ),
            ingestion_run_id=request.ingestion_run_id,
            correlation_id=request.correlation.correlation_id,
        )
        return PutArtifactResult(
            status=ArtifactPutStatus.SUCCEEDED,
            ingestion_run_id=request.ingestion_run_id,
            correlation=request.correlation,
            kind=request.kind,
            persisted_at=persisted_at,
            reference=reference,
            raw_evidence=raw_evidence,
            diagnostics=(diagnostic,),
        )

    def open(self, reference: ArtifactReference) -> ArtifactReader:
        if not isinstance(reference, ArtifactReference):
            raise TypeError("FileArtifactStore.open expects ArtifactReference.")
        path = self._path_from_reference(reference)
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError("ArtifactReference does not resolve to a regular stored file.")
        return FileArtifactReader(reference=reference, path=path)

    def exists(self, reference: ArtifactReference) -> bool:
        if not isinstance(reference, ArtifactReference):
            raise TypeError("FileArtifactStore.exists expects ArtifactReference.")
        path = self._path_from_reference(reference)
        return path.is_file() and not path.is_symlink()

    def _path_for(self, request: PutArtifactRequest) -> Path:
        return (
            self._root
            / "runs"
            / str(request.ingestion_run_id)
            / request.kind.value
            / request.name
        )

    def _write_create_once(self, path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.parent / f".{path.name}.{uuid4().hex}.tmp"
        try:
            with temporary.open("xb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.link(temporary, path)
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    def _path_from_reference(self, reference: ArtifactReference) -> Path:
        locator = reference.resource.locator
        if locator is None:
            raise ValueError("FileArtifactStore requires ArtifactReference resource locator.")
        if reference.resource.namespace != "pyingestkit.artifact.file":
            raise ValueError("ArtifactReference is not owned by FileArtifactStore.")

        parsed = urlsplit(locator)
        if parsed.scheme != "file":
            raise ValueError("FileArtifactStore only opens file:// ArtifactReference values.")
        if parsed.netloc not in {"", "localhost"}:
            raise ValueError("FileArtifactStore does not accept remote file authorities.")

        raw_path = url2pathname(unquote(parsed.path))
        candidate = Path(raw_path).resolve(strict=False)
        root = self._root.resolve(strict=False)
        if not candidate.is_relative_to(root):
            raise ValueError("ArtifactReference resolves outside FileArtifactStore root.")
        if reference.resource.resource_id != _resource_id(locator):
            raise ValueError("ArtifactReference resource identity does not match its locator.")
        if reference.checksum_algorithm != "sha256" or reference.checksum is None:
            raise ValueError("FileArtifactStore requires SHA-256 ArtifactReference evidence.")
        return candidate

    def _failed(
        self,
        request: PutArtifactRequest,
        *,
        status: ArtifactPutStatus,
        code: str,
        category: FailureCategory,
        retryability: Retryability,
        summary: str,
    ) -> PutArtifactResult:
        failure = FailureEvidence(
            error_code=code,
            category=category,
            retryability=retryability,
            uncertainty=OutcomeUncertainty.KNOWN,
            ingestion_run_id=request.ingestion_run_id,
            correlation_id=request.correlation.correlation_id,
            source_component="FileArtifactStore",
            message_summary=summary,
        )
        diagnostic = Diagnostic(
            code=code,
            severity=DiagnosticSeverity.ERROR,
            summary=summary,
            stage="persist_raw" if request.kind is ArtifactKind.RAW else "persist_artifact",
            target_context="file-artifact-store",
            ingestion_run_id=request.ingestion_run_id,
            correlation_id=request.correlation.correlation_id,
        )
        return PutArtifactResult(
            status=status,
            ingestion_run_id=request.ingestion_run_id,
            correlation=request.correlation,
            kind=request.kind,
            diagnostics=(diagnostic,),
            failure=failure,
        )


def _artifact_id(request: PutArtifactRequest, checksum: str) -> str:
    material = (
        f"{request.ingestion_run_id}\x00{request.kind.value}\x00"
        f"{request.name}\x00{checksum}"
    ).encode("utf-8")
    return f"{request.kind.value}_{hashlib.sha256(material).hexdigest()}"


def _resource_id(uri: str) -> str:
    return f"file_{hashlib.sha256(uri.encode('utf-8')).hexdigest()}"
