"""Qualified V2 target materialization API during the V1 transition."""

from pyingestkit.adapters.postgres import PostgresTargetV2
from pyingestkit.domain.targets import (
    TargetLoadModeV2,
    TargetLoadRequestV2,
    TargetLoadResultV2,
    TargetLoadStatusV2,
)
from pyingestkit.ports.targets import DatasetTargetV2, TargetDescriptorV2

__all__ = [
    "DatasetTargetV2",
    "PostgresTargetV2",
    "TargetDescriptorV2",
    "TargetLoadModeV2",
    "TargetLoadRequestV2",
    "TargetLoadResultV2",
    "TargetLoadStatusV2",
]
