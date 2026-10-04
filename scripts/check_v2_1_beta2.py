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
from pyingestkit.domain.governance import PublicationLifecycleEventType

ROOT = Path(__file__).resolve().parents[1]
LOT23_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "governance_v2_1_alpha1.json"
LOT27_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "governance_v2_1_beta1.json"
LOT28_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "governance_v2_1_beta2.json"
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
    lot27 = _load(LOT27_FIXTURE)
    lot28 = _load(LOT28_FIXTURE)
    stable = _load(STABLE_FIXTURE)

    if lot28["schema_version"] != 1 or lot28["milestone"] != "LOT-28":
        raise SystemExit("Unexpected LOT-28 governed rollback fixture")
    if lot28["version"] != "2.1.0b2" or pyingestkit.__version__ != "2.1.0b2":
        raise SystemExit(f"Expected 2.1.0b2, got {pyingestkit.__version__}")
    if V2_API_PHASE != "LOT-28_BETA":
        raise SystemExit(f"Unexpected V2 API phase: {V2_API_PHASE}")
    if V2_COMPLETED_LOTS[-1] != "LOT-28":
        raise SystemExit(f"LOT-28 is not current: {V2_COMPLETED_LOTS[-1]}")
    if V2_MILESTONE_CANDIDATE != "2.1.0b2":
        raise SystemExit(f"Unexpected milestone candidate: {V2_MILESTONE_CANDIDATE}")

    expected_root = tuple(str(item) for item in stable["root_exports"])
    if tuple(pyingestkit.__all__) != expected_root:
        raise SystemExit("LOT-28 widened the frozen 2.0 package root")

    expected_governance = tuple(str(item) for item in lot23["namespace_exports"])
    if tuple(governance.__all__) != expected_governance:
        raise SystemExit("LOT-28 drifted the frozen LOT-23 governance namespace")
    if tuple(V2_IMPLEMENTED_GOVERNANCE_VALUES) != expected_governance:
        raise SystemExit("LOT-28 drifted the frozen LOT-23 governance inventory")

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

    previous_providers = lot27["providers"]
    assert isinstance(previous_providers, dict)
    expected_provider_values = (
        "FileConditionalDatasetPublisher",
        "FileDatasetVersionGarbageCollector",
        "MemoryPublicationLedger",
        "PostgresPublicationLedger",
        "S3ConditionalDatasetPublisher",
        "S3DatasetVersionGarbageCollector",
    )
    if tuple(V2_IMPLEMENTED_GOVERNANCE_PROVIDER_VALUES) != expected_provider_values:
        raise SystemExit("LOT-28 drifted the LOT-27 governance provider inventory")
    for qualified_name_raw in previous_providers.values():
        _resolve(str(qualified_name_raw))

    expected_rollback_exports = tuple(str(item) for item in lot28["rollback_exports"])
    if tuple(rollback.__all__) != expected_rollback_exports:
        raise SystemExit("LOT-28 qualified rollback namespace drift")
    if "pyingestkit.governance.rollback" not in V2_PUBLIC_NAMESPACE_BASELINE:
        raise SystemExit("LOT-28 rollback namespace missing from V2 public namespace baseline")
    for value in expected_rollback_exports:
        if value in governance.__all__ or value in pyingestkit.__all__:
            raise SystemExit(f"LOT-28 leaked qualified rollback value to frozen root: {value}")

    required_events = {str(item) for item in lot28["required_events"]}
    actual_events = {event.value for event in PublicationLifecycleEventType}
    if not required_events.issubset(actual_events):
        raise SystemExit("LOT-28 required rollback lifecycle events are missing")

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    classifiers = {str(item) for item in project.get("classifiers", [])}
    if "Development Status :: 4 - Beta" not in classifiers:
        raise SystemExit("2.1.0b2 package classifier must remain Beta")
    if "Development Status :: 5 - Production/Stable" in classifiers:
        raise SystemExit("2.1.0b2 package must not claim Production/Stable status")

    for key in ("required_evidence", "required_docs"):
        values = lot28[key]
        assert isinstance(values, list)
        for relative in values:
            if not (ROOT / str(relative)).is_file():
                raise SystemExit(f"Missing LOT-28 {key}: {relative}")

    print(
        "OK: PyIngestKit 2.1.0b2 LOT-28 preserves frozen 2.0/LOT-23 "
        "contracts and qualifies governed rollback without replay coupling"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
