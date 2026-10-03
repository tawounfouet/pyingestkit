"""Explicit semantic migration from maintained V1 public contracts into V2."""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlsplit

from pyingestkit.core.job import Job
from pyingestkit.declarative.step_definition import FunctionStep
from pyingestkit.domain.artifacts import ArtifactReference
from pyingestkit.domain.datasets import DatasetVersionReference
from pyingestkit.domain.datasets.publication import PublishedDataset
from pyingestkit.domain.ingestion import IngestionDefinition
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.sources import Source

from .export import V1SemanticExport
from .models import (
    CompatibilityShimDecision,
    LegacyJobMigrationResult,
    LegacyReplayMigrationEvidence,
    LegacyStepAssessment,
    MigrationDisposition,
    MigrationIssue,
    MigrationReport,
    StepOwnership,
    V1MigrationResult,
)

_SHIM_DECISIONS = (
    CompatibilityShimDecision(
        shim="V2 Job alias",
        decision="rejected",
        reason=(
            "V2 authoring root is IngestionDefinition; generic Job alias would "
            "preserve wrong semantics."
        ),
    ),
    CompatibilityShimDecision(
        shim="V2 Pipeline alias",
        decision="rejected",
        reason=(
            "Scheduling/orchestration and transformation DAGs are not PyIngestKit V2 core concepts."
        ),
    ),
    CompatibilityShimDecision(
        shim="V2 Step alias",
        decision="rejected",
        reason=(
            "Arbitrary Python Step execution cannot be migrated without ownership classification."
        ),
    ),
    CompatibilityShimDecision(
        shim="V1 private metadata table reader",
        decision="rejected",
        reason="Migration consumes public record contracts or portable semantic exports only.",
    ),
    CompatibilityShimDecision(
        shim="migration-only public-record adapter",
        decision="accepted",
        reason="A one-way anti-corruption layer can preserve semantics without polluting V2 core.",
    ),
)


class LegacyJobMigrationHints:
    """Explicit information V1 Job alone cannot safely reveal."""

    def __init__(
        self,
        *,
        source: Source,
        decoder: str,
        dataset: str,
        validation_policy: str | None = None,
        versioning_policy: str | None = None,
        publication_policy: str | None = None,
        options: tuple[tuple[str, str], ...] = (),
        metadata: tuple[tuple[str, str], ...] = (),
        step_ownership: tuple[tuple[str, StepOwnership], ...] = (),
    ) -> None:
        if not isinstance(source, Source):
            raise TypeError("LegacyJobMigrationHints source must be V2 Source.")
        if not isinstance(decoder, str) or not decoder.strip():
            raise ValueError("LegacyJobMigrationHints decoder must be non-blank.")
        if not isinstance(dataset, str) or not dataset.strip():
            raise ValueError("LegacyJobMigrationHints dataset must be non-blank.")
        if any(not isinstance(item, tuple) or len(item) != 2 for item in step_ownership):
            raise TypeError("LegacyJobMigrationHints step_ownership must contain pairs.")
        if any(not isinstance(owner, StepOwnership) for _, owner in step_ownership):
            raise TypeError("LegacyJobMigrationHints ownership values must be StepOwnership.")
        self.source = source
        self.decoder = decoder
        self.dataset = dataset
        self.validation_policy = validation_policy
        self.versioning_policy = versioning_policy
        self.publication_policy = publication_policy
        self.options = options
        self.metadata = metadata
        self.step_ownership = step_ownership

    def ownership_for(self, step_name: str) -> StepOwnership | None:
        values = dict(self.step_ownership)
        return values.get(step_name)


class V1JobMigrator:
    """Convert V1 Job identity/configuration into V2 ingestion intent with explicit gaps."""

    def migrate(self, job: Job, hints: LegacyJobMigrationHints) -> LegacyJobMigrationResult:
        if not isinstance(job, Job):
            raise TypeError("V1JobMigrator expects a V1 Job.")
        if not isinstance(hints, LegacyJobMigrationHints):
            raise TypeError("V1JobMigrator expects LegacyJobMigrationHints.")

        issues: list[MigrationIssue] = []
        assessments: list[LegacyStepAssessment] = []
        pipeline = job.pipeline()

        for step in pipeline:
            owner = hints.ownership_for(step.name)
            if owner is None:
                owner = (
                    StepOwnership.TRANSFORMATION
                    if isinstance(step, FunctionStep)
                    else StepOwnership.UNKNOWN
                )
            disposition, reason = _step_disposition(owner)
            assessments.append(
                LegacyStepAssessment(
                    step_name=step.name,
                    implementation_type=f"{type(step).__module__}.{type(step).__qualname__}",
                    ownership=owner,
                    disposition=disposition,
                    reason=reason,
                )
            )
            if disposition is not MigrationDisposition.EXACT:
                issues.append(
                    MigrationIssue(
                        code="job.step.requires_explicit_migration",
                        disposition=disposition,
                        summary=reason,
                        source_identity=f"{job.id}:{step.name}",
                        details=(("ownership", owner.value),),
                    )
                )

        if job.depends_on:
            issues.append(
                MigrationIssue(
                    code="job.dependencies.orchestration_externalized",
                    disposition=MigrationDisposition.MANUAL,
                    summary=(
                        "V1 job dependencies belong to orchestration and are not copied into "
                        "IngestionDefinition."
                    ),
                    source_identity=job.id,
                    details=(("depends_on", ",".join(job.depends_on)),),
                )
            )

        metadata = tuple(hints.metadata) + (
            ("migration.source_framework", "pyingestkit-v1"),
            ("migration.v1.job_id", job.id),
            ("migration.v1.job_version", job.version),
            ("migration.v1.definition_style", job.definition_style),
        )
        definition = IngestionDefinition(
            name=job.id,
            source=hints.source,
            decoder=hints.decoder,
            dataset=hints.dataset,
            validation_policy=hints.validation_policy,
            versioning_policy=hints.versioning_policy,
            publication_policy=hints.publication_policy,
            options=hints.options,
            metadata=metadata,
        )
        return LegacyJobMigrationResult(
            definition=definition,
            report=MigrationReport(
                source_version=job.version,
                target_version="2",
                issues=tuple(issues),
                step_assessments=tuple(assessments),
                shim_decisions=_SHIM_DECISIONS,
            ),
        )


class V1SemanticImporter:
    """Import one portable V1 semantic export into V2 reference contracts."""

    def import_export(self, export: V1SemanticExport) -> V1MigrationResult:
        if not isinstance(export, V1SemanticExport):
            raise TypeError("V1SemanticImporter expects V1SemanticExport.")

        issues: list[MigrationIssue] = []
        artifacts: list[ArtifactReference] = []
        artifact_by_id: dict[str, ArtifactReference] = {}

        for item in export.artifacts:
            locator = item.storage_uri or item.path
            if item.source_uri or item.resolved_url:
                issues.append(
                    MigrationIssue(
                        code="artifact.source_locator.not_promoted",
                        disposition=MigrationDisposition.LOSSY,
                        summary=(
                            "Historical source URLs remain migration input evidence but are "
                            "not promoted into portable V2 artifact metadata."
                        ),
                        source_identity=item.artifact_id,
                    )
                )
            if item.storage_uri is None:
                issues.append(
                    MigrationIssue(
                        code="artifact.remote_locator.unavailable",
                        disposition=MigrationDisposition.LOSSY,
                        summary=(
                            "V1 artifact has no remote storage URI; migration retains its "
                            "workspace path as a local-only locator."
                        ),
                        source_identity=item.artifact_id,
                        details=(("path", item.path),),
                    )
                )
            resource = ResourceReference(
                namespace="pyingestkit.migration.v1.artifact",
                resource_id=_stable_id("artifact", locator),
                locator=locator,
                media_type=item.content_type,
                format=_format_from_locator(locator),
                metadata=_metadata(
                    ("v1.run_id", item.run_id),
                    ("v1.status_code", item.status_code),
                    ("v1.etag", item.etag),
                    ("v1.last_modified", item.last_modified),
                ),
            )
            reference = ArtifactReference(
                artifact_id=item.artifact_id,
                kind=item.kind,
                resource=resource,
                checksum=item.sha256,
                checksum_algorithm="sha256",
                media_type=item.content_type,
                size_bytes=item.size_bytes,
                created_at=_aware_datetime(item.created_at, "artifact created_at"),
                metadata=(("migration.source", "v1"),),
            )
            artifacts.append(reference)
            artifact_by_id[item.artifact_id] = reference

        versions: list[DatasetVersionReference] = []
        version_by_identity: dict[tuple[str, str], DatasetVersionReference] = {}
        for item in export.dataset_versions:
            artifact = (
                None
                if item.source_artifact_id is None
                else artifact_by_id.get(item.source_artifact_id)
            )
            if item.source_artifact_id is not None and artifact is None:
                issues.append(
                    MigrationIssue(
                        code="dataset_version.source_artifact.unresolved",
                        disposition=MigrationDisposition.LOSSY,
                        summary="V1 source artifact identity could not be resolved in this export.",
                        source_identity=f"{item.dataset_id}:{item.version_id}",
                        details=(("source_artifact_id", item.source_artifact_id),),
                    )
                )
            issues.append(
                MigrationIssue(
                    code="dataset_version.schema_fingerprint.unavailable",
                    disposition=MigrationDisposition.LOSSY,
                    summary=(
                        "V1 DatasetVersion does not expose the V2 schema fingerprint; "
                        "content identity is retained but schema identity remains unknown."
                    ),
                    source_identity=f"{item.dataset_id}:{item.version_id}",
                )
            )
            locator = ResourceReference(
                namespace="pyingestkit.migration.v1.dataset_version",
                resource_id=_stable_id("dataset-version", item.snapshot_uri),
                locator=item.snapshot_uri,
                format=_format_from_locator(item.snapshot_uri),
                metadata=_metadata(
                    ("v1.job_id", item.job_id),
                    ("v1.job_version", item.job_version),
                    ("v1.created_from_run_id", item.created_from_run_id),
                    ("v1.source_raw_sha256", item.source_raw_sha256),
                ),
            )
            reference = DatasetVersionReference(
                dataset_id=item.dataset_id,
                version_id=item.version_id,
                created_at=_aware_datetime(item.created_at, "dataset version created_at"),
                schema_fingerprint=None,
                content_fingerprint=item.fingerprint,
                artifact_reference=artifact,
                locator=locator,
            )
            versions.append(reference)
            version_by_identity[reference.identity] = reference

        publications: list[PublishedDataset] = []
        for item in export.publications:
            version = version_by_identity.get((item.dataset_id, item.version_id))
            if version is None:
                issues.append(
                    MigrationIssue(
                        code="publication.version.unresolved",
                        disposition=MigrationDisposition.UNSUPPORTED,
                        summary="Published pointer references a DatasetVersion absent from export.",
                        source_identity=f"{item.dataset_id}:{item.version_id}",
                    )
                )
                continue
            try:
                run_id = IngestionRunId.parse(item.published_from_run_id)
            except (TypeError, ValueError):
                issues.append(
                    MigrationIssue(
                        code="publication.run_id.invalid",
                        disposition=MigrationDisposition.UNSUPPORTED,
                        summary="V1 publication run id is not a V2 UUID-backed IngestionRunId.",
                        source_identity=f"{item.dataset_id}:{item.version_id}",
                        details=(("run_id", item.published_from_run_id),),
                    )
                )
                continue
            publications.append(
                PublishedDataset(
                    dataset_id=item.dataset_id,
                    version=version,
                    published_at=_aware_datetime(item.published_at, "published_at"),
                    published_from_run_id=run_id,
                )
            )

        replays = tuple(
            LegacyReplayMigrationEvidence(
                run_id=item.run_id,
                source_run_id=item.source_run_id,
                source_job_id=item.source_job_id,
                source_job_version=item.source_job_version,
                executed_job_version=item.executed_job_version,
                verification_mode=item.verification_mode,
                expected_fingerprint=item.expected_fingerprint,
                actual_fingerprint=item.actual_fingerprint,
                status=item.status,
            )
            for item in export.replays
        )
        for item in export.replays:
            issues.append(
                MigrationIssue(
                    code="replay.request.requires_definition_and_raw",
                    disposition=MigrationDisposition.MANUAL,
                    summary=(
                        "V1 replay history is preserved as evidence, but a V2 ReplayRequest "
                        "also requires an explicit IngestionDefinition and origin RAW reference."
                    ),
                    source_identity=item.run_id,
                    details=(("source_run_id", item.source_run_id),),
                )
            )

        return V1MigrationResult(
            artifacts=tuple(artifacts),
            dataset_versions=tuple(versions),
            publications=tuple(publications),
            replays=replays,
            report=MigrationReport(
                source_version=export.source_version,
                target_version="2",
                issues=tuple(issues),
                shim_decisions=_SHIM_DECISIONS,
            ),
        )


def _step_disposition(owner: StepOwnership) -> tuple[MigrationDisposition, str]:
    if owner in {StepOwnership.ACQUISITION, StepOwnership.INGESTION}:
        return (
            MigrationDisposition.MANUAL,
            "Step semantics must be re-expressed as V2 Source/decoder/validation policies.",
        )
    if owner is StepOwnership.TRANSFORMATION:
        return (
            MigrationDisposition.MANUAL,
            "Transformation Step belongs in PyTransformKit, not PyIngestKit V2 core.",
        )
    if owner is StepOwnership.MATERIALIZATION:
        return (
            MigrationDisposition.MANUAL,
            "Materialization Step must be re-expressed through a V2 target adapter.",
        )
    if owner in {StepOwnership.OBSERVABILITY, StepOwnership.ORCHESTRATION}:
        return (
            MigrationDisposition.MANUAL,
            "Step belongs outside the V2 ingestion definition runtime.",
        )
    return (
        MigrationDisposition.UNSUPPORTED,
        "Step ownership is unknown; automatic migration is unsafe.",
    )


def _metadata(*pairs: tuple[str, object | None]) -> tuple[tuple[str, str], ...]:
    return tuple((key, str(value)) for key, value in pairs if value is not None)


def _stable_id(kind: str, locator: str) -> str:
    return f"{kind}_{hashlib.sha256(locator.encode()).hexdigest()}"


def _format_from_locator(locator: str) -> str | None:
    path = urlsplit(locator).path or locator
    suffix = Path(path).suffix.lower().lstrip(".")
    return suffix or None


def _aware_datetime(value: str, name: str):
    from datetime import datetime

    try:
        result = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be ISO 8601.") from exc
    if result.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware.")
    return result
