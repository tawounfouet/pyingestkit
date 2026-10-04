from __future__ import annotations

import importlib
import inspect
import json
import tomllib
from pathlib import Path

import pyingestkit
import pyingestkit.governance as governance
import pyingestkit.governance.rollback as rollback
from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_GOVERNANCE_PROVIDER_VALUES,
    V2_IMPLEMENTED_GOVERNANCE_VALUES,
    V2_MILESTONE_CANDIDATE,
    V2_PUBLIC_NAMESPACE_BASELINE,
)

ROOT = Path(__file__).resolve().parents[1]
LOT23_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "governance_v2_1_alpha1.json"
LOT28_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "governance_v2_1_beta2.json"
LOT29_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "governance_v2_1_rc1.json"
STABLE_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "stable_release_v2.json"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


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
        if not name.startswith("_") and callable(value)
    }


def main() -> int:
    lot23 = _load(LOT23_FIXTURE)
    lot28 = _load(LOT28_FIXTURE)
    lot29 = _load(LOT29_FIXTURE)
    stable = _load(STABLE_FIXTURE)

    if lot29["schema_version"] != 1 or lot29["milestone"] != "LOT-29":
        raise SystemExit("Unexpected LOT-29 governance RC fixture")
    if lot29["version"] != "2.1.0rc1" or pyingestkit.__version__ != "2.1.0rc1":
        raise SystemExit(f"Expected 2.1.0rc1, got {pyingestkit.__version__}")
    if V2_API_PHASE != "LOT-29_RC":
        raise SystemExit(f"Unexpected V2 API phase: {V2_API_PHASE}")
    if V2_COMPLETED_LOTS[-1] != "LOT-29":
        raise SystemExit(f"LOT-29 is not current: {V2_COMPLETED_LOTS[-1]}")
    if V2_COMPLETED_LOTS.count("LOT-29") != 1:
        raise SystemExit("LOT-29 completion marker must occur exactly once")
    if V2_MILESTONE_CANDIDATE != "2.1.0rc1":
        raise SystemExit(f"Unexpected milestone candidate: {V2_MILESTONE_CANDIDATE}")

    expected_root = tuple(str(item) for item in stable["root_exports"])
    if tuple(pyingestkit.__all__) != expected_root:
        raise SystemExit("LOT-29 widened the frozen 2.0 package root")

    expected_governance = tuple(str(item) for item in lot23["namespace_exports"])
    if tuple(governance.__all__) != expected_governance:
        raise SystemExit("LOT-29 drifted the frozen LOT-23 governance namespace")
    if tuple(V2_IMPLEMENTED_GOVERNANCE_VALUES) != expected_governance:
        raise SystemExit("LOT-29 drifted the frozen LOT-23 governance inventory")

    protocols = lot23["protocols"]
    signatures = lot23["protocol_signatures"]
    assert isinstance(protocols, dict)
    assert isinstance(signatures, dict)
    for qualified_name, expected_methods_raw in protocols.items():
        protocol = _resolve(str(qualified_name))
        if not isinstance(protocol, type):
            raise SystemExit(f"LOT-23 Protocol is not a class: {qualified_name}")
        expected_methods = {str(item) for item in expected_methods_raw}
        if _method_names(protocol) != expected_methods:
            raise SystemExit(f"LOT-23 Protocol method drift: {qualified_name}")
        raw_signatures = signatures[str(qualified_name)]
        assert isinstance(raw_signatures, dict)
        for method_name, expected_parameters_raw in raw_signatures.items():
            expected_parameters = [str(item) for item in expected_parameters_raw]
            actual_parameters = list(
                inspect.signature(getattr(protocol, str(method_name))).parameters
            )
            if actual_parameters != expected_parameters:
                raise SystemExit(
                    f"LOT-23 signature drift for {qualified_name}.{method_name}: "
                    f"{actual_parameters} != {expected_parameters}"
                )

    expected_providers = tuple(str(item) for item in lot29["provider_inventory"])
    if tuple(V2_IMPLEMENTED_GOVERNANCE_PROVIDER_VALUES) != expected_providers:
        raise SystemExit("LOT-29 changed the LOT-28 governance provider inventory")

    expected_rollback_exports = tuple(str(item) for item in lot28["rollback_exports"])
    if tuple(rollback.__all__) != expected_rollback_exports:
        raise SystemExit("LOT-29 changed the LOT-28 rollback namespace")
    if any(value in pyingestkit.__all__ for value in expected_rollback_exports):
        raise SystemExit("LOT-29 leaked rollback values into the frozen package root")

    namespaces = tuple(str(item) for item in lot29["qualified_namespaces"])
    if any(namespace not in V2_PUBLIC_NAMESPACE_BASELINE for namespace in namespaces):
        raise SystemExit("LOT-29 required qualified namespace missing from V2 baseline")

    for key in ("cross_provider_evidence", "required_evidence", "required_docs"):
        values = lot29[key]
        assert isinstance(values, list)
        for relative in values:
            if not (ROOT / str(relative)).is_file():
                raise SystemExit(f"Missing LOT-29 {key}: {relative}")

    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    jobs = lot29["required_release_blocking_jobs"]
    assert isinstance(jobs, list)
    for job in jobs:
        marker = f"  {job}:"
        if marker not in workflow:
            raise SystemExit(f"Missing release-blocking LOT-29 CI job: {job}")
    for job in jobs:
        dependency = f"      - {job}"
        if dependency not in workflow:
            raise SystemExit(f"LOT-29 job is not wired into stable-release-gate: {job}")

    if "2.1.0rc1" not in workflow or "check_v2_1_rc1.py" not in workflow:
        raise SystemExit("LOT-29 CI workflow does not qualify the exact RC candidate")

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    classifiers = {str(item) for item in project.get("classifiers", [])}
    if "Development Status :: 4 - Beta" not in classifiers:
        raise SystemExit("2.1.0rc1 must remain pre-stable in package metadata")
    if "Development Status :: 5 - Production/Stable" in classifiers:
        raise SystemExit("2.1.0rc1 must not claim Production/Stable status")

    print(
        "OK: PyIngestKit 2.1.0rc1 LOT-29 freezes the 2.1 governance contract, "
        "preserves 2.0 compatibility and wires the full RC conformance matrix"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
