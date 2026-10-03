from __future__ import annotations

from dataclasses import fields

import pyingestkit.artifacts as public_artifacts
from pyingestkit.adapters.filesystem import FileArtifactStore
from pyingestkit.domain.artifacts import RawArtifactEvidence
from pyingestkit.ports.artifacts import ArtifactStore
from pyingestkit.targets import Target

from ._imports import imported_roots, matches_prefix, python_files

FORBIDDEN_ARTIFACT_IMPORTS = {
    "pandas",
    "polars",
    "pyarrow",
    "pytransformkit",
    "pyworkflowkit",
    "sqlalchemy",
    "pyingestkit.targets",
}


def test_artifact_domain_and_port_do_not_import_transform_or_target_layers() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(
        python_files("domain/artifacts", "ports/artifacts.py")
    ).items():
        for module in modules:
            if matches_prefix(module, FORBIDDEN_ARTIFACT_IMPORTS):
                violations.append(f"{path}: {module}")
    assert not violations, "\n".join(violations)


def test_artifact_store_is_not_target_contract() -> None:
    assert ArtifactStore.__module__ == "pyingestkit.ports.artifacts"
    assert not issubclass(FileArtifactStore, Target)


def test_raw_evidence_does_not_own_dataset_or_transformation_state() -> None:
    names = {field.name for field in fields(RawArtifactEvidence)}

    assert names.isdisjoint(
        {
            "dataset",
            "dataset_version",
            "published_dataset",
            "transformation",
            "logical_plan",
            "target",
        }
    )


def test_v2_artifacts_namespace_is_promoted_at_rc() -> None:
    assert "ArtifactStore" in public_artifacts.__all__
    assert "ArtifactReference" in public_artifacts.__all__
    assert "PutArtifactRequest" in public_artifacts.__all__
    assert "ArtifactURI" not in public_artifacts.__all__
    assert "RawArtifact" not in public_artifacts.__all__
