"""Ports for promoting externally produced resources into governed versions."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pyingestkit.domain.datasets import DatasetVersion
from pyingestkit.domain.datasets.materialization import ResourceDatasetVersionRequestV2


@runtime_checkable
class DatasetVersionMaterializerV2(Protocol):
    """Materialize one portable resource as an immutable DatasetVersion."""

    def materialize(
        self,
        request: ResourceDatasetVersionRequestV2,
    ) -> DatasetVersion: ...
