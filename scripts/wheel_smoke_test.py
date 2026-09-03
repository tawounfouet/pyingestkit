from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import venv
from pathlib import Path

EXPECTED_VERSION = "0.2.0"


def run(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    framework_wheel = root / "dist" / f"pyingestkit-{EXPECTED_VERSION}-py3-none-any.whl"
    demo_wheel = (
        root
        / "examples"
        / "plugin_package"
        / "dist"
        / f"pyingestkit_demo_jobs-{EXPECTED_VERSION}-py3-none-any.whl"
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
        run(
            [str(python), "-m", "pip", "install", str(framework_wheel), str(demo_wheel)],
            cwd=root,
            env=env,
        )
        run(
            [
                str(python),
                "-c",
                (
                    "import pyingestkit; "
                    f"assert pyingestkit.__version__ == '{EXPECTED_VERSION}'; "
                    "print('installed_from=' + pyingestkit.__file__)"
                ),
            ],
            cwd=root,
            env=env,
        )
        run([str(pyingest), "--version"], cwd=root, env=env)
        run([str(pyingest), "jobs"], cwd=root, env=env)
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
        run(
            [
                str(pyingest),
                "run",
                "demo.http_csv",
                "--config",
                "examples/plugin_package/demo-http.yml",
            ],
            cwd=root,
            env=env,
        )
        run(
            [
                str(pyingest),
                "run",
                "demo.http_json",
                "--config",
                "examples/plugin_package/demo-http.yml",
            ],
            cwd=root,
            env=env,
        )
        run([str(pyingest), "runs"], cwd=root, env=env)

    shutil.rmtree(workspace, ignore_errors=True)
    print("OK: V0.2.0 wheels install and execute all reference jobs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
