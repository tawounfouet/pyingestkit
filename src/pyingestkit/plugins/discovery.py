from __future__ import annotations

import logging
from dataclasses import dataclass
from importlib.metadata import EntryPoint, entry_points
from typing import Any

from pyingestkit.core.exceptions import PluginError
from pyingestkit.core.job import Job
from pyingestkit.core.registry import JobRegistry
from pyingestkit.declarative import JobDefinition

ENTRY_POINT_GROUP = "pyingestkit.jobs"
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PluginFailure:
    """One isolated plugin-discovery failure.

    ``entry_point`` is the entry-point name declared by the external package;
    ``error`` is a stable human diagnostic in ``ExceptionType: message`` form.
    """

    entry_point: str
    error: str


@dataclass(frozen=True, slots=True)
class DiscoveryReport:
    """Tolerant plugin-discovery result containing healthy jobs and failures."""

    jobs: tuple[Job, ...]
    failures: tuple[PluginFailure, ...]


def _entry_points() -> tuple[EntryPoint, ...]:
    """Return job entry points in deterministic order.

    ``importlib.metadata`` does not make ordering a cross-environment contract.
    Sorting here prevents package installation order from changing which plugin
    is considered first when duplicate logical job IDs are present.
    """

    discovered = entry_points()
    selected = discovered.select(group=ENTRY_POINT_GROUP)
    return tuple(sorted(selected, key=lambda item: (item.name, item.value)))


def _coerce_job(value: Any, entry_point: EntryPoint) -> Job:
    if isinstance(value, JobDefinition):
        return value.build()
    if isinstance(value, Job):
        return value
    if isinstance(value, type) and issubclass(value, Job):
        return value()
    if callable(value):
        produced = value()
        if isinstance(produced, JobDefinition):
            return produced.build()
        if isinstance(produced, Job):
            return produced
    raise PluginError(
        f"Entry point '{entry_point.name}' must expose a JobDefinition, Job instance, "
        "Job subclass, or zero-arg factory"
    )


def discover_plugins() -> DiscoveryReport:
    """Discover external jobs while isolating failures.

    Healthy plugins remain available even if another third-party entry point
    cannot import, validates incorrectly, or duplicates an already-discovered
    logical job ID. For duplicate IDs, deterministic entry-point ordering means
    the first entry point wins and later duplicates are reported as failures.
    """

    jobs: list[Job] = []
    failures: list[PluginFailure] = []
    discovered = _entry_points()
    seen_job_ids: dict[str, str] = {}
    logger.debug("Discovering ingestion plugins count=%d", len(discovered))
    for entry_point in discovered:
        try:
            loaded = entry_point.load()
            job = _coerce_job(loaded, entry_point)
            job.validate_definition()
            previous = seen_job_ids.get(job.id)
            if previous is not None:
                raise PluginError(
                    f"Duplicate ingestion job id '{job.id}' from entry point "
                    f"'{entry_point.name}'; already provided by '{previous}'"
                )
            seen_job_ids[job.id] = entry_point.name
            jobs.append(job)
            logger.debug(
                "Loaded ingestion plugin entry_point=%s job_id=%s", entry_point.name, job.id
            )
        except Exception as exc:  # noqa: BLE001 - third-party plugin isolation boundary
            error = f"{exc.__class__.__name__}: {exc}"
            failures.append(PluginFailure(entry_point.name, error))
            logger.error(
                "Failed loading ingestion plugin entry_point=%s error=%s",
                entry_point.name,
                error,
            )
    return DiscoveryReport(tuple(jobs), tuple(failures))


def discover_jobs(*, strict: bool = True) -> tuple[Job, ...]:
    """Return discovered jobs, raising on any plugin failure when ``strict``.

    ``strict=True`` is the stable library default. CLI registry loading uses the
    tolerant helpers below so one unrelated broken third-party plugin does not
    make healthy installed jobs unusable.
    """

    report = discover_plugins()
    if strict and report.failures:
        details = "; ".join(f"{item.entry_point}: {item.error}" for item in report.failures)
        raise PluginError(f"One or more ingestion plugins failed to load: {details}")
    return report.jobs


def load_registry_with_diagnostics() -> tuple[JobRegistry, tuple[PluginFailure, ...]]:
    """Build a tolerant registry and return isolated plugin diagnostics."""

    report = discover_plugins()
    registry = JobRegistry()
    registry.register_many(report.jobs)
    return registry, report.failures


def load_registry() -> JobRegistry:
    """Build a tolerant registry containing all healthy discovered jobs."""

    registry, _ = load_registry_with_diagnostics()
    return registry
