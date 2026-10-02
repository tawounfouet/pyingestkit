from __future__ import annotations

from pyingestkit.validation.v2 import ValidationRuleV2

from ._imports import imported_roots, matches_prefix, python_files

FORBIDDEN_IMPORTS = {
    "duckdb",
    "pandas",
    "polars",
    "pyarrow",
    "pytransformkit",
    "pyworkflowkit",
    "sqlalchemy",
}


def test_validation_quality_v2_boundary_is_engine_neutral() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(
        python_files("validation/v2.py", "quality/v2.py")
    ).items():
        for module in modules:
            if matches_prefix(module, FORBIDDEN_IMPORTS):
                violations.append(f"{path}: {module}")
    assert not violations, "\n".join(violations)


def test_validation_rule_v2_surface_is_narrow() -> None:
    public = {name for name in dir(ValidationRuleV2) if not name.startswith("_")}

    assert {"id", "evaluate"}.issubset(public)
    assert public.isdisjoint({"acquire", "decode", "load", "persist", "transform"})
