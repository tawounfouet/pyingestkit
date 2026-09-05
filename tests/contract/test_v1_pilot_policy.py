from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "tests" / "contract" / "fixtures" / "pilots_v1.json"
EXPECTED_JOBS = {
    "demo.local_file",
    "demo.http_csv",
    "demo.http_json",
    "demo.ndjson_quality",
    "demo.excel_quality",
    "demo.parquet_quality",
    "demo.versioned_ndjson",
    "demo.versioned_postgres",
    "demo.versioned_s3",
}


def _contract() -> dict[str, object]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_b2_contract_is_versioned_and_anchored_to_b1() -> None:
    contract = _contract()
    assert contract["schema_version"] == 1
    assert contract["milestone"] == "V1.0.0-b2"
    assert contract["baseline"]["b1_merge_sha"] == (
        "9dc4dcfc8363937f4d7653292cce411f559fbf69"
    )


def test_b2_does_not_expand_product_scope() -> None:
    scope = _contract()["scope"]
    assert scope["introduces_new_ingestion_provider"] is False
    assert scope["introduces_orchestration_platform"] is False


def test_representative_pilots_cover_all_reference_jobs() -> None:
    pilots = _contract()["pilots"]
    assert len(pilots) == 5
    covered = {job_id for pilot in pilots for job_id in pilot["job_ids"]}
    assert covered == EXPECTED_JOBS
    assert {pilot["execution_class"] for pilot in pilots} == {
        "offline",
        "service-backed-ci",
    }


def test_service_backed_pilots_name_explicit_ci_evidence() -> None:
    pilots = _contract()["pilots"]
    service_pilots = [pilot for pilot in pilots if pilot["execution_class"] == "service-backed-ci"]
    assert {pilot["ci_job"] for pilot in service_pilots} == {
        "postgres-e2e",
        "object-storage-e2e",
    }


def test_b2_machine_gate_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_v1_pilots.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "V1.0.0-b2" in result.stdout
