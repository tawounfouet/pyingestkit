from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_v2_baseline_packages_import_without_creating_files(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src = repo_root / "src"
    modules = (
        "pyingestkit.domain",
        "pyingestkit.application",
        "pyingestkit.ports",
        "pyingestkit.adapters",
        "pyingestkit.serialization",
        "pyingestkit.observability",
        "pyingestkit.integrations",
        "pyingestkit.integrations.pytransformkit",
    )
    code = "\n".join(f"import {module}" for module in modules)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(src)
    subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert list(tmp_path.iterdir()) == []
