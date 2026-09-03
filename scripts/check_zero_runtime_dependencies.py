from pathlib import Path
import tomllib

root = Path(__file__).resolve().parents[1]
with (root / "pyproject.toml").open("rb") as handle:
    config = tomllib.load(handle)

deps = config["project"].get("dependencies", [])
if deps:
    raise SystemExit(f"Runtime dependencies must be empty in V0.1, got: {deps}")
print("OK: V0.1 has zero mandatory third-party runtime dependencies")
