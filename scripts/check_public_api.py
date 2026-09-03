from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))

import pyingestkit

expected = {"Job", "Step", "Pipeline", "RunContext", "RunResult", "RunStatus", "StepResult"}
actual = set(pyingestkit.__all__)
if actual != expected:
    raise SystemExit(f"Unexpected public API. expected={sorted(expected)} actual={sorted(actual)}")
print("OK: public API matches V0.1 contract")
