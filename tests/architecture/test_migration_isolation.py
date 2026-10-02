from __future__ import annotations

from ._imports import imported_roots, matches_prefix, python_files

V2_INWARD_LAYERS = (
    "domain",
    "application",
    "ports",
    "serialization",
    "observability",
)


def test_v2_core_does_not_depend_on_v1_migration_namespace() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(python_files(*V2_INWARD_LAYERS)).items():
        for module in modules:
            if matches_prefix(module, {"pyingestkit.migration"}):
                violations.append(f"{path}: {module}")
    assert not violations, "\n".join(violations)
