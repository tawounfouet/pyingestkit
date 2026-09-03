from __future__ import annotations

from importlib.metadata import EntryPoint, entry_points
import logging
from typing import Any

from pyingestkit.core.exceptions import PluginError
from pyingestkit.core.job import Job
from pyingestkit.core.registry import JobRegistry

ENTRY_POINT_GROUP = "pyingestkit.jobs"
logger = logging.getLogger(__name__)


def _entry_points() -> tuple[EntryPoint, ...]:
    discovered = entry_points()
    selected = discovered.select(group=ENTRY_POINT_GROUP)
    return tuple(selected)


def _coerce_job(value: Any, entry_point: EntryPoint) -> Job:
    if isinstance(value, Job):
        return value
    if isinstance(value, type) and issubclass(value, Job):
        return value()
    if callable(value):
        produced = value()
        if isinstance(produced, Job):
            return produced
    raise PluginError(
        f"Entry point '{entry_point.name}' must expose a Job instance, Job subclass, or zero-arg Job factory"
    )


def discover_jobs() -> tuple[Job, ...]:
    jobs: list[Job] = []
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
            if isinstance(exc, PluginError):
                raise
            logger.exception("Failed loading ingestion plugin entry_point=%s", entry_point.name)
            raise PluginError(f"Failed loading plugin '{entry_point.name}': {exc}") from exc
    return tuple(jobs)


def load_registry() -> JobRegistry:
    registry = JobRegistry()
    registry.register_many(discover_jobs())
    return registry
