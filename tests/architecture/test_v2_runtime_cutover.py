from __future__ import annotations

from pyingestkit.runtime.v2 import IngestionResult, IngestionRun, IngestionRuntime

from ._imports import imported_roots, python_files

V2_OWNED_PATHS = (
    "domain",
    "application",
    "ports",
    "serialization",
    "runtime/v2.py",
    "replay/v2.py",
    "publication/v2.py",
    "artifacts/v2.py",
)

FORBIDDEN_LEGACY_RUNTIME_IMPORTS = {
    "pyingestkit.runtime.runner",
    "pyingestkit.core",
}


def test_lot12_v2_owned_code_does_not_import_legacy_execution_runtime() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(python_files(*V2_OWNED_PATHS)).items():
        for module in modules:
            if any(
                module == forbidden or module.startswith(f"{forbidden}.")
                for forbidden in FORBIDDEN_LEGACY_RUNTIME_IMPORTS
            ):
                violations.append(f"{path}: {module}")
    assert not violations, "\n".join(violations)


def test_lot12_qualified_runtime_surface_is_v2_only() -> None:
    assert IngestionRun.__module__ == "pyingestkit.domain.runtime.execution"
    assert IngestionResult.__module__ == "pyingestkit.domain.runtime.execution"
    assert IngestionRuntime.__module__ == "pyingestkit.application.runtime"
