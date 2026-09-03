from __future__ import annotations

from datetime import datetime, timezone
import logging
from time import perf_counter
from typing import Any

from pyingestkit.artifacts.base import ArtifactStore
from pyingestkit.artifacts.raw import RawArtifact
from pyingestkit.core.context import RunContext
from pyingestkit.core.events import Event, EventBus, EventType
from pyingestkit.core.job import Job
from pyingestkit.core.result import RunResult, RunStatus, StepResult
from pyingestkit.logging import log_context
from pyingestkit.metadata import MemoryMetadataStore, MetadataStore
from pyingestkit.provenance.manifest import RunManifest

logger = logging.getLogger(__name__)


def _raw_artifacts(value: Any, *, _seen: set[int] | None = None) -> tuple[RawArtifact, ...]:
    """Extract RAW artifacts from common nested step outputs without imposing a data model."""
    if isinstance(value, RawArtifact):
        return (value,)
    seen = _seen if _seen is not None else set()
    identity = id(value)
    if identity in seen:
        return ()
    seen.add(identity)
    if isinstance(value, dict):
        values = value.values()
    elif isinstance(value, (list, tuple, set, frozenset)):
        values = value
    else:
        return ()
    artifacts: list[RawArtifact] = []
    for item in values:
        artifacts.extend(_raw_artifacts(item, _seen=seen))
    return tuple(artifacts)


class Runner:
    """Execute a Job against ArtifactStore and MetadataStore contracts.

    Runner never selects SQLite/PostgreSQL itself. Applications (including the
    CLI) choose the metadata adapter. An in-memory store is used only when a
    programmatic caller deliberately omits one.
    """

    def __init__(
        self,
        artifact_store: ArtifactStore,
        *,
        metadata_store: MetadataStore | None = None,
        events: EventBus | None = None,
    ) -> None:
        self.artifact_store = artifact_store
        self.metadata_store = metadata_store or MemoryMetadataStore()
        self.events = events or EventBus()

    def _emit(self, event: Event) -> tuple[str, ...]:
        self.metadata_store.record_event(event)
        return self.events.emit(event)

    def run(
        self,
        job: Job,
        *,
        initial_data: Any = None,
        parameters: dict[str, Any] | None = None,
        fixture_mode: bool = False,
    ) -> RunResult:
        job.validate_definition()
        context = RunContext(
            job_id=job.id,
            job_version=job.version,
            artifact_store=self.artifact_store,
            fixture_mode=fixture_mode,
            parameters=parameters or {},
        )
        run_id = str(context.run_id)
        manifest = RunManifest(
            run_id=run_id,
            job_id=job.id,
            job_version=job.version,
            started_at=context.started_at,
        )
        warnings: list[str] = []
        step_results: list[StepResult] = []
        data = initial_data
        error: str | None = None
        status = RunStatus.SUCCESS
        started_clock = perf_counter()

        self.artifact_store.prepare_run(job.id, context.run_id)
        self.metadata_store.initialize()
        self.metadata_store.start_run(context)

        with log_context(run_id=run_id, job_id=job.id):
            logger.info("Run started")
            try:
                warnings.extend(self._emit(Event(EventType.RUN_STARTED, run_id, job.id)))
                for position, step in enumerate(job.pipeline(), start=1):
                    with log_context(step=step.step_name):
                        logger.info("Step started")
                        step_started_at = datetime.now(timezone.utc)
                        step_clock = perf_counter()
                        try:
                            warnings.extend(
                                self._emit(
                                    Event(
                                        EventType.STEP_STARTED,
                                        run_id,
                                        job.id,
                                        payload={"step": step.step_name},
                                    )
                                )
                            )
                            data = step.execute(context, data)
                            completed_at = datetime.now(timezone.utc)
                            step_result = StepResult(
                                step_name=step.step_name,
                                status=RunStatus.SUCCESS,
                                started_at=step_started_at,
                                completed_at=completed_at,
                                duration_seconds=perf_counter() - step_clock,
                                output=data,
                            )
                            step_results.append(step_result)
                            self.metadata_store.record_step(run_id, position, step_result)
                            for artifact in _raw_artifacts(data):
                                manifest.add_artifact(artifact)
                                self.metadata_store.record_artifact(run_id, artifact, kind="raw")
                            logger.info(
                                "Step succeeded %.3fs",
                                step_result.duration_seconds,
                            )
                            warnings.extend(
                                self._emit(
                                    Event(
                                        EventType.STEP_SUCCEEDED,
                                        run_id,
                                        job.id,
                                        payload={
                                            "step": step.step_name,
                                            "duration_seconds": step_result.duration_seconds,
                                        },
                                    )
                                )
                            )
                        except Exception as exc:
                            completed_at = datetime.now(timezone.utc)
                            error = f"{exc.__class__.__name__}: {exc}"
                            step_result = StepResult(
                                step_name=step.step_name,
                                status=RunStatus.FAILED,
                                started_at=step_started_at,
                                completed_at=completed_at,
                                duration_seconds=perf_counter() - step_clock,
                                error=error,
                            )
                            if (
                                step_results
                                and step_results[-1].step_name == step.step_name
                                and step_results[-1].status is RunStatus.SUCCESS
                            ):
                                # A critical post-step hook may fail after the successful
                                # execution result was recorded. Replace that result rather
                                # than emitting two records for one pipeline position.
                                step_results[-1] = step_result
                            else:
                                step_results.append(step_result)
                            self.metadata_store.record_step(run_id, position, step_result)
                            status = RunStatus.FAILED
                            logger.exception("Step failed")
                            try:
                                warnings.extend(
                                    self._emit(
                                        Event(
                                            EventType.STEP_FAILED,
                                            run_id,
                                            job.id,
                                            payload={"step": step.step_name, "error": error},
                                        )
                                    )
                                )
                            except Exception as hook_exc:
                                warnings.append(
                                    f"Failed emitting STEP_FAILED lifecycle event: {hook_exc}"
                                )
                            break
            except Exception as exc:
                status = RunStatus.FAILED
                error = f"{exc.__class__.__name__}: {exc}"
                logger.exception("Run lifecycle failed")

            completed_at = datetime.now(timezone.utc)
            duration_seconds = perf_counter() - started_clock

            def build_result() -> RunResult:
                return RunResult(
                    run_id=run_id,
                    job_id=job.id,
                    job_version=job.version,
                    status=status,
                    started_at=context.started_at,
                    completed_at=completed_at,
                    duration_seconds=duration_seconds,
                    steps=tuple(step_results),
                    error=error,
                    warnings=tuple(warnings),
                )

            # Manifest writing is part of the run lifecycle. A failure here must
            # not leave queryable metadata claiming SUCCESS.
            provisional = build_result()
            manifest.finalize(provisional)
            try:
                manifest_path = self.artifact_store.write_json(
                    job.id, context.run_id, "manifest.json", manifest.as_dict()
                )
                logger.debug("Run manifest written path=%s", manifest_path)
            except Exception as exc:
                status = RunStatus.FAILED
                error = f"{exc.__class__.__name__}: {exc}"
                logger.exception("Run manifest write failed")

            final_event_type = (
                EventType.RUN_SUCCEEDED if status is RunStatus.SUCCESS else EventType.RUN_FAILED
            )
            try:
                warnings.extend(
                    self._emit(
                        Event(
                            final_event_type,
                            run_id,
                            job.id,
                            payload={"error": error, "duration_seconds": duration_seconds},
                        )
                    )
                )
            except Exception as exc:
                status = RunStatus.FAILED
                error = f"{exc.__class__.__name__}: {exc}"
                fallback = Event(
                    EventType.RUN_FAILED,
                    run_id,
                    job.id,
                    payload={"error": error, "duration_seconds": duration_seconds},
                )
                self.metadata_store.record_event(fallback)
                logger.exception("Final lifecycle hook failed")

            result = build_result()
            self.metadata_store.finish_run(result)

            # Rewrite the manifest so final hook warnings/failures are reflected.
            manifest.finalize(result)
            try:
                manifest_path = self.artifact_store.write_json(
                    job.id, context.run_id, "manifest.json", manifest.as_dict()
                )
                logger.debug("Run manifest finalized path=%s", manifest_path)
            except Exception:
                # If the first write already failed this may fail again. Metadata
                # remains authoritative for the failure and the exception is logged.
                logger.exception("Unable to finalize run manifest")

            if result.succeeded:
                logger.info("Run succeeded %.3fs", result.duration_seconds)
            else:
                logger.error("Run failed %.3fs error=%s", result.duration_seconds, error)
            return result
