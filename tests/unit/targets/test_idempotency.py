from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from pyingestkit import Dataset
from pyingestkit.metadata import MemoryMetadataStore, TargetLoadRecord
from pyingestkit.targets import (
    IdempotencyAction,
    IdempotencyPolicy,
    LoadMode,
    Target,
    TargetCapabilities,
    TargetLoadConflictError,
    TargetLoadExecutor,
    TargetLoadRequest,
    TargetLoadResult,
    TargetLoadStatus,
)


class _FakeTarget(Target):
    def __init__(self) -> None:
        self.calls = 0
        self._closed = False

    @property
    def target_id(self) -> str:
        return "fake.target"

    @property
    def capabilities(self) -> TargetCapabilities:
        return TargetCapabilities(transactional=True, append=True, truncate_load=True, replace=True)

    def open(self):
        return self

    def load(self, request: TargetLoadRequest) -> TargetLoadResult:
        self.calls += 1
        now = datetime.now(UTC)
        return TargetLoadResult(
            load_id=f"backend-{uuid4()}",
            target_id=self.target_id,
            dataset_id=request.dataset_id,
            dataset_version_id=request.dataset_version_id,
            run_id=request.run_id,
            mode=request.mode,
            status=TargetLoadStatus.SUCCESS,
            rows_input=request.dataset.row_count,
            rows_loaded=request.dataset.row_count,
            rows_verified=None,
            started_at=now,
            completed_at=now,
            duration_seconds=0.0,
            destination=self.resolve_destination(request),
        )

    def close(self) -> None:
        self._closed = True


class TargetLoadIdempotencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.target = _FakeTarget()
        self.store = MemoryMetadataStore()
        self.executor = TargetLoadExecutor(target=self.target, metadata_store=self.store)
        self.dataset = Dataset([{"id": 1}], fields=("id",))

    def _request(
        self,
        *,
        run_id: str,
        version: str | None = "v1",
        mode: LoadMode = LoadMode.APPEND,
        policy: IdempotencyPolicy = IdempotencyPolicy.AUTO,
    ) -> TargetLoadRequest:
        return TargetLoadRequest(
            target_id=self.target.target_id,
            dataset_id="demo.idempotency",
            dataset_version_id=version,
            run_id=run_id,
            dataset=self.dataset,
            table="target_table",
            mode=mode,
            idempotency_policy=policy,
        )

    def _record(
        self,
        *,
        load_id: str,
        version: str,
        status: TargetLoadStatus,
        mode: LoadMode = LoadMode.APPEND,
    ) -> None:
        now = datetime.now(UTC)
        self.store.record_target_load(
            TargetLoadRecord(
                load_id=load_id,
                run_id=f"prior-{load_id}",
                target_id=self.target.target_id,
                dataset_id="demo.idempotency",
                dataset_version_id=version,
                mode=mode.value,
                status=status.value,
                destination="target_table",
                rows_input=1,
                rows_loaded=1 if status is TargetLoadStatus.SUCCESS else 0,
                rows_verified=None,
                started_at=now,
                completed_at=now,
                duration_seconds=0.0,
                idempotency_action=None,
                metrics={},
                error=None,
                created_at=now,
            )
        )

    def test_same_successful_identity_is_skipped_and_audited(self) -> None:
        self._record(load_id="prior-success", version="v1", status=TargetLoadStatus.SUCCESS)

        result = self.executor.execute(self._request(run_id="run-skip"))

        self.assertIs(result.status, TargetLoadStatus.SKIPPED)
        self.assertIs(result.idempotency_action, IdempotencyAction.SKIP)
        self.assertEqual(self.target.calls, 0)
        rows = self.store.list_target_loads(run_id="run-skip")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, "SKIPPED")
        self.assertEqual(rows[0].idempotency_action, "skip")

    def test_failed_equivalent_load_is_retried(self) -> None:
        self._record(load_id="prior-failed", version="v1", status=TargetLoadStatus.ROLLED_BACK)

        result = self.executor.execute(self._request(run_id="run-retry"))

        self.assertIs(result.status, TargetLoadStatus.SUCCESS)
        self.assertIs(result.idempotency_action, IdempotencyAction.RETRY)
        self.assertEqual(self.target.calls, 1)

    def test_different_successful_version_is_reloaded(self) -> None:
        self._record(load_id="prior-v1", version="v1", status=TargetLoadStatus.SUCCESS)

        result = self.executor.execute(self._request(run_id="run-reload", version="v2"))

        self.assertIs(result.idempotency_action, IdempotencyAction.RELOAD)
        self.assertEqual(self.target.calls, 1)

    def test_active_equivalent_load_is_a_conflict(self) -> None:
        self._record(load_id="prior-running", version="v1", status=TargetLoadStatus.RUNNING)

        with self.assertRaises(TargetLoadConflictError):
            self.executor.execute(self._request(run_id="run-conflict"))
        self.assertEqual(self.target.calls, 0)

    def test_disabled_policy_executes_even_after_success(self) -> None:
        self._record(load_id="prior-success", version="v1", status=TargetLoadStatus.SUCCESS)

        result = self.executor.execute(
            self._request(run_id="run-force", policy=IdempotencyPolicy.DISABLED)
        )

        self.assertIs(result.idempotency_action, IdempotencyAction.EXECUTE)
        self.assertEqual(self.target.calls, 1)

    def test_auto_without_version_executes_but_does_not_claim_equivalence(self) -> None:
        result = self.executor.execute(self._request(run_id="run-unversioned", version=None))

        self.assertIs(result.idempotency_action, IdempotencyAction.EXECUTE)
        self.assertEqual(self.target.calls, 1)


if __name__ == "__main__":
    unittest.main()
