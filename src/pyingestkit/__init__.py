"""PyIngestKit public API."""

import logging

from .core.context import RunContext
from .core.job import Job
from .core.pipeline import Pipeline
from .core.result import RunResult, RunStatus, StepResult
from .core.step import Step

__all__ = [
    "Job",
    "Pipeline",
    "RunContext",
    "RunResult",
    "RunStatus",
    "Step",
    "StepResult",
]

__version__ = "0.1.4"

# Library best practice: never configure application handlers at import time.
logging.getLogger(__name__).addHandler(logging.NullHandler())
