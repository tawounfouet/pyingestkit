from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from pyingestkit.artifacts.base import ArtifactStore
from pyingestkit.core.context import RunContext
from pyingestkit.core.events import Event, EventBus, EventType
from pyingestkit.core.job import Job
from pyingestkit.core.result import RunResult, RunStatus, StepResult
from pyingestkit.provenance.manifest import RunManifest


class Runner:
    def __init__(self, artifact_store: ArtifactStore, *, events: EventBus | None = None) -> None:
        self.artifact_store = artifact_store
        self.events = events or EventBus()

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
        self.artifact_store.prepare_run(job.id, context.run_id)
        manifest = RunManifest(
            run_id=str(context.run_id),
            job_id=job.id,
            job_version=job.version,
            started_at=context.started_at,
        )
        warnings: list[str] = list(
            self.events.emit(Event(EventType.RUN_STARTED, str(context.run_id), job.id))
        )
        started_clock = perf_counter()
        step_results: list[StepResult] = []
        data = initial_data
        error: str | None = None
        status = RunStatus.SUCCESS

        try:
            for step in job.pipeline():
                warnings.extend(
                    self.events.emit(
                        Event(
                            EventType.STEP_STARTED,
                            str(context.run_id),
                            job.id,
                            payload={"step": step.step_name},
                        )
                    )
                )
                step_started_at = datetime.now(timezone.utc)
                step_clock = perf_counter()
                try:
                    data = step.execute(context, data)
                    completed_at = datetime.now(timezone.utc)
                    result = StepResult(
                        step_name=step.step_name,
                        status=RunStatus.SUCCESS,
                        started_at=step_started_at,
                        completed_at=completed_at,
                        duration_seconds=perf_counter() - step_clock,
                        output=data,
                    )
                    step_results.append(result)
                    warnings.extend(
                        self.events.emit(
                            Event(
                                EventType.STEP_SUCCEEDED,
                                str(context.run_id),
                                job.id,
                                payload={"step": step.step_name},
                            )
                        )
                    )
                except Exception as exc:
                    completed_at = datetime.now(timezone.utc)
                    error = f"{exc.__class__.__name__}: {exc}"
                    step_results.append(
                        StepResult(
                            step_name=step.step_name,
                            status=RunStatus.FAILED,
                            started_at=step_started_at,
                            completed_at=completed_at,
                            duration_seconds=perf_counter() - step_clock,
                            error=error,
                        )
                    )
                    status = RunStatus.FAILED
                    warnings.extend(
                        self.events.emit(
                            Event(
                                EventType.STEP_FAILED,
                                str(context.run_id),
                                job.id,
                                payload={"step": step.step_name, "error": error},
                            )
                        )
                    )
                    break
        except Exception as exc:
            status = RunStatus.FAILED
            error = f"{exc.__class__.__name__}: {exc}"

        completed_at = datetime.now(timezone.utc)
        result = RunResult(
            run_id=str(context.run_id),
            job_id=job.id,
            job_version=job.version,
            status=status,
            started_at=context.started_at,
            completed_at=completed_at,
            duration_seconds=perf_counter() - started_clock,
            steps=tuple(step_results),
            error=error,
            warnings=tuple(warnings),
        )
        manifest.finalize(result)
        self.artifact_store.write_json(job.id, context.run_id, "manifest.json", manifest.as_dict())
        final_event = EventType.RUN_SUCCEEDED if status is RunStatus.SUCCESS else EventType.RUN_FAILED
        self.events.emit(Event(final_event, str(context.run_id), job.id, payload={"error": error}))
        return result
