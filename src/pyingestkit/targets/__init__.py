"""Provider-neutral PyIngestKit 2.0 target contracts."""

from pyingestkit.domain.targets import (
    TargetLoadModeV2,
    TargetLoadRequestV2,
    TargetLoadResultV2,
    TargetLoadStatusV2,
)
from pyingestkit.ports.targets import DatasetTargetV2, TargetDescriptorV2

__all__ = [
    "DatasetTargetV2",
    "TargetDescriptorV2",
    "TargetLoadModeV2",
    "TargetLoadRequestV2",
    "TargetLoadResultV2",
    "TargetLoadStatusV2",
]
