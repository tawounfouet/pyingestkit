from __future__ import annotations

import unittest
from datetime import UTC, datetime

from pyingestkit import Dataset, DatasetProfiler, QualityReport, ValidationResult


class QualityReportTests(unittest.TestCase):
    def test_aggregate_is_json_oriented_without_dataset_rows(self) -> None:
        profile = DatasetProfiler().profile(Dataset([{"id": 1}]))
        report = QualityReport(
            run_id="run-1",
            job_id="demo.quality",
            source_artifact_id="raw-1",
            validation=ValidationResult(),
            profile=profile,
            generated_at=datetime(2026, 9, 4, tzinfo=UTC),
        )

        payload = report.as_dict()
        self.assertEqual(payload["report_version"], "1")
        self.assertEqual(payload["validation"]["valid"], True)
        self.assertEqual(payload["profile"]["row_count"], 1)
        self.assertNotIn("rows", repr(payload))


if __name__ == "__main__":
    unittest.main()
