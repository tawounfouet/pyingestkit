from __future__ import annotations

import pyingestkit.migration as migration
import pyingestkit.migration.v2 as qualified_migration
from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_MIGRATION_VALUES,
    V2_IMPLEMENTED_QUALIFIED_MIGRATION_VALUES,
)

_EXPECTED = (
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
)


def test_lot18_phase_and_completed_lot_are_recorded() -> None:
    assert V2_API_PHASE == "LOT-18_V1_SEMANTIC_MIGRATION"
    assert V2_COMPLETED_LOTS[-1] == "LOT-18"


def test_lot18_migration_values_are_explicit() -> None:
    assert V2_IMPLEMENTED_MIGRATION_VALUES == _EXPECTED
    assert tuple(migration.__all__) == _EXPECTED


def test_lot18_qualified_migration_toolkit_is_explicit() -> None:
    assert V2_IMPLEMENTED_QUALIFIED_MIGRATION_VALUES == tuple(
        qualified_migration.__all__
    )
