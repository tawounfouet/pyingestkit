from __future__ import annotations

from ._imports import imported_roots, matches_prefix, python_files

FORBIDDEN_IMPORTS = {
    "importlib",
    "pyingestkit.core",
    "pyingestkit.plugins",
    "pyingestkit.runtime.runner",
}


def test_lot18_migration_does_not_execute_or_discover_v1_plugins() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(python_files("migration")).items():
        for module in modules:
            if matches_prefix(module, FORBIDDEN_IMPORTS):
                violations.append(f"{path}: {module}")
    assert not violations, "\n".join(violations)


def test_lot18_legacy_imports_are_confined_to_migration_namespace() -> None:
    imports = imported_roots(python_files("migration"))
    modules = {module for values in imports.values() for module in values}

    assert "pyingestkit.config" in modules
    assert "pyingestkit.metadata.models" in modules
