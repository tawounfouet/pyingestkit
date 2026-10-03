"""Pure retention planning and lifecycle-state capture for PyIngestKit LOT-27."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol, runtime_checkable

from pyingestkit.domain.datasets import DatasetVersionReference
from pyingestkit.domain.governance import (
    GarbageCollectionPlan,
    GarbageCollectionPlanId,
    PublicationIntent,
    PublicationLifecycleEvent,
    PublicationLifecycleEventType,
    PublicationSnapshot,
    RetentionPolicy,
    VersionHold,
)
from pyingestkit.domain.shared.validation import require_non_blank, validate_aware_datetime
from pyingestkit.ports.dataset_versions import DatasetVersionStore
from pyingestkit.ports.governance import ConditionalDatasetPublisher, PublicationLedger


@runtime_checkable
class VersionHoldRepository(Protocol):
    """Additive hold persistence kept outside the frozen PublicationLedger port."""

    def place_hold(self, hold: VersionHold) -> VersionHold: ...

    def release_hold(
        self,
        reference: DatasetVersionReference,
        *,
        released_at: datetime,
    ) -> bool: ...

    def list_active_holds(self, dataset_id: str) -> tuple[VersionHold, ...]: ...


@dataclass(frozen=True, slots=True)
class RetentionState:
    """Read-only lifecycle evidence consumed by the pure retention planner."""

    dataset_id: str
    inventory: tuple[DatasetVersionReference, ...]
    current: PublicationSnapshot
    active_holds: tuple[VersionHold, ...]
    unresolved_operations: tuple[PublicationIntent, ...]
    verified_versions: tuple[DatasetVersionReference, ...]

    def __post_init__(self) -> None:
        require_non_blank(self.dataset_id, "RetentionState dataset_id")
        if self.current.dataset_id != self.dataset_id:
            raise ValueError("RetentionState current publication dataset mismatch.")
        inventory_ids = _validate_references(
            self.inventory,
            dataset_id=self.dataset_id,
            name="RetentionState inventory",
        )
        verified_ids = _validate_references(
            self.verified_versions,
            dataset_id=self.dataset_id,
            name="RetentionState verified_versions",
        )
        if not verified_ids.issubset(inventory_ids):
            raise ValueError("RetentionState verified versions must belong to inventory.")
        for hold in self.active_holds:
            if not isinstance(hold, VersionHold):
                raise TypeError("RetentionState active_holds must contain VersionHold values.")
            if hold.dataset_version.dataset_id != self.dataset_id:
                raise ValueError("RetentionState contains a foreign active hold.")
        for intent in self.unresolved_operations:
            if not isinstance(intent, PublicationIntent):
                raise TypeError(
                    "RetentionState unresolved_operations must contain PublicationIntent values."
                )
            if intent.dataset_id != self.dataset_id:
                raise ValueError("RetentionState contains a foreign unresolved operation.")


class RetentionStateLoader:
    """Capture provider truth without performing destructive lifecycle actions."""

    def __init__(
        self,
        *,
        store: DatasetVersionStore,
        publisher: ConditionalDatasetPublisher,
        ledger: PublicationLedger,
        holds: VersionHoldRepository,
    ) -> None:
        if not isinstance(store, DatasetVersionStore):
            raise TypeError("RetentionStateLoader store must satisfy DatasetVersionStore.")
        if not isinstance(publisher, ConditionalDatasetPublisher):
            raise TypeError(
                "RetentionStateLoader publisher must satisfy ConditionalDatasetPublisher."
            )
        if not isinstance(ledger, PublicationLedger):
            raise TypeError("RetentionStateLoader ledger must satisfy PublicationLedger.")
        if not isinstance(holds, VersionHoldRepository):
            raise TypeError("RetentionStateLoader holds must satisfy VersionHoldRepository.")
        self._store = store
        self._publisher = publisher
        self._ledger = ledger
        self._holds = holds

    def capture(self, dataset_id: str) -> RetentionState:
        require_non_blank(dataset_id, "RetentionStateLoader dataset_id")
        inventory = self._store.list(dataset_id)
        verified: list[DatasetVersionReference] = []
        for reference in inventory:
            verification_succeeded = True
            try:
                self._store.read(reference)
            except Exception:  # noqa: BLE001 - any verification failure protects the version
                verification_succeeded = False
            if verification_succeeded:
                verified.append(reference)
        return RetentionState(
            dataset_id=dataset_id,
            inventory=inventory,
            current=self._publisher.inspect(dataset_id),
            active_holds=self._holds.list_active_holds(dataset_id),
            unresolved_operations=self._ledger.list_unresolved(dataset_id),
            verified_versions=tuple(verified),
        )


class RetentionPlanner:
    """Deterministically derive one immutable GC plan from captured lifecycle state."""

    @staticmethod
    def plan(
        state: RetentionState,
        *,
        policy: RetentionPolicy,
        created_at: datetime,
        plan_id: GarbageCollectionPlanId | None = None,
    ) -> GarbageCollectionPlan:
        if not isinstance(state, RetentionState):
            raise TypeError("RetentionPlanner.plan requires RetentionState.")
        if not isinstance(policy, RetentionPolicy):
            raise TypeError("RetentionPlanner.plan policy must be RetentionPolicy.")
        validate_aware_datetime(created_at, "RetentionPlanner created_at")
        resolved_plan_id = plan_id or GarbageCollectionPlanId.new()
        if not isinstance(resolved_plan_id, GarbageCollectionPlanId):
            raise TypeError("RetentionPlanner plan_id must be GarbageCollectionPlanId or None.")

        ordered = tuple(sorted(state.inventory, key=_retention_sort_key, reverse=True))
        inventory_by_id = {reference.identity: reference for reference in ordered}
        verified_ids = {reference.identity for reference in state.verified_versions}
        protected_ids: set[tuple[str, str]] = set()

        protected_ids.update(reference.identity for reference in ordered[: policy.keep_last])
        protected_ids.update(
            hold.dataset_version.identity
            for hold in state.active_holds
            if hold.dataset_version.identity in inventory_by_id
        )
        protected_ids.update(
            intent.dataset_version.identity
            for intent in state.unresolved_operations
            if intent.dataset_version.identity in inventory_by_id
        )
        if state.current.published_dataset is not None:
            current_identity = state.current.published_dataset.version.identity
            if current_identity in inventory_by_id:
                protected_ids.add(current_identity)

        protected_ids.update(set(inventory_by_id).difference(verified_ids))

        if policy.min_age_seconds is not None:
            cutoff = created_at - timedelta(seconds=policy.min_age_seconds)
            for reference in ordered:
                if reference.created_at is None or reference.created_at > cutoff:
                    protected_ids.add(reference.identity)

        protected = tuple(reference for reference in ordered if reference.identity in protected_ids)
        candidates = tuple(
            reference for reference in ordered if reference.identity not in protected_ids
        )
        evidence = RetentionPlanner.evidence_fingerprint(
            state,
            policy=policy,
            created_at=created_at,
        )
        return GarbageCollectionPlan(
            plan_id=resolved_plan_id,
            dataset_id=state.dataset_id,
            created_at=created_at,
            policy=policy,
            protected_versions=protected,
            candidate_versions=candidates,
            evidence_fingerprint=evidence,
        )

    @staticmethod
    def evidence_fingerprint(
        state: RetentionState,
        *,
        policy: RetentionPolicy,
        created_at: datetime,
    ) -> str:
        if not isinstance(state, RetentionState):
            raise TypeError("RetentionPlanner.evidence_fingerprint requires RetentionState.")
        if not isinstance(policy, RetentionPolicy):
            raise TypeError("RetentionPlanner policy must be RetentionPolicy.")
        validate_aware_datetime(created_at, "RetentionPlanner evidence created_at")
        current = state.current.published_dataset
        payload = {
            "dataset_id": state.dataset_id,
            "created_at": created_at.isoformat(),
            "policy": {
                "keep_last": policy.keep_last,
                "min_age_seconds": policy.min_age_seconds,
            },
            "inventory": [
                {
                    "dataset_id": reference.dataset_id,
                    "version_id": reference.version_id,
                    "created_at": (
                        None if reference.created_at is None else reference.created_at.isoformat()
                    ),
                }
                for reference in sorted(state.inventory, key=_retention_sort_key, reverse=True)
            ],
            "current": {
                "revision": str(state.current.revision),
                "version_id": None if current is None else current.version.version_id,
            },
            "active_holds": [
                {
                    "version_id": hold.dataset_version.version_id,
                    "held_at": hold.held_at.isoformat(),
                    "reason": hold.reason,
                }
                for hold in sorted(
                    state.active_holds,
                    key=lambda item: (
                        item.dataset_version.version_id,
                        item.held_at,
                        item.reason or "",
                    ),
                )
            ],
            "unresolved": [
                {
                    "operation_id": str(intent.operation_id),
                    "version_id": intent.dataset_version.version_id,
                    "expected_revision": str(intent.expected_revision),
                    "intent_fingerprint": intent.intent_fingerprint,
                }
                for intent in sorted(
                    state.unresolved_operations,
                    key=lambda item: (item.requested_at, str(item.operation_id)),
                )
            ],
            "verified": sorted(reference.version_id for reference in state.verified_versions),
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return f"sha256-{hashlib.sha256(encoded).hexdigest()}"


def record_retention_plan(
    ledger: PublicationLedger,
    plan: GarbageCollectionPlan,
) -> None:
    """Persist append-only evidence that one immutable GC plan was created."""
    if not isinstance(ledger, PublicationLedger):
        raise TypeError("record_retention_plan ledger must satisfy PublicationLedger.")
    if not isinstance(plan, GarbageCollectionPlan):
        raise TypeError("record_retention_plan requires GarbageCollectionPlan.")
    ledger.append(
        PublicationLifecycleEvent(
            event_id=f"retention-plan:{plan.plan_id}",
            event_type=PublicationLifecycleEventType.RETENTION_PLAN_CREATED,
            dataset_id=plan.dataset_id,
            occurred_at=plan.created_at,
            metadata=(
                ("plan_id", str(plan.plan_id)),
                ("evidence_fingerprint", plan.evidence_fingerprint),
                ("protected_count", str(len(plan.protected_versions))),
                ("candidate_count", str(len(plan.candidate_versions))),
            ),
        )
    )


def _retention_sort_key(reference: DatasetVersionReference) -> tuple[float, str]:
    return (
        reference.created_at.timestamp() if reference.created_at is not None else float("-inf"),
        reference.version_id,
    )


def _validate_references(
    references: tuple[DatasetVersionReference, ...],
    *,
    dataset_id: str,
    name: str,
) -> set[tuple[str, str]]:
    if not isinstance(references, tuple):
        raise TypeError(f"{name} must be a tuple.")
    identities: set[tuple[str, str]] = set()
    for reference in references:
        if not isinstance(reference, DatasetVersionReference):
            raise TypeError(f"{name} must contain DatasetVersionReference values.")
        if reference.dataset_id != dataset_id:
            raise ValueError(f"{name} contains a foreign dataset version.")
        if reference.identity in identities:
            raise ValueError(f"{name} contains duplicate dataset-version identity.")
        identities.add(reference.identity)
    return identities


__all__ = [
    "RetentionPlanner",
    "RetentionState",
    "RetentionStateLoader",
    "VersionHoldRepository",
    "record_retention_plan",
]
