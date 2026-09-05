from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pyingestkit.config import MetadataBackend, load_config
from pyingestkit.core.exceptions import ConfigurationError


class ConfigTests(unittest.TestCase):
    def test_load_valid_yaml_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pyingest.yml"
            path.write_text(
                """
runtime:
  workspace: .work
  fixture_mode: true
  parameters:
    source: fixture
metadata:
  backend: sqlite
logging:
  level: WARNING
  format: plain
  file:
    enabled: true
    path: .work/logs/pyingest.log
    level: DEBUG
    format: json
""".strip(),
                encoding="utf-8",
            )
            config = load_config(path)
            self.assertEqual(config.runtime.workspace, Path(".work"))
            self.assertTrue(config.runtime.fixture_mode)
            self.assertEqual(config.runtime.parameters["source"], "fixture")
            self.assertIs(config.metadata.backend, MetadataBackend.SQLITE)
            self.assertEqual(config.logging.level, "WARNING")
            self.assertTrue(config.logging.file.enabled)

    def test_postgres_config_uses_environment_variable_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pyingest.yml"
            path.write_text(
                "metadata:\n  backend: postgres\n  postgres:\n    dsn_env: CUSTOM_DATABASE_URL\n",
                encoding="utf-8",
            )
            config = load_config(path)
            self.assertIs(config.metadata.backend, MetadataBackend.POSTGRES)
            self.assertEqual(config.metadata.postgres.dsn_env, "CUSTOM_DATABASE_URL")

    def test_postgres_target_config_keeps_credentials_out_of_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pyingest.yml"
            path.write_text(
                """
targets:
  warehouse:
    type: postgres
    target_id: postgres.demo.reference
    dsn_env: PYINGEST_TARGET_DATABASE_URL
    schema: reference
    table: demo_dataset
    load_mode: append
""".strip(),
                encoding="utf-8",
            )
            config = load_config(path)
            target = config.targets["warehouse"]
            self.assertEqual(target.target_id, "postgres.demo.reference")
            self.assertEqual(target.dsn_env, "PYINGEST_TARGET_DATABASE_URL")
            self.assertEqual(target.schema_name, "reference")
            self.assertEqual(target.table, "demo_dataset")
            self.assertFalse(hasattr(target, "dsn"))

    def test_postgres_target_config_rejects_dsn_as_target_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pyingest.yml"
            path.write_text(
                (
                    "targets:\n  warehouse:\n"
                    "    target_id: postgresql://user:secret@host/db\n"
                    "    table: demo\n"
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ConfigurationError):
                load_config(path)

    def test_invalid_logging_level_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pyingest.yml"
            path.write_text("logging:\n  level: LOUD\n", encoding="utf-8")
            with self.assertRaises(ConfigurationError):
                load_config(path)

    def test_unknown_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pyingest.yml"
            path.write_text("unknown: true\n", encoding="utf-8")
            with self.assertRaises(ConfigurationError):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
