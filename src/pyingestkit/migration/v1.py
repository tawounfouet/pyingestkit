"""Explicit V1 -> V2 semantic migration planning.

This module is intentionally the only V2 migration boundary allowed to import
stable V1 configuration contracts. It produces data-only migration decisions
and never loads plugin entry points or resolves secret environment variables.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import hashlib


from pyingestkit.config import (
    ArtifactBackend,
    MetadataBackend,
    PostgresTargetConfig,
    PyIngestKitConfig,
)
from pyingestkit.domain.artifacts import ArtifactReference
from pyingestkit.domain.datasets import DatasetVersionReference
from pyingestkit.domain.datasets.publication import PublishedDataset
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.shared.validation import require_non_blank, validate_metadata
from pyingestkit.domain.targets import TargetLoadModeV2
from pyingestkit.metadata.models import (
    ArtifactRecord,
    DatasetVersionRecord,
    PublishedDatasetRecord,
)


class MigrationDispositionV2(StrEnum):
    """How safely one V1 semantic can move into the current V2 architecture."""

    AUTOMATIC = "automatic"
    RETAINED_V1_ONLY = "retained_v1_only"
    REWRITE_REQUIRED = "rewrite_required"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class MigrationDecisionV2:
    """One deterministic, secret-free migration decision."""

    subject: str
    source_contract: str
    target_contract: str | None
    disposition: MigrationDispositionV2
    reason: str
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        require_non_blank(self.subject, "MigrationDecisionV2 subject")
        require_non_blank(self.source_contract, "MigrationDecisionV2 source_contract")
        if self.target_contract is not None:
            require_non_blank(self.target_contract, "MigrationDecisionV2 target_contract")
        if not isinstance(self.disposition, MigrationDispositionV2):
            raise TypeError(
                "MigrationDecisionV2 disposition must be MigrationDispositionV2."
            )
        require_non_blank(self.reason, "MigrationDecisionV2 reason")
        validate_metadata(self.metadata, name="MigrationDecisionV2 metadata")


@dataclass(frozen=True, slots=True)
class V1PostgresTargetMigrationV2:
    """Secret-free V2 settings derived from one stable V1 PostgreSQL target."""

    target_id: str
    dsn_env: str
    schema: str | None
    table: str
    mode: TargetLoadModeV2

    def __post_init__(self) -> None:
        require_non_blank(self.target_id, "V1PostgresTargetMigrationV2 target_id")
        require_non_blank(self.dsn_env, "V1PostgresTargetMigrationV2 dsn_env")
        require_non_blank(self.table, "V1PostgresTargetMigrationV2 table")
        if not isinstance(self.mode, TargetLoadModeV2):
            raise TypeError(
                "V1PostgresTargetMigrationV2 mode must be TargetLoadModeV2."
            )

    @property
    def environment_variables(self) -> tuple[str, ...]:
        """Return secret references, never resolved values."""
        return (self.dsn_env,)


@dataclass(frozen=True, slots=True)
class V1PluginMigrationAssessment:
    """Non-executable assessment of one V1 plugin entry-point declaration."""

    entry_point_name: str
    entry_point_value: str
    disposition: MigrationDispositionV2
    target_contract: str
    reason: str

    def __post_init__(self) -> None:
        require_non_blank(
            self.entry_point_name,
            "V1PluginMigrationAssessment entry_point_name",
        )
        require_non_blank(
            self.entry_point_value,
            "V1PluginMigrationAssessment entry_point_value",
        )
        if not isinstance(self.disposition, MigrationDispositionV2):
            raise TypeError(
                "V1PluginMigrationAssessment disposition must be MigrationDispositionV2."
            )
        require_non_blank(
            self.target_contract,
            "V1PluginMigrationAssessment target_contract",
        )
        require_non_blank(self.reason, "V1PluginMigrationAssessment reason")


@dataclass(frozen=True, slots=True)
class V1ProjectMigrationPlan:
    """Complete semantic migration assessment for one validated V1 config."""

    workspace: Path
    decisions: tuple[MigrationDecisionV2, ...]
    postgres_targets: tuple[V1PostgresTargetMigrationV2, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.workspace, Path):
            raise TypeError("V1ProjectMigrationPlan workspace must be Path.")
        if not isinstance(self.decisions, tuple):
            raise TypeError("V1ProjectMigrationPlan decisions must be a tuple.")
        if any(not isinstance(item, MigrationDecisionV2) for item in self.decisions):
            raise TypeError(
                "V1ProjectMigrationPlan decisions must contain MigrationDecisionV2."
            )
        if not isinstance(self.postgres_targets, tuple):
            raise TypeError("V1ProjectMigrationPlan postgres_targets must be a tuple.")
        if any(
            not isinstance(item, V1PostgresTargetMigrationV2)
            for item in self.postgres_targets
        ):
            raise TypeError(
                "V1ProjectMigrationPlan postgres_targets must contain "
                "V1PostgresTargetMigrationV2."
            )

    @property
    def blocked(self) -> tuple[MigrationDecisionV2, ...]:
        return tuple(
            item
            for item in self.decisions
            if item.disposition is MigrationDispositionV2.BLOCKED
        )

    @property
    def rewrite_required(self) -> tuple[MigrationDecisionV2, ...]:
        return tuple(
            item
            for item in self.decisions
            if item.disposition is MigrationDispositionV2.REWRITE_REQUIRED
        )

    @property
    def automatically_migratable(self) -> tuple[MigrationDecisionV2, ...]:
        return tuple(
            item
            for item in self.decisions
            if item.disposition is MigrationDispositionV2.AUTOMATIC
        )

    @property
    def can_materialize_supported_backends(self) -> bool:
        """Whether currently supported V2 backend/target semantics are unblocked."""
        return not self.blocked


def migrate_v1_artifact_record(record: ArtifactRecord) -> ArtifactReference:
    """Convert one stable V1 artifact metadata row into a portable V2 reference."""
    if not isinstance(record, ArtifactRecord):
        raise TypeError("migrate_v1_artifact_record expects ArtifactRecord.")

    locator = record.storage_uri
    if locator is None:
        locator = Path(record.path).resolve().as_uri()

    resource = ResourceReference(
        namespace="pyingestkit.v1.artifact",
        resource_id=record.artifact_id,
        locator=locator,
        media_type=record.content_type,
        format=_format_from_locator(locator),
        metadata=(("legacy_run_id", record.run_id),),
    )
    return ArtifactReference(
        artifact_id=record.artifact_id,
        kind=record.kind,
        resource=resource,
        checksum=record.sha256,
        checksum_algorithm="sha256",
        media_type=record.content_type,
        size_bytes=record.size_bytes,
        created_at=record.created_at,
        metadata=(("legacy_run_id", record.run_id),),
    )


def migrate_v1_dataset_version_record(
    record: DatasetVersionRecord,
) -> DatasetVersionReference:
    """Convert one stable V1 dataset-version metadata row into a V2 reference."""
    if not isinstance(record, DatasetVersionRecord):
        raise TypeError(
            "migrate_v1_dataset_version_record expects DatasetVersionRecord."
        )

    locator = ResourceReference(
        namespace="pyingestkit.v1.dataset_version_snapshot",
        resource_id=f"v1_snapshot_{hashlib.sha256(record.snapshot_uri.encode()).hexdigest()}",
        locator=record.snapshot_uri,
        format="json",
        metadata=(
            ("legacy_created_from_run_id", record.created_from_run_id),
            ("legacy_job_id", record.job_id),
            ("legacy_job_version", record.job_version),
            ("legacy_source_artifact_id", record.source_artifact_id or ""),
            ("legacy_source_raw_sha256", record.source_raw_sha256 or ""),
        ),
    )
    return DatasetVersionReference(
        dataset_id=record.dataset_id,
        version_id=record.version_id,
        created_at=record.created_at,
        content_fingerprint=record.fingerprint,
        locator=locator,
    )


def migrate_v1_published_dataset_record(
    record: PublishedDatasetRecord,
    *,
    version: DatasetVersionReference,
) -> PublishedDataset:
    """Convert one V1 publication pointer after its version reference is migrated."""
    if not isinstance(record, PublishedDatasetRecord):
        raise TypeError(
            "migrate_v1_published_dataset_record expects PublishedDatasetRecord."
        )
    if not isinstance(version, DatasetVersionReference):
        raise TypeError(
            "migrate_v1_published_dataset_record version must be DatasetVersionReference."
        )
    if version.identity != (record.dataset_id, record.version_id):
        raise ValueError(
            "PublishedDatasetRecord identity must match the supplied migrated version."
        )
    try:
        run_id = IngestionRunId.parse(record.published_from_run_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "PublishedDatasetRecord published_from_run_id must be a UUID for V2 migration."
        ) from exc
    return PublishedDataset(
        dataset_id=record.dataset_id,
        version=version,
        published_at=record.published_at,
        published_from_run_id=run_id,
    )


def migrate_v1_postgres_target_config(
    config: PostgresTargetConfig,
) -> V1PostgresTargetMigrationV2:
    """Translate safe V1 target semantics without resolving the DSN secret."""
    if not isinstance(config, PostgresTargetConfig):
        raise TypeError(
            "migrate_v1_postgres_target_config expects PostgresTargetConfig."
        )
    return V1PostgresTargetMigrationV2(
        target_id=config.target_id,
        dsn_env=config.dsn_env,
        schema=config.schema_name,
        table=config.table,
        mode=TargetLoadModeV2(config.load_mode),
    )


def plan_v1_config_migration(config: PyIngestKitConfig) -> V1ProjectMigrationPlan:
    """Build a deterministic V1 -> V2 migration plan from validated config."""
    if not isinstance(config, PyIngestKitConfig):
        raise TypeError("plan_v1_config_migration expects PyIngestKitConfig.")

    decisions: list[MigrationDecisionV2] = []
    workspace = config.runtime.workspace

    decisions.append(
        MigrationDecisionV2(
            subject="runtime.workspace",
            source_contract="PyIngestKitConfig.runtime.workspace",
            target_contract="explicit adapter roots",
            disposition=MigrationDispositionV2.AUTOMATIC,
            reason=(
                "V2 adapters receive storage roots explicitly rather than through a "
                "global Runner workspace."
            ),
            metadata=(("workspace", str(workspace)),),
        )
    )

    if config.runtime.fixture_mode:
        decisions.append(
            MigrationDecisionV2(
                subject="runtime.fixture_mode",
                source_contract="PyIngestKitConfig.runtime.fixture_mode",
                target_contract=None,
                disposition=MigrationDispositionV2.REWRITE_REQUIRED,
                reason=(
                    "V2 has no global fixture-mode switch; tests must inject explicit "
                    "sources, clients or adapters."
                ),
            )
        )

    if config.runtime.parameters:
        decisions.append(
            MigrationDecisionV2(
                subject="runtime.parameters",
                source_contract="PyIngestKitConfig.runtime.parameters",
                target_contract="IngestionDefinition.options / caller inputs",
                disposition=MigrationDispositionV2.REWRITE_REQUIRED,
                reason=(
                    "Free-form V1 runtime parameters may contain job-specific semantics "
                    "and cannot be assigned to V2 definitions automatically."
                ),
                metadata=(("parameter_count", str(len(config.runtime.parameters))),),
            )
        )

    decisions.append(_artifact_backend_decision(config))

    if config.metadata.backend is MetadataBackend.SQLITE:
        metadata = (
            ("backend", "sqlite"),
            (
                "path",
                str(
                    config.metadata.sqlite.path
                    or (workspace / "state" / "pyingest.sqlite3")
                ),
            ),
        )
    else:
        metadata = (
            ("backend", "postgres"),
            ("dsn_env", config.metadata.postgres.dsn_env),
        )
    decisions.append(
        MigrationDecisionV2(
            subject="metadata",
            source_contract="PyIngestKitConfig.metadata",
            target_contract=None,
            disposition=MigrationDispositionV2.RETAINED_V1_ONLY,
            reason=(
                "The current V2 runtime does not expose a general metadata-store port. "
                "V1 metadata remains readable for migration/audit but is not silently "
                "rebound to a V2 backend."
            ),
            metadata=metadata,
        )
    )

    targets = tuple(
        migrate_v1_postgres_target_config(target)
        for _, target in sorted(config.targets.items())
    )
    for target in targets:
        decisions.append(
            MigrationDecisionV2(
                subject=f"target.{target.target_id}",
                source_contract="PostgresTargetConfig",
                target_contract="PostgresTargetV2 + TargetLoadRequestV2",
                disposition=MigrationDispositionV2.AUTOMATIC,
                reason=(
                    "Logical target identity, secret environment reference, schema, "
                    "table and load mode map directly to the V2 PostgreSQL target "
                    "contracts."
                ),
                metadata=(
                    ("target_id", target.target_id),
                    ("dsn_env", target.dsn_env),
                    ("schema", target.schema or ""),
                    ("table", target.table),
                    ("load_mode", target.mode.value),
                ),
            )
        )

    decisions.append(
        MigrationDecisionV2(
            subject="logging",
            source_contract="PyIngestKitConfig.logging",
            target_contract=None,
            disposition=MigrationDispositionV2.RETAINED_V1_ONLY,
            reason=(
                "V1 CLI logging policy remains a maintained operational surface and "
                "is not part of the portable V2 ingestion domain."
            ),
            metadata=(
                ("level", config.logging.level),
                ("format", config.logging.format.value),
            ),
        )
    )

    return V1ProjectMigrationPlan(
        workspace=workspace,
        decisions=tuple(decisions),
        postgres_targets=targets,
    )


def assess_v1_plugin_entry_point(
    entry_point_name: str,
    entry_point_value: str,
) -> V1PluginMigrationAssessment:
    """Assess one V1 job plugin declaration without importing plugin code."""
    require_non_blank(entry_point_name, "V1 plugin entry_point_name")
    require_non_blank(entry_point_value, "V1 plugin entry_point_value")
    return V1PluginMigrationAssessment(
        entry_point_name=entry_point_name,
        entry_point_value=entry_point_value,
        disposition=MigrationDispositionV2.REWRITE_REQUIRED,
        target_contract="IngestionDefinition + explicit V2 registries/adapters",
        reason=(
            "V1 plugin entry points expose executable Job/JobDefinition/Pipeline "
            "semantics. LOT-18 deliberately does not execute or auto-translate plugin "
            "code; authors must express acquisition/decoder/validation/target intent "
            "as explicit V2 contracts."
        ),
    )


def _artifact_backend_decision(config: PyIngestKitConfig) -> MigrationDecisionV2:
    if config.artifacts.backend is ArtifactBackend.LOCAL:
        return MigrationDecisionV2(
            subject="artifacts",
            source_contract="ArtifactConfig(local)",
            target_contract="FileArtifactStore + FileDatasetVersionStore",
            disposition=MigrationDispositionV2.AUTOMATIC,
            reason=(
                "The V1 workspace can be reused as an explicit local V2 storage root."
            ),
            metadata=(("root", str(config.runtime.workspace)),),
        )

    s3 = config.artifacts.s3
    if s3.bucket is None:
        return MigrationDecisionV2(
            subject="artifacts",
            source_contract="ArtifactConfig(s3)",
            target_contract="S3ArtifactStoreV2 + S3DatasetVersionStoreV2",
            disposition=MigrationDispositionV2.BLOCKED,
            reason="V1 S3 configuration must provide a bucket before migration.",
            metadata=(
                ("prefix", s3.prefix),
                ("endpoint_url_env", s3.endpoint_url_env or ""),
            ),
        )

    return MigrationDecisionV2(
        subject="artifacts",
        source_contract="ArtifactConfig(s3)",
        target_contract="S3ArtifactStoreV2 + S3DatasetVersionStoreV2",
        disposition=MigrationDispositionV2.AUTOMATIC,
        reason=(
            "Bucket/prefix/region and endpoint environment-reference semantics map "
            "directly to the V2 S3-compatible stores."
        ),
        metadata=(
            ("bucket", s3.bucket),
            ("prefix", s3.prefix),
            ("region_name", s3.region_name or ""),
            ("endpoint_url_env", s3.endpoint_url_env or ""),
        ),
    )


def _format_from_locator(locator: str) -> str | None:
    path = locator.split("?", 1)[0].rstrip("/")
    name = path.rsplit("/", 1)[-1]
    if "." not in name:
        return None
    suffix = name.rsplit(".", 1)[-1].strip().lower()
    return suffix or None
