from __future__ import annotations

import os
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


def resolve_config_path_with_source(path: Path | None = None) -> tuple[Path | None, str]:
    """Resolve the configuration file path and return the resolution origin method."""
    if path is not None:
        return path, "explicit (--config)"

    env_path = os.getenv("PYINGEST_CONFIG")
    if env_path and env_path.strip():
        candidate = Path(env_path.strip())
        if candidate.exists():
            return candidate, f"environment (PYINGEST_CONFIG={env_path.strip()})"
        raise ConfigurationError(
            f"Configuration file specified in PYINGEST_CONFIG={env_path!r} does not exist"
        )

    env_name = os.getenv("PYINGEST_ENV")
    if env_name and env_name.strip():
        candidate = Path(f"pyingest.yml.{env_name.strip()}")
        if candidate.exists():
            return candidate, f"profile (PYINGEST_ENV={env_name.strip()} -> {candidate})"

    if "PYTEST_CURRENT_TEST" in os.environ:
        return None, "fallback (default in-memory)"

    for filename in DEFAULT_CONFIG_FILES:
        candidate = Path(filename)
        if candidate.exists():
            return candidate, f"default_file ({filename})"

    return None, "fallback (default in-memory)"


def resolve_config_path(path: Path | None = None) -> Path | None:
    """Resolve the configuration file path via explicit argument, env var, or default files."""
    candidate, _ = resolve_config_path_with_source(path)
    return candidate


def load_config(path: Path | None = None) -> PyIngestKitConfig:
    """Load and validate a YAML project configuration file.

    If path is None, attempts auto-discovery via PYINGEST_CONFIG or default project configuration files.
    Falls back to a default PyIngestKitConfig instance if no file is found.
    """
    resolved = resolve_config_path(path)
    if resolved is None:
        return PyIngestKitConfig()

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
        return PyIngestKitConfig.model_validate(payload)
    except PydanticValidationError as exc:
        raise ConfigurationError(f"Invalid PyIngestKit configuration: {exc}") from exc
