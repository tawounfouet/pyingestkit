from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from pyingestkit.artifacts.base import ArtifactStore


@dataclass(slots=True)
class RunContext:
    job_id: str
    job_version: str
    artifact_store: ArtifactStore
    run_id: UUID = field(default_factory=uuid4)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    as_of: date | None = None
    fixture_mode: bool = False
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def parameter(self, name: str, default: Any = None) -> Any:
        return self.parameters.get(name, default)
