from __future__ import annotations

from pyingestkit.adapters.http import HttpSourceConnector
from pyingestkit.sources.http.v2 import HttpAccessPolicy

from ._imports import imported_roots, python_files


def test_lot13_httpx_is_confined_to_provider_implementation() -> None:
    imports = imported_roots(python_files("adapters/http"))
    violations: list[str] = []
    for path, modules in imports.items():
        if "httpx" in modules and path.name != "_httpx.py":
            violations.append(f"{path}: httpx")
    assert not violations, "\n".join(violations)


def test_lot13_http_adapter_does_not_import_legacy_runtime() -> None:
    forbidden = {"pyingestkit.runtime.runner", "pyingestkit.core"}
    violations: list[str] = []
    for path, modules in imported_roots(python_files("adapters/http")).items():
        for module in modules:
            if any(module == item or module.startswith(f"{item}.") for item in forbidden):
                violations.append(f"{path}: {module}")
    assert not violations, "\n".join(violations)


def test_lot13_qualified_http_surface_is_v2() -> None:
    assert HttpSourceConnector.__module__ == "pyingestkit.adapters.http.source"
    assert HttpAccessPolicy.__module__ == "pyingestkit.adapters.http.source"
