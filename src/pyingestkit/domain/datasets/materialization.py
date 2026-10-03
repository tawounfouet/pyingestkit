"""Dataset-version materialization requests for external produced resources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.shared.validation import (
    require_non_blank,
    validate_aware_datetime,
    validate_metadata,
)


@dataclass(frozen=True, slots=True)
class ResourceDatasetVersionRequestV2:
    """Promote one already-produced resource into governed DatasetVersion state."""

    dataset_id: str
    resource: ResourceReference
    ingestion_run_id: IngestionRunId
    created_at: datetime
    provenance: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        require_non_blank(self.dataset_id, "ResourceDatasetVersionRequestV2 dataset_id")
        if not isinstance(self.resource, ResourceReference):
            raise TypeError(
                "ResourceDatasetVersionRequestV2 resource must be ResourceReference."
            )
        if self.resource.locator is None:
            raise ValueError(
                "ResourceDatasetVersionRequestV2 requires a concrete resource locator."
            )
        if not isinstance(self.ingestion_run_id, IngestionRunId):
            raise TypeError(
                "ResourceDatasetVersionRequestV2 ingestion_run_id must be IngestionRunId."
            )
        validate_aware_datetime(
            self.created_at,
            "ResourceDatasetVersionRequestV2 created_at",
        )
        validate_metadata(
            self.provenance,
            name="ResourceDatasetVersionRequestV2 provenance",
        )
