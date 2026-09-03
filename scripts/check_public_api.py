from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))

import pyingestkit

expected = {
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
}
actual = set(pyingestkit.__all__)
if actual != expected:
    raise SystemExit(f"Unexpected public API. expected={sorted(expected)} actual={sorted(actual)}")
if pyingestkit.__version__ != "0.2.0a1":
    raise SystemExit(f"Unexpected version: {pyingestkit.__version__}")
print("OK: public API matches V0.2.0-a1 Foundation-compatible contract")
