from __future__ import annotations

import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.declarative import JobDefinition
from pyingestkit.metadata import SQLiteMetadataStore
from pyingestkit.runtime import Runner

ROOT = Path(__file__).resolve().parents[2]
DEMO_PACKAGE = ROOT / "examples" / "plugin_package"


class DemoPluginPackageContractTests(unittest.TestCase):
    def test_demo_package_declares_pyingestkit_entry_point(self) -> None:
        payload = tomllib.loads((DEMO_PACKAGE / "pyproject.toml").read_text(encoding="utf-8"))
        entry_points = payload["project"]["entry-points"]["pyingestkit.jobs"]
        self.assertEqual(
            entry_points["demo-local-file"],
            "pyingestkit_demo_jobs.local_file:job_definition",
        )
        self.assertIn("demo-http-csv", entry_points)
        self.assertIn("demo-http-json", entry_points)
        self.assertIn("demo-ndjson-quality", entry_points)
        self.assertIn("demo-excel-quality", entry_points)
        self.assertIn("demo-parquet-quality", entry_points)

    def test_demo_job_is_declarative_and_runnable(self) -> None:
        src = str(DEMO_PACKAGE / "src")
        sys.path.insert(0, src)
        try:
            from pyingestkit_demo_jobs.local_file import job_definition

            self.assertIsInstance(job_definition, JobDefinition)
            built = job_definition.build()
            self.assertEqual(built.id, "demo.local_file")
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / "input.txt"
                source.write_text("demo\n", encoding="utf-8")
                workspace = root / "workspace"
                result = Runner(
                    LocalArtifactStore(workspace),
                    metadata_store=SQLiteMetadataStore.for_workspace(workspace),
                ).run(built, parameters={"path": str(source)})
                self.assertTrue(result.succeeded, result.error)
        finally:
            sys.path.remove(src)
            sys.modules.pop("pyingestkit_demo_jobs", None)
            sys.modules.pop("pyingestkit_demo_jobs.local_file", None)

    def test_demo_config_uses_unified_workspace(self) -> None:
        config = (DEMO_PACKAGE / "demo.yml").read_text(encoding="utf-8")
        self.assertIn("workspace: .pyingest", config)
        self.assertNotIn(".pyingest-demo", config)
        self.assertTrue((DEMO_PACKAGE / "data" / "sample.txt").is_file())


if __name__ == "__main__":
    unittest.main()
