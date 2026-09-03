from __future__ import annotations

import sys
import tomllib
import unittest
from pathlib import Path

from pyingestkit.declarative import JobDefinition

ROOT = Path(__file__).resolve().parents[2]
DEMO_PACKAGE = ROOT / "examples" / "plugin_package"


class ReferenceJobContractTests(unittest.TestCase):
    def test_demo_package_declares_three_reference_entry_points(self) -> None:
        payload = tomllib.loads((DEMO_PACKAGE / "pyproject.toml").read_text(encoding="utf-8"))
        entry_points = payload["project"]["entry-points"]["pyingestkit.jobs"]
        self.assertEqual(
            entry_points,
            {
                "demo-local-file": "pyingestkit_demo_jobs.local_file:job_definition",
                "demo-http-csv": "pyingestkit_demo_jobs.http_csv:job_definition",
                "demo-http-json": "pyingestkit_demo_jobs.http_json:job_definition",
            },
        )

    def test_reference_job_ids_and_pipelines_are_stable(self) -> None:
        src = str(DEMO_PACKAGE / "src")
        sys.path.insert(0, src)
        try:
            from pyingestkit_demo_jobs.http_csv import job_definition as csv_job
            from pyingestkit_demo_jobs.http_json import job_definition as json_job
            from pyingestkit_demo_jobs.local_file import job_definition as local_job

            jobs = (local_job, csv_job, json_job)
            self.assertTrue(all(isinstance(job, JobDefinition) for job in jobs))
            self.assertEqual(
                [job.id for job in jobs],
                ["demo.local_file", "demo.http_csv", "demo.http_json"],
            )
            self.assertEqual([len(job.build().pipeline()) for job in jobs], [1, 3, 3])
        finally:
            sys.path.remove(src)

    def test_http_demo_config_is_fixture_first(self) -> None:
        config = (DEMO_PACKAGE / "demo-http.yml").read_text(encoding="utf-8")
        self.assertIn("fixture_mode: true", config)
        self.assertIn("workspace: .pyingest", config)


if __name__ == "__main__":
    unittest.main()
