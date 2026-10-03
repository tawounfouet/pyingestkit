from __future__ import annotations

from pyingestkit.stores import S3ArtifactStoreV2, S3DatasetVersionStoreV2

from ._imports import imported_roots, matches_prefix, python_files

FORBIDDEN_IMPORTS = {
    "pyingestkit.artifacts.s3",
    "pyingestkit.versioning.s3",
    "pyingestkit.core",
    "pyingestkit.runtime.runner",
}


def test_lot15_s3_adapter_does_not_import_v1_storage_runtime() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(python_files("adapters/s3")).items():
        for module in modules:
            if matches_prefix(module, FORBIDDEN_IMPORTS):
                violations.append(f"{path}: {module}")
    assert not violations, "\n".join(violations)


def test_lot15_boto3_is_lazy_and_confined_to_object_client_factory() -> None:
    imports = imported_roots(python_files("adapters/s3"))
    violations: list[str] = []
    for path, modules in imports.items():
        if "boto3" in modules and path.name != "_objects.py":
            violations.append(f"{path}: boto3")
    assert not violations, "\n".join(violations)


def test_lot15_s3_stores_are_v2_adapter_types() -> None:
    assert S3ArtifactStoreV2.__module__ == "pyingestkit.adapters.s3.artifact_store"
    assert S3DatasetVersionStoreV2.__module__ == (
        "pyingestkit.adapters.s3.dataset_version_store"
    )
