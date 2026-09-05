from __future__ import annotations

import re
from os import environ, getenv
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError as PydanticValidationError

from pyingestkit.core.exceptions import ConfigurationError

from .models import PyIngestKitConfig

DEFAULT_CONFIG_FILES: tuple[str, ...] = (
    "pyingest.yml",
    "pyingestkit.yml",
    ".pyingest.yml",
)
_PROFILE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _profile_name(value: str) -> str:
    """Normalize and validate the user-facing ``PYINGEST_ENV`` profile name."""

    normalized = value.strip()
    if not normalized or not _PROFILE_NAME.fullmatch(normalized):
        raise ConfigurationError(
            "PYINGEST_ENV must be a simple profile name containing only letters, digits, '.', '_' "
            "or '-'"
        )
    return normalized


def resolve_config_path_with_source(path: Path | None = None) -> tuple[Path | None, str]:
    """Resolve configuration path and return its stable V1 resolution source token.

    Resolution order is part of the V1 configuration contract:

    ``explicit -> PYINGEST_CONFIG -> PYINGEST_ENV -> default project file -> in-memory``.
    """

    if path is not None:
        return path, "explicit"

    env_path = getenv("PYINGEST_CONFIG")
    if env_path and env_path.strip():
        candidate = Path(env_path.strip())
        if candidate.exists():
            return candidate, "environment"
        raise ConfigurationError(
            f"Configuration file specified in PYINGEST_CONFIG={env_path!r} does not exist"
        )

    env_name = getenv("PYINGEST_ENV")
    if env_name and env_name.strip():
        profile = _profile_name(env_name)
        candidate = Path(f"pyingest.yml.{profile}")
        if candidate.exists():
            return candidate, "profile"
        raise ConfigurationError(
            f"Configuration profile PYINGEST_ENV={profile!r} requires {candidate}, but it does not exist"
        )

    if "PYTEST_CURRENT_TEST" in environ:
        return None, "in_memory"

    for filename in DEFAULT_CONFIG_FILES:
        candidate = Path(filename)
        if candidate.exists():
            return candidate, "default_file"

    return None, "in_memory"


def resolve_config_path(path: Path | None = None) -> Path | None:
    """Resolve the configuration file path using the stable V1 precedence."""

    candidate, _ = resolve_config_path_with_source(path)
    return candidate


def _apply_environment_overrides(config: PyIngestKitConfig) -> PyIngestKitConfig:
    workspace = getenv("PYINGEST_WORKSPACE")
    if workspace is None or not workspace.strip():
        return config
    runtime = config.runtime.model_copy(update={"workspace": Path(workspace.strip())})
    return config.model_copy(update={"runtime": runtime})


def load_config(path: Path | None = None) -> PyIngestKitConfig:
    """Load and validate the V1 project configuration contract.

    File selection uses ``resolve_config_path``. ``PYINGEST_WORKSPACE`` is then applied as an
    environment override to ``runtime.workspace``. CLI ``--workspace`` remains the highest-precedence
    workspace override at the application boundary.
    """

    resolved = resolve_config_path(path)
    if resolved is None:
        return _apply_environment_overrides(PyIngestKitConfig())

    try:
        raw_text = resolved.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigurationError(f"Unable to read configuration file {resolved}: {exc}") from exc

    try:
        payload: Any = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Invalid YAML in configuration file {resolved}: {exc}") from exc

    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ConfigurationError("PyIngestKit configuration root must be a YAML mapping")

    try:
        config = PyIngestKitConfig.model_validate(payload)
    except PydanticValidationError as exc:
        raise ConfigurationError(f"Invalid PyIngestKit configuration: {exc}") from exc
    return _apply_environment_overrides(config)
