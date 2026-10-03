from __future__ import annotations

from pyingestkit.replay.v2 import ReplayServiceV2

from ._imports import imported_roots, matches_prefix, python_files

FORBIDDEN_IMPORTS = {
    "boto3",
    "httpx",
    "pandas",
    "polars",
    "psycopg",
    "pyarrow",
    "pytransformkit",
    "pyworkflowkit",
    "sqlalchemy",
    "pyingestkit.application.sources",
    "pyingestkit.core",
    "pyingestkit.runtime.runner",
}


def test_lot11_replay_service_has_no_live_source_or_provider_dependency() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(python_files("application/replay.py")).items():
        for module in modules:
            if matches_prefix(module, FORBIDDEN_IMPORTS):
                violations.append(f"{path}: {module}")
    assert not violations, "\n".join(violations)


def test_lot11_replay_service_surface_is_replay_only() -> None:
    public = {name for name in dir(ReplayServiceV2) if not name.startswith("_")}

    assert "replay" in public
    assert public.isdisjoint({"acquire", "fetch", "publish", "run_job", "run_pipeline"})
