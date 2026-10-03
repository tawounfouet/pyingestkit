"""Immutable V2 replay request/result contracts."""

from __future__ import annotations

from dataclasses import dataclass

from pyingestkit.domain.artifacts import ArtifactReference
from pyingestkit.domain.datasets.references import DatasetVersionReference
from pyingestkit.domain.ingestion import IngestionDefinition
from pyingestkit.domain.runtime import IngestionResult
from pyingestkit.domain.shared import IngestionRunId


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
class ReplayResult:
    """Strict replay evidence linking a new run to its historical RAW origin."""

    source_run_id: IngestionRunId
    origin_raw_artifact: ArtifactReference
    replay_raw_artifact: ArtifactReference
    ingestion: IngestionResult
    expected_dataset_version: DatasetVersionReference | None = None
    matched: bool | None = None

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

    @property
    def succeeded(self) -> bool:
        return self.ingestion.succeeded and self.matched is not False

    @property
    def replay_run_id(self) -> IngestionRunId:
        return self.ingestion.ingestion_run_id
