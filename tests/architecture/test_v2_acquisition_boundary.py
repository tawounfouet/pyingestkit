from __future__ import annotations

from dataclasses import fields

import pyingestkit.sources as public_sources
from pyingestkit.application.sources import SourceRegistry
from pyingestkit.domain.acquisition import AcquisitionResult
from pyingestkit.ports.sources import SourceConnector

from ._imports import imported_roots, matches_prefix, python_files

FORBIDDEN_FILE_ADAPTER_IMPORTS = {
    "boto3",
    "botocore",
    "httpx",
    "openpyxl",
    "pandas",
    "polars",
    "psycopg",
    "pyarrow",
    "pytransformkit",
    "pyworkflowkit",
    "sqlalchemy",
}


def test_file_adapter_has_no_provider_or_sibling_framework_dependency() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(python_files("adapters/filesystem")).items():
        for module in modules:
            if matches_prefix(module, FORBIDDEN_FILE_ADAPTER_IMPORTS):
                violations.append(f"{path}: {module}")
    assert not violations, "\n".join(violations)


def test_acquisition_result_does_not_persist_raw_or_dataset_state() -> None:
    names = {field.name for field in fields(AcquisitionResult)}

    assert names.isdisjoint(
        {
            "artifact_store",
            "artifact_reference",
            "dataset_version",
            "published_dataset",
            "target",
        }
    )


def test_source_connector_is_a_port_not_a_provider_base_class() -> None:
    assert SourceConnector.__module__ == "pyingestkit.ports.sources"


def test_source_registry_is_explicit_not_global() -> None:
    first = SourceRegistry()
    second = SourceRegistry()

    assert first is not second
    assert len(first) == 0
    assert len(second) == 0


def test_v1_sources_star_import_contract_is_unchanged() -> None:
    assert public_sources.__all__ == ["LocalSource", "Source"]
    assert hasattr(public_sources, "SourceRegistry")
    assert hasattr(public_sources, "FileSourceConnector")
