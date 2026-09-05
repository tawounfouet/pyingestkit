from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from pyingestkit import Step, job
from pyingestkit.config import ArtifactBackend, MetadataBackend, load_config
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

    def test_s3_artifact_config_contains_no_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pyingest.yml"
            path.write_text(
                """
artifacts:
  backend: s3
  s3:
    bucket: pyingest-raw
    prefix: company/ingest
    region_name: eu-west-3
    endpoint_url_env: PYINGEST_S3_ENDPOINT_URL
""".strip(),
                encoding="utf-8",
            )
            config = load_config(path)
            self.assertIs(config.artifacts.backend, ArtifactBackend.S3)
            self.assertEqual(config.artifacts.s3.bucket, "pyingest-raw")
            self.assertEqual(config.artifacts.s3.prefix, "company/ingest")
            self.assertFalse(hasattr(config.artifacts.s3, "access_key"))
            self.assertFalse(hasattr(config.artifacts.s3, "secret_key"))

    def test_invalid_logging_level_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pyingest.yml"
            path.write_text("logging:\n  level: LOUD\n", encoding="utf-8")
            with self.assertRaises(ConfigurationError):
                load_config(path)

    def test_env_var_config_auto_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "custom.yml"
            path.write_text("logging:\n  level: DEBUG\n", encoding="utf-8")
            os.environ["PYINGEST_CONFIG"] = str(path)
            try:
                config = load_config()
                self.assertEqual(config.logging.level, "DEBUG")
            finally:
                os.environ.pop("PYINGEST_CONFIG", None)

    def test_job_backend_requirements_declaration(self) -> None:
        class DummyStep(Step):
            def execute(self, context, data):
                return data

        @job(
            id="public.test_job",
            version="1.0.0",
            requires_artifacts="s3",
            requires_metadata="postgres",
        )
        def test_job() -> None:
            DummyStep()

        compiled_job = test_job.build()
        self.assertEqual(compiled_job.requires_artifacts, "s3")
        self.assertEqual(compiled_job.requires_metadata, "postgres")


if __name__ == "__main__":
    unittest.main()
