from __future__ import annotations

import importlib
import inspect
import json
import re
import tomllib
from pathlib import Path

import pyingestkit
from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_MILESTONE_CANDIDATE,
    V2_TARGET_ROOT_EXPORTS,
)

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

    if stable["schema_version"] != 1:
        raise SystemExit("Unsupported V2 stable contract schema")
    if stable["version"] != "2.0.0" or pyingestkit.__version__ != "2.0.0":
        raise SystemExit(f"Expected stable 2.0.0, got {pyingestkit.__version__}")

    stable_root = tuple(str(item) for item in stable["root_exports"])
    rc_root = tuple(str(item) for item in rc["root_exports"])
    if stable_root != rc_root:
        raise SystemExit("Stable root differs from the qualified RC root")
    if tuple(pyingestkit.__all__) != stable_root or V2_TARGET_ROOT_EXPORTS != stable_root:
        raise SystemExit("Installed/machine-readable root differs from stable freeze")

    stable_protocols = stable["stable_protocols"]
    rc_protocols = rc["stable_protocols"]
    if stable_protocols != rc_protocols:
        raise SystemExit("Stable Protocol fixture differs from the qualified RC fixture")
    assert isinstance(stable_protocols, dict)
    for qualified_name, expected_raw in stable_protocols.items():
        protocol = _resolve(str(qualified_name))
        if not isinstance(protocol, type):
            raise SystemExit(f"Stable Protocol is not a class: {qualified_name}")
        expected = {str(item) for item in expected_raw}
        actual = _method_names(protocol)
        if actual != expected:
            raise SystemExit(
                f"Protocol drift for {qualified_name}: {sorted(actual)} != {sorted(expected)}"
            )

    stable_runtime = stable["runtime"]
    rc_runtime = rc["runtime"]
    if stable_runtime != rc_runtime:
        raise SystemExit("Stable runtime signature fixture differs from the RC fixture")
    assert isinstance(stable_runtime, dict)
    method_name = str(stable_runtime["canonical_method"])
    actual_parameters = list(
        inspect.signature(getattr(pyingestkit.IngestionRuntime, method_name)).parameters
    )
    expected_parameters = [str(item) for item in stable_runtime["parameters"]]
    if actual_parameters != expected_parameters:
        raise SystemExit(
            f"IngestionRuntime.{method_name} signature drift: "
            f"{actual_parameters} != {expected_parameters}"
        )

    stable_wire = stable["wire_contracts"]
    if not isinstance(stable_wire, dict):
        raise SystemExit("Stable wire contract fixture must be an object")
    current_wire = wire.get("contracts")
    if stable_wire != current_wire:
        raise SystemExit("Stable wire versions differ from the frozen boundary fixture")

    forbidden = {str(item) for item in stable["forbidden_root_exports"]}
    leaked = forbidden.intersection(pyingestkit.__all__)
    if leaked:
        raise SystemExit(f"Legacy root exports leaked into stable V2: {sorted(leaked)}")

    if V2_API_PHASE != "LOT-22_STABLE":
        raise SystemExit(f"Unexpected V2 stable phase: {V2_API_PHASE}")
    if V2_COMPLETED_LOTS[-1] != "LOT-22":
        raise SystemExit(f"LOT-22 is not current: {V2_COMPLETED_LOTS[-1]}")
    if V2_MILESTONE_CANDIDATE != "2.0.0":
        raise SystemExit(f"Unexpected stable milestone: {V2_MILESTONE_CANDIDATE}")

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    classifiers = {str(item) for item in project.get("classifiers", [])}
    if "Development Status :: 5 - Production/Stable" not in classifiers:
        raise SystemExit("Stable package classifier is missing")
    if "Programming Language :: Python :: 3.14" not in classifiers:
        raise SystemExit("Python 3.14 classifier is missing from the stable package")

    extras = project.get("optional-dependencies", {})
    expected_extras = {str(item) for item in stable["provider_extras"]}
    missing_extras = expected_extras.difference(extras)
    if missing_extras:
        raise SystemExit(f"Missing stable provider extras: {sorted(missing_extras)}")

    base_dependencies = {
        _distribution_name(str(requirement))
        for requirement in project.get("dependencies", [])
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
        raise SystemExit(f"Provider dependencies leaked into stable base: {sorted(leaked_base)}")

    for relative in stable["required_docs"]:
        if not (ROOT / str(relative)).is_file():
            raise SystemExit(f"Missing stable release documentation: {relative}")

    print(
        "OK: PyIngestKit 2.0.0 preserves the qualified RC root, runtime, "
        "Protocol and wire-contract freeze"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
