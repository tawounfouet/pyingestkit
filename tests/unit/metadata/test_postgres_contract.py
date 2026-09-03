from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from pyingestkit.metadata import MetadataStore, PostgresMetadataStore


class PostgresContractTests(unittest.TestCase):
    def test_adapter_implements_metadata_contract(self) -> None:
        self.assertTrue(issubclass(PostgresMetadataStore, MetadataStore))

    def test_psycopg_is_optional_extra(self) -> None:
        root = Path(__file__).resolve().parents[3]
        payload = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        postgres = payload["project"]["optional-dependencies"]["postgres"]
        self.assertTrue(any("psycopg" in item for item in postgres))


if __name__ == "__main__":
    unittest.main()
