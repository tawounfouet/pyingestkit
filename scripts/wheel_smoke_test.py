from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import venv
from pathlib import Path

FRAMEWORK_VERSION = "1.0.0rc1"
DEMO_VERSION = "1.0.0rc1"
QUALITY_JOBS = ("demo.ndjson_quality", "demo.excel_quality", "demo.parquet_quality")
VERSIONED_JOB = "demo.versioned_ndjson"


def run(command: list[str], *, cwd: Path, env: dict[str, str], capture: bool = False) -> str:
    print("+", " ".join(command), flush=True)
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
        text=True,
        capture_output=capture,
    )
    if capture:
        print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=os.sys.stderr)
    return completed.stdout if capture else ""


def json_command(command: list[str], *, cwd: Path, env: dict[str, str]) -> object:
    return json.loads(run(command, cwd=cwd, env=env, capture=True))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    framework_wheel = root / "dist" / f"pyingestkit-{FRAMEWORK_VERSION}-py3-none-any.whl"
    demo_wheel = (
        root
        / "examples"
        / "plugin_package"
        / "dist"
        / f"pyingestkit_demo_jobs-{DEMO_VERSION}-py3-none-any.whl"
    )
    for artifact in (framework_wheel, demo_wheel):
        if not artifact.is_file():
            raise SystemExit(f"Missing built wheel: {artifact}")

    workspace = root / ".pyingest"
    shutil.rmtree(workspace, ignore_errors=True)

    with tempfile.TemporaryDirectory(prefix="pyingestkit-wheel-smoke-") as tmp:
        env_dir = Path(tmp) / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(env_dir)
        if os.name == "nt":
            python = env_dir / "Scripts" / "python.exe"
            pyingest = env_dir / "Scripts" / "pyingest.exe"
        else:
            python = env_dir / "bin" / "python"
            pyingest = env_dir / "bin" / "pyingest"

        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONNOUSERSITE"] = "1"

        run([str(python), "-m", "pip", "install", "--upgrade", "pip"], cwd=root, env=env)
        framework_requirement = (
            "pyingestkit[excel,parquet,postgres,s3] @ " + framework_wheel.resolve().as_uri()
        )
        run(
            [str(python), "-m", "pip", "install", framework_requirement, str(demo_wheel)],
            cwd=root,
            env=env,
        )
        run(
            [
                str(python),
                "-c",
                (
                    "import boto3, openpyxl, pyarrow, psycopg, pyingestkit; "
                    "from pyingestkit import ("
                    "ArtifactURI, IdempotencyAction, IdempotencyPolicy, PostgresTarget, "
                    "S3ArtifactStore, S3DatasetVersionStore, StoredArtifact, TargetLoadExecutor); "
                    f"assert pyingestkit.__version__ == '{FRAMEWORK_VERSION}'; "
                    "assert ArtifactURI.s3('bucket', 'raw/key').scheme == 's3'; "
                    "assert S3ArtifactStore.__name__ == 'S3ArtifactStore'; "
                    "assert S3DatasetVersionStore.__name__ == 'S3DatasetVersionStore'; "
                    "assert StoredArtifact.__name__ == 'StoredArtifact'; "
                    "assert PostgresTarget.B2_CAPABILITIES.truncate_load; "
                    "assert PostgresTarget.B2_CAPABILITIES.replace; "
                    "assert IdempotencyAction.SKIP.value == 'skip'; "
                    "assert IdempotencyPolicy.AUTO.value == 'auto'; "
                    "assert TargetLoadExecutor.__name__ == 'TargetLoadExecutor'; "
                    "print('installed_from=' + pyingestkit.__file__); "
                    "print('openpyxl=' + openpyxl.__version__); "
                    "print('pyarrow=' + pyarrow.__version__)"
                ),
            ],
            cwd=root,
            env=env,
        )
        run([str(pyingest), "--version"], cwd=root, env=env)
        jobs_output = run([str(pyingest), "jobs", "--json"], cwd=root, env=env, capture=True)
        installed_ids = {entry["id"] for entry in json.loads(jobs_output)}
        expected_ids = {
            "demo.local_file",
            "demo.http_csv",
            "demo.http_json",
            "demo.ndjson_quality",
            "demo.excel_quality",
            "demo.parquet_quality",
            VERSIONED_JOB,
            "demo.versioned_postgres",
            "demo.versioned_s3",
        }
        if installed_ids != expected_ids:
            raise SystemExit(f"Unexpected installed jobs: {sorted(installed_ids)}")

        run(
            [str(pyingest), "run", "demo.local_file", "--config", "examples/plugin_package/demo.yml"],
            cwd=root,
            env=env,
        )
        for job_id in ("demo.http_csv", "demo.http_json"):
            run(
                [str(pyingest), "run", job_id, "--config", "examples/plugin_package/demo-http.yml"],
                cwd=root,
                env=env,
            )
        for job_id in QUALITY_JOBS:
            run(
                [str(pyingest), "run", job_id, "--config", "examples/plugin_package/demo-quality.yml"],
                cwd=root,
                env=env,
            )

        first = json_command(
            [
                str(pyingest),
                "run",
                VERSIONED_JOB,
                "--config",
                "examples/plugin_package/demo-versioned.yml",
                "--param",
                "revision=1",
                "--json",
            ],
            cwd=root,
            env=env,
        )
        second = json_command(
            [
                str(pyingest),
                "run",
                VERSIONED_JOB,
                "--config",
                "examples/plugin_package/demo-versioned.yml",
                "--param",
                "revision=2",
                "--json",
            ],
            cwd=root,
            env=env,
        )
        assert isinstance(first, dict)
        assert isinstance(second, dict)
        if first.get("status") != "SUCCESS" or second.get("status") != "SUCCESS":
            raise SystemExit("Versioned V1 RC reference runs did not succeed")

        second_run_id = str(second["run_id"])
        diff_path = (
            workspace
            / "runs"
            / "demo"
            / "versioned_ndjson"
            / second_run_id
            / "reports"
            / "diff.json"
        )
        diff = json.loads(diff_path.read_text(encoding="utf-8"))
        expected_summary = {"added": 1, "removed": 1, "changed": 1, "unchanged": 1}
        if diff.get("summary") != expected_summary:
            raise SystemExit(f"Unexpected V1 RC diff summary: {diff.get('summary')}")

        versions = json_command(
            [
                str(pyingest),
                "versions",
                VERSIONED_JOB,
                "--config",
                "examples/plugin_package/demo-versioned.yml",
                "--workspace",
                str(workspace),
                "--json",
            ],
            cwd=root,
            env=env,
        )
        if not isinstance(versions, list) or len(versions) != 2:
            raise SystemExit(f"Expected exactly 2 content-addressed versions, got: {versions}")

        published = json_command(
            [
                str(pyingest),
                "published",
                VERSIONED_JOB,
                "--config",
                "examples/plugin_package/demo-versioned.yml",
                "--workspace",
                str(workspace),
                "--json",
            ],
            cwd=root,
            env=env,
        )
        assert isinstance(published, dict)
        if published.get("published_from_run_id") != second_run_id:
            raise SystemExit("PublishedDataset does not point to revision 2")

        replay = json_command(
            [
                str(pyingest),
                "replay",
                second_run_id,
                "--config",
                "examples/plugin_package/demo-versioned.yml",
                "--json",
            ],
            cwd=root,
            env=env,
        )
        assert isinstance(replay, dict)
        if replay.get("status") != "SUCCESS":
            raise SystemExit(f"Replay failed: {replay}")
        if replay.get("verification_mode") != "STRICT" or replay.get("matched") is not True:
            raise SystemExit(f"Replay was not strictly reproducible: {replay}")
        if replay.get("expected_fingerprint") != published.get("fingerprint"):
            raise SystemExit("Replay expected fingerprint differs from published revision 2")
        if replay.get("actual_fingerprint") != published.get("fingerprint"):
            raise SystemExit("Replay actual fingerprint differs from published revision 2")

        replay_manifest = (
            workspace
            / "runs"
            / "demo"
            / "versioned_ndjson"
            / str(replay["run_id"])
            / "manifest.json"
        )
        replay_payload = json.loads(replay_manifest.read_text(encoding="utf-8"))
        replay_lineage = replay_payload.get("replay") or {}
        if replay_lineage.get("source_run_id") != second_run_id:
            raise SystemExit("Replay manifest lineage is missing the source run")
        if replay_lineage.get("matched") is not True:
            raise SystemExit("Replay manifest does not record a successful fingerprint verification")

        run(
            [
                str(pyingest),
                "runs",
                "--config",
                "examples/plugin_package/demo-versioned.yml",
                "--workspace",
                str(workspace),
            ],
            cwd=root,
            env=env,
        )

        reports = list(workspace.glob("runs/demo/*/*/reports/profile.json"))
        if len(reports) != 6:
            raise SystemExit(
                "Expected 6 profile reports including live V1/V2 and replay, "
                f"found {len(reports)}"
            )
        for report_path in reports:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            row_count = payload["profile"]["row_count"]
            if row_count not in (2, 3):
                raise SystemExit(f"Unexpected profile report: {report_path}")

    shutil.rmtree(workspace, ignore_errors=True)
    print(
        "OK: V1.0.0rc1 wheels expose nine reference jobs and preserve local/postgres contracts "
        "while service-backed CI proves full cross-host object-storage replay and idempotent load"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
