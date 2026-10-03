"""Portable semantic values used by the V1 -> V2 migration toolkit."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pyingestkit.domain.artifacts import ArtifactReference
from pyingestkit.domain.datasets import DatasetVersionReference, PublishedDataset
from pyingestkit.domain.ingestion import IngestionDefinition


class MigrationDisposition(StrEnum):
    """How safely one legacy semantic can be represented in V2."""

    EXACT = "exact"
    LOSSY = "lossy"
    MANUAL = "manual"
    UNSUPPORTED = "unsupported"


class StepOwnership(StrEnum):
    """Architectural owner for one V1 Step during migration."""

    ACQUISITION = "acquisition"
    INGESTION = "ingestion"
    TRANSFORMATION = "transformation"
    MATERIALIZATION = "materialization"
    OBSERVABILITY = "observability"
    ORCHESTRATION = "orchestration"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class MigrationIssue:
    code: str
    disposition: MigrationDisposition
    summary: str
    source_identity: str
    details: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class LegacyStepAssessment:
    step_name: str
    implementation_type: str
    ownership: StepOwnership
    disposition: MigrationDisposition
    reason: str


@dataclass(frozen=True, slots=True)
class CompatibilityShimDecision:
    shim: str
    decision: str
    reason: str


@dataclass(frozen=True, slots=True)
class MigrationReport:
    source_version: str
    target_version: str
    issues: tuple[MigrationIssue, ...] = ()
    step_assessments: tuple[LegacyStepAssessment, ...] = ()
    shim_decisions: tuple[CompatibilityShimDecision, ...] = ()

    @property
    def lossy_count(self) -> int:
        return sum(
            item.disposition is MigrationDisposition.LOSSY
            for item in self.issues
        )

    @property
    def manual_count(self) -> int:
        return sum(
            item.disposition is MigrationDisposition.MANUAL
            for item in self.issues
        )

    @property
    def unsupported_count(self) -> int:
        return sum(
            item.disposition is MigrationDisposition.UNSUPPORTED
            for item in self.issues
        )

    @property
    def safe_to_apply(self) -> bool:
        return self.manual_count == 0 and self.unsupported_count == 0


@dataclass(frozen=True, slots=True)
class LegacyReplayMigrationEvidence:
    run_id: str
    source_run_id: str
    source_job_id: str
    source_job_version: str
    executed_job_version: str
    verification_mode: str
    expected_fingerprint: str | None
    actual_fingerprint: str | None
    status: str


@dataclass(frozen=True, slots=True)
class V1MigrationResult:
    artifacts: tuple[ArtifactReference, ...]
    dataset_versions: tuple[DatasetVersionReference, ...]
    publications: tuple[PublishedDataset, ...]
    replays: tuple[LegacyReplayMigrationEvidence, ...]
    report: MigrationReport


@dataclass(frozen=True, slots=True)
class LegacyJobMigrationResult:
    definition: IngestionDefinition
    report: MigrationReport
