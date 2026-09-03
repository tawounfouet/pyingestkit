from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError as PydanticValidationError

from pyingestkit.core.exceptions import ConfigurationError

from .models import PyIngestKitConfig


def load_config(path: Path) -> PyIngestKitConfig:
    """Load and validate a YAML project configuration file."""
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigurationError(f"Unable to read configuration file {path}: {exc}") from exc

    try:
        payload: Any = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Invalid YAML in configuration file {path}: {exc}") from exc

    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ConfigurationError("PyIngestKit configuration root must be a YAML mapping")

    try:
        return PyIngestKitConfig.model_validate(payload)
    except PydanticValidationError as exc:
        raise ConfigurationError(f"Invalid PyIngestKit configuration: {exc}") from exc
