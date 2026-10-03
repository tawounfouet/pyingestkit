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
from pyingestkit.ports.governance import PublicationLedger

ROOT = Path(__file__).resolve().parents[1]
LOT23_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "governance_v2_1_alpha1.json"
LOT24_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "governance_v2_1_alpha2.json"
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
    stable = _load(STABLE_FIXTURE)

    if lot24["schema_version"] != 1 or lot24["milestone"] != "LOT-24":
        raise SystemExit("Unexpected LOT-24 lifecycle-ledger fixture")
    if lot24["version"] != "2.1.0a2" or pyingestkit.__version__ != "2.1.0a2":
        raise SystemExit(f"Expected 2.1.0a2, got {pyingestkit.__version__}")
    if V2_API_PHASE != "LOT-24_ALPHA":
        raise SystemExit(f"Unexpected V2 API phase: {V2_API_PHASE}")
    if V2_COMPLETED_LOTS[-1] != "LOT-24":
        raise SystemExit(f"LOT-24 is not current: {V2_COMPLETED_LOTS[-1]}")
    if V2_MILESTONE_CANDIDATE != "2.1.0a2":
        raise SystemExit(f"Unexpected milestone candidate: {V2_MILESTONE_CANDIDATE}")

    expected_root = tuple(str(item) for item in stable["root_exports"])
    if tuple(pyingestkit.__all__) != expected_root:
        raise SystemExit("LOT-24 widened the frozen 2.0 package root")

    expected_exports = tuple(str(item) for item in lot23["namespace_exports"])
    if tuple(governance.__all__) != expected_exports:
        raise SystemExit("LOT-24 drifted the frozen LOT-23 governance namespace")
    if tuple(V2_IMPLEMENTED_GOVERNANCE_VALUES) != expected_exports:
        raise SystemExit("LOT-24 drifted the frozen LOT-23 governance inventory")

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

    adapters = lot24["adapters"]
    assert isinstance(adapters, dict)
    resolved_adapters: dict[str, type[object]] = {}
    for provider, qualified_name_raw in adapters.items():
        resolved = _resolve(str(qualified_name_raw))
        if not isinstance(resolved, type):
            raise SystemExit(f"LOT-24 adapter is not a class: {provider}")
        resolved_adapters[str(provider)] = resolved
        if not issubclass(resolved, PublicationLedger):
            raise SystemExit(f"LOT-24 adapter does not implement PublicationLedger: {provider}")

    expected_provider_values = tuple(
        sorted(adapter.__name__ for adapter in resolved_adapters.values())
    )
    if tuple(sorted(V2_IMPLEMENTED_GOVERNANCE_PROVIDER_VALUES)) != expected_provider_values:
        raise SystemExit("LOT-24 provider inventory differs from milestone fixture")

    postgres_module = importlib.import_module(
        "pyingestkit.adapters.postgres.publication_ledger"
    )
    metadata = getattr(postgres_module, "_METADATA")
    expected_tables = {str(item) for item in lot24["postgres_tables"]}
    if set(metadata.tables) != expected_tables:
        raise SystemExit(
            f"LOT-24 PostgreSQL table drift: {sorted(metadata.tables)} != "
            f"{sorted(expected_tables)}"
        )

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    classifiers = {str(item) for item in project.get("classifiers", [])}
    if "Development Status :: 3 - Alpha" not in classifiers:
        raise SystemExit("2.1.0a2 package classifier must remain Alpha")
    if "Development Status :: 5 - Production/Stable" in classifiers:
        raise SystemExit("2.1.0a2 package must not claim Production/Stable status")

    for key in ("required_evidence", "required_docs"):
        for relative in lot24[key]:
            if not (ROOT / str(relative)).is_file():
                raise SystemExit(f"Missing LOT-24 {key}: {relative}")

    print(
        "OK: PyIngestKit 2.1.0a2 LOT-24 preserves LOT-23 contracts and "
        "qualifies Memory/PostgreSQL lifecycle ledger adapters"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
