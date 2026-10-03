from __future__ import annotations

import pyingestkit.runtime as v1_runtime
from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_RUNTIME_VALUES,
)
from pyingestkit.runtime.v2 import IngestionResult, IngestionRun


def test_lot09_phase_and_completed_lot_are_recorded() -> None:
    assert "LOT-09" in V2_COMPLETED_LOTS
    assert V2_COMPLETED_LOTS.index("LOT-09") <= V2_COMPLETED_LOTS.index(V2_COMPLETED_LOTS[-1])
    assert V2_API_PHASE.startswith("LOT-")


def test_lot09_public_values_are_recorded() -> None:
    assert {"IngestionResult", "IngestionRun"}.issubset(V2_IMPLEMENTED_RUNTIME_VALUES)


def test_lot09_symbols_are_importable_from_qualified_v2_runtime() -> None:
    assert IngestionRun.__module__ == "pyingestkit.domain.runtime.execution"
    assert IngestionResult.__module__ == "pyingestkit.domain.runtime.execution"


def test_v1_runtime_export_surface_remains_exact() -> None:
    assert v1_runtime.__all__ == ["Runner"]
