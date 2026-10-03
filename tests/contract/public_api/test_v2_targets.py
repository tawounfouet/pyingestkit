from __future__ import annotations

from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_TARGET_VALUES,
)
from pyingestkit.targets.v2 import (
    DatasetTargetV2,
    PostgresTargetV2,
    TargetDescriptorV2,
    TargetLoadModeV2,
    TargetLoadRequestV2,
    TargetLoadResultV2,
    TargetLoadStatusV2,
)

_EXPECTED = (
    "DatasetTargetV2",
    "PostgresTargetV2",
    "TargetDescriptorV2",
    "TargetLoadModeV2",
    "TargetLoadRequestV2",
    "TargetLoadResultV2",
    "TargetLoadStatusV2",
)


def test_lot14_phase_and_completed_lot_are_recorded() -> None:
    assert V2_API_PHASE == "LOT-14_POSTGRES_TARGET"
    assert V2_COMPLETED_LOTS[-1] == "LOT-14"


def test_lot14_target_values_are_recorded_and_importable() -> None:
    assert V2_IMPLEMENTED_TARGET_VALUES == _EXPECTED
    values = (
        DatasetTargetV2,
        PostgresTargetV2,
        TargetDescriptorV2,
        TargetLoadModeV2,
        TargetLoadRequestV2,
        TargetLoadResultV2,
        TargetLoadStatusV2,
    )
    assert tuple(value.__name__ for value in values) == _EXPECTED
