from __future__ import annotations

from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_FORBIDDEN_LEGACY_ROOT_EXPORTS,
    V2_IMPLEMENTED_BOUNDARY_VALUES,
    V2_PUBLIC_NAMESPACE_BASELINE,
    V2_TARGET_ROOT_EXPORTS,
)

EXPECTED_TARGET_ROOT = (
    "ArtifactReference",
    "DatasetVersion",
    "DatasetVersionReference",
    "IngestionDefinition",
    "IngestionResult",
    "IngestionRun",
    "IngestionRunId",
    "IngestionRuntime",
    "PublishedDataset",
    "ResourceReference",
    "Source",
)


def test_v2_target_root_is_exact_and_deterministic() -> None:
    assert V2_TARGET_ROOT_EXPORTS == EXPECTED_TARGET_ROOT


def test_v2_target_root_does_not_contain_legacy_execution_names() -> None:
    assert set(V2_TARGET_ROOT_EXPORTS).isdisjoint(V2_FORBIDDEN_LEGACY_ROOT_EXPORTS)


def test_v2_public_namespace_baseline_is_unique() -> None:
    assert len(V2_PUBLIC_NAMESPACE_BASELINE) == len(set(V2_PUBLIC_NAMESPACE_BASELINE))


def test_lot01_records_real_boundary_implementation_phase() -> None:
    assert V2_API_PHASE == "LOT-01_BOUNDARY_VALUES"
    assert "IngestionRunId" in V2_IMPLEMENTED_BOUNDARY_VALUES
    assert "IngestionDefinition" not in V2_IMPLEMENTED_BOUNDARY_VALUES
