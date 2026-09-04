from __future__ import annotations

import unittest

from pyingestkit import (
    Dataset,
    DatasetDiffer,
    DatasetFingerprinter,
    DiffPolicy,
    SnapshotCodec,
)
from pyingestkit.diff.report import diff_report_payload


class V040StableContractsTests(unittest.TestCase):
    def test_serialization_and_report_versions_are_frozen(self) -> None:
        self.assertEqual(DatasetFingerprinter.CODEC_VERSION, 1)
        self.assertEqual(SnapshotCodec.SNAPSHOT_VERSION, "1")

        dataset = Dataset([{"id": 1}], fields=("id",))
        diff = DatasetDiffer(DiffPolicy(key_fields=("id",))).compare(dataset, dataset)
        payload = diff_report_payload(
            diff,
            run_id="00000000-0000-0000-0000-000000000000",
            job_id="contract.v040",
            step_name="Diff",
            dataset_id="contract.v040",
        )
        self.assertEqual(payload["report_version"], "1")


if __name__ == "__main__":
    unittest.main()
