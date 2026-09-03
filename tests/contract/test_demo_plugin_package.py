from __future__ import annotations

import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.runtime import Runner


ROOT = Path(__file__).resolve().parents[2]
DEMO_PACKAGE = ROOT / "examples" / "plugin_package"


class DemoPluginPackageContractTests(unittest.TestCase):
    def test_demo_package_declares_pyingestkit_entry_point(self) -> None:
        payload = tomllib.loads((DEMO_PACKAGE / "pyproject.toml").read_text(encoding="utf-8"))
        entry_points = payload["project"]["entry-points"]["pyingestkit.jobs"]
        self.assertEqual(
            entry_points["demo-local-file"],
            "pyingestkit_demo_jobs.local_file:job",
        )

    def test_demo_job_is_zero_arg_and_runnable(self) -> None:
        src = str(DEMO_PACKAGE / "src")
        sys.path.insert(0, src)
        try:
            from pyingestkit_demo_jobs.local_file import job

            job.validate_definition()
            self.assertEqual(job.id, "demo.local_file")
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / "input.txt"
                source.write_text("demo\n", encoding="utf-8")
                result = Runner(LocalArtifactStore(root / "workspace")).run(
                    job, parameters={"path": str(source)}
                )
                self.assertTrue(result.succeeded, result.error)
        finally:
            sys.path.remove(src)
            sys.modules.pop("pyingestkit_demo_jobs", None)
            sys.modules.pop("pyingestkit_demo_jobs.local_file", None)

    def test_demo_config_exists_and_references_sample(self) -> None:
        self.assertTrue((DEMO_PACKAGE / "demo.yml").is_file())
        self.assertTrue((DEMO_PACKAGE / "data" / "sample.txt").is_file())


if __name__ == "__main__":
    unittest.main()
