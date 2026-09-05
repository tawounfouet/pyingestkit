from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_v1_provider_sdks_remain_optional_extras() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    base_dependencies = "\n".join(project["project"]["dependencies"]).lower()

    for provider_dependency in ("boto3", "psycopg", "openpyxl", "pyarrow"):
        assert provider_dependency not in base_dependencies

    extras = project["project"]["optional-dependencies"]
    assert any("boto3" in dependency.lower() for dependency in extras["s3"])
    assert any("psycopg" in dependency.lower() for dependency in extras["postgres"])
    assert any("openpyxl" in dependency.lower() for dependency in extras["excel"])
    assert any("pyarrow" in dependency.lower() for dependency in extras["parquet"])


def test_v1_core_does_not_depend_on_provider_implementations() -> None:
    core_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "src" / "pyingestkit" / "core").rglob("*.py"))
    )
    forbidden = (
        "import boto3",
        "from boto3",
        "import psycopg",
        "from psycopg",
        "pyingestkit.artifacts.s3",
        "pyingestkit.targets.postgres",
        "PostgresTarget",
        "S3ArtifactStore",
    )
    for token in forbidden:
        assert token not in core_text


def test_v1_runner_depends_on_contracts_not_optional_provider_sdks() -> None:
    runner = (ROOT / "src" / "pyingestkit" / "runtime" / "runner.py").read_text(
        encoding="utf-8"
    )
    for token in ("boto3", "psycopg", "PostgresTarget", "S3ArtifactStore"):
        assert token not in runner


def test_v1_framework_keeps_orchestration_platform_dependencies_out_of_core() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = "\n".join(project["project"]["dependencies"]).lower()
    for forbidden in ("airflow", "dagster", "prefect", "celery", "kafka", "pyspark"):
        assert forbidden not in dependencies
