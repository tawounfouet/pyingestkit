from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))

import pyingestkit

expected = {
    "CsvParser",
    "Dataset",
    "DatasetContract",
    "DatasetProfile",
    "DatasetProfiler",
    "FieldContract",
    "FieldProfile",
    "ExcelParser",
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
}
actual = set(pyingestkit.__all__)
if actual != expected:
    raise SystemExit(f"Unexpected public API. expected={sorted(expected)} actual={sorted(actual)}")
if pyingestkit.__version__ != "0.3.0":
    raise SystemExit(f"Unexpected version: {pyingestkit.__version__}")
print("OK: public API matches V0.3.0 Quality & Formats release contract")
