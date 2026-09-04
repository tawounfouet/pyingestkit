from __future__ import annotations

from abc import ABC, abstractmethod

from .models import (
    DatasetVersionRecord,
    DatasetVersionRunRecord,
    DiffRecord,
    PublishedDatasetRecord,
    ReplayRecord,
    ReproducibilityRecord,
    TargetLoadRecord,
)


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


class VersionMetadataCapability(ABC):
    """Optional capability for immutable Dataset version and published-pointer metadata."""

    @abstractmethod
    def record_dataset_version(self, record: DatasetVersionRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def record_dataset_version_run(self, record: DatasetVersionRunRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_dataset_versions(self, dataset_id: str) -> tuple[DatasetVersionRecord, ...]:
        raise NotImplementedError

    @abstractmethod
    def record_published_dataset(self, record: PublishedDatasetRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_published_dataset(self, dataset_id: str) -> PublishedDatasetRecord | None:
        raise NotImplementedError


class ReplayMetadataCapability(ABC):
    """Optional capability for replay lineage and reproducibility metadata."""

    @abstractmethod
    def record_replay_run(self, record: ReplayRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_replay_run(self, run_id: str) -> ReplayRecord | None:
        raise NotImplementedError

    @abstractmethod
    def record_run_reproducibility(self, record: ReproducibilityRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_run_reproducibility(self, run_id: str) -> ReproducibilityRecord | None:
        raise NotImplementedError

    @abstractmethod
    def find_expected_fingerprint_for_run(self, run_id: str, dataset_id: str) -> str | None:
        raise NotImplementedError

class TargetLoadMetadataCapability(ABC):
    """Optional capability for auditable target materialization records.

    Kept separate from MetadataStore so existing third-party stores remain valid.
    B1 persists facts only; load-mode idempotency remains a B2 concern.
    """

    @abstractmethod
    def record_target_load(self, record: TargetLoadRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_target_load(self, load_id: str) -> TargetLoadRecord | None:
        raise NotImplementedError

    @abstractmethod
    def list_target_loads(
        self,
        *,
        run_id: str | None = None,
        dataset_id: str | None = None,
        target_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> tuple[TargetLoadRecord, ...]:
        raise NotImplementedError
