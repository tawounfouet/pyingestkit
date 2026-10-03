from __future__ import annotations

from ._imports import imported_roots, matches_prefix, python_files

SAFE_PLANNER_FORBIDDEN_IMPORTS = {
    "importlib",
    "pyingestkit.core",
    "pyingestkit.plugins",
    "pyingestkit.runtime.runner",
}

QUALIFIED_TOOLKIT_FORBIDDEN_IMPORTS = {
    "importlib",
    "pyingestkit.plugins",
    "pyingestkit.runtime.runner",
}

_ALLOWED_TOOLKIT_LEGACY_IMPORTS = {
    "pyingestkit.core.job",
    "pyingestkit.declarative.step_definition",
}


def test_lot18_safe_planner_never_imports_executable_v1_runtime() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(python_files("migration/v1.py")).items():
        for module in modules:
            if matches_prefix(module, SAFE_PLANNER_FORBIDDEN_IMPORTS):
                violations.append(f"{path}: {module}")
    assert not violations, "\n".join(violations)


def test_lot18_qualified_toolkit_does_not_discover_plugins_or_runner() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(python_files("migration/v2")).items():
        for module in modules:
            if matches_prefix(module, QUALIFIED_TOOLKIT_FORBIDDEN_IMPORTS):
                violations.append(f"{path}: {module}")
    assert not violations, "\n".join(violations)


def test_lot18_v1_execution_imports_are_confined_to_explicit_job_migrator() -> None:
    violations: list[str] = []
    imports = imported_roots(python_files("migration/v2"))
    for path, modules in imports.items():
        for module in modules:
            if module.startswith("pyingestkit.core") or module.startswith(
                "pyingestkit.declarative"
            ):
                if path.name != "toolkit.py" or module not in _ALLOWED_TOOLKIT_LEGACY_IMPORTS:
                    violations.append(f"{path}: {module}")
    assert not violations, "\n".join(violations)


def test_lot18_legacy_data_imports_are_confined_to_migration_namespace() -> None:
    imports = imported_roots(python_files("migration"))
    modules = {module for values in imports.values() for module in values}

    assert "pyingestkit.config" in modules
    assert "pyingestkit.metadata.models" in modules
