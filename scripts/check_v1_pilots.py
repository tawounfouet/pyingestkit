from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "tests" / "contract" / "fixtures" / "pilots_v1.json"
B1_MERGE_SHA = "9dc4dcfc8363937f4d7653292cce411f559fbf69"
EXPECTED_JOB_IDS = {
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


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_path(relative: str, *, kind: str) -> None:
    path = ROOT / relative
    if not path.exists():
        raise SystemExit(f"B2 pilot contract references missing {kind}: {relative}")


def main() -> None:
    contract = _load_json(CONTRACT_PATH)
    if contract.get("schema_version") != 1:
        raise SystemExit("B2 pilot contract schema_version must be 1")
    if contract.get("milestone") != "V1.0.0-b2":
        raise SystemExit("B2 pilot contract milestone must be V1.0.0-b2")

    baseline = contract.get("baseline", {})
    if baseline.get("b1_merge_sha") != B1_MERGE_SHA:
        raise SystemExit("B2 pilot contract must remain anchored to the sealed B1 merge SHA")

    scope = contract.get("scope", {})
    if scope.get("introduces_new_ingestion_provider") is not False:
        raise SystemExit("B2 must not introduce a new ingestion provider")
    if scope.get("introduces_orchestration_platform") is not False:
        raise SystemExit("B2 must not introduce an orchestration platform")

    pilots = contract.get("pilots")
    if not isinstance(pilots, list) or not pilots:
        raise SystemExit("B2 pilot contract must define at least one pilot")

    pilot_ids: set[str] = set()
    covered_jobs: set[str] = set()
    covered_entry_points: set[str] = set()
    service_ci_jobs: set[str] = set()
    for pilot in pilots:
        if not isinstance(pilot, dict):
            raise SystemExit("Each B2 pilot must be an object")
        pilot_id = pilot.get("id")
        if not isinstance(pilot_id, str) or not pilot_id:
            raise SystemExit("Each B2 pilot must have a non-empty id")
        if pilot_id in pilot_ids:
            raise SystemExit(f"Duplicate B2 pilot id: {pilot_id}")
        pilot_ids.add(pilot_id)

        execution_class = pilot.get("execution_class")
        if execution_class not in {"offline", "service-backed-ci"}:
            raise SystemExit(f"Unsupported execution_class for {pilot_id}: {execution_class}")
        if execution_class == "service-backed-ci":
            ci_job = pilot.get("ci_job")
            if not isinstance(ci_job, str) or not ci_job:
                raise SystemExit(f"Service-backed pilot {pilot_id} must name its CI job")
            service_ci_jobs.add(ci_job)

        jobs = pilot.get("job_ids")
        entry_points = pilot.get("entry_points")
        evidence = pilot.get("evidence")
        configs = pilot.get("configs")
        if not all(isinstance(value, list) and value for value in (jobs, entry_points, evidence, configs)):
            raise SystemExit(f"Pilot {pilot_id} must declare jobs, entry points, configs and evidence")

        covered_jobs.update(str(value) for value in jobs)
        covered_entry_points.update(str(value) for value in entry_points)
        for relative in configs:
            _require_path(str(relative), kind="config")
        for relative in evidence:
            _require_path(str(relative), kind="evidence")

    if covered_jobs != EXPECTED_JOB_IDS:
        missing = sorted(EXPECTED_JOB_IDS - covered_jobs)
        extra = sorted(covered_jobs - EXPECTED_JOB_IDS)
        raise SystemExit(f"B2 pilot job coverage drift: missing={missing} extra={extra}")

    demo_pyproject = tomllib.loads(
        (ROOT / "examples" / "plugin_package" / "pyproject.toml").read_text(encoding="utf-8")
    )
    declared_entry_points = set(
        demo_pyproject["project"]["entry-points"]["pyingestkit.jobs"].keys()
    )
    if covered_entry_points != declared_entry_points:
        missing = sorted(declared_entry_points - covered_entry_points)
        extra = sorted(covered_entry_points - declared_entry_points)
        raise SystemExit(f"B2 pilot entry-point coverage drift: missing={missing} extra={extra}")

    docs = contract.get("required_docs")
    if not isinstance(docs, list) or not docs:
        raise SystemExit("B2 pilot contract must name required user documentation")
    for relative in docs:
        _require_path(str(relative), kind="documentation")

    ci_text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    required_ci_jobs = contract.get("required_ci_jobs")
    if not isinstance(required_ci_jobs, list) or not required_ci_jobs:
        raise SystemExit("B2 pilot contract must name required CI jobs")
    for job_name in required_ci_jobs:
        if f"  {job_name}:" not in ci_text:
            raise SystemExit(f"B2 required CI job is missing: {job_name}")
    if not service_ci_jobs.issubset(set(str(value) for value in required_ci_jobs)):
        raise SystemExit("Every service-backed pilot CI job must be release-blocking in B2")

    print(
        "OK: V1 representative pilot and documentation contract is intact "
        f"(V1.0.0-b2, {len(pilot_ids)} pilots, {len(covered_jobs)} reference jobs)"
    )


if __name__ == "__main__":
    main()
