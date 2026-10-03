from __future__ import annotations

from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_S3_VALUES,
)
from pyingestkit.adapters.s3 import (
    S3ArtifactReaderV2,
    S3ArtifactStoreV2,
    S3ClientV2,
    S3DatasetVersionStoreV2,
)
from pyingestkit.stores import S3ArtifactStoreV2 as StoresS3ArtifactStoreV2
from pyingestkit.stores import S3DatasetVersionStoreV2 as StoresS3DatasetVersionStoreV2

_EXPECTED = (
    "S3ArtifactReaderV2",
    "S3ArtifactStoreV2",
    "S3ClientV2",
    "S3DatasetVersionStoreV2",
)


def test_lot15_phase_and_completed_lot_are_recorded() -> None:
    assert "LOT-15" in V2_COMPLETED_LOTS
    assert V2_COMPLETED_LOTS.index("LOT-15") <= V2_COMPLETED_LOTS.index(V2_COMPLETED_LOTS[-1])
    assert V2_API_PHASE.startswith("LOT-")


def test_lot15_s3_values_remain_recorded_and_importable() -> None:
    assert set(_EXPECTED).issubset(V2_IMPLEMENTED_S3_VALUES)
    values = (
        S3ArtifactReaderV2,
        S3ArtifactStoreV2,
        S3ClientV2,
        S3DatasetVersionStoreV2,
    )
    assert tuple(value.__name__ for value in values) == _EXPECTED
    assert StoresS3ArtifactStoreV2 is S3ArtifactStoreV2
    assert StoresS3DatasetVersionStoreV2 is S3DatasetVersionStoreV2
