from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import venv
from pathlib import Path

FRAMEWORK_VERSION = "0.3.0"
DEMO_VERSION = "0.3.0"
QUALITY_JOBS = ("demo.ndjson_quality", "demo.excel_quality", "demo.parquet_quality")


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
    return completed.stdout if capture else ""


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
        framework_requirement = f"pyingestkit[excel,parquet] @ {framework_wheel.resolve().as_uri()}"
        run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                framework_requirement,
                str(demo_wheel),
            ],
            cwd=root,
            env=env,
        )
        run(
            [
                str(python),
                "-c",
                (
                    "import openpyxl, pyarrow, pyingestkit; "
                    f"assert pyingestkit.__version__ == '{FRAMEWORK_VERSION}'; "
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
        }
        if installed_ids != expected_ids:
            raise SystemExit(f"Unexpected installed jobs: {sorted(installed_ids)}")

        run(
            [
                str(pyingest),
                "run",
                "demo.local_file",
                "--config",
                "examples/plugin_package/demo.yml",
            ],
            cwd=root,
            env=env,
        )
        for job_id in ("demo.http_csv", "demo.http_json"):
            run(
                [
                    str(pyingest),
                    "run",
                    job_id,
                    "--config",
                    "examples/plugin_package/demo-http.yml",
                ],
                cwd=root,
                env=env,
            )
        for job_id in QUALITY_JOBS:
            run(
                [
                    str(pyingest),
                    "run",
                    job_id,
                    "--config",
                    "examples/plugin_package/demo-quality.yml",
                ],
                cwd=root,
                env=env,
            )
        run([str(pyingest), "runs"], cwd=root, env=env)

        reports = list(workspace.glob("runs/demo/*/*/reports/profile.json"))
        if len(reports) != 3:
            raise SystemExit(f"Expected 3 profile reports, found {len(reports)}")
        for report_path in reports:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            if payload["profile"]["row_count"] != 2:
                raise SystemExit(f"Unexpected profile report: {report_path}")

    shutil.rmtree(workspace, ignore_errors=True)
    print("OK: V0.3.0 wheels install extras and execute all six reference jobs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
