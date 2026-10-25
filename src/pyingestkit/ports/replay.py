"""Port contracts for V2 replay provenance resolution and historical reconstruction."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from pyingestkit.domain.replay import ReplayLineage, ReplayRequest
from pyingestkit.domain.shared import IngestionRunId


@runtime_checkable
class ReplayProvenanceResolver(Protocol):
    """Resolve durable historical evidence into an executable ReplayRequest."""

    def resolve_from_version(
        self,
        dataset_id: str,
        version_id: str,
        *,
        parameter_overrides: Mapping[str, object] | None = None,
    ) -> ReplayRequest:
        """Resolve historical version evidence into a strict ReplayRequest."""
        ...

    def resolve_from_run(
        self,
        source_run_id: IngestionRunId,
        *,
        parameter_overrides: Mapping[str, object] | None = None,
    ) -> ReplayRequest:
        """Resolve historical run evidence into a strict ReplayRequest."""
        ...


@runtime_checkable
class ReplayLineageLedger(Protocol):
    """Protocol for recording and querying durable replay lineage."""

    def record_replay_lineage(self, lineage: ReplayLineage) -> ReplayLineage:
        """Record or verify an immutable replay lineage evidence."""
        ...

    def list_replays(
        self,
        dataset_id: str | None = None,
        source_run_id: IngestionRunId | None = None,
    ) -> tuple[ReplayLineage, ...]:
        """List recorded replay lineages matching optional dataset_id and source_run_id."""
        ...


__all__ = ["ReplayLineageLedger", "ReplayProvenanceResolver"]
