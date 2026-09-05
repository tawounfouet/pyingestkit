from __future__ import annotations

import sys
import tomllib
import unittest
from pathlib import Path

from pyingestkit.declarative import JobDefinition

ROOT = Path(__file__).resolve().parents[2]
DEMO_PACKAGE = ROOT / "examples" / "plugin_package"


class ReferenceJobContractTests(unittest.TestCase):
    def test_demo_package_declares_nine_reference_entry_points(self) -> None:
        payload = tomllib.loads((DEMO_PACKAGE / "pyproject.toml").read_text(encoding="utf-8"))
        entry_points = payload["project"]["entry-points"]["pyingestkit.jobs"]
        self.assertEqual(
            entry_points,
            {
                "demo-local-file": "pyingestkit_demo_jobs.local_file:job_definition",
                "demo-http-csv": "pyingestkit_demo_jobs.http_csv:job_definition",
                "demo-http-json": "pyingestkit_demo_jobs.http_json:job_definition",
                "demo-ndjson-quality": "pyingestkit_demo_jobs.ndjson_quality:job_definition",
                "demo-excel-quality": "pyingestkit_demo_jobs.excel_quality:job_definition",
                "demo-parquet-quality": "pyingestkit_demo_jobs.parquet_quality:job_definition",
                "demo-versioned-ndjson": "pyingestkit_demo_jobs.versioned_ndjson:job_definition",
                "demo-versioned-postgres": (
                    "pyingestkit_demo_jobs.versioned_postgres:job_definition"
                ),
                "demo-versioned-s3": "pyingestkit_demo_jobs.versioned_s3:job_definition",
            },
        )

    def test_reference_job_ids_and_pipelines_are_stable(self) -> None:
        src = str(DEMO_PACKAGE / "src")
        sys.path.insert(0, src)
        try:
            from pyingestkit_demo_jobs.excel_quality import job_definition as excel_job
            from pyingestkit_demo_jobs.http_csv import job_definition as csv_job
            from pyingestkit_demo_jobs.http_json import job_definition as json_job
            from pyingestkit_demo_jobs.local_file import job_definition as local_job
            from pyingestkit_demo_jobs.ndjson_quality import job_definition as ndjson_job
            from pyingestkit_demo_jobs.parquet_quality import job_definition as parquet_job
            from pyingestkit_demo_jobs.versioned_ndjson import (
                job_definition as versioned_ndjson_job,
            )
            from pyingestkit_demo_jobs.versioned_postgres import (
                job_definition as versioned_postgres_job,
            )
            from pyingestkit_demo_jobs.versioned_s3 import job_definition as versioned_s3_job

            jobs = (
                local_job,
                csv_job,
                json_job,
                ndjson_job,
                excel_job,
                parquet_job,
                versioned_ndjson_job,
                versioned_postgres_job,
                versioned_s3_job,
            )
            self.assertTrue(all(isinstance(job, JobDefinition) for job in jobs))
            self.assertEqual(
                [job.id for job in jobs],
                [
                    "demo.local_file",
                    "demo.http_csv",
                    "demo.http_json",
                    "demo.ndjson_quality",
                    "demo.excel_quality",
                    "demo.parquet_quality",
                    "demo.versioned_ndjson",
                    "demo.versioned_postgres",
                    "demo.versioned_s3",
                ],
            )
            self.assertEqual(
                [len(job.build().pipeline()) for job in jobs],
                [1, 3, 3, 4, 4, 4, 5, 5, 5],
            )
            self.assertTrue(all(job.version == "0.4.0" for job in jobs[:-2]))
            self.assertEqual(jobs[-2].version, "0.5.1")
            self.assertEqual(jobs[-1].version, "0.6.0")
        finally:

            sys.path.remove(src)

    def test_demo_configs_are_fixture_first(self) -> None:
        configs = (
            (DEMO_PACKAGE / "demo-http.yml").read_text(encoding="utf-8"),
            (DEMO_PACKAGE / "demo-quality.yml").read_text(encoding="utf-8"),
            (DEMO_PACKAGE / "demo-versioned.yml").read_text(encoding="utf-8"),
            (DEMO_PACKAGE / "demo-versioned-postgres.yml").read_text(encoding="utf-8"),
            (DEMO_PACKAGE / "demo-versioned-s3.yml").read_text(encoding="utf-8"),
            (DEMO_PACKAGE / "demo-all-postgres.yml").read_text(encoding="utf-8"),
        )
        for config in configs:
            self.assertIn("fixture_mode: true", config)
            self.assertIn("workspace: .pyingest", config)


if __name__ == "__main__":
    unittest.main()
