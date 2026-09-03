from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import EntryPoint, entry_points
import logging
from typing import Any

from pyingestkit.core.exceptions import PluginError
from pyingestkit.core.job import Job
from pyingestkit.core.registry import JobRegistry
from pyingestkit.declarative import JobDefinition

ENTRY_POINT_GROUP = "pyingestkit.jobs"
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PluginFailure:
    entry_point: str
    error: str


@dataclass(frozen=True, slots=True)
class DiscoveryReport:
    jobs: tuple[Job, ...]
    failures: tuple[PluginFailure, ...]


def _entry_points() -> tuple[EntryPoint, ...]:
    discovered = entry_points()
    selected = discovered.select(group=ENTRY_POINT_GROUP)
    return tuple(selected)


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
    jobs: list[Job] = []
    failures: list[PluginFailure] = []
    discovered = _entry_points()
    logger.debug("Discovering ingestion plugins count=%d", len(discovered))
    for entry_point in discovered:
        try:
            loaded = entry_point.load()
            job = _coerce_job(loaded, entry_point)
            job.validate_definition()
            jobs.append(job)
            logger.debug("Loaded ingestion plugin entry_point=%s job_id=%s", entry_point.name, job.id)
        except Exception as exc:
            error = f"{exc.__class__.__name__}: {exc}"
            failures.append(PluginFailure(entry_point.name, error))
            logger.error("Failed loading ingestion plugin entry_point=%s error=%s", entry_point.name, error)
    return DiscoveryReport(tuple(jobs), tuple(failures))


def discover_jobs(*, strict: bool = True) -> tuple[Job, ...]:
    report = discover_plugins()
    if strict and report.failures:
        details = "; ".join(f"{item.entry_point}: {item.error}" for item in report.failures)
        raise PluginError(f"One or more ingestion plugins failed to load: {details}")
    return report.jobs


def load_registry_with_diagnostics() -> tuple[JobRegistry, tuple[PluginFailure, ...]]:
    report = discover_plugins()
    registry = JobRegistry()
    registry.register_many(report.jobs)
    return registry, report.failures


def load_registry() -> JobRegistry:
    registry, _ = load_registry_with_diagnostics()
    return registry
