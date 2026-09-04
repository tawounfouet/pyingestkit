"""PyIngestKit public API."""

import logging as _stdlib_logging

from ._version import __version__ as __version__
from .contracts import DatasetContract, FieldContract
from .core.context import RunContext
from .core.job import Job
from .core.pipeline import Pipeline
from .core.result import RunResult, RunStatus, StepResult
from .core.step import Step
from .dataset import Dataset
from .declarative import JobDefinition, StepDefinition, StepInvocation, job, step
from .parsers import CsvParser, ExcelParser, JsonParser, NdjsonParser, ParquetParser
from .profiling import DatasetProfile, DatasetProfiler, FieldProfile
from .quality import QualityReport
from .runtime.runner import Runner
from .validation import ValidationIssue, ValidationResult

__all__ = [
    "CsvParser",
    "Dataset",
    "DatasetContract",
    "DatasetProfile",
    "DatasetProfiler",
    "ExcelParser",
    "FieldContract",
    "FieldProfile",
    "Job",
    "JobDefinition",
    "JsonParser",
    "NdjsonParser",
    "ParquetParser",
    "Pipeline",
    "QualityReport",
    "RunContext",
    "RunResult",
    "RunStatus",
    "Runner",
    "Step",
    "StepDefinition",
    "StepInvocation",
    "StepResult",
    "ValidationIssue",
    "ValidationResult",
    "job",
    "step",
]

# Library best practice: never configure application handlers at import time.
_stdlib_logging.getLogger(__name__).addHandler(_stdlib_logging.NullHandler())
