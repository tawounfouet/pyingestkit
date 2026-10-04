from __future__ import annotations

import importlib
import inspect
import json
import re
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
    V2_PUBLIC_NAMESPACE_BASELINE,
)
from pyingestkit.adapters.postgres.publication_ledger import (
    _PUBLICATION_EVENT,
    _PUBLICATION_OPERATION,
    _VERSION_HOLD,
)
from pyingestkit.domain.governance import (
    ConditionalPublicationStatus,
    DatasetVersionDeletionReconciliationStatus,
    DatasetVersionDeletionStatus,
    PublicationLifecycleEventType,
    PublicationOperationId,
    PublicationRevision,
    RetentionPolicy,
)
from pyingestkit.governance._ledger_codec import _SCHEMA_VERSION
from pyingestkit.governance.rollback import GovernedRollbackService

ROOT = Path(__file__).resolve().parents[1]
STABLE_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "governance_v2_1_stable.json"
RC_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "governance_v2_1_rc1.json"
LOT23_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "governance_v2_1_alpha1.json"
STABLE_20_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "stable_release_v2.json"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(qualified_name: str) -> object:
    module_name, _, attribute = qualified_name.rpartition(".")
    if not module_name or not attribute:
        raise SystemExit(f"Invalid qualified contract name: {qualified_name}")
    return getattr(importlib.import_module(module_name), attribute)


def main() -> int:
    stable = _load(STABLE_FIXTURE)
    rc = _load(RC_FIXTURE)
    lot23 = _load(LOT23_FIXTURE)
    stable20 = _load(STABLE_20_FIXTURE)

    if stable["schema_version"] != 1 or stable["milestone"] != "LOT-30":
        raise SystemExit("Unexpected LOT-30 stable governance fixture")
    if stable["version"] != "2.1.0" or pyingestkit.__version__ != "2.1.0":
        raise SystemExit(f"Expected stable 2.1.0, got {pyingestkit.__version__}")
    if V2_API_PHASE != "LOT-30_STABLE":
        raise SystemExit(f"Unexpected V2 stable phase: {V2_API_PHASE}")
    if V2_COMPLETED_LOTS[-1] != "LOT-30" or V2_COMPLETED_LOTS.count("LOT-30") != 1:
        raise SystemExit("LOT-30 must be the unique current milestone")
    if V2_MILESTONE_CANDIDATE != "2.1.0":
        raise SystemExit(f"Unexpected stable milestone: {V2_MILESTONE_CANDIDATE}")

    stable_root = tuple(str(item) for item in stable["root_exports"])
    stable20_root = tuple(str(item) for item in stable20["root_exports"])
    if stable_root != stable20_root or tuple(pyingestkit.__all__) != stable20_root:
        raise SystemExit("LOT-30 changed the frozen PyIngestKit 2.0 package root")

    stable_governance = tuple(str(item) for item in stable["governance_namespace_exports"])
    lot23_governance = tuple(str(item) for item in lot23["namespace_exports"])
    if stable_governance != lot23_governance:
        raise SystemExit("LOT-30 stable governance exports differ from LOT-23 freeze")
    if tuple(governance.__all__) != stable_governance:
        raise SystemExit("Installed governance namespace differs from stable freeze")
    if tuple(V2_IMPLEMENTED_GOVERNANCE_VALUES) != stable_governance:
        raise SystemExit("Machine-readable governance inventory differs from stable freeze")

    stable_protocols = stable["protocols"]
    lot23_signatures = lot23["protocol_signatures"]
    assert isinstance(stable_protocols, dict)
    assert isinstance(lot23_signatures, dict)
    if stable_protocols != lot23_signatures:
        raise SystemExit("LOT-30 Protocol signatures differ from the qualified LOT-23 contract")
    for qualified_name, methods_raw in stable_protocols.items():
        protocol = _resolve(str(qualified_name))
        if not isinstance(protocol, type):
            raise SystemExit(f"Stable governance Protocol is not a class: {qualified_name}")
        assert isinstance(methods_raw, dict)
        actual_methods = {
            name
            for name, value in vars(protocol).items()
            if not name.startswith("_") and callable(value)
        }
        expected_methods = {str(name) for name in methods_raw}
        if actual_methods != expected_methods:
            raise SystemExit(f"Governance Protocol method drift: {qualified_name}")
        for method_name, expected_parameters_raw in methods_raw.items():
            expected_parameters = [str(item) for item in expected_parameters_raw]
            actual_parameters = list(
                inspect.signature(getattr(protocol, str(method_name))).parameters
            )
            if actual_parameters != expected_parameters:
                raise SystemExit(
                    f"Governance signature drift for {qualified_name}.{method_name}: "
                    f"{actual_parameters} != {expected_parameters}"
                )

    retention = stable["retention_policy"]
    assert isinstance(retention, dict)
    retention_signature = inspect.signature(RetentionPolicy)
    expected_parameters = [str(item) for item in retention["parameters"]]
    if list(retention_signature.parameters) != expected_parameters:
        raise SystemExit("RetentionPolicy constructor schema drift")
    defaults = retention["defaults"]
    assert isinstance(defaults, dict)
    for name, expected in defaults.items():
        if retention_signature.parameters[str(name)].default != expected:
            raise SystemExit(f"RetentionPolicy default drift: {name}")

    lifecycle = stable["lifecycle_ledger"]
    assert isinstance(lifecycle, dict)
    if _SCHEMA_VERSION != lifecycle["schema_version"]:
        raise SystemExit("Lifecycle ledger schema version drift")
    table_names = {
        "intent_table": _PUBLICATION_OPERATION.name,
        "event_table": _PUBLICATION_EVENT.name,
        "hold_table": _VERSION_HOLD.name,
    }
    for name, actual in table_names.items():
        if actual != lifecycle[name]:
            raise SystemExit(f"Lifecycle persistence table drift: {name}")

    expected_events = [str(item) for item in stable["lifecycle_event_types"]]
    actual_events = [item.value for item in PublicationLifecycleEventType]
    if actual_events != expected_events:
        raise SystemExit("PublicationLifecycleEventType stable values drifted")

    operation = stable["operation_id_serialization"]
    assert isinstance(operation, dict)
    operation_pattern = re.compile(str(operation["stable_pattern"]))
    sample_operation = PublicationOperationId.parse(
        "00000000-0000-0000-0000-000000000000"
    )
    if operation_pattern.fullmatch(str(sample_operation)) is None:
        raise SystemExit("PublicationOperationId stable serialization pattern drift")

    revision = stable["revision_serialization"]
    assert isinstance(revision, dict)
    if str(PublicationRevision.initial()) != revision["initial"]:
        raise SystemExit("PublicationRevision initial token drift")
    pattern = re.compile(str(revision["stable_pattern"]))
    sample_revision = PublicationRevision("rev-" + ("0" * 32))
    if pattern.fullmatch(str(sample_revision)) is None:
        raise SystemExit("PublicationRevision stable serialization pattern drift")
    try:
        PublicationRevision("etag-provider-token")
    except ValueError:
        pass
    else:
        raise SystemExit("Provider token leaked into portable PublicationRevision")

    expected_providers = tuple(str(item) for item in stable["provider_inventory"])
    rc_providers = tuple(str(item) for item in rc["provider_inventory"])
    if expected_providers != rc_providers:
        raise SystemExit("Stable provider inventory differs from the qualified RC")
    if tuple(V2_IMPLEMENTED_GOVERNANCE_PROVIDER_VALUES) != expected_providers:
        raise SystemExit("Installed governance provider inventory differs from stable freeze")

    results = stable["result_contracts"]
    assert isinstance(results, dict)
    if [item.value for item in ConditionalPublicationStatus] != results[
        "conditional_publication_status"
    ]:
        raise SystemExit("ConditionalPublicationStatus values drifted")
    if [item.value for item in DatasetVersionDeletionStatus] != results[
        "dataset_version_deletion_status"
    ]:
        raise SystemExit("DatasetVersionDeletionStatus values drifted")
    if [item.value for item in DatasetVersionDeletionReconciliationStatus] != results[
        "dataset_version_deletion_reconciliation_status"
    ]:
        raise SystemExit("DatasetVersionDeletionReconciliationStatus values drifted")
    rollback_return = inspect.signature(GovernedRollbackService.rollback).return_annotation
    if str(rollback_return) != str(results["rollback_result"]):
        raise SystemExit("Governed rollback result contract drifted")

    namespaces = tuple(str(item) for item in stable["qualified_namespaces"])
    if any(namespace not in V2_PUBLIC_NAMESPACE_BASELINE for namespace in namespaces):
        raise SystemExit("Stable governance namespace missing from V2 baseline")

    for relative in stable["required_docs"]:
        if not (ROOT / str(relative)).is_file():
            raise SystemExit(f"Missing 2.1 stable release documentation: {relative}")

    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    jobs = stable["required_release_blocking_jobs"]
    assert isinstance(jobs, list)
    for job in jobs:
        if f"  {job}:" not in workflow:
            raise SystemExit(f"Missing stable governance CI job: {job}")
        if f"      - {job}" not in workflow:
            raise SystemExit(f"Stable governance job not wired into terminal gate: {job}")
    if "check_v2_1_stable.py" not in workflow or "2.1.0" not in workflow:
        raise SystemExit("CI does not qualify the exact PyIngestKit 2.1.0 stable candidate")
    if "2.1.0rc1" in workflow:
        raise SystemExit("Stable CI still contains release-candidate artifact/version assertions")

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    classifiers = {str(item) for item in project.get("classifiers", [])}
    if "Development Status :: 5 - Production/Stable" not in classifiers:
        raise SystemExit("2.1.0 stable package classifier is missing")
    if "Development Status :: 4 - Beta" in classifiers:
        raise SystemExit("2.1.0 stable package must not retain Beta status")
    if "Programming Language :: Python :: 3.14" not in classifiers:
        raise SystemExit("Python 3.14 classifier is missing from stable package")

    print(
        "OK: PyIngestKit 2.1.0 LOT-30 promotes the unchanged qualified governance "
        "contract to stable while preserving the frozen 2.0 compatibility baseline"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
