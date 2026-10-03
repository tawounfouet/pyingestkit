from __future__ import annotations

import importlib
import inspect
import json
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
FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "release_candidate_v2.json"


def _fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _resolve(qualified_name: str) -> object:
    module_name, _, attribute = qualified_name.rpartition(".")
    if not module_name or not attribute:
        raise SystemExit(f"Invalid qualified contract name: {qualified_name}")
    module = importlib.import_module(module_name)
    return getattr(module, attribute)


def _method_names(protocol: type[object]) -> set[str]:
    return {
        name
        for name, value in vars(protocol).items()
        if not name.startswith("_") and (callable(value) or isinstance(value, property))
    }


def main() -> int:
    contract = _fixture()
    if contract["schema_version"] != 1:
        raise SystemExit("Unsupported V2 RC contract schema")

    expected_version = str(contract["version"])
    if pyingestkit.__version__ != expected_version:
        raise SystemExit(f"Expected PyIngestKit {expected_version}, got {pyingestkit.__version__}")

    root_exports = tuple(str(item) for item in contract["root_exports"])
    if tuple(pyingestkit.__all__) != root_exports:
        raise SystemExit(
            f"V2 RC root drift: expected {root_exports}, got {tuple(pyingestkit.__all__)}"
        )
    if V2_TARGET_ROOT_EXPORTS != root_exports:
        raise SystemExit("Machine-readable V2 target root disagrees with installed root")

    forbidden = {str(item) for item in contract["forbidden_root_exports"]}
    leaked = forbidden.intersection(pyingestkit.__all__)
    if leaked:
        raise SystemExit(f"Legacy root exports leaked into V2 RC: {sorted(leaked)}")

    if V2_API_PHASE != "LOT-21_RELEASE_CANDIDATE":
        raise SystemExit(f"Unexpected V2 API phase: {V2_API_PHASE}")
    if V2_COMPLETED_LOTS[-1] != "LOT-21":
        raise SystemExit(f"LOT-21 is not the current completed lot: {V2_COMPLETED_LOTS[-1]}")
    if V2_MILESTONE_CANDIDATE != expected_version:
        raise SystemExit(
            f"Milestone candidate {V2_MILESTONE_CANDIDATE} != package {expected_version}"
        )

    runtime_contract = contract["runtime"]
    assert isinstance(runtime_contract, dict)
    method_name = str(runtime_contract["canonical_method"])
    runtime_method = getattr(pyingestkit.IngestionRuntime, method_name)
    actual_parameters = list(inspect.signature(runtime_method).parameters)
    expected_parameters = [str(item) for item in runtime_contract["parameters"]]
    if actual_parameters != expected_parameters:
        raise SystemExit(
            f"IngestionRuntime.{method_name} signature drift: "
            f"{actual_parameters} != {expected_parameters}"
        )

    protocols = contract["stable_protocols"]
    assert isinstance(protocols, dict)
    for qualified_name, expected_methods_raw in protocols.items():
        protocol = _resolve(str(qualified_name))
        if not isinstance(protocol, type):
            raise SystemExit(f"Stable protocol is not a class: {qualified_name}")
        expected_methods = {str(item) for item in expected_methods_raw}
        actual_methods = _method_names(protocol)
        if actual_methods != expected_methods:
            raise SystemExit(
                f"Protocol drift for {qualified_name}: "
                f"{sorted(actual_methods)} != {sorted(expected_methods)}"
            )

    for relative in contract["required_docs"]:
        path = ROOT / str(relative)
        if not path.is_file():
            raise SystemExit(f"Missing V2 RC documentation: {relative}")

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    dynamic = project.get("dynamic", [])
    if "version" not in dynamic:
        raise SystemExit("Package version must remain sourced from pyingestkit._version")

    print(
        "OK: PyIngestKit 2.0.0rc1 root, runtime and stable provider Protocols "
        "match the LOT-21 release-candidate freeze"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
