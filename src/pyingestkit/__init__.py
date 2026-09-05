"""PyIngestKit public API."""

import logging as _stdlib_logging

from ._version import __version__ as __version__
from .artifacts import ArtifactURI
from .contracts import DatasetContract, FieldContract
from .core.context import RunContext
from .core.job import Job
from .core.pipeline import Pipeline
from .core.result import RunResult, RunStatus, StepResult
from .core.step import Step
from .dataset import Dataset
from .declarative import JobDefinition, StepDefinition, StepInvocation, job, step
from .diff import DatasetDiff, DatasetDiffer, DiffEntry, DiffKind, DiffPolicy, SchemaDiff
from .parsers import CsvParser, ExcelParser, JsonParser, NdjsonParser, ParquetParser
from .profiling import DatasetProfile, DatasetProfiler, FieldProfile
from .quality import QualityReport
from .replay import ReplayContext, ReplayRawArtifact, ReplayResult, ReplayService
from .runtime.runner import Runner
from .targets import (
    IdempotencyAction,
    IdempotencyPolicy,
    LoadMode,
    PostgresTarget,
    Target,
    TargetCapabilities,
    TargetLoadDecision,
    TargetLoadExecutor,
    TargetLoadRequest,
    TargetLoadResult,
    TargetLoadStatus,
)
from .validation import ValidationIssue, ValidationResult
from .versioning import (
    DatasetFingerprint,
    DatasetFingerprinter,
    DatasetFingerprintPolicy,
    DatasetVersion,
    DatasetVersionStore,
    FilesystemDatasetVersionStore,
    PublishedDataset,
    SnapshotCodec,
)

__all__ = [
    "ArtifactURI",
    "CsvParser",
    "Dataset",
    "DatasetContract",
    "DatasetDiff",
    "DatasetDiffer",
    "DatasetFingerprint",
    "DatasetFingerprinter",
    "DatasetFingerprintPolicy",
    "DatasetProfile",
    "DatasetProfiler",
    "DatasetVersion",
    "DatasetVersionStore",
    "DiffEntry",
    "DiffKind",
    "DiffPolicy",
    "ExcelParser",
    "FieldContract",
    "FieldProfile",
    "FilesystemDatasetVersionStore",
    "Job",
    "JobDefinition",
    "JsonParser",
    "IdempotencyAction",
    "IdempotencyPolicy",
    "NdjsonParser",
    "ParquetParser",
    "Pipeline",
    "PublishedDataset",
    "QualityReport",
    "ReplayContext",
    "ReplayRawArtifact",
    "ReplayResult",
    "ReplayService",
    "RunContext",
    "RunResult",
    "RunStatus",
    "Runner",
    "SchemaDiff",
    "SnapshotCodec",
    "Step",
    "StepDefinition",
    "StepInvocation",
    "StepResult",
    "LoadMode",
    "PostgresTarget",
    "Target",
    "TargetCapabilities",
    "TargetLoadDecision",
    "TargetLoadExecutor",
    "TargetLoadRequest",
    "TargetLoadResult",
    "TargetLoadStatus",
    "ValidationIssue",
    "ValidationResult",
    "job",
    "step",
]

# Library best practice: never configure application handlers at import time.
_stdlib_logging.getLogger(__name__).addHandler(_stdlib_logging.NullHandler())
