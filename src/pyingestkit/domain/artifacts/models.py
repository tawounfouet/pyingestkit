"""Immutable artifact persistence values for PyIngestKit V2."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from pyingestkit.domain.acquisition import AcquisitionResult, AcquisitionStatus
from .references import ArtifactReference
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import CorrelationContext, Diagnostic, FailureEvidence
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.shared.validation import (
    require_non_blank,
    validate_aware_datetime,
    validate_metadata,
    validate_optional_text,
)


class ArtifactKind(StrEnum):
    """Portable artifact categories owned by PyIngestKit."""

    RAW = "raw"
    MANIFEST = "manifest"
    REPORT = "report"
    REJECTED_RECORDS = "rejected_records"
    OTHER = "other"


class ArtifactPutStatus(StrEnum):
    """Outcome of one durable artifact persistence attempt."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CONFLICT = "conflict"

    @property
    def terminal(self) -> bool:
        return True


@dataclass(frozen=True, slots=True)
class ArtifactRetention:
    """Portable retention intent attached to durable artifact evidence."""

    retain: bool = True
    retain_until: datetime | None = None
    policy_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.retain, bool):
            raise TypeError("ArtifactRetention retain must be bool.")
        validate_aware_datetime(self.retain_until, "ArtifactRetention retain_until")
        validate_optional_text(self.policy_id, "ArtifactRetention policy_id")
        if not self.retain and self.retain_until is not None:
            raise ValueError("ArtifactRetention retain_until requires retain=True.")


@dataclass(frozen=True, slots=True)
class PutArtifactRequest:
    """Explicit request to persist exact bytes as durable material evidence."""

    ingestion_run_id: IngestionRunId
    correlation: CorrelationContext
    kind: ArtifactKind
    name: str
    content: bytes
    media_type: str | None = None
    source_resource: ResourceReference | None = None
    source_acquired_at: datetime | None = None
    expected_checksum_algorithm: str | None = None
    expected_checksum: str | None = None
    retention: ArtifactRetention = field(default_factory=ArtifactRetention)
    manifest_artifact_id: str | None = None
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.ingestion_run_id, IngestionRunId):
            raise TypeError("PutArtifactRequest ingestion_run_id must be an IngestionRunId.")
        if not isinstance(self.correlation, CorrelationContext):
            raise TypeError("PutArtifactRequest correlation must be a CorrelationContext.")
        if not isinstance(self.kind, ArtifactKind):
            raise TypeError("PutArtifactRequest kind must be an ArtifactKind.")
        _validate_artifact_name(self.name)
        if not isinstance(self.content, bytes):
            raise TypeError("PutArtifactRequest content must be bytes.")
        validate_optional_text(self.media_type, "PutArtifactRequest media_type")
        if self.source_resource is not None and not isinstance(
            self.source_resource,
            ResourceReference,
        ):
            raise TypeError("PutArtifactRequest source_resource must be a ResourceReference.")
        validate_aware_datetime(
            self.source_acquired_at,
            "PutArtifactRequest source_acquired_at",
        )
        validate_optional_text(
            self.expected_checksum_algorithm,
            "PutArtifactRequest expected_checksum_algorithm",
        )
        validate_optional_text(
            self.expected_checksum,
            "PutArtifactRequest expected_checksum",
        )
        if (self.expected_checksum_algorithm is None) != (self.expected_checksum is None):
            raise ValueError(
                "PutArtifactRequest expected checksum algorithm/value must be provided together."
            )
        if (
            self.expected_checksum_algorithm is not None
            and self.expected_checksum_algorithm.lower() != "sha256"
        ):
            raise ValueError("LOT-04 FileArtifactStore supports SHA-256 integrity evidence only.")
        if not isinstance(self.retention, ArtifactRetention):
            raise TypeError("PutArtifactRequest retention must be ArtifactRetention.")
        validate_optional_text(
            self.manifest_artifact_id,
            "PutArtifactRequest manifest_artifact_id",
        )
        validate_metadata(self.metadata, name="PutArtifactRequest metadata")

        if (
            self.correlation.ingestion_run_id is not None
            and self.correlation.ingestion_run_id != str(self.ingestion_run_id)
        ):
            raise ValueError(
                "PutArtifactRequest correlation ingestion_run_id must match "
                "the native IngestionRunId."
            )

        if self.kind is ArtifactKind.RAW:
            if self.source_resource is None:
                raise ValueError("RAW PutArtifactRequest requires source_resource.")
            if self.source_acquired_at is None:
                raise ValueError("RAW PutArtifactRequest requires source_acquired_at.")

    @classmethod
    def from_acquisition(
        cls,
        acquisition: AcquisitionResult,
        *,
        name: str,
        retention: ArtifactRetention | None = None,
        manifest_artifact_id: str | None = None,
        metadata: tuple[tuple[str, str], ...] = (),
    ) -> PutArtifactRequest:
        """Build a RAW request from exact bytes returned by acquisition."""
        if not isinstance(acquisition, AcquisitionResult):
            raise TypeError("acquisition must be an AcquisitionResult.")
        if acquisition.status is not AcquisitionStatus.SUCCEEDED:
            raise ValueError("Only successful acquisition results can be persisted as RAW.")
        if acquisition.content is None or acquisition.resource is None:
            raise ValueError("Successful acquisition is missing content/resource evidence.")
        if acquisition.checksum_algorithm is None or acquisition.checksum is None:
            raise ValueError("Successful acquisition is missing checksum evidence.")

        return cls(
            ingestion_run_id=acquisition.ingestion_run_id,
            correlation=acquisition.correlation,
            kind=ArtifactKind.RAW,
            name=name,
            content=acquisition.content,
            media_type=acquisition.media_type,
            source_resource=acquisition.resource,
            source_acquired_at=acquisition.acquired_at,
            expected_checksum_algorithm=acquisition.checksum_algorithm,
            expected_checksum=acquisition.checksum,
            retention=retention or ArtifactRetention(),
            manifest_artifact_id=manifest_artifact_id,
            metadata=metadata,
        )


@dataclass(frozen=True, slots=True)
class RawArtifactEvidence:
    """RAW semantics linking durable bytes back to their acquisition evidence."""

    reference: ArtifactReference
    source_resource: ResourceReference
    ingestion_run_id: IngestionRunId
    acquired_at: datetime
    persisted_at: datetime
    retention: ArtifactRetention
    manifest_artifact_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.reference, ArtifactReference):
            raise TypeError("RawArtifactEvidence reference must be an ArtifactReference.")
        if self.reference.kind != ArtifactKind.RAW.value:
            raise ValueError("RawArtifactEvidence reference must have kind='raw'.")
        if not isinstance(self.source_resource, ResourceReference):
            raise TypeError("RawArtifactEvidence source_resource must be a ResourceReference.")
        if not isinstance(self.ingestion_run_id, IngestionRunId):
            raise TypeError("RawArtifactEvidence ingestion_run_id must be an IngestionRunId.")
        validate_aware_datetime(self.acquired_at, "RawArtifactEvidence acquired_at")
        validate_aware_datetime(self.persisted_at, "RawArtifactEvidence persisted_at")
        if not isinstance(self.retention, ArtifactRetention):
            raise TypeError("RawArtifactEvidence retention must be ArtifactRetention.")
        validate_optional_text(
            self.manifest_artifact_id,
            "RawArtifactEvidence manifest_artifact_id",
        )

    @property
    def portable(self) -> bool:
        return True


@dataclass(frozen=True, slots=True)
class PutArtifactResult:
    """Structured result of one artifact-store put operation."""

    status: ArtifactPutStatus
    ingestion_run_id: IngestionRunId
    correlation: CorrelationContext
    kind: ArtifactKind
    persisted_at: datetime | None = None
    reference: ArtifactReference | None = None
    raw_evidence: RawArtifactEvidence | None = None
    diagnostics: tuple[Diagnostic, ...] = ()
    failure: FailureEvidence | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, ArtifactPutStatus):
            raise TypeError("PutArtifactResult status must be ArtifactPutStatus.")
        if not isinstance(self.ingestion_run_id, IngestionRunId):
            raise TypeError("PutArtifactResult ingestion_run_id must be an IngestionRunId.")
        if not isinstance(self.correlation, CorrelationContext):
            raise TypeError("PutArtifactResult correlation must be a CorrelationContext.")
        if not isinstance(self.kind, ArtifactKind):
            raise TypeError("PutArtifactResult kind must be an ArtifactKind.")
        validate_aware_datetime(self.persisted_at, "PutArtifactResult persisted_at")

        if self.reference is not None and not isinstance(self.reference, ArtifactReference):
            raise TypeError("PutArtifactResult reference must be an ArtifactReference.")
        if self.raw_evidence is not None and not isinstance(
            self.raw_evidence,
            RawArtifactEvidence,
        ):
            raise TypeError("PutArtifactResult raw_evidence must be RawArtifactEvidence.")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("PutArtifactResult diagnostics must be a tuple.")
        if any(not isinstance(item, Diagnostic) for item in self.diagnostics):
            raise TypeError("PutArtifactResult diagnostics must contain Diagnostic values.")
        if self.failure is not None and not isinstance(self.failure, FailureEvidence):
            raise TypeError("PutArtifactResult failure must be FailureEvidence.")

        if self.status is ArtifactPutStatus.SUCCEEDED:
            if self.persisted_at is None:
                raise ValueError("Successful PutArtifactResult requires persisted_at.")
            if self.reference is None:
                raise ValueError("Successful PutArtifactResult requires ArtifactReference.")
            if self.failure is not None:
                raise ValueError("Successful PutArtifactResult cannot contain FailureEvidence.")
            if self.kind is ArtifactKind.RAW and self.raw_evidence is None:
                raise ValueError("Successful RAW persistence requires RawArtifactEvidence.")
            if self.kind is not ArtifactKind.RAW and self.raw_evidence is not None:
                raise ValueError("Only RAW PutArtifactResult may contain RawArtifactEvidence.")
        else:
            if self.persisted_at is not None:
                raise ValueError("Failed/conflicting PutArtifactResult cannot claim persisted_at.")
            if self.failure is None:
                raise ValueError("Non-successful PutArtifactResult requires FailureEvidence.")
            if self.reference is not None or self.raw_evidence is not None:
                raise ValueError("Failed/conflicting PutArtifactResult cannot expose durable evidence.")


def _validate_artifact_name(value: str) -> None:
    require_non_blank(value, "PutArtifactRequest name")
    if value in {".", ".."} or "/" in value or "\\" in value or "\x00" in value:
        raise ValueError("PutArtifactRequest name must be a single safe path component.")
