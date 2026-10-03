from __future__ import annotations

import importlib
import inspect
import json
import tomllib
from pathlib import Path

import pyingestkit
import pyingestkit.governance as governance
from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_GOVERNANCE_PROVIDER_VALUES,
    V2_IMPLEMENTED_GOVERNANCE_VALUES,
    V2_MILESTONE_CANDIDATE,
)
from pyingestkit.ports.governance import (
    ConditionalDatasetPublisher,
    PublicationLedger,
)

ROOT = Path(__file__).resolve().parents[1]
LOT23_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "governance_v2_1_alpha1.json"
LOT24_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "governance_v2_1_alpha2.json"
LOT25_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "governance_v2_1_alpha3.json"
STABLE_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "stable_release_v2.json"


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
    lot24 = _load(LOT24_FIXTURE)
    lot25 = _load(LOT25_FIXTURE)
    stable = _load(STABLE_FIXTURE)

    if lot25["schema_version"] != 1 or lot25["milestone"] != "LOT-25":
        raise SystemExit("Unexpected LOT-25 filesystem-CAS fixture")
    if lot25["version"] != "2.1.0a3" or pyingestkit.__version__ != "2.1.0a3":
        raise SystemExit(f"Expected 2.1.0a3, got {pyingestkit.__version__}")
    if V2_API_PHASE != "LOT-25_ALPHA":
        raise SystemExit(f"Unexpected V2 API phase: {V2_API_PHASE}")
    if V2_COMPLETED_LOTS[-1] != "LOT-25":
        raise SystemExit(f"LOT-25 is not current: {V2_COMPLETED_LOTS[-1]}")
    if V2_MILESTONE_CANDIDATE != "2.1.0a3":
        raise SystemExit(f"Unexpected milestone candidate: {V2_MILESTONE_CANDIDATE}")

    expected_root = tuple(str(item) for item in stable["root_exports"])
    if tuple(pyingestkit.__all__) != expected_root:
        raise SystemExit("LOT-25 widened the frozen 2.0 package root")

    expected_exports = tuple(str(item) for item in lot23["namespace_exports"])
    if tuple(governance.__all__) != expected_exports:
        raise SystemExit("LOT-25 drifted the frozen LOT-23 governance namespace")
    if tuple(V2_IMPLEMENTED_GOVERNANCE_VALUES) != expected_exports:
        raise SystemExit("LOT-25 drifted the frozen LOT-23 governance inventory")

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

    lot24_adapters = lot24["adapters"]
    assert isinstance(lot24_adapters, dict)
    for provider, qualified_name_raw in lot24_adapters.items():
        resolved = _resolve(str(qualified_name_raw))
        if not isinstance(resolved, type) or not issubclass(resolved, PublicationLedger):
            raise SystemExit(f"LOT-24 ledger contract regressed: {provider}")

    providers = lot25["providers"]
    assert isinstance(providers, dict)
    filesystem = _resolve(str(providers["filesystem_conditional"]))
    if not isinstance(filesystem, type):
        raise SystemExit("LOT-25 filesystem conditional provider is not a class")
    if not issubclass(filesystem, ConditionalDatasetPublisher):
        raise SystemExit("LOT-25 filesystem provider does not implement conditional port")

    expected_provider_values = (
        "FileConditionalDatasetPublisher",
        "MemoryPublicationLedger",
        "PostgresPublicationLedger",
    )
    if tuple(V2_IMPLEMENTED_GOVERNANCE_PROVIDER_VALUES) != expected_provider_values:
        raise SystemExit("LOT-25 governance provider inventory drift")

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    classifiers = {str(item) for item in project.get("classifiers", [])}
    if "Development Status :: 3 - Alpha" not in classifiers:
        raise SystemExit("2.1.0a3 package classifier must remain Alpha")
    if "Development Status :: 5 - Production/Stable" in classifiers:
        raise SystemExit("2.1.0a3 package must not claim Production/Stable status")

    for key in ("required_evidence", "required_docs"):
        for relative in lot25[key]:
            if not (ROOT / str(relative)).is_file():
                raise SystemExit(f"Missing LOT-25 {key}: {relative}")

    print(
        "OK: PyIngestKit 2.1.0a3 LOT-25 preserves frozen 2.0/LOT-23 "
        "contracts and qualifies filesystem conditional publication"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
