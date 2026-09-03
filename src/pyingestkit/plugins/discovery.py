from __future__ import annotations

from importlib.metadata import EntryPoint, entry_points
from typing import Any

from pyingestkit.core.exceptions import PluginError
from pyingestkit.core.job import Job
from pyingestkit.core.registry import JobRegistry

ENTRY_POINT_GROUP = "pyingestkit.jobs"


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
    for entry_point in _entry_points():
        try:
            loaded = entry_point.load()
            job = _coerce_job(loaded, entry_point)
            job.validate_definition()
            jobs.append(job)
        except Exception as exc:
            if isinstance(exc, PluginError):
                raise
            raise PluginError(f"Failed loading plugin '{entry_point.name}': {exc}") from exc
    return tuple(jobs)


def load_registry() -> JobRegistry:
    registry = JobRegistry()
    registry.register_many(discover_jobs())
    return registry
