"""V2 published-dataset pointer semantics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pyingestkit.domain.datasets.references import DatasetVersionReference
from pyingestkit.domain.shared.identifiers import IngestionRunId
from pyingestkit.domain.shared.validation import require_non_blank, validate_aware_datetime


@dataclass(frozen=True, slots=True)
class PublishedDataset:
    """Immutable evidence for the currently published dataset version."""

    dataset_id: str
    version: DatasetVersionReference
    published_at: datetime
    published_from_run_id: IngestionRunId

    def __post_init__(self) -> None:
        require_non_blank(self.dataset_id, "PublishedDataset dataset_id")
        if not isinstance(self.version, DatasetVersionReference):
            raise TypeError("PublishedDataset version must be DatasetVersionReference.")
        if self.version.dataset_id != self.dataset_id:
            raise ValueError("PublishedDataset version must belong to dataset_id.")
        if not isinstance(self.published_at, datetime):
            raise TypeError("PublishedDataset published_at must be a datetime.")
        validate_aware_datetime(self.published_at, "PublishedDataset published_at")
        if not isinstance(self.published_from_run_id, IngestionRunId):
            raise TypeError("PublishedDataset published_from_run_id must be IngestionRunId.")

    @property
    def version_id(self) -> str:
        return self.version.version_id
