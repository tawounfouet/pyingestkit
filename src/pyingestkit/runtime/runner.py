from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import UUID

from pyingestkit.artifacts.base import ArtifactStore
from pyingestkit.artifacts.raw import RawArtifact
from pyingestkit.core.context import RunContext
from pyingestkit.core.events import Event, EventBus, EventType
from pyingestkit.core.exceptions import ValidationError
from pyingestkit.core.job import Job
from pyingestkit.core.result import RunResult, RunStatus, StepResult
from pyingestkit.logging import log_context
from pyingestkit.metadata import MemoryMetadataStore, MetadataStore
from pyingestkit.profiling import DatasetProfile
from pyingestkit.provenance.manifest import RunManifest
from pyingestkit.validation import ValidationResult, ValidationSeverity

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
    values: Iterable[Any]
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


def _validation_results(
    value: Any, *, _seen: set[int] | None = None
) -> tuple[ValidationResult, ...]:
    """Extract validation results from common nested step outputs."""
    if isinstance(value, ValidationResult):
        return (value,)
    seen = _seen if _seen is not None else set()
    identity = id(value)
    if identity in seen:
        return ()
    seen.add(identity)
    values: Iterable[Any]
    if isinstance(value, dict):
        values = value.values()
    elif isinstance(value, (list, tuple, set, frozenset)):
        values = value
    else:
        return ()
    results: list[ValidationResult] = []
    for item in values:
        results.extend(_validation_results(item, _seen=seen))
    return tuple(results)


def _dataset_profiles(value: Any, *, _seen: set[int] | None = None) -> tuple[DatasetProfile, ...]:
    """Extract dataset profiles from common nested step outputs."""
    if isinstance(value, DatasetProfile):
        return (value,)
    seen = _seen if _seen is not None else set()
    identity = id(value)
    if identity in seen:
        return ()
    seen.add(identity)
    values: Iterable[Any]
    if isinstance(value, dict):
        values = value.values()
    elif isinstance(value, (list, tuple, set, frozenset)):
        values = value
    else:
        return ()
    profiles: list[DatasetProfile] = []
    for item in values:
        profiles.extend(_dataset_profiles(item, _seen=seen))
    return tuple(profiles)


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

    def _record_validation_result(
        self,
        *,
        run_id: str,
        run_uuid: UUID,
        job_id: str,
        step_name: str,
        result: ValidationResult,
        manifest: RunManifest,
    ) -> tuple[str, ...]:
        status = "PASSED" if result.is_valid else "FAILED"
        severity = "INFO" if result.is_valid else ValidationSeverity.ERROR.value
        summary = (
            f"Dataset validation {status.lower()}: "
            f"{result.error_count} error(s), {result.warning_count} warning(s)"
        )
        metadata = {
            "step": step_name,
            "valid": result.is_valid,
            "error_count": result.error_count,
            "warning_count": result.warning_count,
            "issue_count": result.issue_count,
            "review_count": result.review_count,
            "issues_truncated": result.issues_truncated,
        }
        self.metadata_store.record_validation(
            run_id,
            rule="dataset_contract",
            severity=severity,
            status=status,
            message=summary,
            metadata=metadata,
        )
        for issue in result.issues:
            issue_status = "FAILED" if issue.severity is ValidationSeverity.ERROR else "REVIEW"
            self.metadata_store.record_validation(
                run_id,
                rule=issue.rule,
                severity=issue.severity.value,
                status=issue_status,
                message=issue.message,
                metadata={
                    "step": step_name,
                    "field": issue.field,
                    "row_index": issue.row_index,
                    "constraint": issue.constraint,
                    "context": dict(issue.context) if issue.context is not None else None,
                },
            )
        manifest.validations.append({"step": step_name, **result.as_dict()})
        report_path = "reports/validation.json"
        self.artifact_store.write_json(
            job_id,
            run_uuid,
            report_path,
            {
                "report_version": "1",
                "kind": "validation",
                "run_id": run_id,
                "job_id": job_id,
                "validations": manifest.validations,
            },
        )
        if not any(report.get("path") == report_path for report in manifest.reports):
            manifest.reports.append({"kind": "validation", "path": report_path})
        warnings = list(
            self._emit(
                Event(
                    EventType.VALIDATION_COMPLETED,
                    run_id,
                    job_id,
                    payload=metadata,
                )
            )
        )
        warnings.extend(
            self._emit(
                Event(
                    EventType.QUALITY_REPORT_WRITTEN,
                    run_id,
                    job_id,
                    payload={"step": step_name, "kind": "validation", "path": report_path},
                )
            )
        )
        return tuple(warnings)

    def _record_dataset_profile(
        self,
        *,
        run_id: str,
        run_uuid: UUID,
        job_id: str,
        step_name: str,
        profile: DatasetProfile,
        manifest: RunManifest,
    ) -> tuple[str, ...]:
        profile_count = sum(report.get("kind") == "profile" for report in manifest.reports)
        report_path = (
            "reports/profile.json"
            if profile_count == 0
            else f"reports/profile-{profile_count + 1}.json"
        )
        payload = {
            "report_version": "1",
            "kind": "profile",
            "run_id": run_id,
            "job_id": job_id,
            "step": step_name,
            "profile": profile.as_dict(),
        }
        self.artifact_store.write_json(job_id, run_uuid, report_path, payload)
        manifest.reports.append({"kind": "profile", "path": report_path, "step": step_name})
        metadata = {
            "step": step_name,
            "row_count": profile.row_count,
            "field_count": profile.field_count,
            "duplicate_row_count": profile.duplicate_row_count,
            "duration_ms": profile.duration_ms,
            "path": report_path,
        }
        warnings = list(
            self._emit(
                Event(
                    EventType.PROFILE_COMPLETED,
                    run_id,
                    job_id,
                    payload=metadata,
                )
            )
        )
        warnings.extend(
            self._emit(
                Event(
                    EventType.QUALITY_REPORT_WRITTEN,
                    run_id,
                    job_id,
                    payload={"step": step_name, "kind": "profile", "path": report_path},
                )
            )
        )
        return tuple(warnings)

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
                        step_started_at = datetime.now(UTC)
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
                            validations = _validation_results(data)
                            for validation in validations:
                                warnings.extend(
                                    self._record_validation_result(
                                        run_id=run_id,
                                        run_uuid=context.run_id,
                                        job_id=job.id,
                                        step_name=step.step_name,
                                        result=validation,
                                        manifest=manifest,
                                    )
                                )
                            validation_errors = sum(
                                validation.error_count for validation in validations
                            )
                            if validation_errors:
                                raise ValidationError(
                                    f"Dataset validation failed with {validation_errors} error(s)"
                                )

                            profiles = _dataset_profiles(data)
                            for profile in profiles:
                                warnings.extend(
                                    self._record_dataset_profile(
                                        run_id=run_id,
                                        run_uuid=context.run_id,
                                        job_id=job.id,
                                        step_name=step.step_name,
                                        profile=profile,
                                        manifest=manifest,
                                    )
                                )

                            completed_at = datetime.now(UTC)
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
                        except Exception as exc:  # noqa: BLE001 - user step execution boundary
                            completed_at = datetime.now(UTC)
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
                            except Exception as hook_exc:  # noqa: BLE001 - lifecycle hook boundary
                                warnings.append(
                                    f"Failed emitting STEP_FAILED lifecycle event: {hook_exc}"
                                )
                            break
            except Exception as exc:  # noqa: BLE001 - run lifecycle boundary
                status = RunStatus.FAILED
                error = f"{exc.__class__.__name__}: {exc}"
                logger.exception("Run lifecycle failed")

            completed_at = datetime.now(UTC)
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
            except Exception as exc:  # noqa: BLE001 - artifact backend boundary
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
            except Exception as exc:  # noqa: BLE001 - final lifecycle hook boundary
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
            except Exception:  # noqa: BLE001 - best-effort manifest finalization boundary
                # If the first write already failed this may fail again. Metadata
                # remains authoritative for the failure and the exception is logged.
                logger.exception("Unable to finalize run manifest")

            if result.succeeded:
                logger.info("Run succeeded %.3fs", result.duration_seconds)
            else:
                logger.error("Run failed %.3fs error=%s", result.duration_seconds, error)
            return result
