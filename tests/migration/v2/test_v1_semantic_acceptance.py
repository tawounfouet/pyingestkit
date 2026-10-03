from __future__ import annotations

import json
from pathlib import Path

from pyingestkit.adapters.postgres import PostgresTargetV2
from pyingestkit.migration import (
    MigrationDispositionV2,
    assess_v1_plugin_entry_point,
    plan_v1_config_migration,
)
from pyingestkit.replay.v2 import ReplayServiceV2
from pyingestkit.stores import S3ArtifactStoreV2, S3DatasetVersionStoreV2
from pyingestkit.config import PyIngestKitConfig

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "fixtures" / "migration" / "v1" / "manifest.json"


def test_lot18_manifest_kinds_have_executable_v2_acceptance_surfaces() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    lot18 = {
        item["kind"]
        for item in payload["evidence"]
        if "LOT-18" in item["target_lot"].split("/")
    }

    assert lot18 == {"configuration", "plugins", "postgres", "replay", "s3"}
    assert ReplayServiceV2.__module__ == "pyingestkit.application.replay"
    assert PostgresTargetV2.__module__ == "pyingestkit.adapters.postgres.target"
    assert S3ArtifactStoreV2.__module__ == "pyingestkit.adapters.s3.artifact_store"
    assert S3DatasetVersionStoreV2.__module__ == (
        "pyingestkit.adapters.s3.dataset_version_store"
    )


def test_lot18_configuration_and_plugin_migration_are_explicit_not_implicit() -> None:
    plan = plan_v1_config_migration(PyIngestKitConfig())
    plugin = assess_v1_plugin_entry_point(
        "demo-local-file",
        "pyingestkit_demo_jobs.local_file:job_definition",
    )

    assert plan.can_materialize_supported_backends is True
    assert plugin.disposition is MigrationDispositionV2.REWRITE_REQUIRED
