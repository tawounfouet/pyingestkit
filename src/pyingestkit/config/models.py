from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RuntimeConfig(BaseModel):
    """Validated runtime defaults loaded from project configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace: Path = Path(".pyingest")
    fixture_mode: bool = False
    parameters: dict[str, Any] = Field(default_factory=dict)


class PyIngestKitConfig(BaseModel):
    """Root configuration model for a PyIngestKit project."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
