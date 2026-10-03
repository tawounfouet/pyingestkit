from __future__ import annotations

import pyingestkit.runtime as v1_runtime
from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_RUNTIME_VALUES,
)
from pyingestkit.runtime.v2 import IngestionResult, IngestionRun, IngestionRuntime


def test_lot10_phase_and_completed_lot_are_recorded() -> None:
    assert V2_API_PHASE == "LOT-10_INGESTION_RUNTIME"
    assert V2_COMPLETED_LOTS[-1] == "LOT-10"


def test_lot10_runtime_is_recorded_and_importable() -> None:
    assert "IngestionRuntime" in V2_IMPLEMENTED_RUNTIME_VALUES
    assert IngestionRuntime.__module__ == "pyingestkit.application.runtime"
    assert IngestionRun.__module__ == "pyingestkit.domain.runtime.execution"
    assert IngestionResult.__module__ == "pyingestkit.domain.runtime.execution"


def test_v1_runtime_namespace_remains_exact_during_lot10() -> None:
    assert v1_runtime.__all__ == ["Runner"]
