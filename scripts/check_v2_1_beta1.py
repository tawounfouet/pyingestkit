from __future__ import annotations

import importlib
import inspect
import json
import tomllib
from pathlib import Path

import pyingestkit
import pyingestkit.adapters.s3 as s3
import pyingestkit.governance as governance
import pyingestkit.governance.retention as retention
from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_GOVERNANCE_PROVIDER_VALUES,
    V2_IMPLEMENTED_GOVERNANCE_VALUES,
    V2_IMPLEMENTED_S3_VALUES,
    V2_MILESTONE_CANDIDATE,
)
from pyingestkit.governance.retention import VersionHoldRepository
from pyingestkit.ports.governance import (
    ConditionalDatasetPublisher,
    DatasetVersionGarbageCollector,
    PublicationLedger,
)

ROOT = Path(__file__).resolve().parents[1]
LOT23_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "governance_v2_1_alpha1.json"
LOT24_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "governance_v2_1_alpha2.json"
LOT25_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "governance_v2_1_alpha3.json"
LOT26_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "governance_v2_1_alpha4.json"
LOT27_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "governance_v2_1_beta1.json"
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
    lot26 = _load(LOT26_FIXTURE)
    lot27 = _load(LOT27_FIXTURE)
    stable = _load(STABLE_FIXTURE)

    if lot27["schema_version"] != 1 or lot27["milestone"] != "LOT-27":
        raise SystemExit("Unexpected LOT-27 retention/GC fixture")
    if lot27["version"] != "2.1.0b1" or pyingestkit.__version__ != "2.1.0b1":
        raise SystemExit(f"Expected 2.1.0b1, got {pyingestkit.__version__}")
    if V2_API_PHASE != "LOT-27_BETA":
        raise SystemExit(f"Unexpected V2 API phase: {V2_API_PHASE}")
    if V2_COMPLETED_LOTS[-1] != "LOT-27":
        raise SystemExit(f"LOT-27 is not current: {V2_COMPLETED_LOTS[-1]}")
    if V2_MILESTONE_CANDIDATE != "2.1.0b1":
        raise SystemExit(f"Unexpected milestone candidate: {V2_MILESTONE_CANDIDATE}")

    expected_root = tuple(str(item) for item in stable["root_exports"])
    if tuple(pyingestkit.__all__) != expected_root:
        raise SystemExit("LOT-27 widened the frozen 2.0 package root")

    expected_exports = tuple(str(item) for item in lot23["namespace_exports"])
    if tuple(governance.__all__) != expected_exports:
        raise SystemExit("LOT-27 drifted the frozen LOT-23 governance namespace")
    if tuple(V2_IMPLEMENTED_GOVERNANCE_VALUES) != expected_exports:
        raise SystemExit("LOT-27 drifted the frozen LOT-23 governance inventory")

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
        if not issubclass(resolved, VersionHoldRepository):
            raise SystemExit(f"LOT-27 hold repository missing on ledger: {provider}")

    lot25_providers = lot25["providers"]
    assert isinstance(lot25_providers, dict)
    filesystem_conditional = _resolve(str(lot25_providers["filesystem_conditional"]))
    if not isinstance(filesystem_conditional, type) or not issubclass(
        filesystem_conditional,
        ConditionalDatasetPublisher,
    ):
        raise SystemExit("LOT-25 filesystem conditional provider regressed")

    lot26_providers = lot26["providers"]
    assert isinstance(lot26_providers, dict)
    s3_conditional = _resolve(str(lot26_providers["s3_conditional"]))
    if not isinstance(s3_conditional, type) or not issubclass(
        s3_conditional,
        ConditionalDatasetPublisher,
    ):
        raise SystemExit("LOT-26 S3 conditional provider regressed")

    providers = lot27["providers"]
    assert isinstance(providers, dict)
    for key in ("filesystem_gc", "s3_gc"):
        collector = _resolve(str(providers[key]))
        if not isinstance(collector, type) or not issubclass(
            collector,
            DatasetVersionGarbageCollector,
        ):
            raise SystemExit(f"LOT-27 GC provider does not implement frozen port: {key}")

    expected_provider_values = (
        "FileConditionalDatasetPublisher",
        "FileDatasetVersionGarbageCollector",
        "MemoryPublicationLedger",
        "PostgresPublicationLedger",
        "S3ConditionalDatasetPublisher",
        "S3DatasetVersionGarbageCollector",
    )
    if tuple(V2_IMPLEMENTED_GOVERNANCE_PROVIDER_VALUES) != expected_provider_values:
        raise SystemExit("LOT-27 governance provider inventory drift")

    expected_retention_exports = tuple(str(item) for item in lot27["retention_exports"])
    if tuple(retention.__all__) != expected_retention_exports:
        raise SystemExit("LOT-27 qualified retention namespace drift")
    for value in expected_retention_exports:
        if value in governance.__all__:
            raise SystemExit(f"LOT-27 widened frozen governance root with {value}")

    expected_s3_exports = tuple(str(item) for item in lot27["s3_namespace_exports"])
    if tuple(s3.__all__) != expected_s3_exports:
        raise SystemExit("LOT-27 S3 provider namespace drift")
    if tuple(V2_IMPLEMENTED_S3_VALUES) != expected_s3_exports:
        raise SystemExit("LOT-27 S3 implementation inventory drift")

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    classifiers = {str(item) for item in project.get("classifiers", [])}
    if "Development Status :: 4 - Beta" not in classifiers:
        raise SystemExit("2.1.0b1 package classifier must be Beta")
    if "Development Status :: 3 - Alpha" in classifiers:
        raise SystemExit("2.1.0b1 package must no longer claim Alpha status")
    if "Development Status :: 5 - Production/Stable" in classifiers:
        raise SystemExit("2.1.0b1 package must not claim Production/Stable status")

    for key in ("required_evidence", "required_docs"):
        for relative in lot27[key]:
            if not (ROOT / str(relative)).is_file():
                raise SystemExit(f"Missing LOT-27 {key}: {relative}")

    print(
        "OK: PyIngestKit 2.1.0b1 LOT-27 preserves frozen 2.0/LOT-23 "
        "contracts and qualifies retention, holds and guarded File/S3 GC"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
