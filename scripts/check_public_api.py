from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))

import pyingestkit

expected = {
    "CsvParser",
    "Dataset",
    "DatasetFingerprintPolicy",
    "DatasetFingerprinter",
    "DatasetFingerprint",
    "DatasetDiffer",
    "DatasetDiff",
    "DatasetContract",
    "DatasetProfile",
    "DatasetProfiler",
    "DatasetVersion",
    "DatasetVersionStore",
    "FieldContract",
    "FieldProfile",
    "FilesystemDatasetVersionStore",
    "ExcelParser",
    "SchemaDiff",
    "SnapshotCodec",
    "DiffPolicy",
    "DiffKind",
    "DiffEntry",
    "IdempotencyAction",
    "IdempotencyPolicy",
    "Job",
    "JobDefinition",
    "JsonParser",
    "LoadMode",
    "NdjsonParser",
    "ParquetParser",
    "Pipeline",
    "PostgresTarget",
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
    "Step",
    "StepDefinition",
    "StepInvocation",
    "StepResult",
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
}
actual = set(pyingestkit.__all__)
if actual != expected:
    raise SystemExit(f"Unexpected public API. expected={sorted(expected)} actual={sorted(actual)}")
if pyingestkit.__version__ != "0.5.1":
    raise SystemExit(f"Unexpected version: {pyingestkit.__version__}")
print("OK: public API matches V0.5.1 PostgreSQL persistence maintenance contract")
