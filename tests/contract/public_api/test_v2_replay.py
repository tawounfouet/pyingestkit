from __future__ import annotations

import pyingestkit.replay as v1_replay
from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_REPLAY_VALUES,
)
from pyingestkit.replay.v2 import ReplayRequest, ReplayResult, ReplayServiceV2


def test_lot11_phase_and_completed_lot_are_recorded() -> None:
    assert V2_API_PHASE == "LOT-11_STRICT_REPLAY"
    assert V2_COMPLETED_LOTS[-1] == "LOT-11"


def test_lot11_replay_values_are_recorded_and_qualified() -> None:
    assert {"ReplayRequest", "ReplayResult", "ReplayServiceV2"}.issubset(
        V2_IMPLEMENTED_REPLAY_VALUES
    )
    assert ReplayRequest.__module__ == "pyingestkit.domain.replay.models"
    assert ReplayResult.__module__ == "pyingestkit.domain.replay.models"
    assert ReplayServiceV2.__module__ == "pyingestkit.application.replay"


def test_v1_replay_namespace_remains_exact_during_lot11() -> None:
    assert v1_replay.__all__ == [
        "ReplayContext",
        "ReplayRawArtifact",
        "ReplayResult",
        "ReplayService",
        "materialize_replayed_raw",
    ]
