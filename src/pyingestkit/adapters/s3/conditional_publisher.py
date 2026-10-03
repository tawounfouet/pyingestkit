"""S3 compare-and-swap publication for PyIngestKit 2.1 LOT-26."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from pyingestkit.adapters.s3._objects import (
    S3ConditionalWriteCapabilityErrorV2,
    S3ConditionalWriteConflictV2,
)
from pyingestkit.adapters.s3.dataset_version_store import S3DatasetVersionStoreV2
from pyingestkit.domain.datasets.publication import PublishedDataset
from pyingestkit.domain.governance import (
    ConditionalPublicationOutcome,
    ConditionalPublicationStatus,
    PublicationIntent,
    PublicationLifecycleEvent,
    PublicationLifecycleEventType,
    PublicationRevision,
    PublicationSnapshot,
)
from pyingestkit.domain.runtime import (
    FailureCategory,
    FailureEvidence,
    OutcomeUncertainty,
    Retryability,
)
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.ports.governance import ConditionalDatasetPublisher, PublicationLedger

_GOVERNANCE_REVISION = "governance_revision"
_GOVERNANCE_OPERATION_ID = "governance_operation_id"
_GOVERNANCE_INTENT_FINGERPRINT = "governance_intent_fingerprint"


class S3ConditionalDatasetPublisher(ConditionalDatasetPublisher):
    """Governed S3 pointer publication using provider-enforced conditional writes."""

    def __init__(
        self,
        *,
        store: S3DatasetVersionStoreV2,
        ledger: PublicationLedger,
        clock: Callable[[], datetime] | None = None,
        fault_injector: Callable[[str], None] | None = None,
    ) -> None:
        if not isinstance(store, S3DatasetVersionStoreV2):
            raise TypeError(
                "S3ConditionalDatasetPublisher store must be S3DatasetVersionStoreV2."
            )
        if not isinstance(ledger, PublicationLedger):
            raise TypeError(
                "S3ConditionalDatasetPublisher ledger must satisfy PublicationLedger."
            )
        self._store = store
        self._ledger = ledger
        self._clock = clock or (lambda: datetime.now(UTC))
        self._fault_injector = fault_injector
        probe_key = self._store._objects.key(
            "governance",
            "conditional-probes",
            uuid4().hex,
        )
        self._store._objects.qualify_conditional_writes(probe_key=probe_key)

    @property
    def store(self) -> S3DatasetVersionStoreV2:
        return self._store

    def inspect(self, dataset_id: str) -> PublicationSnapshot:
        snapshot, _, _ = self._inspect_with_metadata(dataset_id)
        return snapshot

    def compare_and_publish(
        self,
        intent: PublicationIntent,
    ) -> ConditionalPublicationOutcome:
        if not isinstance(intent, PublicationIntent):
            raise TypeError(
                "S3ConditionalDatasetPublisher.compare_and_publish requires PublicationIntent."
            )
        self._ensure_registered(intent)
        current, metadata, provider_etag = self._inspect_with_metadata(intent.dataset_id)

        if self._pointer_matches_intent(current, metadata, intent):
            if self._is_unresolved(intent):
                self._append_if_unresolved(
                    intent,
                    PublicationLifecycleEventType.PUBLICATION_RECONCILED_COMMITTED,
                    previous_revision=intent.expected_revision,
                    next_revision=current.revision,
                )
            return ConditionalPublicationOutcome(
                intent=intent,
                status=ConditionalPublicationStatus.SUCCEEDED,
                completed_at=self._now(),
                snapshot=current,
                provider_operation_reference=self._provider_reference(intent),
            )

        if current.revision != intent.expected_revision:
            self._append_if_unresolved(
                intent,
                PublicationLifecycleEventType.PUBLICATION_CONFLICT,
                previous_revision=intent.expected_revision,
                next_revision=current.revision,
            )
            return self._failure_outcome(
                intent,
                status=ConditionalPublicationStatus.CONFLICT,
                code="governance.s3.revision_conflict",
                category=FailureCategory.CONFLICT,
                retryability=Retryability.NON_RETRYABLE,
                summary="Expected publication revision is stale.",
                snapshot=current,
            )

        try:
            stored = self._store.get(
                intent.dataset_version.dataset_id,
                intent.dataset_version.version_id,
            )
            if stored.identity != intent.dataset_version.identity:
                raise ValueError(
                    "Publication intent version identity does not match stored version."
                )
            self._store.read(stored)
        except (KeyError, RuntimeError, ValueError) as exc:
            return self._failure_outcome(
                intent,
                status=ConditionalPublicationStatus.FAILED,
                code="governance.s3.version_invalid",
                category=FailureCategory.INTEGRITY,
                retryability=Retryability.NON_RETRYABLE,
                summary=(
                    f"Target dataset version cannot be safely published: {type(exc).__name__}."
                ),
                snapshot=current,
            )

        next_revision = PublicationRevision.new()
        published_at = self._now()
        published = PublishedDataset(
            dataset_id=stored.dataset_id,
            version=stored,
            published_at=published_at,
            published_from_run_id=intent.ingestion_run_id,
        )
        pointer_key = self._store._published_key(intent.dataset_id)
        payload = _json_bytes(
            {
                "publication_schema": "1",
                "dataset_id": stored.dataset_id,
                "version_id": stored.version_id,
                "published_at": published_at.isoformat(),
                "published_from_run_id": str(intent.ingestion_run_id),
                _GOVERNANCE_REVISION: str(next_revision),
                _GOVERNANCE_OPERATION_ID: str(intent.operation_id),
                _GOVERNANCE_INTENT_FINGERPRINT: intent.intent_fingerprint,
            }
        )

        try:
            self._inject("before_conditional_write")
            if provider_etag is None:
                self._store._objects.put_if_absent(
                    pointer_key,
                    payload,
                    kind="published-dataset",
                    content_type="application/json",
                )
            else:
                self._store._objects.put_if_match(
                    pointer_key,
                    payload,
                    expected_etag=provider_etag,
                    kind="published-dataset",
                    content_type="application/json",
                )
            self._inject("after_conditional_write")
        except S3ConditionalWriteConflictV2:
            latest, _, _ = self._inspect_with_metadata(intent.dataset_id)
            self._append_if_unresolved(
                intent,
                PublicationLifecycleEventType.PUBLICATION_CONFLICT,
                previous_revision=intent.expected_revision,
                next_revision=latest.revision,
            )
            return self._failure_outcome(
                intent,
                status=ConditionalPublicationStatus.CONFLICT,
                code="governance.s3.provider_precondition_conflict",
                category=FailureCategory.CONFLICT,
                retryability=Retryability.NON_RETRYABLE,
                summary="S3 conditional write rejected a stale provider token.",
                snapshot=latest,
            )
        except (OSError, RuntimeError):
            self._append_unknown_best_effort(
                intent,
                current.revision,
                next_revision,
            )
            return self._failure_outcome(
                intent,
                status=ConditionalPublicationStatus.UNKNOWN_OUTCOME,
                code="governance.s3.unknown_outcome",
                category=FailureCategory.UNKNOWN_OUTCOME,
                retryability=Retryability.RETRYABLE_AFTER_RECONCILIATION,
                uncertainty=OutcomeUncertainty.REQUIRES_RECONCILIATION,
                summary=(
                    "Conditional S3 publication may have committed; reconciliation is required."
                ),
            )

        snapshot = PublicationSnapshot(
            dataset_id=stored.dataset_id,
            revision=next_revision,
            published_dataset=published,
        )
        try:
            self._append_if_unresolved(
                intent,
                PublicationLifecycleEventType.PUBLICATION_COMMITTED,
                previous_revision=current.revision,
                next_revision=next_revision,
            )
        except Exception:  # noqa: BLE001 - backend failure after provider commit is uncertain
            self._append_unknown_best_effort(
                intent,
                current.revision,
                next_revision,
            )
            return self._failure_outcome(
                intent,
                status=ConditionalPublicationStatus.UNKNOWN_OUTCOME,
                code="governance.s3.ledger_outcome_unknown",
                category=FailureCategory.UNKNOWN_OUTCOME,
                retryability=Retryability.RETRYABLE_AFTER_RECONCILIATION,
                uncertainty=OutcomeUncertainty.REQUIRES_RECONCILIATION,
                summary=("S3 pointer commit succeeded but durable outcome evidence is uncertain."),
            )

        return ConditionalPublicationOutcome(
            intent=intent,
            status=ConditionalPublicationStatus.SUCCEEDED,
            completed_at=self._now(),
            snapshot=snapshot,
            provider_operation_reference=self._provider_reference(intent),
        )

    def reconcile(
        self,
        intent: PublicationIntent,
    ) -> ConditionalPublicationOutcome:
        """Reconcile provider truth for an uncertain S3 operation without republishing."""
        if not isinstance(intent, PublicationIntent):
            raise TypeError("S3ConditionalDatasetPublisher.reconcile requires PublicationIntent.")
        existing = self._ledger.get_operation(intent.operation_id)
        if existing is None:
            raise KeyError(str(intent.operation_id))
        existing.assert_same_intent_as(intent)

        snapshot, metadata, _ = self._inspect_with_metadata(intent.dataset_id)
        if self._pointer_matches_intent(snapshot, metadata, intent):
            self._append_if_unresolved(
                intent,
                PublicationLifecycleEventType.PUBLICATION_RECONCILED_COMMITTED,
                previous_revision=intent.expected_revision,
                next_revision=snapshot.revision,
            )
            return ConditionalPublicationOutcome(
                intent=intent,
                status=ConditionalPublicationStatus.SUCCEEDED,
                completed_at=self._now(),
                snapshot=snapshot,
                provider_operation_reference=self._provider_reference(intent),
            )

        if snapshot.revision == intent.expected_revision:
            self._append_if_unresolved(
                intent,
                PublicationLifecycleEventType.PUBLICATION_RECONCILED_NOT_COMMITTED,
                previous_revision=snapshot.revision,
            )
            return self._failure_outcome(
                intent,
                status=ConditionalPublicationStatus.FAILED,
                code="governance.s3.reconciled_not_committed",
                category=FailureCategory.SIDE_EFFECT_FAILED,
                retryability=Retryability.NON_RETRYABLE,
                summary=(
                    "Reconciliation confirmed that the conditional S3 publication was not committed."
                ),
                snapshot=snapshot,
            )

        self._append_if_unresolved(
            intent,
            PublicationLifecycleEventType.PUBLICATION_RECONCILED_CONFLICT,
            previous_revision=intent.expected_revision,
            next_revision=snapshot.revision,
        )
        return self._failure_outcome(
            intent,
            status=ConditionalPublicationStatus.CONFLICT,
            code="governance.s3.reconciled_conflict",
            category=FailureCategory.CONFLICT,
            retryability=Retryability.NON_RETRYABLE,
            summary="Reconciliation observed a different committed S3 publication.",
            snapshot=snapshot,
        )

    def _ensure_registered(self, intent: PublicationIntent) -> None:
        existing = self._ledger.get_operation(intent.operation_id)
        if existing is not None:
            existing.assert_same_intent_as(intent)
            return
        requested = self._event(
            intent,
            PublicationLifecycleEventType.PUBLICATION_REQUESTED,
            previous_revision=intent.expected_revision,
        )
        transaction = getattr(self._ledger, "transaction", None)
        if callable(transaction):
            with transaction() as ledger:
                ledger.register(intent)
                ledger.append(requested)
            return
        self._ledger.register(intent)
        self._ledger.append(requested)

    def _append_if_unresolved(
        self,
        intent: PublicationIntent,
        event_type: PublicationLifecycleEventType,
        *,
        previous_revision: PublicationRevision | None = None,
        next_revision: PublicationRevision | None = None,
    ) -> None:
        if not self._is_unresolved(intent):
            return
        self._ledger.append(
            self._event(
                intent,
                event_type,
                previous_revision=previous_revision,
                next_revision=next_revision,
            )
        )

    def _append_unknown_best_effort(
        self,
        intent: PublicationIntent,
        previous_revision: PublicationRevision,
        next_revision: PublicationRevision,
    ) -> None:
        try:
            self._append_if_unresolved(
                intent,
                PublicationLifecycleEventType.PUBLICATION_OUTCOME_UNKNOWN,
                previous_revision=previous_revision,
                next_revision=next_revision,
            )
        except Exception:  # noqa: BLE001 - uncertainty evidence is deliberately best effort
            return

    def _event(
        self,
        intent: PublicationIntent,
        event_type: PublicationLifecycleEventType,
        *,
        previous_revision: PublicationRevision | None = None,
        next_revision: PublicationRevision | None = None,
    ) -> PublicationLifecycleEvent:
        return PublicationLifecycleEvent(
            event_id=f"{intent.operation_id}:{event_type.value}",
            event_type=event_type,
            dataset_id=intent.dataset_id,
            occurred_at=self._now(),
            operation_id=intent.operation_id,
            dataset_version=intent.dataset_version,
            previous_revision=previous_revision,
            next_revision=next_revision,
            provider_operation_reference=self._provider_reference(intent),
        )

    def _failure_outcome(
        self,
        intent: PublicationIntent,
        *,
        status: ConditionalPublicationStatus,
        code: str,
        category: FailureCategory,
        retryability: Retryability,
        summary: str,
        snapshot: PublicationSnapshot | None = None,
        uncertainty: OutcomeUncertainty = OutcomeUncertainty.KNOWN,
    ) -> ConditionalPublicationOutcome:
        return ConditionalPublicationOutcome(
            intent=intent,
            status=status,
            completed_at=self._now(),
            snapshot=snapshot,
            failure=FailureEvidence(
                error_code=code,
                category=category,
                retryability=retryability,
                uncertainty=uncertainty,
                ingestion_run_id=intent.ingestion_run_id,
                correlation_id=intent.correlation.correlation_id,
                source_component="governance.s3",
                message_summary=summary,
            ),
            provider_operation_reference=self._provider_reference(intent),
        )

    def _inspect_with_metadata(
        self,
        dataset_id: str,
    ) -> tuple[PublicationSnapshot, dict[str, object], str | None]:
        pointer_key = self._store._published_key(dataset_id)
        try:
            raw, provider_etag = self._store._objects.read_with_etag(pointer_key)
        except KeyError:
            return (
                PublicationSnapshot(
                    dataset_id=dataset_id,
                    revision=PublicationRevision.initial(),
                ),
                {},
                None,
            )
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("S3 publication pointer is not valid JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError("S3 publication pointer must be a JSON object.")
        if payload.get("dataset_id") != dataset_id:
            raise ValueError("S3 publication pointer identity mismatch.")

        reference = self._store.get(dataset_id, str(payload["version_id"]))
        published = PublishedDataset(
            dataset_id=dataset_id,
            version=reference,
            published_at=datetime.fromisoformat(str(payload["published_at"])),
            published_from_run_id=IngestionRunId.parse(str(payload["published_from_run_id"])),
        )
        revision_raw = payload.get(_GOVERNANCE_REVISION)
        revision = (
            self._legacy_revision(raw)
            if revision_raw is None
            else PublicationRevision.parse(str(revision_raw))
        )
        return (
            PublicationSnapshot(
                dataset_id=dataset_id,
                revision=revision,
                published_dataset=published,
            ),
            payload,
            provider_etag,
        )

    @staticmethod
    def _legacy_revision(raw_pointer: bytes) -> PublicationRevision:
        digest = hashlib.sha256(raw_pointer).hexdigest()[:32]
        return PublicationRevision.parse(f"rev-{digest}")

    @staticmethod
    def _pointer_matches_intent(
        snapshot: PublicationSnapshot,
        metadata: dict[str, object],
        intent: PublicationIntent,
    ) -> bool:
        published = snapshot.published_dataset
        return (
            published is not None
            and published.version.identity == intent.dataset_version.identity
            and metadata.get(_GOVERNANCE_OPERATION_ID) == str(intent.operation_id)
            and metadata.get(_GOVERNANCE_INTENT_FINGERPRINT) == intent.intent_fingerprint
        )

    def _is_unresolved(self, intent: PublicationIntent) -> bool:
        return any(
            candidate.operation_id == intent.operation_id
            for candidate in self._ledger.list_unresolved(intent.dataset_id)
        )

    def _provider_reference(self, intent: PublicationIntent) -> str:
        digest = hashlib.sha256(intent.dataset_id.encode("utf-8")).hexdigest()[:16]
        return f"s3-pointer:{digest}:{intent.operation_id}"

    def _inject(self, phase: str) -> None:
        if self._fault_injector is not None:
            self._fault_injector(phase)

    def _now(self) -> datetime:
        value = self._clock()
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("S3ConditionalDatasetPublisher clock must return aware datetime.")
        return value


__all__ = [
    "S3ConditionalDatasetPublisher",
    "S3ConditionalWriteCapabilityErrorV2",
]


def _json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
