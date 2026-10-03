"""Strict V2 replay from durable historical RAW."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime

from pyingestkit.application.runtime import IngestionRuntime
from pyingestkit.domain.artifacts import (
    ArtifactIntegrityError,
    ArtifactKind,
    ArtifactPutStatus,
    ArtifactRetention,
    PutArtifactRequest,
)
from pyingestkit.domain.replay import ReplayRequest, ReplayResult
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId


class ReplayServiceV2:
    """Replay exact historical RAW without resolving or acquiring the live source."""

    def __init__(
        self,
        *,
        runtime: IngestionRuntime,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(runtime, IngestionRuntime):
            raise TypeError("ReplayServiceV2 runtime must be IngestionRuntime.")
        self._runtime = runtime
        self._clock = clock or (lambda: datetime.now(UTC))

    def replay(
        self,
        request: ReplayRequest,
        *,
        ingestion_run_id: IngestionRunId | None = None,
        correlation: CorrelationContext | None = None,
    ) -> ReplayResult:
        """Execute strict replay with a new run id and no live-source fallback."""
        if not isinstance(request, ReplayRequest):
            raise TypeError("ReplayServiceV2 replay request must be ReplayRequest.")
        run_id = ingestion_run_id or IngestionRunId.new()
        if not isinstance(run_id, IngestionRunId):
            raise TypeError("ReplayServiceV2 ingestion_run_id must be IngestionRunId.")
        if run_id == request.source_run_id:
            raise ValueError("ReplayServiceV2 must allocate a new IngestionRunId.")
        context = self._correlation(run_id, correlation)

        try:
            content = self._runtime.artifact_store.open(request.origin_raw_artifact).read()
        except (ArtifactIntegrityError, FileNotFoundError, OSError, ValueError) as exc:
            raise ArtifactIntegrityError(
                "Historical RAW is not readable with its recorded integrity evidence."
            ) from exc

        origin = request.origin_raw_artifact
        acquired_at = origin.created_at or self._now()
        raw_put = self._runtime.artifact_store.put(
            PutArtifactRequest(
                ingestion_run_id=run_id,
                correlation=context,
                kind=ArtifactKind.RAW,
                name="replay.raw",
                content=content,
                media_type=origin.media_type,
                source_resource=origin.resource,
                source_acquired_at=acquired_at,
                expected_checksum_algorithm=origin.checksum_algorithm,
                expected_checksum=origin.checksum,
                retention=ArtifactRetention(retain=True),
                metadata=(
                    ("replay_origin_run_id", str(request.source_run_id)),
                    ("replay_origin_artifact_id", origin.artifact_id),
                ),
            )
        )
        if raw_put.status is not ArtifactPutStatus.SUCCEEDED:
            if raw_put.failure is None:
                raise AssertionError("Replay RAW persistence failure invariant was not preserved.")
            if raw_put.reference is not None:
                raise AssertionError("Failed replay RAW persistence exposed a reference.")
            raise ArtifactIntegrityError(
                "Historical RAW could not be materialized for the replay run."
            )
        if raw_put.reference is None:
            raise AssertionError("Successful replay RAW persistence requires ArtifactReference.")
        if raw_put.reference.checksum != origin.checksum:
            raise ArtifactIntegrityError("Materialized replay RAW checksum differs from origin.")

        expected_version_id = (
            None
            if request.expected_dataset_version is None
            else request.expected_dataset_version.version_id
        )
        ingestion = self._runtime.execute_from_raw(
            request.definition,
            raw_artifact=raw_put.reference,
            raw_content=content,
            validation_rules=request.validation_rules,
            publish=False,
            expected_version_id=expected_version_id,
            ingestion_run_id=run_id,
            correlation=context,
        )

        matched: bool | None = None
        if request.expected_dataset_version is not None:
            if ingestion.dataset_version is not None:
                matched = (
                    ingestion.dataset_version.identity
                    == request.expected_dataset_version.identity
                )
            elif ingestion.failure is not None and ingestion.failure.error_code == (
                "runtime.version_mismatch"
            ):
                matched = False

        return ReplayResult(
            source_run_id=request.source_run_id,
            origin_raw_artifact=origin,
            replay_raw_artifact=raw_put.reference,
            ingestion=ingestion,
            expected_dataset_version=request.expected_dataset_version,
            matched=matched,
        )

    @staticmethod
    def _correlation(
        run_id: IngestionRunId,
        correlation: CorrelationContext | None,
    ) -> CorrelationContext:
        if correlation is None:
            return CorrelationContext(ingestion_run_id=str(run_id))
        if not isinstance(correlation, CorrelationContext):
            raise TypeError("ReplayServiceV2 correlation must be CorrelationContext.")
        if correlation.ingestion_run_id not in {None, str(run_id)}:
            raise ValueError("ReplayServiceV2 correlation run identity mismatch.")
        if correlation.ingestion_run_id is None:
            return replace(correlation, ingestion_run_id=str(run_id))
        return correlation

    def _now(self) -> datetime:
        value = self._clock()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ValueError("ReplayServiceV2 clock must return timezone-aware datetime.")
        return value
