"""Explicit migration tooling for PyIngestKit major-version boundaries."""

from pyingestkit.migration.v1 import (
    MigrationDecisionV2,
    MigrationDispositionV2,
    V1PluginMigrationAssessment,
    V1PostgresTargetMigrationV2,
    V1ProjectMigrationPlan,
    assess_v1_plugin_entry_point,
    migrate_v1_artifact_record,
    migrate_v1_dataset_version_record,
    migrate_v1_postgres_target_config,
    migrate_v1_published_dataset_record,
    plan_v1_config_migration,
)

__all__ = [
    "MigrationDecisionV2",
    "MigrationDispositionV2",
    "V1PluginMigrationAssessment",
    "V1PostgresTargetMigrationV2",
    "V1ProjectMigrationPlan",
    "assess_v1_plugin_entry_point",
    "migrate_v1_artifact_record",
    "migrate_v1_dataset_version_record",
    "migrate_v1_postgres_target_config",
    "migrate_v1_published_dataset_record",
    "plan_v1_config_migration",
]
