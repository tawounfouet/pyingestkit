"""V2 dataset-version persistence and publication ports."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from pyingestkit.domain.datasets.publication import PublishedDataset
from pyingestkit.domain.datasets.references import DatasetVersionReference
from pyingestkit.domain.datasets.version import DatasetVersion
from pyingestkit.domain.decoding.models import DecodedRepresentation
from pyingestkit.domain.shared.identifiers import IngestionRunId


@runtime_checkable
class DatasetVersionStore(Protocol):
    """Durable immutable storage for logical dataset versions."""

    def put(self, version: DatasetVersion) -> DatasetVersionReference: ...

    def get(self, dataset_id: str, version_id: str) -> DatasetVersionReference: ...

    def list(self, dataset_id: str) -> tuple[DatasetVersionReference, ...]: ...

    def read(self, reference: DatasetVersionReference) -> DecodedRepresentation: ...


@runtime_checkable
class DatasetPublisher(Protocol):
    """Atomic current-pointer publication over stored dataset versions."""

    def publish(
        self,
        reference: DatasetVersionReference,
        *,
        ingestion_run_id: IngestionRunId,
        published_at: datetime,
    ) -> PublishedDataset: ...

    def get_published(self, dataset_id: str) -> PublishedDataset | None: ...
