"""Immutable V2 replay request/result contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from pyingestkit.domain.artifacts import ArtifactReference
from pyingestkit.domain.datasets.references import DatasetVersionReference
from pyingestkit.domain.ingestion import IngestionDefinition
from pyingestkit.domain.runtime import IngestionResult
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.shared.validation import require_non_blank, validate_aware_datetime


@dataclass(frozen=True, slots=True)
class ReplayRequest:
    """Strict replay intent over one exact historical RAW artifact."""

    source_run_id: IngestionRunId
    definition: IngestionDefinition
    origin_raw_artifact: ArtifactReference
    expected_dataset_version: DatasetVersionReference | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_run_id, IngestionRunId):
            raise TypeError("ReplayRequest source_run_id must be IngestionRunId.")
        if not isinstance(self.definition, IngestionDefinition):
            raise TypeError("ReplayRequest definition must be IngestionDefinition.")
        if not isinstance(self.origin_raw_artifact, ArtifactReference):
            raise TypeError("ReplayRequest origin_raw_artifact must be ArtifactReference.")
        if self.origin_raw_artifact.kind != "raw":
            raise ValueError("ReplayRequest requires a RAW origin artifact.")
        if (
            self.origin_raw_artifact.checksum_algorithm != "sha256"
            or self.origin_raw_artifact.checksum is None
        ):
            raise ValueError("ReplayRequest requires SHA-256 origin RAW integrity evidence.")
        if self.expected_dataset_version is not None:
            if not isinstance(self.expected_dataset_version, DatasetVersionReference):
                raise TypeError(
                    "ReplayRequest expected_dataset_version must be DatasetVersionReference."
                )
            if self.expected_dataset_version.dataset_id != self.definition.dataset:
                raise ValueError(
                    "ReplayRequest expected dataset version must belong to definition dataset."
                )


@dataclass(frozen=True, slots=True)
class ReplayLineage:
    """Immutable causal lineage evidence between a source run and its replay run."""

    source_run_id: IngestionRunId
    replay_run_id: IngestionRunId
    dataset_id: str
    version_id: str
    origin_raw_checksum: str
    replay_raw_checksum: str
    matched: bool
    replayed_at: datetime
    published: bool = False
    lineage_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_run_id, IngestionRunId):
            raise TypeError("ReplayLineage source_run_id must be IngestionRunId.")
        if not isinstance(self.replay_run_id, IngestionRunId):
            raise TypeError("ReplayLineage replay_run_id must be IngestionRunId.")
        if self.source_run_id == self.replay_run_id:
            raise ValueError("ReplayLineage requires replay_run_id != source_run_id.")
        require_non_blank(self.dataset_id, "ReplayLineage dataset_id")
        require_non_blank(self.version_id, "ReplayLineage version_id")
        require_non_blank(self.origin_raw_checksum, "ReplayLineage origin_raw_checksum")
        require_non_blank(self.replay_raw_checksum, "ReplayLineage replay_raw_checksum")
        if self.origin_raw_checksum != self.replay_raw_checksum:
            raise ValueError("ReplayLineage origin and replay raw checksums must match.")
        if not isinstance(self.matched, bool):
            raise TypeError("ReplayLineage matched must be a boolean.")
        if not isinstance(self.replayed_at, datetime):
            raise TypeError("ReplayLineage replayed_at must be datetime.")
        validate_aware_datetime(self.replayed_at, "ReplayLineage replayed_at")
        if not isinstance(self.published, bool):
            raise TypeError("ReplayLineage published must be a boolean.")
        if self.lineage_id is not None:
            require_non_blank(self.lineage_id, "ReplayLineage lineage_id")
        else:
            object.__setattr__(self, "lineage_id", uuid4().hex)


@dataclass(frozen=True, slots=True)
class ReplayResult:
    """Strict replay evidence linking a new run to its historical RAW origin."""

    source_run_id: IngestionRunId
    origin_raw_artifact: ArtifactReference
    replay_raw_artifact: ArtifactReference
    ingestion: IngestionResult
    expected_dataset_version: DatasetVersionReference | None = None
    matched: bool | None = None
    lineage: ReplayLineage | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_run_id, IngestionRunId):
            raise TypeError("ReplayResult source_run_id must be IngestionRunId.")
        if not isinstance(self.origin_raw_artifact, ArtifactReference):
            raise TypeError("ReplayResult origin_raw_artifact must be ArtifactReference.")
        if not isinstance(self.replay_raw_artifact, ArtifactReference):
            raise TypeError("ReplayResult replay_raw_artifact must be ArtifactReference.")
        if not isinstance(self.ingestion, IngestionResult):
            raise TypeError("ReplayResult ingestion must be IngestionResult.")
        if self.ingestion.ingestion_run_id == self.source_run_id:
            raise ValueError("ReplayResult must use a new IngestionRunId.")
        if self.origin_raw_artifact.kind != "raw" or self.replay_raw_artifact.kind != "raw":
            raise ValueError("ReplayResult origin/replayed artifacts must both be RAW.")
        if self.replay_raw_artifact.checksum != self.origin_raw_artifact.checksum:
            raise ValueError("ReplayResult replayed RAW checksum must equal origin checksum.")
        if self.expected_dataset_version is not None and not isinstance(
            self.expected_dataset_version,
            DatasetVersionReference,
        ):
            raise TypeError(
                "ReplayResult expected_dataset_version must be DatasetVersionReference."
            )
        if self.matched is not None and not isinstance(self.matched, bool):
            raise TypeError("ReplayResult matched must be bool or None.")
        if self.expected_dataset_version is None and self.matched is not None:
            raise ValueError("ReplayResult matched requires expected_dataset_version.")
        if self.lineage is not None and not isinstance(self.lineage, ReplayLineage):
            raise TypeError("ReplayResult lineage must be ReplayLineage or None.")

    @property
    def succeeded(self) -> bool:
        return self.ingestion.succeeded and self.matched is not False

    @property
    def replay_run_id(self) -> IngestionRunId:
        return self.ingestion.ingestion_run_id
