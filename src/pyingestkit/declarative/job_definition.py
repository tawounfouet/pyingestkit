from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pyingestkit.core.job import Job
from pyingestkit.core.pipeline import Pipeline

from .builder import PipelineBuilder


class DeclarativeJob(Job):
    definition_style = "declarative"

    def __init__(
        self,
        *,
        job_id: str,
        version: str,
        description: str,
        depends_on: tuple[str, ...],
        pipeline: Pipeline,
        requires_artifacts: str | None = None,
        requires_metadata: str | None = None,
    ) -> None:
        self.id = job_id
        self.version = version
        self.description = description
        self.depends_on = depends_on
        self._pipeline = pipeline
        self.requires_artifacts = requires_artifacts
        self.requires_metadata = requires_metadata

    def pipeline(self) -> Pipeline:
        return self._pipeline


@dataclass
class JobDefinition:
    fn: Callable[[], Any]
    id: str
    version: str = "0.1.0"
    description: str = ""
    depends_on: tuple[str, ...] = ()
    requires_artifacts: str | None = None
    requires_metadata: str | None = None

    def build(self) -> Job:
        builder = PipelineBuilder()
        with builder:
            result = self.fn()
        if result is not None:
            raise TypeError("A @job function must declare steps and return None")
        pipeline = Pipeline(
            invocation.definition.to_step(invocation) for invocation in builder.invocations
        )
        job = DeclarativeJob(
            job_id=self.id,
            version=self.version,
            description=self.description,
            depends_on=self.depends_on,
            pipeline=pipeline,
            requires_artifacts=self.requires_artifacts,
            requires_metadata=self.requires_metadata,
        )
        job.validate_definition()
        return job
