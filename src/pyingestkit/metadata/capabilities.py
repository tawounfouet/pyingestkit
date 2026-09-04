from __future__ import annotations

from abc import ABC, abstractmethod

from .models import DiffRecord


class DiffMetadataCapability(ABC):
    """Optional metadata capability for V0.4 dataset-diff observation.

    This is deliberately separate from MetadataStore so third-party V0.3 stores
    remain valid without implementing new abstract methods.
    """

    @abstractmethod
    def record_dataset_diff(self, record: DiffRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_dataset_diffs(self, run_id: str) -> tuple[DiffRecord, ...]:
        raise NotImplementedError
