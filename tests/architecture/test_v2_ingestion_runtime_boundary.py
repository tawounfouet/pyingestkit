from __future__ import annotations

from pyingestkit.runtime.v2 import IngestionRuntime

from ._imports import imported_roots, matches_prefix, python_files

FORBIDDEN_IMPORTS = {
    "boto3",
    "pandas",
    "polars",
    "psycopg",
    "pyarrow",
    "pytransformkit",
    "pyworkflowkit",
    "sqlalchemy",
    "pyingestkit.core",
    "pyingestkit.runtime.runner",
}


def test_lot10_runtime_depends_on_ports_not_provider_sdks_or_legacy_runner() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(python_files("application/runtime.py")).items():
        for module in modules:
            if matches_prefix(module, FORBIDDEN_IMPORTS):
                violations.append(f"{path}: {module}")
    assert not violations, "\n".join(violations)


def test_lot10_runtime_surface_has_no_job_pipeline_step_vocabulary() -> None:
    public = {name for name in dir(IngestionRuntime) if not name.startswith("_")}

    assert "execute" in public
    assert public.isdisjoint({"job", "pipeline", "step", "run_job", "run_pipeline"})
