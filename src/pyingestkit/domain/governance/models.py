"""Provider-neutral lifecycle-governance values for PyIngestKit 2.1."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pyingestkit.domain.datasets import DatasetVersionReference
from pyingestkit.domain.datasets.publication import PublishedDataset
from pyingestkit.domain.runtime import (
    CorrelationContext,
    FailureCategory,
    FailureEvidence,
    OutcomeUncertainty,
)
from pyingestkit.domain.shared import Identifier, IngestionRunId
from pyingestkit.domain.shared.validation import (
    require_non_blank,
    validate_aware_datetime,
    validate_metadata,
    validate_optional_text,
)

_REVISION = re.compile(r"^rev-[0-9a-f]{32}$")
_EVIDENCE_FINGERPRINT = re.compile(r"^sha256-[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class PublicationOperationId(Identifier):
    """Identity of one governed publication operation."""


@dataclass(frozen=True, slots=True)
class GarbageCollectionPlanId(Identifier):
    """Identity of one immutable garbage-collection plan."""


@dataclass(frozen=True, slots=True)
class PublicationRevision:
    """Opaque framework-owned publication revision used for CAS."""

    value: str

    def __post_init__(self) -> None:
        require_non_blank(self.value, "PublicationRevision value")
        if self.value != "initial" and _REVISION.fullmatch(self.value) is None:
            raise ValueError(
                "PublicationRevision must be 'initial' or a framework rev-<uuid-hex> token."
            )

    @classmethod
    def initial(cls) -> PublicationRevision:
        return cls("initial")

    @classmethod
    def new(cls) -> PublicationRevision:
        return cls(f"rev-{uuid4().hex}")

    @classmethod
    def parse(cls, value: str) -> PublicationRevision:
        return cls(value)

    @property
    def is_initial(self) -> bool:
        return self.value == "initial"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PublicationSnapshot:
    """Observed governed publication pointer plus its opaque revision."""

    dataset_id: str
    revision: PublicationRevision
    published_dataset: PublishedDataset | None = None

    def __post_init__(self) -> None:
        require_non_blank(self.dataset_id, "PublicationSnapshot dataset_id")
        if not isinstance(self.revision, PublicationRevision):
            raise TypeError("PublicationSnapshot revision must be PublicationRevision.")
        if self.published_dataset is None:
            if not self.revision.is_initial:
                raise ValueError("Unpublished PublicationSnapshot must use the initial revision.")
            return
        if not isinstance(self.published_dataset, PublishedDataset):
            raise TypeError(
                "PublicationSnapshot published_dataset must be PublishedDataset or None."
            )
        if self.published_dataset.dataset_id != self.dataset_id:
            raise ValueError("PublicationSnapshot published dataset identity mismatch.")
        if self.revision.is_initial:
            raise ValueError("Published PublicationSnapshot cannot use the initial revision.")


@dataclass(frozen=True, slots=True)
class PublicationIntent:
    """Idempotent intent for one conditional publication attempt."""

    operation_id: PublicationOperationId
    dataset_version: DatasetVersionReference
    expected_revision: PublicationRevision
    ingestion_run_id: IngestionRunId
    correlation: CorrelationContext
    requested_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.operation_id, PublicationOperationId):
            raise TypeError("PublicationIntent operation_id must be PublicationOperationId.")
        if not isinstance(self.dataset_version, DatasetVersionReference):
            raise TypeError("PublicationIntent dataset_version must be DatasetVersionReference.")
        if not isinstance(self.expected_revision, PublicationRevision):
            raise TypeError("PublicationIntent expected_revision must be PublicationRevision.")
        if not isinstance(self.ingestion_run_id, IngestionRunId):
            raise TypeError("PublicationIntent ingestion_run_id must be IngestionRunId.")
        if not isinstance(self.correlation, CorrelationContext):
            raise TypeError("PublicationIntent correlation must be CorrelationContext.")
        validate_aware_datetime(self.requested_at, "PublicationIntent requested_at")
        if self.correlation.ingestion_run_id not in {None, str(self.ingestion_run_id)}:
            raise ValueError("PublicationIntent correlation run identity mismatch.")

    @property
    def dataset_id(self) -> str:
        return self.dataset_version.dataset_id

    @property
    def intent_fingerprint(self) -> str:
        payload = {
            "dataset_id": self.dataset_version.dataset_id,
            "version_id": self.dataset_version.version_id,
            "expected_revision": str(self.expected_revision),
            "ingestion_run_id": str(self.ingestion_run_id),
            "correlation_id": str(self.correlation.correlation_id),
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return f"sha256-{hashlib.sha256(encoded).hexdigest()}"

    def same_intent_as(self, other: PublicationIntent) -> bool:
        if not isinstance(other, PublicationIntent):
            return False
        return (
            self.operation_id == other.operation_id
            and self.intent_fingerprint == other.intent_fingerprint
        )

    def assert_same_intent_as(self, other: PublicationIntent) -> None:
        """Fail closed when one operation identity is reused for another intent."""
        if not isinstance(other, PublicationIntent):
            raise TypeError("PublicationIntent comparison requires PublicationIntent.")
        if self.operation_id != other.operation_id:
            raise ValueError("PublicationIntent operation identity mismatch.")
        if self.intent_fingerprint != other.intent_fingerprint:
            raise ValueError(
                "PublicationOperationId cannot be reused for a different publication intent."
            )


class PublicationLifecycleEventType(StrEnum):
    """Append-only lifecycle event families accepted by RFC-001."""

    VERSION_OBSERVED = "version_observed"
    PUBLICATION_REQUESTED = "publication_requested"
    PUBLICATION_COMMITTED = "publication_committed"
    PUBLICATION_CONFLICT = "publication_conflict"
    PUBLICATION_OUTCOME_UNKNOWN = "publication_outcome_unknown"
    PUBLICATION_RECONCILED_COMMITTED = "publication_reconciled_committed"
    PUBLICATION_RECONCILED_NOT_COMMITTED = "publication_reconciled_not_committed"
    PUBLICATION_RECONCILED_CONFLICT = "publication_reconciled_conflict"
    ROLLBACK_REQUESTED = "rollback_requested"
    ROLLBACK_COMMITTED = "rollback_committed"
    HOLD_PLACED = "hold_placed"
    HOLD_RELEASED = "hold_released"
    RETENTION_PLAN_CREATED = "retention_plan_created"
    GC_DELETE_REQUESTED = "gc_delete_requested"
    GC_DELETE_COMMITTED = "gc_delete_committed"
    GC_DELETE_FAILED = "gc_delete_failed"
    GC_DELETE_OUTCOME_UNKNOWN = "gc_delete_outcome_unknown"


@dataclass(frozen=True, slots=True)
class PublicationLifecycleEvent:
    """Portable non-secret evidence for one lifecycle transition."""

    event_id: str
    event_type: PublicationLifecycleEventType
    dataset_id: str
    occurred_at: datetime
    operation_id: PublicationOperationId | None = None
    dataset_version: DatasetVersionReference | None = None
    previous_revision: PublicationRevision | None = None
    next_revision: PublicationRevision | None = None
    provider_operation_reference: str | None = None
    failure: FailureEvidence | None = None
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        require_non_blank(self.event_id, "PublicationLifecycleEvent event_id")
        if not isinstance(self.event_type, PublicationLifecycleEventType):
            raise TypeError(
                "PublicationLifecycleEvent event_type must be PublicationLifecycleEventType."
            )
        require_non_blank(self.dataset_id, "PublicationLifecycleEvent dataset_id")
        validate_aware_datetime(self.occurred_at, "PublicationLifecycleEvent occurred_at")
        if self.operation_id is not None and not isinstance(
            self.operation_id, PublicationOperationId
        ):
            raise TypeError(
                "PublicationLifecycleEvent operation_id must be PublicationOperationId or None."
            )
        if self.dataset_version is not None:
            if not isinstance(self.dataset_version, DatasetVersionReference):
                raise TypeError(
                    "PublicationLifecycleEvent dataset_version must be "
                    "DatasetVersionReference or None."
                )
            if self.dataset_version.dataset_id != self.dataset_id:
                raise ValueError("PublicationLifecycleEvent dataset identity mismatch.")
        for name, revision in (
            ("previous_revision", self.previous_revision),
            ("next_revision", self.next_revision),
        ):
            if revision is not None and not isinstance(revision, PublicationRevision):
                raise TypeError(
                    f"PublicationLifecycleEvent {name} must be PublicationRevision or None."
                )
        validate_optional_text(
            self.provider_operation_reference,
            "PublicationLifecycleEvent provider_operation_reference",
        )
        if self.failure is not None and not isinstance(self.failure, FailureEvidence):
            raise TypeError("PublicationLifecycleEvent failure must be FailureEvidence or None.")
        validate_metadata(self.metadata, name="PublicationLifecycleEvent metadata")


class ConditionalPublicationStatus(StrEnum):
    """Semantic outcome of a conditional publication attempt."""

    SUCCEEDED = "succeeded"
    CONFLICT = "conflict"
    FAILED = "failed"
    UNKNOWN_OUTCOME = "unknown_outcome"


@dataclass(frozen=True, slots=True)
class ConditionalPublicationOutcome:
    """Provider-neutral result of compare-and-publish."""

    intent: PublicationIntent
    status: ConditionalPublicationStatus
    completed_at: datetime
    snapshot: PublicationSnapshot | None = None
    failure: FailureEvidence | None = None
    provider_operation_reference: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.intent, PublicationIntent):
            raise TypeError("ConditionalPublicationOutcome intent must be PublicationIntent.")
        if not isinstance(self.status, ConditionalPublicationStatus):
            raise TypeError(
                "ConditionalPublicationOutcome status must be ConditionalPublicationStatus."
            )
        validate_aware_datetime(self.completed_at, "ConditionalPublicationOutcome completed_at")
        if self.completed_at < self.intent.requested_at:
            raise ValueError(
                "ConditionalPublicationOutcome completed_at cannot precede requested_at."
            )
        if self.snapshot is not None and not isinstance(self.snapshot, PublicationSnapshot):
            raise TypeError(
                "ConditionalPublicationOutcome snapshot must be PublicationSnapshot or None."
            )
        validate_optional_text(
            self.provider_operation_reference,
            "ConditionalPublicationOutcome provider_operation_reference",
        )

        if self.status is ConditionalPublicationStatus.SUCCEEDED:
            if self.failure is not None:
                raise ValueError("Successful conditional publication cannot contain failure.")
            if self.snapshot is None or self.snapshot.published_dataset is None:
                raise ValueError(
                    "Successful conditional publication requires a published snapshot."
                )
            if (
                self.snapshot.published_dataset.version.identity
                != self.intent.dataset_version.identity
            ):
                raise ValueError("Conditional publication success version identity mismatch.")
            return

        if self.failure is None:
            raise ValueError("Non-success conditional publication requires FailureEvidence.")
        if not isinstance(self.failure, FailureEvidence):
            raise TypeError("ConditionalPublicationOutcome failure must be FailureEvidence.")
        if self.failure.ingestion_run_id != self.intent.ingestion_run_id:
            raise ValueError("Conditional publication failure run identity mismatch.")
        if self.failure.correlation_id != self.intent.correlation.correlation_id:
            raise ValueError("Conditional publication failure correlation identity mismatch.")
        if self.status is ConditionalPublicationStatus.UNKNOWN_OUTCOME:
            if self.failure.category is not FailureCategory.UNKNOWN_OUTCOME:
                raise ValueError("UNKNOWN_OUTCOME requires UNKNOWN_OUTCOME failure category.")
            if self.failure.uncertainty is not OutcomeUncertainty.REQUIRES_RECONCILIATION:
                raise ValueError("UNKNOWN_OUTCOME requires reconciliation evidence.")


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    """Minimal deterministic retention policy accepted for PyIngestKit 2.1."""

    keep_last: int = 1
    min_age_seconds: int | None = None

    def __post_init__(self) -> None:
        if isinstance(self.keep_last, bool) or not isinstance(self.keep_last, int):
            raise TypeError("RetentionPolicy keep_last must be an int.")
        if self.keep_last < 1:
            raise ValueError("RetentionPolicy keep_last must be >= 1.")
        if self.min_age_seconds is not None:
            if isinstance(self.min_age_seconds, bool) or not isinstance(
                self.min_age_seconds, int
            ):
                raise TypeError("RetentionPolicy min_age_seconds must be an int or None.")
            if self.min_age_seconds < 0:
                raise ValueError("RetentionPolicy min_age_seconds must be >= 0.")


@dataclass(frozen=True, slots=True)
class VersionHold:
    """Explicit lifecycle protection for one immutable dataset version."""

    dataset_version: DatasetVersionReference
    held_at: datetime
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.dataset_version, DatasetVersionReference):
            raise TypeError("VersionHold dataset_version must be DatasetVersionReference.")
        validate_aware_datetime(self.held_at, "VersionHold held_at")
        validate_optional_text(self.reason, "VersionHold reason")


@dataclass(frozen=True, slots=True)
class GarbageCollectionPlan:
    """Immutable output of retention planning; execution is a separate concern."""

    plan_id: GarbageCollectionPlanId
    dataset_id: str
    created_at: datetime
    policy: RetentionPolicy
    protected_versions: tuple[DatasetVersionReference, ...]
    candidate_versions: tuple[DatasetVersionReference, ...]
    evidence_fingerprint: str

    def __post_init__(self) -> None:
        if not isinstance(self.plan_id, GarbageCollectionPlanId):
            raise TypeError("GarbageCollectionPlan plan_id must be GarbageCollectionPlanId.")
        require_non_blank(self.dataset_id, "GarbageCollectionPlan dataset_id")
        validate_aware_datetime(self.created_at, "GarbageCollectionPlan created_at")
        if not isinstance(self.policy, RetentionPolicy):
            raise TypeError("GarbageCollectionPlan policy must be RetentionPolicy.")
        if _EVIDENCE_FINGERPRINT.fullmatch(self.evidence_fingerprint) is None:
            raise ValueError(
                "GarbageCollectionPlan evidence_fingerprint must be sha256-<64 lowercase hex>."
            )
        protected = _validate_version_tuple(
            self.protected_versions,
            dataset_id=self.dataset_id,
            name="GarbageCollectionPlan protected_versions",
        )
        candidates = _validate_version_tuple(
            self.candidate_versions,
            dataset_id=self.dataset_id,
            name="GarbageCollectionPlan candidate_versions",
        )
        overlap = protected.intersection(candidates)
        if overlap:
            raise ValueError("GarbageCollectionPlan protected/candidate versions must be disjoint.")


class DatasetVersionDeletionStatus(StrEnum):
    """Semantic result of a destructive dataset-version operation."""

    DELETED = "deleted"
    ALREADY_ABSENT = "already_absent"
    FAILED = "failed"
    UNKNOWN_OUTCOME = "unknown_outcome"


@dataclass(frozen=True, slots=True)
class DatasetVersionDeletionResult:
    """Operation-specific deletion result using shared uncertainty primitives."""

    dataset_version: DatasetVersionReference
    status: DatasetVersionDeletionStatus
    completed_at: datetime
    failure: FailureEvidence | None = None
    provider_operation_reference: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.dataset_version, DatasetVersionReference):
            raise TypeError(
                "DatasetVersionDeletionResult dataset_version must be DatasetVersionReference."
            )
        if not isinstance(self.status, DatasetVersionDeletionStatus):
            raise TypeError(
                "DatasetVersionDeletionResult status must be DatasetVersionDeletionStatus."
            )
        validate_aware_datetime(self.completed_at, "DatasetVersionDeletionResult completed_at")
        validate_optional_text(
            self.provider_operation_reference,
            "DatasetVersionDeletionResult provider_operation_reference",
        )
        if self.status in {
            DatasetVersionDeletionStatus.DELETED,
            DatasetVersionDeletionStatus.ALREADY_ABSENT,
        }:
            if self.failure is not None:
                raise ValueError("Successful deletion result cannot contain failure.")
            return
        if self.failure is None:
            raise ValueError("Failed/unknown deletion result requires FailureEvidence.")
        if not isinstance(self.failure, FailureEvidence):
            raise TypeError("DatasetVersionDeletionResult failure must be FailureEvidence.")
        if self.status is DatasetVersionDeletionStatus.UNKNOWN_OUTCOME:
            if self.failure.category is not FailureCategory.UNKNOWN_OUTCOME:
                raise ValueError("Unknown deletion outcome requires UNKNOWN_OUTCOME failure.")
            if self.failure.uncertainty is not OutcomeUncertainty.REQUIRES_RECONCILIATION:
                raise ValueError("Unknown deletion outcome requires reconciliation evidence.")


class DatasetVersionDeletionReconciliationStatus(StrEnum):
    """Observed provider truth after an uncertain deletion."""

    CONFIRMED_DELETED = "confirmed_deleted"
    CONFIRMED_PRESENT = "confirmed_present"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DatasetVersionDeletionReconciliationResult:
    """Reconciliation result for one prior uncertain deletion."""

    dataset_version: DatasetVersionReference
    status: DatasetVersionDeletionReconciliationStatus
    reconciled_at: datetime
    failure: FailureEvidence | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.dataset_version, DatasetVersionReference):
            raise TypeError(
                "DatasetVersionDeletionReconciliationResult dataset_version must be "
                "DatasetVersionReference."
            )
        if not isinstance(self.status, DatasetVersionDeletionReconciliationStatus):
            raise TypeError(
                "DatasetVersionDeletionReconciliationResult status must be "
                "DatasetVersionDeletionReconciliationStatus."
            )
        validate_aware_datetime(
            self.reconciled_at,
            "DatasetVersionDeletionReconciliationResult reconciled_at",
        )
        if self.status in {
            DatasetVersionDeletionReconciliationStatus.CONFIRMED_DELETED,
            DatasetVersionDeletionReconciliationStatus.CONFIRMED_PRESENT,
        }:
            if self.failure is not None:
                raise ValueError("Confirmed deletion reconciliation cannot contain failure.")
            return
        if self.failure is None:
            raise ValueError("Conflict/unknown deletion reconciliation requires FailureEvidence.")
        if not isinstance(self.failure, FailureEvidence):
            raise TypeError(
                "DatasetVersionDeletionReconciliationResult failure must be FailureEvidence."
            )


def _validate_version_tuple(
    values: tuple[DatasetVersionReference, ...],
    *,
    dataset_id: str,
    name: str,
) -> set[tuple[str, str]]:
    if not isinstance(values, tuple):
        raise TypeError(f"{name} must be a tuple.")
    identities: set[tuple[str, str]] = set()
    for value in values:
        if not isinstance(value, DatasetVersionReference):
            raise TypeError(f"{name} must contain DatasetVersionReference values.")
        if value.dataset_id != dataset_id:
            raise ValueError(f"{name} contains a foreign dataset version.")
        if value.identity in identities:
            raise ValueError(f"{name} contains duplicate dataset-version identity.")
        identities.add(value.identity)
    return identities
