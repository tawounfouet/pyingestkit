from __future__ import annotations

import time
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from pyingestkit.metadata import TargetLoadMetadataCapability, TargetLoadRecord

from .base import Target
from .errors import (
    TargetConfigurationError,
    TargetError,
    TargetLoadConflictError,
    TargetLoadError,
)
from .models import (
    IdempotencyAction,
    IdempotencyPolicy,
    TargetLoadDecision,
    TargetLoadRequest,
    TargetLoadResult,
    TargetLoadStatus,
)

_RETRYABLE = {"FAILED", "ROLLED_BACK"}
_ACTIVE = {"PENDING", "RUNNING"}


class TargetLoadExecutor:
    """Execute one Target load with history-driven idempotency and audit recording.

    This is deliberately a local execution service, not a workflow orchestrator. It
    keeps MetadataStore concerns outside Target implementations while making B1
    target-load history operationally useful.
    """

    def __init__(self, *, target: Target, metadata_store: TargetLoadMetadataCapability) -> None:
        self.target = target
        self.metadata_store = metadata_store

    def decide(self, request: TargetLoadRequest) -> TargetLoadDecision:
        self._validate_target(request)
        destination = self.target.resolve_destination(request)

        if request.idempotency_policy is IdempotencyPolicy.DISABLED:
            return TargetLoadDecision(
                action=IdempotencyAction.EXECUTE,
                reason="idempotency policy is disabled",
            )
        if request.dataset_version_id is None:
            return TargetLoadDecision(
                action=IdempotencyAction.EXECUTE,
                reason="dataset_version_id is unavailable; history cannot prove equivalence",
            )

        successful = self.metadata_store.list_target_loads(
            dataset_id=request.dataset_id,
            target_id=request.target_id,
            dataset_version_id=request.dataset_version_id,
            destination=destination,
            mode=request.mode.value,
            status=TargetLoadStatus.SUCCESS.value,
            limit=1,
        )
        if not successful:
            successful = self.metadata_store.list_target_loads(
                dataset_id=request.dataset_id,
                target_id=request.target_id,
                dataset_version_id=request.dataset_version_id,
                destination=destination,
                mode=request.mode.value,
                status=TargetLoadStatus.SKIPPED.value,
                limit=1,
            )
        if successful:
            prior = successful[0]
            return TargetLoadDecision(
                action=IdempotencyAction.SKIP,
                reason="same dataset version, destination and load mode already succeeded",
                prior_load_id=prior.load_id,
                prior_status=TargetLoadStatus(prior.status),
            )

        exact_latest = self.metadata_store.list_target_loads(
            dataset_id=request.dataset_id,
            target_id=request.target_id,
            dataset_version_id=request.dataset_version_id,
            destination=destination,
            mode=request.mode.value,
            limit=1,
        )
        if exact_latest:
            latest = exact_latest[0]
            if latest.status in _ACTIVE:
                raise TargetLoadConflictError(
                    "Equivalent target load is already active: "
                    f"load_id={latest.load_id} status={latest.status}"
                )
            if latest.status in _RETRYABLE:
                return TargetLoadDecision(
                    action=IdempotencyAction.RETRY,
                    reason="equivalent target load previously failed or rolled back",
                    prior_load_id=latest.load_id,
                    prior_status=TargetLoadStatus(latest.status),
                )

        previous_success = self.metadata_store.list_target_loads(
            dataset_id=request.dataset_id,
            target_id=request.target_id,
            destination=destination,
            status=TargetLoadStatus.SUCCESS.value,
            limit=1,
        )
        if previous_success:
            previous = previous_success[0]
            return TargetLoadDecision(
                action=IdempotencyAction.RELOAD,
                reason="destination has a successful load for a different version or mode",
                prior_load_id=previous.load_id,
                prior_status=TargetLoadStatus(previous.status),
            )

        return TargetLoadDecision(
            action=IdempotencyAction.EXECUTE,
            reason="no equivalent or previous successful target load exists",
        )

    def execute(self, request: TargetLoadRequest) -> TargetLoadResult:
        decision = self.decide(request)
        destination = self.target.resolve_destination(request)
        load_id = str(uuid4())
        started_at = datetime.now(UTC)
        started = time.perf_counter()

        if decision.action is IdempotencyAction.SKIP:
            completed_at = datetime.now(UTC)
            result = TargetLoadResult(
                load_id=load_id,
                target_id=request.target_id,
                dataset_id=request.dataset_id,
                dataset_version_id=request.dataset_version_id,
                run_id=request.run_id,
                mode=request.mode,
                status=TargetLoadStatus.SKIPPED,
                rows_input=request.dataset.row_count,
                rows_loaded=0,
                rows_verified=None,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=max(time.perf_counter() - started, 0.0),
                destination=destination,
                idempotency_action=decision.action,
                metrics={"skipped": 1},
            )
            self.metadata_store.record_target_load(TargetLoadRecord.from_result(result))
            return result

        self.metadata_store.record_target_load(
            TargetLoadRecord(
                load_id=load_id,
                run_id=request.run_id,
                target_id=request.target_id,
                dataset_id=request.dataset_id,
                dataset_version_id=request.dataset_version_id,
                mode=request.mode.value,
                status=TargetLoadStatus.RUNNING.value,
                destination=destination,
                rows_input=request.dataset.row_count,
                rows_loaded=0,
                rows_verified=None,
                started_at=started_at,
                completed_at=None,
                duration_seconds=None,
                idempotency_action=decision.action.value,
                metrics={},
                error=None,
                created_at=started_at,
            )
        )

        try:
            target_result = self.target.load(request)
        except TargetLoadError as exc:
            self._record_failure(
                request=request,
                load_id=load_id,
                destination=destination,
                started_at=started_at,
                started=started,
                action=decision.action,
                status=TargetLoadStatus.ROLLED_BACK,
                error=str(exc),
            )
            raise
        except TargetError as exc:
            self._record_failure(
                request=request,
                load_id=load_id,
                destination=destination,
                started_at=started_at,
                started=started,
                action=decision.action,
                status=TargetLoadStatus.FAILED,
                error=str(exc),
            )
            raise

        result = replace(
            target_result,
            load_id=load_id,
            idempotency_action=decision.action,
        )
        self.metadata_store.record_target_load(TargetLoadRecord.from_result(result))
        return result

    def _record_failure(
        self,
        *,
        request: TargetLoadRequest,
        load_id: str,
        destination: str,
        started_at: datetime,
        started: float,
        action: IdempotencyAction,
        status: TargetLoadStatus,
        error: str,
    ) -> None:
        completed_at = datetime.now(UTC)
        self.metadata_store.record_target_load(
            TargetLoadRecord(
                load_id=load_id,
                run_id=request.run_id,
                target_id=request.target_id,
                dataset_id=request.dataset_id,
                dataset_version_id=request.dataset_version_id,
                mode=request.mode.value,
                status=status.value,
                destination=destination,
                rows_input=request.dataset.row_count,
                rows_loaded=0,
                rows_verified=None,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=max(time.perf_counter() - started, 0.0),
                idempotency_action=action.value,
                metrics={},
                error=error,
                created_at=started_at,
            )
        )

    def _validate_target(self, request: TargetLoadRequest) -> None:
        if request.target_id != self.target.target_id:
            raise TargetConfigurationError(
                f"TargetLoadRequest targets {request.target_id!r}, "
                f"but executor target is {self.target.target_id!r}"
            )
