"""V2 target materialization port."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from pyingestkit.domain.shared.validation import require_non_blank
from pyingestkit.domain.targets import TargetLoadRequestV2, TargetLoadResultV2


@dataclass(frozen=True, slots=True)
class TargetDescriptorV2:
    """Portable target capabilities without exposing provider clients."""

    id: str
    display_name: str
    target_version: str
    transactional: bool
    bulk_load: bool
    supported_modes: tuple[str, ...]

    def __post_init__(self) -> None:
        require_non_blank(self.id, "TargetDescriptorV2 id")
        require_non_blank(self.display_name, "TargetDescriptorV2 display_name")
        require_non_blank(self.target_version, "TargetDescriptorV2 target_version")
        if not isinstance(self.transactional, bool):
            raise TypeError("TargetDescriptorV2 transactional must be bool.")
        if not isinstance(self.bulk_load, bool):
            raise TypeError("TargetDescriptorV2 bulk_load must be bool.")
        if not isinstance(self.supported_modes, tuple) or not self.supported_modes:
            raise ValueError("TargetDescriptorV2 supported_modes must be a non-empty tuple.")


@runtime_checkable
class DatasetTargetV2(Protocol):
    """Atomic materialization port for immutable dataset versions."""

    @property
    def descriptor(self) -> TargetDescriptorV2: ...

    def load(self, request: TargetLoadRequestV2) -> TargetLoadResultV2: ...

    def close(self) -> None: ...
