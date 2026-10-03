from __future__ import annotations

import pyingestkit.runtime as public_runtime
import pyingestkit.runtime.v2 as v2_runtime
from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_RUNTIME_SURFACE,
    V2_RUNTIME_SURFACE_EXPORTS,
)


def test_lot12_phase_and_completed_lot_are_recorded() -> None:
    assert "LOT-12" in V2_COMPLETED_LOTS
    assert V2_COMPLETED_LOTS.index("LOT-12") <= V2_COMPLETED_LOTS.index(V2_COMPLETED_LOTS[-1])
    assert V2_API_PHASE.startswith("LOT-")


def test_runtime_root_is_promoted_at_rc() -> None:
    assert tuple(public_runtime.__all__) == V2_RUNTIME_SURFACE_EXPORTS
    assert "Runner" not in public_runtime.__all__


def test_lot12_v2_runtime_surface_is_explicit() -> None:
    assert V2_RUNTIME_SURFACE == "pyingestkit.runtime"
    assert {"IngestionResult", "IngestionRun", "IngestionRuntime"}.issubset(
        V2_RUNTIME_SURFACE_EXPORTS
    )
    assert set(v2_runtime.__all__).issubset(set(V2_RUNTIME_SURFACE_EXPORTS))
