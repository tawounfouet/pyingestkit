from __future__ import annotations

import inspect

import pyingestkit
import pyingestkit.governance as governance
import pyingestkit.governance.rollback as rollback
from pyingestkit.application.replay import ReplayServiceV2
from pyingestkit.governance.rollback import GovernedRollbackService
from pyingestkit.ports.governance import (
    ConditionalDatasetPublisher,
    DatasetVersionGarbageCollector,
    PublicationLedger,
)


def test_lot28_rollback_service_is_qualified_only() -> None:
    assert rollback.__all__ == ["GovernedRollbackService"]
    assert GovernedRollbackService.__module__ == "pyingestkit.governance.rollback"
    assert "GovernedRollbackService" not in governance.__all__
    assert "GovernedRollbackService" not in pyingestkit.__all__


def test_lot28_does_not_expand_frozen_governance_protocols() -> None:
    assert set(vars(PublicationLedger)).issuperset(
        {"register", "append", "get_operation", "list_operations", "list_unresolved"}
    )
    assert set(vars(ConditionalDatasetPublisher)).issuperset(
        {"inspect", "compare_and_publish"}
    )
    assert set(vars(DatasetVersionGarbageCollector)).issuperset(
        {"delete", "reconcile_delete"}
    )


def test_lot28_strict_replay_still_calls_runtime_with_publish_false() -> None:
    source = inspect.getsource(ReplayServiceV2.replay)
    assert "publish=False" in source
    assert "GovernedRollbackService" not in source
