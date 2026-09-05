from __future__ import annotations

import json
from pathlib import Path
from typing import Any, NoReturn

import typer
import yaml

from pyingestkit.artifacts import ArtifactStore, S3ArtifactStore, create_artifact_store
from pyingestkit.config import PyIngestKitConfig, load_config
from pyingestkit.core.exceptions import ConfigurationError
from pyingestkit.core.job import Job
from pyingestkit.core.registry import JobRegistry
from pyingestkit.metadata import MetadataStore, create_metadata_store
from pyingestkit.plugins.discovery import (
    PluginFailure,
    load_registry,
    load_registry_with_diagnostics,
)
from pyingestkit.versioning import (
    DatasetVersionStore,
    FilesystemDatasetVersionStore,
    S3DatasetVersionStore,
)

from .console import error_console


def get_registry() -> JobRegistry:
    """Load installed jobs while isolating unrelated broken plugins."""
    return load_registry()


def get_registry_with_diagnostics() -> tuple[JobRegistry, tuple[PluginFailure, ...]]:
    return load_registry_with_diagnostics()


def get_job_or_exit(registry: JobRegistry, job_id: str) -> Job:
    try:
        return registry.get(job_id)
    except KeyError:
        fail(f"Unknown ingestion job: {job_id}", code=2)


def project_config_or_exit(config: Path | None) -> PyIngestKitConfig:
    try:
        return load_config(config)
    except ConfigurationError as exc:
        fail(str(exc), code=2)


def validate_job_requirements_or_exit(
    job: Job,
    project_config: PyIngestKitConfig,
) -> None:
    """Ensure that the resolved configuration satisfies the explicit backend requirements of the job."""
    if job.requires_artifacts is not None:
        configured_backend = project_config.artifacts.backend.value.lower()
        required_backend = job.requires_artifacts.lower()
        if configured_backend != required_backend:
            fail(
                f"Ingestion job '{job.id}' requires an artifact backend of type {required_backend!r}, "
                f"but {configured_backend!r} is configured.\n"
                "Please specify a compatible configuration file using `--config <file.yml>` "
                "or set the PYINGEST_CONFIG environment variable.",
                code=2,
            )

    if job.requires_metadata is not None:
        configured_backend = project_config.metadata.backend.value.lower()
        required_backend = job.requires_metadata.lower()
        if configured_backend != required_backend:
            fail(
                f"Ingestion job '{job.id}' requires a metadata backend of type {required_backend!r}, "
                f"but {configured_backend!r} is configured.\n"
                "Please specify a compatible configuration file using `--config <file.yml>` "
                "or set the PYINGEST_CONFIG environment variable.",
                code=2,
            )


def artifact_store_or_exit(
    project_config: PyIngestKitConfig,
    *,
    workspace: Path,
) -> ArtifactStore:
    try:
        return create_artifact_store(project_config.artifacts, workspace=workspace)
    except ConfigurationError as exc:
        fail(str(exc), code=2)


def metadata_store_or_exit(
    project_config: PyIngestKitConfig,
    *,
    workspace: Path,
) -> MetadataStore:
    try:
        return create_metadata_store(project_config.metadata, workspace=workspace)
    except ConfigurationError as exc:
        fail(str(exc), code=2)


def dataset_version_store_or_exit(
    project_config: PyIngestKitConfig,
    *,
    workspace: Path,
) -> DatasetVersionStore:
    artifact_store = artifact_store_or_exit(project_config, workspace=workspace)
    if isinstance(artifact_store, S3ArtifactStore):
        return S3DatasetVersionStore(artifact_store)
    root = getattr(artifact_store, "root", workspace)
    return FilesystemDatasetVersionStore(root)


def parse_params_json(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        fail(f"--params-json must be valid JSON: {exc}", code=2)
    if not isinstance(parsed, dict):
        fail("--params-json must decode to a JSON object", code=2)
    return parsed


def parse_param_assignments(values: list[str] | None) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for item in values or []:
        if "=" not in item:
            fail(f"--param must use KEY=VALUE syntax, got: {item!r}", code=2)
        key, raw_value = item.split("=", 1)
        key = key.strip()
        if not key:
            fail("--param key cannot be empty", code=2)
        try:
            value = yaml.safe_load(raw_value)
        except yaml.YAMLError as exc:
            fail(f"Invalid value for --param {key}: {exc}", code=2)
        parsed[key] = value
    return parsed


def fail(message: str, *, code: int = 1) -> NoReturn:
    error_console.print(f"[bold red]Error:[/bold red] {message}")
    raise typer.Exit(code=code)
