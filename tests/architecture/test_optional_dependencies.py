from __future__ import annotations

import re
import tomllib
from pathlib import Path

from pyingestkit._architecture_v2 import V2_SUPPORTED_PYTHON

ROOT = Path(__file__).resolve().parents[2]
OPTIONAL_PROVIDER_DISTRIBUTIONS = {
    "boto3",
    "openpyxl",
    "psycopg",
    "pyarrow",
    "pytransformkit",
}


def _distribution_name(requirement: str) -> str:
    match = re.match(r"[A-Za-z0-9_.-]+", requirement)
    assert match is not None
    return match.group(0).lower().replace("_", "-")


def test_optional_provider_sdks_are_not_base_dependencies() -> None:
    payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = payload["project"]["dependencies"]
    base_names = {_distribution_name(item) for item in dependencies}
    assert base_names.isdisjoint(OPTIONAL_PROVIDER_DISTRIBUTIONS)


def test_v2_target_python_matrix_is_explicit() -> None:
    assert V2_SUPPORTED_PYTHON == ("3.11", "3.12", "3.13", "3.14")
