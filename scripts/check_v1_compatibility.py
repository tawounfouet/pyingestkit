from __future__ import annotations

import importlib
import json
import sys
import tempfile
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pyingestkit.dataset import Dataset
from pyingestkit.diff import DatasetDiff, DiffPolicy, SchemaDiff
from pyingestkit.provenance.manifest import RunManifest
from pyingestkit.replay import ReplayContext
from pyingestkit.validation import ValidationIssue, ValidationReport, ValidationSeverity
from pyingestkit.versioning import (
    DatasetFingerprint,
    FilesystemDatasetVersionStore,
    SnapshotCodec,
)

CONTRACT_PATH = ROOT / "tests" / "contract" / "fixtures" / "compatibility_v1.json"


def _contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _resolve(qualified_name: str) -> Any:
    module_name, attribute = qualified_name.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, attribute)


def _assert_keys(label: str, payload: dict[str, Any], expected: list[str]) -> None:
    actual = list(payload)
    if actual != expected:
        raise SystemExit(f"{label} keys changed. expected={expected} actual={actual}")


def _check_enums(contract: dict[str, Any]) -> None:
    for qualified_name, expected in contract["enums"].items():
        enum_type = _resolve(qualified_name)
        actual = {name: member.value for name, member in enum_type.__members__.items()}
        if actual != expected:
            raise SystemExit(
                f"Enum contract changed for {qualified_name}. expected={expected} actual={actual}"
            )


def _check_dataclasses(contract: dict[str, Any]) -> None:
    for qualified_name, expected in contract["dataclasses"].items():
        value = _resolve(qualified_name)
        if not is_dataclass(value):
            raise SystemExit(f"Compatibility contract expected a dataclass: {qualified_name}")
        actual = [field.name for field in fields(value)]
        if actual != expected:
            raise SystemExit(
                f"Dataclass contract changed for {qualified_name}. expected={expected} actual={actual}"
            )


def _check_abstract_contracts(contract: dict[str, Any]) -> None:
    for qualified_name, expected in contract["abstract_contracts"].items():
        value = _resolve(qualified_name)
        actual = sorted(value.__abstractmethods__)
        if actual != sorted(expected):
            raise SystemExit(
                f"Abstract contract changed for {qualified_name}. expected={sorted(expected)} "
                f"actual={actual}"
            )


def _check_persistent_formats(contract: dict[str, Any]) -> None:
    formats = contract["persistent_formats"]
    now = datetime(2026, 1, 1, tzinfo=UTC)

    manifest = RunManifest(run_id="run-1", job_id="demo.job", job_version="1.0.0", started_at=now)
    manifest_payload = manifest.as_dict()
    _assert_keys("run_manifest", manifest_payload, formats["run_manifest"]["keys"])
    if manifest_payload["schema_version"] != formats["run_manifest"]["schema_version"]:
        raise SystemExit("RunManifest schema_version changed without updating the V1 contract")

    dataset = Dataset([{"id": 1, "name": "alpha"}], fields=("id", "name"))
    snapshot = SnapshotCodec().encode(dataset)
    _assert_keys("dataset_snapshot", snapshot, formats["dataset_snapshot"]["keys"])
    if snapshot[formats["dataset_snapshot"]["schema_field"]] != formats["dataset_snapshot"][
        "schema_version"
    ]:
        raise SystemExit("Dataset snapshot schema version changed without a compatibility decision")

    fingerprint = DatasetFingerprint(
        algorithm="sha256",
        value="0" * 64,
        order_sensitive=False,
        row_count=1,
        field_count=2,
    )
    _assert_keys(
        "dataset_fingerprint",
        fingerprint.as_dict(),
        formats["dataset_fingerprint"]["keys"],
    )

    diff = DatasetDiff(
        previous_fingerprint=fingerprint,
        candidate_fingerprint=fingerprint,
        policy=DiffPolicy(),
        schema=SchemaDiff(
            added_fields=(),
            removed_fields=(),
            common_fields=("id", "name"),
            field_order_changed=False,
        ),
        added_count=0,
        removed_count=0,
        changed_count=0,
        unchanged_count=1,
        entries=(),
    )
    _assert_keys("dataset_diff", diff.as_dict(), formats["dataset_diff"]["keys"])

    replay = ReplayContext(
        source_run_id="source-run",
        source_job_id="demo.job",
        source_job_version="1.0.0",
        raw_artifacts=(),
        verification_mode="strict",
    )
    _assert_keys(
        "replay_manifest",
        replay.as_manifest_dict(executed_job_version="1.0.0"),
        formats["replay_manifest"]["keys"],
    )

    issue = ValidationIssue(
        rule="required",
        message="missing",
        severity=ValidationSeverity.ERROR,
    )
    _assert_keys("validation_issue", issue.as_dict(), formats["validation_issue"]["keys"])
    report = ValidationReport([issue])
    _assert_keys("validation_report", report.as_dict(), formats["validation_report"]["keys"])

    with tempfile.TemporaryDirectory(prefix="pyingestkit-v1-compat-") as directory:
        root = Path(directory)
        store = FilesystemDatasetVersionStore(root)
        version = store.create_version(
            dataset,
            dataset_id="demo.data",
            created_from_run_id="run-1",
            job_id="demo.job",
            job_version="1.0.0",
        )
        version_path = root / "versions" / "demo" / "data" / version.version_id / "version.json"
        version_payload = json.loads(version_path.read_text(encoding="utf-8"))
        _assert_keys(
            "dataset_version_metadata",
            version_payload,
            formats["dataset_version_metadata"]["keys"],
        )
        schema_field = formats["dataset_version_metadata"]["schema_field"]
        if version_payload[schema_field] != formats["dataset_version_metadata"]["schema_version"]:
            raise SystemExit("DatasetVersion metadata schema changed without a compatibility decision")

        store.publish(version, run_id="run-1")
        pointer_path = root / "published" / "demo" / "data" / "current.json"
        pointer_payload = json.loads(pointer_path.read_text(encoding="utf-8"))
        _assert_keys(
            "published_dataset_pointer",
            pointer_payload,
            formats["published_dataset_pointer"]["keys"],
        )
        schema_field = formats["published_dataset_pointer"]["schema_field"]
        if pointer_payload[schema_field] != formats["published_dataset_pointer"]["schema_version"]:
            raise SystemExit("Published pointer schema changed without a compatibility decision")


def main() -> None:
    contract = _contract()
    if contract["schema_version"] != 1:
        raise SystemExit(f"Unsupported compatibility contract schema: {contract['schema_version']!r}")
    _check_enums(contract)
    _check_dataclasses(contract)
    _check_abstract_contracts(contract)
    _check_persistent_formats(contract)
    print("OK: V1 compatibility contract is intact (V1.0.0-a2)")


if __name__ == "__main__":
    main()
