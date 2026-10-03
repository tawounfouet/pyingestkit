"""Filesystem compare-and-swap publication for PyIngestKit 2.1 LOT-25."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO, Protocol, cast
from uuid import uuid4

from pyingestkit.adapters.filesystem.dataset_version_store import FileDatasetVersionStore
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

_DATASET_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_GOVERNANCE_REVISION = "governance_revision"
_GOVERNANCE_OPERATION_ID = "governance_operation_id"
_GOVERNANCE_INTENT_FINGERPRINT = "governance_intent_fingerprint"


class _LockTimeoutError(TimeoutError):
    pass


class FileConditionalDatasetPublisher(ConditionalDatasetPublisher):
    """Governed filesystem pointer publication with inter-process CAS semantics."""

    def __init__(
        self,
        *,
        store: FileDatasetVersionStore,
        ledger: PublicationLedger,
        clock: Callable[[], datetime] | None = None,
        lock_timeout_seconds: float = 10.0,
        fault_injector: Callable[[str], None] | None = None,
    ) -> None:
        if not isinstance(store, FileDatasetVersionStore):
            raise TypeError(
                "FileConditionalDatasetPublisher store must be FileDatasetVersionStore."
            )
        if not isinstance(ledger, PublicationLedger):
            raise TypeError(
                "FileConditionalDatasetPublisher ledger must satisfy PublicationLedger."
            )
        if isinstance(lock_timeout_seconds, bool) or not isinstance(
            lock_timeout_seconds, (int, float)
        ):
            raise TypeError("lock_timeout_seconds must be a number.")
        if lock_timeout_seconds < 0:
            raise ValueError("lock_timeout_seconds must be >= 0.")
        self._store = store
        self._ledger = ledger
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lock_timeout_seconds = float(lock_timeout_seconds)
        self._fault_injector = fault_injector

    @property
    def store(self) -> FileDatasetVersionStore:
        return self._store

    def inspect(self, dataset_id: str) -> PublicationSnapshot:
        snapshot, _ = self._inspect_with_metadata(dataset_id)
        return snapshot

    def compare_and_publish(
        self,
        intent: PublicationIntent,
    ) -> ConditionalPublicationOutcome:
        if not isinstance(intent, PublicationIntent):
            raise TypeError(
                "FileConditionalDatasetPublisher.compare_and_publish requires PublicationIntent."
            )
        self._ensure_registered(intent)

        try:
            with _interprocess_lock(
                self._lock_path(intent.dataset_id),
                timeout_seconds=self._lock_timeout_seconds,
            ):
                return self._compare_and_publish_locked(intent)
        except _LockTimeoutError:
            return self._failure_outcome(
                intent,
                status=ConditionalPublicationStatus.FAILED,
                code="governance.filesystem.lock_timeout",
                category=FailureCategory.TIMEOUT,
                retryability=Retryability.RETRYABLE,
                summary=("Filesystem publication lock could not be acquired before timeout."),
            )

    def reconcile(
        self,
        intent: PublicationIntent,
    ) -> ConditionalPublicationOutcome:
        """Reconcile provider truth for an uncertain operation without republishing."""
        if not isinstance(intent, PublicationIntent):
            raise TypeError("FileConditionalDatasetPublisher.reconcile requires PublicationIntent.")
        existing = self._ledger.get_operation(intent.operation_id)
        if existing is None:
            raise KeyError(str(intent.operation_id))
        existing.assert_same_intent_as(intent)

        snapshot, metadata = self._inspect_with_metadata(intent.dataset_id)
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
                code="governance.filesystem.reconciled_not_committed",
                category=FailureCategory.SIDE_EFFECT_FAILED,
                retryability=Retryability.NON_RETRYABLE,
                summary=(
                    "Reconciliation confirmed that the conditional publication was not committed."
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
            code="governance.filesystem.reconciled_conflict",
            category=FailureCategory.CONFLICT,
            retryability=Retryability.NON_RETRYABLE,
            summary="Reconciliation observed a different committed publication.",
            snapshot=snapshot,
        )

    def _compare_and_publish_locked(
        self,
        intent: PublicationIntent,
    ) -> ConditionalPublicationOutcome:
        current, metadata = self._inspect_with_metadata(intent.dataset_id)

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
                code="governance.filesystem.revision_conflict",
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
        except (KeyError, OSError, ValueError) as exc:
            return self._failure_outcome(
                intent,
                status=ConditionalPublicationStatus.FAILED,
                code="governance.filesystem.version_invalid",
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
        pointer = self._current_path(intent.dataset_id)
        pointer.parent.mkdir(parents=True, exist_ok=True)
        temporary = pointer.with_name(f".{pointer.name}.governed-{uuid4().hex}.tmp")
        payload = {
            "publication_schema": "1",
            "dataset_id": stored.dataset_id,
            "version_id": stored.version_id,
            "published_at": published_at.isoformat(),
            "published_from_run_id": str(intent.ingestion_run_id),
            _GOVERNANCE_REVISION: str(next_revision),
            _GOVERNANCE_OPERATION_ID: str(intent.operation_id),
            _GOVERNANCE_INTENT_FINGERPRINT: intent.intent_fingerprint,
        }

        replaced = False
        try:
            _write_json(temporary, payload)
            self._inject("before_replace")
            os.replace(temporary, pointer)
            replaced = True
            _fsync_directory(pointer.parent)
            self._inject("after_replace")
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            if replaced:
                self._append_unknown_best_effort(
                    intent,
                    current.revision,
                    next_revision,
                )
                return self._failure_outcome(
                    intent,
                    status=ConditionalPublicationStatus.UNKNOWN_OUTCOME,
                    code="governance.filesystem.unknown_outcome",
                    category=FailureCategory.UNKNOWN_OUTCOME,
                    retryability=Retryability.RETRYABLE_AFTER_RECONCILIATION,
                    uncertainty=OutcomeUncertainty.REQUIRES_RECONCILIATION,
                    summary=(
                        "Filesystem pointer may have been replaced; reconciliation is required."
                    ),
                )
            return self._failure_outcome(
                intent,
                status=ConditionalPublicationStatus.FAILED,
                code="governance.filesystem.publication_failed",
                category=FailureCategory.SIDE_EFFECT_FAILED,
                retryability=Retryability.RETRYABLE,
                summary=(
                    "Filesystem publication failed before pointer replacement: "
                    f"{type(exc).__name__}."
                ),
                snapshot=current,
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
                code="governance.filesystem.ledger_outcome_unknown",
                category=FailureCategory.UNKNOWN_OUTCOME,
                retryability=Retryability.RETRYABLE_AFTER_RECONCILIATION,
                uncertainty=OutcomeUncertainty.REQUIRES_RECONCILIATION,
                summary=("Pointer commit succeeded but durable outcome evidence is uncertain."),
            )

        return ConditionalPublicationOutcome(
            intent=intent,
            status=ConditionalPublicationStatus.SUCCEEDED,
            completed_at=self._now(),
            snapshot=snapshot,
            provider_operation_reference=self._provider_reference(intent),
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
                source_component="governance.filesystem",
                message_summary=summary,
            ),
            provider_operation_reference=self._provider_reference(intent),
        )

    def _inspect_with_metadata(
        self,
        dataset_id: str,
    ) -> tuple[PublicationSnapshot, dict[str, object]]:
        pointer = self._current_path(dataset_id)
        if pointer.is_symlink():
            raise ValueError("Published dataset pointer must be a regular non-symlink file.")
        if not pointer.exists():
            return (
                PublicationSnapshot(
                    dataset_id=dataset_id,
                    revision=PublicationRevision.initial(),
                ),
                {},
            )
        if not pointer.is_file():
            raise ValueError(
                "Published dataset pointer must be a regular non-symlink file."
            )

        try:
            raw = pointer.read_bytes()
            payload = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("Unable to inspect published dataset pointer.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Published dataset pointer must be a JSON object.")
        if payload.get("dataset_id") != dataset_id:
            raise ValueError("Published dataset pointer identity mismatch.")

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

    def _current_path(self, dataset_id: str) -> Path:
        return self._store.root / "published" / Path(*_dataset_parts(dataset_id)) / "current.json"

    def _lock_path(self, dataset_id: str) -> Path:
        pointer = self._current_path(dataset_id)
        return pointer.with_name(".current.governance.lock")

    def _provider_reference(self, intent: PublicationIntent) -> str:
        digest = hashlib.sha256(intent.dataset_id.encode("utf-8")).hexdigest()[:16]
        return f"filesystem-pointer:{digest}:{intent.operation_id}"

    def _inject(self, phase: str) -> None:
        if self._fault_injector is not None:
            self._fault_injector(phase)

    def _now(self) -> datetime:
        value = self._clock()
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("FileConditionalDatasetPublisher clock must return aware datetime.")
        return value


def _dataset_parts(dataset_id: str) -> tuple[str, ...]:
    if not isinstance(dataset_id, str) or not dataset_id.strip():
        raise ValueError("dataset_id must be non-blank.")
    if "/" in dataset_id or "\\" in dataset_id:
        raise ValueError(f"Invalid dataset_id: {dataset_id!r}")
    parts = tuple(dataset_id.split("."))
    if any(_DATASET_PART.fullmatch(part) is None for part in parts):
        raise ValueError(f"Invalid dataset_id: {dataset_id!r}")
    return parts


class _WindowsLockModule(Protocol):
    LK_NBLCK: int
    LK_UNLCK: int

    def locking(self, file_descriptor: int, mode: int, nbytes: int) -> None: ...


class _PosixLockModule(Protocol):
    LOCK_EX: int
    LOCK_NB: int
    LOCK_UN: int

    def flock(self, file_descriptor: int, operation: int) -> None: ...


@contextmanager
def _interprocess_lock(
    path: Path,
    *,
    timeout_seconds: float,
) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    deadline = time.monotonic() + timeout_seconds
    locked = False
    try:
        while True:
            try:
                _lock_handle(handle)
                locked = True
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise _LockTimeoutError(str(path)) from None
                time.sleep(0.01)
        yield
    finally:
        if locked:
            _unlock_handle(handle)
        handle.close()


def _windows_lock_module() -> _WindowsLockModule:
    return cast(_WindowsLockModule, importlib.import_module("msvcrt"))


def _posix_lock_module() -> _PosixLockModule:
    return cast(_PosixLockModule, importlib.import_module("fcntl"))


def _lock_handle(handle: BinaryIO) -> None:
    file_descriptor = handle.fileno()
    if os.name == "nt":
        module = _windows_lock_module()
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        module.locking(file_descriptor, module.LK_NBLCK, 1)
        return
    module = _posix_lock_module()
    module.flock(file_descriptor, module.LOCK_EX | module.LOCK_NB)


def _unlock_handle(handle: BinaryIO) -> None:
    file_descriptor = handle.fileno()
    if os.name == "nt":
        module = _windows_lock_module()
        handle.seek(0)
        module.locking(file_descriptor, module.LK_UNLCK, 1)
        return
    module = _posix_lock_module()
    module.flock(file_descriptor, module.LOCK_UN)


def _write_json(path: Path, payload: object) -> None:
    content = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    flags = getattr(os, "O_DIRECTORY", 0) | os.O_RDONLY
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
