"""Portable LOT-06 quality evidence."""

from __future__ import annotations

from dataclasses import dataclass

from pyingestkit.domain.artifacts import ArtifactReference
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.shared.validation import require_non_blank
from pyingestkit.validation import ValidationResult


@dataclass(frozen=True, slots=True)
class QualityEvidence:
    """Immutable quality evidence independent from the legacy Runner."""

    ingestion_run_id: IngestionRunId
    correlation: CorrelationContext
    source_artifact: ArtifactReference
    decoder_id: str
    validation: ValidationResult
    evidence_version: str = "1"

    def __post_init__(self) -> None:
        if not isinstance(self.ingestion_run_id, IngestionRunId):
            raise TypeError("QualityEvidence ingestion_run_id must be an IngestionRunId.")
        if not isinstance(self.correlation, CorrelationContext):
            raise TypeError("QualityEvidence correlation must be a CorrelationContext.")
        if not isinstance(self.source_artifact, ArtifactReference):
            raise TypeError("QualityEvidence source_artifact must be an ArtifactReference.")
        require_non_blank(self.decoder_id, "QualityEvidence decoder_id")
        if not isinstance(self.validation, ValidationResult):
            raise TypeError("QualityEvidence validation must be ValidationResult.")
        if self.evidence_version != "1":
            raise ValueError("QualityEvidence evidence_version must be '1'.")
