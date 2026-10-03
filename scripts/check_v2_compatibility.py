from __future__ import annotations

import importlib
import inspect
import json
import re
import tomllib
from pathlib import Path

import pyingestkit
from pyingestkit._api_v2 import V2_TARGET_ROOT_EXPORTS

ROOT = Path(__file__).resolve().parents[1]
STABLE_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "stable_release_v2.json"
RC_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "release_candidate_v2.json"
WIRE_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "v2_boundary_values.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(qualified_name: str) -> object:
    module_name, _, attribute = qualified_name.rpartition(".")
    if not module_name or not attribute:
        raise SystemExit(f"Invalid qualified contract name: {qualified_name}")
    return getattr(importlib.import_module(module_name), attribute)


def _method_names(protocol: type[object]) -> set[str]:
    return {
        name
        for name, value in vars(protocol).items()
        if not name.startswith("_") and (callable(value) or isinstance(value, property))
    }


def _distribution_name(requirement: str) -> str:
    match = re.match(r"[A-Za-z0-9_.-]+", requirement)
    if match is None:
        raise SystemExit(f"Unable to parse dependency name: {requirement}")
    return match.group(0).lower().replace("_", "-")


def main() -> int:
    stable = _load(STABLE_FIXTURE)
    rc = _load(RC_FIXTURE)
    wire = _load(WIRE_FIXTURE)

    if stable["schema_version"] != 1 or stable["version"] != "2.0.0":
        raise SystemExit("Unexpected frozen PyIngestKit 2.0 stable fixture")
    if not pyingestkit.__version__.startswith("2."):
        raise SystemExit(f"PyIngestKit 2.x compatibility check received {pyingestkit.__version__}")

    stable_root = tuple(str(item) for item in stable["root_exports"])
    rc_root = tuple(str(item) for item in rc["root_exports"])
    if stable_root != rc_root:
        raise SystemExit("Frozen 2.0 stable root differs from qualified RC root")
    if tuple(pyingestkit.__all__) != stable_root or V2_TARGET_ROOT_EXPORTS != stable_root:
        raise SystemExit("Current package root drifted from the frozen 2.0 baseline")

    stable_protocols = stable["stable_protocols"]
    rc_protocols = rc["stable_protocols"]
    if stable_protocols != rc_protocols:
        raise SystemExit("Frozen 2.0 Protocol fixture differs from qualified RC fixture")
    assert isinstance(stable_protocols, dict)
    for qualified_name, expected_raw in stable_protocols.items():
        protocol = _resolve(str(qualified_name))
        if not isinstance(protocol, type):
            raise SystemExit(f"Frozen Protocol is not a class: {qualified_name}")
        expected = {str(item) for item in expected_raw}
        actual = _method_names(protocol)
        if actual != expected:
            raise SystemExit(
                f"2.0 Protocol drift for {qualified_name}: {sorted(actual)} != {sorted(expected)}"
            )

    stable_runtime = stable["runtime"]
    rc_runtime = rc["runtime"]
    if stable_runtime != rc_runtime:
        raise SystemExit("Frozen 2.0 runtime signature fixture differs from RC fixture")
    assert isinstance(stable_runtime, dict)
    method_name = str(stable_runtime["canonical_method"])
    actual_parameters = list(
        inspect.signature(getattr(pyingestkit.IngestionRuntime, method_name)).parameters
    )
    expected_parameters = [str(item) for item in stable_runtime["parameters"]]
    if actual_parameters != expected_parameters:
        raise SystemExit(
            f"Frozen IngestionRuntime.{method_name} signature drift: "
            f"{actual_parameters} != {expected_parameters}"
        )

    stable_wire = stable["wire_contracts"]
    current_wire = wire.get("contracts")
    if stable_wire != current_wire:
        raise SystemExit("Current wire contracts drifted from the frozen 2.0 baseline")

    forbidden = {str(item) for item in stable["forbidden_root_exports"]}
    leaked = forbidden.intersection(pyingestkit.__all__)
    if leaked:
        raise SystemExit(f"Legacy root exports leaked into 2.x: {sorted(leaked)}")

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    extras = project.get("optional-dependencies", {})
    expected_extras = {str(item) for item in stable["provider_extras"]}
    missing_extras = expected_extras.difference(extras)
    if missing_extras:
        raise SystemExit(f"Missing frozen 2.0 provider extras: {sorted(missing_extras)}")

    base_dependencies = {
        _distribution_name(str(requirement)) for requirement in project.get("dependencies", [])
    }
    forbidden_base = {
        "boto3",
        "httpx",
        "openpyxl",
        "psycopg",
        "pyarrow",
        "sqlalchemy",
        "pytransformkit",
    }
    leaked_base = base_dependencies.intersection(forbidden_base)
    if leaked_base:
        raise SystemExit(f"Provider dependencies leaked into 2.x base: {sorted(leaked_base)}")

    print(
        "OK: current PyIngestKit 2.x preserves the frozen 2.0 root, runtime, "
        "Protocol and wire-contract compatibility baseline"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
