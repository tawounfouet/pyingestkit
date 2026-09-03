"""PyIngestKit public API."""

import logging as _stdlib_logging

from ._version import __version__ as __version__
from .core.context import RunContext
from .core.job import Job
from .core.pipeline import Pipeline
from .core.result import RunResult, RunStatus, StepResult
from .core.step import Step
from .declarative import JobDefinition, StepDefinition, StepInvocation, job, step
from .runtime.runner import Runner

__all__ = [
    "Job",
    "JobDefinition",
    "Pipeline",
    "RunContext",
    "RunResult",
    "RunStatus",
    "Runner",
    "Step",
    "StepDefinition",
    "StepInvocation",
    "StepResult",
    "job",
    "step",
]

# Library best practice: never configure application handlers at import time.
_stdlib_logging.getLogger(__name__).addHandler(_stdlib_logging.NullHandler())
