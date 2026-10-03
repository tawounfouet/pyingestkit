"""In-memory reference implementation of the lifecycle PublicationLedger."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from threading import RLock

from pyingestkit.domain.datasets import DatasetVersionReference
from pyingestkit.domain.governance import (
    PublicationIntent,
    PublicationLifecycleEvent,
    PublicationLifecycleEventType,
    PublicationOperationId,
    VersionHold,
)
from pyingestkit.governance._ledger_codec import (
    assert_event_persistable,
    is_terminal_event,
)
from pyingestkit.domain.shared.validation import validate_aware_datetime
from pyingestkit.ports.governance import PublicationLedger


class MemoryPublicationLedger(PublicationLedger):
    """Deterministic reference ledger for tests and behavioral conformance."""

    def __init__(self) -> None:
        self._operations: dict[PublicationOperationId, PublicationIntent] = {}
        self._events: list[PublicationLifecycleEvent] = []
        self._events_by_id: dict[str, PublicationLifecycleEvent] = {}
        self._resolved: set[PublicationOperationId] = set()
        self._active_holds: dict[tuple[str, str], VersionHold] = {}
        self._lock = RLock()

    def register(self, intent: PublicationIntent) -> PublicationIntent:
        if not isinstance(intent, PublicationIntent):
            raise TypeError("MemoryPublicationLedger.register requires PublicationIntent.")
        with self._lock:
            existing = self._operations.get(intent.operation_id)
            if existing is not None:
                existing.assert_same_intent_as(intent)
                return existing
            self._operations[intent.operation_id] = intent
            return intent

    def append(self, event: PublicationLifecycleEvent) -> None:
        if not isinstance(event, PublicationLifecycleEvent):
            raise TypeError("MemoryPublicationLedger.append requires PublicationLifecycleEvent.")
        assert_event_persistable(event)
        with self._lock:
            existing_event = self._events_by_id.get(event.event_id)
            if existing_event is not None:
                if existing_event != event:
                    raise ValueError(
                        "Lifecycle event ID cannot be reused for different event evidence."
                    )
                return

            if event.operation_id is not None:
                intent = self._operations.get(event.operation_id)
                if intent is None:
                    raise KeyError(str(event.operation_id))
                if intent.dataset_id != event.dataset_id:
                    raise ValueError("Lifecycle event dataset does not match registered intent.")
                if event.operation_id in self._resolved:
                    raise ValueError("Resolved publication operation cannot accept new events.")

            self._events.append(event)
            self._events_by_id[event.event_id] = event
            if event.operation_id is not None and is_terminal_event(event.event_type):
                self._resolved.add(event.operation_id)

    def get_operation(self, operation_id: PublicationOperationId) -> PublicationIntent | None:
        if not isinstance(operation_id, PublicationOperationId):
            raise TypeError(
                "MemoryPublicationLedger.get_operation requires PublicationOperationId."
            )
        with self._lock:
            return self._operations.get(operation_id)

    def list_operations(self, dataset_id: str) -> tuple[PublicationIntent, ...]:
        if not isinstance(dataset_id, str) or not dataset_id.strip():
            raise ValueError("MemoryPublicationLedger dataset_id must be non-blank.")
        with self._lock:
            return tuple(
                sorted(
                    (
                        intent
                        for intent in self._operations.values()
                        if intent.dataset_id == dataset_id
                    ),
                    key=lambda item: (item.requested_at, str(item.operation_id)),
                )
            )

    def list_unresolved(
        self,
        dataset_id: str | None = None,
    ) -> tuple[PublicationIntent, ...]:
        if dataset_id is not None and (not isinstance(dataset_id, str) or not dataset_id.strip()):
            raise ValueError("MemoryPublicationLedger dataset_id must be non-blank or None.")
        with self._lock:
            values = (
                intent
                for operation_id, intent in self._operations.items()
                if operation_id not in self._resolved
                and (dataset_id is None or intent.dataset_id == dataset_id)
            )
            return tuple(
                sorted(values, key=lambda item: (item.requested_at, str(item.operation_id)))
            )

    def list_events(
        self,
        operation_id: PublicationOperationId | None = None,
        *,
        dataset_id: str | None = None,
    ) -> tuple[PublicationLifecycleEvent, ...]:
        """Inspect immutable event history in deterministic append order."""
        if operation_id is not None and not isinstance(operation_id, PublicationOperationId):
            raise TypeError(
                "MemoryPublicationLedger.list_events operation_id must be "
                "PublicationOperationId or None."
            )
        if dataset_id is not None and (not isinstance(dataset_id, str) or not dataset_id.strip()):
            raise ValueError("MemoryPublicationLedger dataset_id must be non-blank or None.")
        with self._lock:
            return tuple(
                event
                for event in self._events
                if (operation_id is None or event.operation_id == operation_id)
                and (dataset_id is None or event.dataset_id == dataset_id)
            )

    def place_hold(self, hold: VersionHold) -> VersionHold:
        if not isinstance(hold, VersionHold):
            raise TypeError("MemoryPublicationLedger.place_hold requires VersionHold.")
        with self._lock:
            existing = self._active_holds.get(hold.dataset_version.identity)
            if existing is not None:
                if existing != hold:
                    raise ValueError("Dataset version already has a different active hold.")
                return existing
            self._active_holds[hold.dataset_version.identity] = hold
            self.append(_hold_event(hold, PublicationLifecycleEventType.HOLD_PLACED, hold.held_at))
            return hold

    def release_hold(
        self,
        reference: DatasetVersionReference,
        *,
        released_at: datetime,
    ) -> bool:
        if not isinstance(reference, DatasetVersionReference):
            raise TypeError(
                "MemoryPublicationLedger.release_hold requires DatasetVersionReference."
            )
        validate_aware_datetime(released_at, "MemoryPublicationLedger released_at")
        with self._lock:
            hold = self._active_holds.get(reference.identity)
            if hold is None:
                return False
            if released_at < hold.held_at:
                raise ValueError("Version hold cannot be released before it was placed.")
            self.append(
                _hold_event(
                    hold,
                    PublicationLifecycleEventType.HOLD_RELEASED,
                    released_at,
                )
            )
            del self._active_holds[reference.identity]
            return True

    def list_active_holds(self, dataset_id: str) -> tuple[VersionHold, ...]:
        if not isinstance(dataset_id, str) or not dataset_id.strip():
            raise ValueError("MemoryPublicationLedger dataset_id must be non-blank.")
        with self._lock:
            return tuple(
                sorted(
                    (
                        hold
                        for hold in self._active_holds.values()
                        if hold.dataset_version.dataset_id == dataset_id
                    ),
                    key=lambda item: (
                        item.held_at,
                        item.dataset_version.version_id,
                    ),
                )
            )

    @contextmanager
    def transaction(self) -> Iterator[MemoryPublicationLedger]:
        """Group multiple ledger mutations atomically for conformance testing."""
        with self._lock:
            operations = dict(self._operations)
            events = list(self._events)
            events_by_id = dict(self._events_by_id)
            resolved = set(self._resolved)
            active_holds = dict(self._active_holds)
            try:
                yield self
            except BaseException:
                self._operations = operations
                self._events = events
                self._events_by_id = events_by_id
                self._resolved = resolved
                self._active_holds = active_holds
                raise


def _hold_event(
    hold: VersionHold,
    event_type: PublicationLifecycleEventType,
    occurred_at: datetime,
) -> PublicationLifecycleEvent:
    digest = hashlib.sha256(
        (
            f"{hold.dataset_version.dataset_id}\0"
            f"{hold.dataset_version.version_id}\0"
            f"{event_type.value}\0"
            f"{occurred_at.isoformat()}"
        ).encode("utf-8")
    ).hexdigest()
    metadata: tuple[tuple[str, str], ...] = ()
    if hold.reason is not None:
        metadata = (("reason", hold.reason),)
    return PublicationLifecycleEvent(
        event_id=f"hold:{digest}",
        event_type=event_type,
        dataset_id=hold.dataset_version.dataset_id,
        occurred_at=occurred_at,
        dataset_version=hold.dataset_version,
        metadata=metadata,
    )
