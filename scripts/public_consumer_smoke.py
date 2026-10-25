"""Public-consumer smoke test for published PyIngestKit distributions."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import venv
from pathlib import Path


def _resolve_default_version() -> str:
    """Resolve framework version from pyproject.toml or src/pyingestkit/_version.py."""
    root = Path(__file__).resolve().parents[1]
    version_file = root / "src" / "pyingestkit" / "_version.py"
    if version_file.is_file():
        import re

        match = re.search(r'^__version__\s*=\s*"([^"]+)"', version_file.read_text(encoding="utf-8"), re.M)
        if match:
            return match.group(1)

    pyproject_file = root / "pyproject.toml"
    if pyproject_file.is_file():
        try:
            import tomllib

            data = tomllib.loads(pyproject_file.read_text(encoding="utf-8"))
            if "version" in data.get("project", {}):
                return str(data["project"]["version"])
        except Exception:
            pass

    return "2.2.0"


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify public consumer experience of published PyIngestKit package."
    )
    parser.add_argument(
        "--package",
        default="pyingestkit",
        help="Package name on PyPI (default: pyingestkit)",
    )
    parser.add_argument(
        "--expected-version",
        default=None,
        help="Expected package version (defaults to active repository version)",
    )
    parser.add_argument(
        "--skip-pypi-wait",
        action="store_true",
        help="Skip polling PyPI for release availability (used when testing local wheels or pre-installed envs)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Max wait time in seconds for PyPI propagation (default: 600s)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=15,
        help="Polling interval in seconds (default: 15s)",
    )
    parser.add_argument(
        "--wheel",
        type=str,
        default=None,
        help="Optional local wheel path to install instead of downloading from PyPI",
    )
    return parser.parse_args()


def _wait_for_pypi(package: str, version: str, timeout: int, interval: int) -> None:
    """Poll PyPI JSON API until target version is available."""
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    print(f"Polling PyPI endpoint for {package}=={version} at {url}...", flush=True)

    start_time = time.monotonic()
    attempt = 1
    max_attempts = max(1, timeout // interval)

    while (time.monotonic() - start_time) < timeout:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": f"pyingestkit-smoke/{version} (verification-script)"},
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    found_version = data.get("info", {}).get("version")
                    if found_version == version:
                        print(f"PyPI version {version} confirmed available on attempt {attempt}!", flush=True)
                        return
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
            pass

        print(
            f"PyPI propagation pending (attempt {attempt}/{max_attempts}, "
            f"elapsed {int(time.monotonic() - start_time)}s)...",
            flush=True,
        )
        time.sleep(interval)
        attempt += 1

    raise SystemExit(
        f"Timed out after {timeout}s waiting for {package}=={version} on PyPI ({url})."
    )


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise AssertionError(
            f"Command failed ({result.returncode}): {' '.join(cmd)}\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
    return result


def _verify_consumer_environment(python_path: Path, pik_path: Path | None, expected_version: str) -> None:
    """Run comprehensive checks inside the clean consumer virtualenv."""
    print("Verifying imports and runtime contracts in clean consumer environment...", flush=True)

    # 1. Root exports and version identity
    code_identity = f"""
import importlib.metadata
import sys
import pyingestkit

pkg_ver = importlib.metadata.version("pyingestkit")
mod_ver = pyingestkit.__version__
assert pkg_ver == "{expected_version}", f"Expected pkg version {expected_version}, got {{pkg_ver}}"
assert mod_ver == "{expected_version}", f"Expected mod version {expected_version}, got {{mod_ver}}"

# Verify root public symbols
from pyingestkit import (
    ArtifactReference,
    DatasetVersion,
    DatasetVersionReference,
    IngestionDefinition,
    IngestionResult,
    IngestionRun,
    IngestionRunId,
    IngestionRuntime,
    PublishedDataset,
    ResourceReference,
    Source,
)

# Verify qualified governance namespaces
import pyingestkit.governance as gov
from pyingestkit.governance.rollback import GovernedRollbackService

assert hasattr(gov, "RetentionPolicy")
assert hasattr(gov, "PublicationLedger")
assert issubclass(GovernedRollbackService, object)

print("CONTRACT_OK")
"""
    result = _run([str(python_path), "-c", code_identity])
    assert "CONTRACT_OK" in result.stdout

    # 2. CLI checks
    cli_commands: list[list[str]] = []
    if pik_path is not None and pik_path.is_file():
        cli_commands.extend([
            [str(pik_path), "--version"],
            [str(pik_path), "--help"],
            [str(pik_path), "doctor", "--json"],
        ])
    
    # Also verify python -m pyingestkit.cli
    cli_commands.extend([
        [str(python_path), "-m", "pyingestkit.cli", "--version"],
        [str(python_path), "-m", "pyingestkit.cli", "--help"],
        [str(python_path), "-m", "pyingestkit.cli", "doctor", "--json"],
    ])

    for cmd in cli_commands:
        res = _run(cmd)
        if "--version" in cmd:
            assert expected_version in res.stdout, f"Expected {expected_version} in version output: {res.stdout}"
        if "doctor" in cmd and "--json" in cmd:
            doctor_json = json.loads(res.stdout)
            assert doctor_json.get("status") in ("healthy", "degraded", "unhealthy")
            assert doctor_json.get("pyingestkit", {}).get("version") == expected_version


def main() -> int:
    args = _args()
    package = args.package
    expected_version = args.expected_version or _resolve_default_version()

    print(f"Starting public consumer smoke test for {package}=={expected_version}")

    # Step 1: Wait for PyPI propagation if requested
    if not args.skip_pypi_wait and not args.wheel:
        _wait_for_pypi(package, expected_version, args.timeout, args.poll_interval)
    else:
        print("Skipping PyPI polling (local wheel or explicit skip).", flush=True)

    # Step 2: Create isolated virtual environment
    with tempfile.TemporaryDirectory(prefix="pyingestkit-consumer-smoke-") as tmp:
        env_dir = Path(tmp) / "venv"
        print(f"Creating isolated consumer virtualenv at {env_dir}...", flush=True)
        venv.EnvBuilder(with_pip=True, clear=True).create(env_dir)

        if os.name == "nt":
            python_path = env_dir / "Scripts" / "python.exe"
            pik_path = env_dir / "Scripts" / "pik.exe"
        else:
            python_path = env_dir / "bin" / "python"
            pik_path = env_dir / "bin" / "pik"

        clean_env = os.environ.copy()
        clean_env.pop("PYTHONPATH", None)
        clean_env["PYTHONNOUSERSITE"] = "1"

        # Upgrade pip in venv
        _run([str(python_path), "-m", "pip", "install", "--upgrade", "pip"], env=clean_env)

        # Step 3: Install distribution
        if args.wheel:
            wheel_path = Path(args.wheel).resolve()
            print(f"Installing local wheel: {wheel_path}...", flush=True)
            _run(
                [
                    str(python_path),
                    "-m",
                    "pip",
                    "install",
                    "--no-cache-dir",
                    f"{wheel_path}[cli,postgres,s3]",
                ],
                env=clean_env,
            )
        else:
            install_target = f"{package}[cli,postgres,s3]=={expected_version}"
            print(f"Installing from PyPI: {install_target}...", flush=True)
            _run(
                [
                    str(python_path),
                    "-m",
                    "pip",
                    "install",
                    "--no-cache-dir",
                    install_target,
                ],
                env=clean_env,
            )

        # Verify dependency graph
        _run([str(python_path), "-m", "pip", "check"], env=clean_env)

        # Step 4: Verify consumer experience
        _verify_consumer_environment(python_path, pik_path if pik_path.is_file() else None, expected_version)

    summary = {
        "public_consumer_smoke": "PASS",
        "package": package,
        "version": expected_version,
        "python": sys.version.split()[0],
        "platform": sys.platform,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
