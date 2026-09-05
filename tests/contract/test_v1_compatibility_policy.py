from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pyingestkit.provenance.manifest import RUN_MANIFEST_SCHEMA_VERSION, RunManifest

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "tests" / "contract" / "fixtures" / "compatibility_v1.json"


def _contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_v1_a2_compatibility_contract_is_versioned_and_anchored_to_a1() -> None:
    contract = _contract()
    assert contract["schema_version"] == 1
    assert contract["milestone"] == "V1.0.0-a2"
    assert contract["baseline"]["a1_merge_sha"] == ("6a4f93e3b4beec4b67a846d22f909abebc95524c")


def test_v1_a2_policy_keeps_physical_metadata_schema_internal() -> None:
    policy = _contract()["policy"]
    assert "internal" in policy["physical_metadata_schema"].lower()
    assert "logical" in policy["physical_metadata_schema"].lower()
    assert "schema-version bump" in policy["persistent_json"].lower()


def test_v1_run_manifest_has_an_explicit_compatibility_schema_version() -> None:
    contract = _contract()["persistent_formats"]["run_manifest"]
    manifest = RunManifest(
        run_id="run-1",
        job_id="demo.job",
        job_version="1.0.0",
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
    ).as_dict()

    assert RUN_MANIFEST_SCHEMA_VERSION == contract["schema_version"] == 1
    assert manifest["schema_version"] == 1
    assert list(manifest) == contract["keys"]


def test_v1_persistent_schema_versions_are_explicit_where_already_versioned() -> None:
    formats = _contract()["persistent_formats"]
    assert formats["dataset_snapshot"]["schema_version"] == "1"
    assert formats["dataset_version_metadata"]["schema_version"] == "1"
    assert formats["published_dataset_pointer"]["schema_version"] == "1"
