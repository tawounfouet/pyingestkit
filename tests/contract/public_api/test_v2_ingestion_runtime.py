from __future__ import annotations

import pyingestkit.runtime as public_runtime
from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_RUNTIME_VALUES,
)
from pyingestkit.runtime.v2 import IngestionResult, IngestionRun, IngestionRuntime


def test_lot10_phase_and_completed_lot_are_recorded() -> None:
    assert "LOT-10" in V2_COMPLETED_LOTS
    assert V2_COMPLETED_LOTS.index("LOT-10") <= V2_COMPLETED_LOTS.index(V2_COMPLETED_LOTS[-1])
    assert V2_API_PHASE.startswith("LOT-")


def test_lot10_runtime_is_recorded_and_importable() -> None:
    assert "IngestionRuntime" in V2_IMPLEMENTED_RUNTIME_VALUES
    assert IngestionRuntime.__module__ == "pyingestkit.application.runtime"
    assert IngestionRun.__module__ == "pyingestkit.domain.runtime.execution"
    assert IngestionResult.__module__ == "pyingestkit.domain.runtime.execution"


def test_runtime_namespace_promotes_ingestion_runtime_at_rc() -> None:
    assert "IngestionRuntime" in public_runtime.__all__
    assert hasattr(IngestionRuntime, "run")
    assert "Runner" not in public_runtime.__all__
