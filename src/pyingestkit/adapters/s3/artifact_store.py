"""S3-compatible ArtifactStore for PyIngestKit V2."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit

from pyingestkit.adapters.s3._objects import (
    S3ClientV2,
    S3ObjectIOV2,
    create_s3_client_v2,
    validate_s3_endpoint_v2,
)
from pyingestkit.domain.artifacts import (
    ArtifactIntegrityError,
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


@dataclass(frozen=True, slots=True)
class S3ArtifactReaderV2:
    """Reader that verifies S3 bytes against portable artifact evidence."""

    reference: ArtifactReference
    _objects: S3ObjectIOV2
    _key: str

    def read(self) -> bytes:
        try:
            content = self._objects.read(self._key)
        except (KeyError, RuntimeError, ValueError) as exc:
            raise ArtifactIntegrityError("Unable to read integrity-verified S3 artifact.") from exc

        if self.reference.checksum_algorithm != "sha256" or self.reference.checksum is None:
            raise ArtifactIntegrityError("S3 artifact reference requires SHA-256 evidence.")
        actual = hashlib.sha256(content).hexdigest()
        if actual != self.reference.checksum:
            raise ArtifactIntegrityError("S3 artifact bytes do not match reference SHA-256.")
        if self.reference.size_bytes is not None and self.reference.size_bytes != len(content):
            raise ArtifactIntegrityError("S3 artifact bytes do not match reference size.")
        return content


class S3ArtifactStoreV2:
    """Create-once V2 artifacts stored in one S3-compatible bucket/prefix."""

    def __init__(
        self,
        *,
        bucket: str,
        prefix: str = "pyingest/v2",
        region_name: str | None = None,
        endpoint_url: str | None = None,
        client: S3ClientV2 | None = None,
    ) -> None:
        validate_s3_endpoint_v2(endpoint_url)
        resolved_client = client or create_s3_client_v2(
            region_name=region_name,
            endpoint_url=endpoint_url,
        )
        self._objects = S3ObjectIOV2(
            bucket=bucket,
            prefix=prefix,
            client=resolved_client,
        )

    @property
    def bucket(self) -> str:
        return self._objects.bucket

    @property
    def prefix(self) -> str:
        return self._objects.prefix

    def put(self, request: PutArtifactRequest) -> PutArtifactResult:
        if not isinstance(request, PutArtifactRequest):
            raise TypeError("S3ArtifactStoreV2.put expects PutArtifactRequest.")

        digest = hashlib.sha256(request.content).hexdigest()
        if request.expected_checksum_algorithm is not None and request.expected_checksum != digest:
            return self._failed(
                request,
                status=ArtifactPutStatus.FAILED,
                code="artifact.integrity.source_checksum_mismatch",
                category=FailureCategory.INTEGRITY,
                retryability=Retryability.NON_RETRYABLE,
                summary="Acquired bytes do not match the expected SHA-256 checksum.",
            )

        key = self._objects.key(
            "runs",
            str(request.ingestion_run_id),
            request.kind.value,
            request.name,
        )
        try:
            created = self._objects.put_create_once(
                key,
                request.content,
                kind=f"artifact-{request.kind.value}",
                content_type=request.media_type,
            )
        except RuntimeError:
            return self._failed(
                request,
                status=ArtifactPutStatus.FAILED,
                code="artifact.s3.write_failed",
                category=FailureCategory.EXTERNAL_PROVIDER,
                retryability=Retryability.UNKNOWN,
                summary="S3 artifact persistence failed.",
            )
        if not created:
            return self._failed(
                request,
                status=ArtifactPutStatus.CONFLICT,
                code="artifact.s3.immutable_conflict",
                category=FailureCategory.CONFLICT,
                retryability=Retryability.NON_RETRYABLE,
                summary="S3 artifact key already exists; immutable artifact was not overwritten.",
            )

        persisted_at = datetime.now(UTC)
        locator = self._objects.uri(key)
        resource = ResourceReference(
            namespace="pyingestkit.artifact.s3",
            resource_id=_resource_id(locator),
            locator=locator,
            media_type=request.media_type,
            format=request.name.rsplit(".", 1)[-1].lower() if "." in request.name else None,
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
        if request.kind.value == "raw":
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
            code="artifact.s3.persisted",
            severity=DiagnosticSeverity.INFO,
            summary="Artifact bytes were durably persisted to S3-compatible storage.",
            stage="persist_raw" if request.kind.value == "raw" else "persist_artifact",
            target_context="s3-artifact-store-v2",
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

    def open(self, reference: ArtifactReference) -> S3ArtifactReaderV2:
        if not isinstance(reference, ArtifactReference):
            raise TypeError("S3ArtifactStoreV2.open expects ArtifactReference.")
        key = self._key_from_reference(reference)
        return S3ArtifactReaderV2(reference=reference, _objects=self._objects, _key=key)

    def exists(self, reference: ArtifactReference) -> bool:
        if not isinstance(reference, ArtifactReference):
            raise TypeError("S3ArtifactStoreV2.exists expects ArtifactReference.")
        key = self._key_from_reference(reference)
        return self._objects.head(key) is not None

    def _key_from_reference(self, reference: ArtifactReference) -> str:
        if reference.resource.namespace != "pyingestkit.artifact.s3":
            raise ValueError("ArtifactReference is not owned by S3ArtifactStoreV2.")
        locator = reference.resource.locator
        if locator is None:
            raise ValueError("S3 ArtifactReference requires locator.")
        parsed = urlsplit(locator)
        if parsed.scheme != "s3" or parsed.netloc != self.bucket:
            raise ValueError("ArtifactReference points to a different S3 bucket.")
        key = parsed.path.lstrip("/")
        expected_prefix = f"{self.prefix}/" if self.prefix else ""
        if expected_prefix and not key.startswith(expected_prefix):
            raise ValueError("ArtifactReference points outside S3ArtifactStoreV2 prefix.")
        if reference.resource.resource_id != _resource_id(locator):
            raise ValueError("ArtifactReference S3 resource identity mismatch.")
        if reference.checksum_algorithm != "sha256" or reference.checksum is None:
            raise ValueError("S3 ArtifactReference requires SHA-256 integrity evidence.")
        return key

    @staticmethod
    def _failed(
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
            source_component="S3ArtifactStoreV2",
            message_summary=summary,
        )
        diagnostic = Diagnostic(
            code=code,
            severity=DiagnosticSeverity.ERROR,
            summary=summary,
            stage="persist_raw" if request.kind.value == "raw" else "persist_artifact",
            target_context="s3-artifact-store-v2",
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
        f"{request.ingestion_run_id}\x00{request.kind.value}\x00{request.name}\x00{checksum}"
    ).encode()
    return f"{request.kind.value}_{hashlib.sha256(material).hexdigest()}"


def _resource_id(locator: str) -> str:
    return f"s3_{hashlib.sha256(locator.encode()).hexdigest()}"
