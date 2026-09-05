from __future__ import annotations

import json
import os
import subprocess
import tempfile
import venv
from pathlib import Path

BASELINE_TAG = "v0.6.0"
BASELINE_VERSION = "0.6.0"
RC_VERSION = "1.0.0rc1"
VERSIONED_JOB = "demo.versioned_ndjson"


def run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    capture: bool = False,
) -> str:
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
    framework_wheel = root / "dist" / f"pyingestkit-{RC_VERSION}-py3-none-any.whl"
    demo_wheel = (
        root
        / "examples"
        / "plugin_package"
        / "dist"
        / f"pyingestkit_demo_jobs-{RC_VERSION}-py3-none-any.whl"
    )
    for artifact in (framework_wheel, demo_wheel):
        if not artifact.is_file():
            raise SystemExit(f"Missing RC wheel: {artifact}")

    git_env = os.environ.copy()
    run(
        ["git", "rev-parse", "--verify", f"refs/tags/{BASELINE_TAG}^{{}}"],
        cwd=root,
        env=git_env,
        capture=True,
    )

    with tempfile.TemporaryDirectory(prefix="pyingestkit-upgrade-smoke-") as tmp:
        temp_root = Path(tmp)
        old_root = temp_root / "v060"
        workspace = temp_root / "workspace"
        env_dir = temp_root / "venv"

        run(
            ["git", "worktree", "add", "--detach", str(old_root), BASELINE_TAG],
            cwd=root,
            env=git_env,
        )
        try:
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
            env["PYINGEST_WORKSPACE"] = str(workspace)

            run(
                [str(python), "-m", "pip", "install", "--upgrade", "pip"],
                cwd=root,
                env=env,
            )
            run(
                [
                    str(python),
                    "-m",
                    "pip",
                    "install",
                    str(old_root),
                    str(old_root / "examples" / "plugin_package"),
                ],
                cwd=root,
                env=env,
            )
            baseline_version = run(
                [str(pyingest), "--version"], cwd=old_root, env=env, capture=True
            )
            if BASELINE_VERSION not in baseline_version:
                raise SystemExit(f"Unexpected baseline CLI version: {baseline_version.strip()}")

            old_config = old_root / "examples" / "plugin_package" / "demo-versioned.yml"
            first = json_command(
                [
                    str(pyingest),
                    "run",
                    VERSIONED_JOB,
                    "--config",
                    str(old_config),
                    "--workspace",
                    str(workspace),
                    "--param",
                    "revision=1",
                    "--json",
                ],
                cwd=old_root,
                env=env,
            )
            second = json_command(
                [
                    str(pyingest),
                    "run",
                    VERSIONED_JOB,
                    "--config",
                    str(old_config),
                    "--workspace",
                    str(workspace),
                    "--param",
                    "revision=2",
                    "--json",
                ],
                cwd=old_root,
                env=env,
            )
            assert isinstance(first, dict)
            assert isinstance(second, dict)
            if first.get("status") != "SUCCESS" or second.get("status") != "SUCCESS":
                raise SystemExit("V0.6.0 baseline runs did not succeed")
            source_run_id = str(second["run_id"])

            run(
                [
                    str(python),
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    str(framework_wheel),
                    str(demo_wheel),
                ],
                cwd=root,
                env=env,
            )
            upgraded_version = run(
                [str(pyingest), "--version"], cwd=root, env=env, capture=True
            )
            if RC_VERSION not in upgraded_version:
                raise SystemExit(f"Unexpected upgraded CLI version: {upgraded_version.strip()}")

            status = json_command(
                [
                    str(pyingest),
                    "status",
                    source_run_id,
                    "--config",
                    str(old_config),
                    "--workspace",
                    str(workspace),
                    "--json",
                ],
                cwd=root,
                env=env,
            )
            assert isinstance(status, dict)
            status_run = status.get("run")
            if not isinstance(status_run, dict) or status_run.get("status") != "SUCCESS":
                raise SystemExit(f"V0.6.0 run history is not readable after upgrade: {status}")

            versions = json_command(
                [
                    str(pyingest),
                    "versions",
                    VERSIONED_JOB,
                    "--config",
                    str(old_config),
                    "--workspace",
                    str(workspace),
                    "--json",
                ],
                cwd=root,
                env=env,
            )
            if not isinstance(versions, list) or len(versions) != 2:
                raise SystemExit(f"V0.6.0 versions are not readable after upgrade: {versions}")

            published = json_command(
                [
                    str(pyingest),
                    "published",
                    VERSIONED_JOB,
                    "--config",
                    str(old_config),
                    "--workspace",
                    str(workspace),
                    "--json",
                ],
                cwd=root,
                env=env,
            )
            assert isinstance(published, dict)
            if published.get("published_from_run_id") != source_run_id:
                raise SystemExit("V0.6.0 publication pointer changed during upgrade")

            replay = json_command(
                [
                    str(pyingest),
                    "replay",
                    source_run_id,
                    "--config",
                    str(old_config),
                    "--workspace",
                    str(workspace),
                    "--json",
                ],
                cwd=root,
                env=env,
            )
            assert isinstance(replay, dict)
            if replay.get("status") != "SUCCESS":
                raise SystemExit(f"V0.6.0 strict replay failed after upgrade: {replay}")
            if replay.get("verification_mode") != "STRICT" or replay.get("matched") is not True:
                raise SystemExit(f"V0.6.0 replay is not strictly reproducible after upgrade: {replay}")
            if replay.get("expected_fingerprint") != published.get("fingerprint"):
                raise SystemExit("Upgrade replay expected fingerprint differs from V0.6 publication")
            if replay.get("actual_fingerprint") != published.get("fingerprint"):
                raise SystemExit("Upgrade replay actual fingerprint differs from V0.6 publication")
        finally:
            run(
                ["git", "worktree", "remove", "--force", str(old_root)],
                cwd=root,
                env=git_env,
            )

    print(
        "OK: V0.6.0 workspace/history/version/publication state upgrades to "
        "V1.0.0rc1 and remains strict-replay compatible"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
