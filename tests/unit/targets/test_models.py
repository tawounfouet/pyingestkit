from __future__ import annotations

import unittest

from pyingestkit import Dataset
from pyingestkit.targets import IdempotencyPolicy, LoadMode, TargetLoadRequest


class TargetModelTests(unittest.TestCase):
    def test_request_freezes_options_and_metadata(self) -> None:
        dataset = Dataset([{"id": 1}], fields=("id",))
        options = {"batch_size": 100}
        metadata = {"owner": "demo"}
        request = TargetLoadRequest(
            target_id="postgres.demo",
            dataset_id="demo.dataset",
            run_id="run-1",
            dataset=dataset,
            table="demo_dataset",
            mode=LoadMode.APPEND,
            key_fields=("id",),
            options=options,
            metadata=metadata,
        )
        options["batch_size"] = 1
        metadata["owner"] = "changed"
        self.assertEqual(request.options["batch_size"], 100)
        self.assertEqual(request.metadata["owner"], "demo")

    def test_request_rejects_dsn_as_target_id(self) -> None:
        dataset = Dataset([], fields=("id",))
        with self.assertRaises(ValueError):
            TargetLoadRequest(
                target_id="postgresql://user:secret@host/db",
                dataset_id="demo.dataset",
                run_id="run-1",
                dataset=dataset,
                table="demo_dataset",
            )

    def test_request_rejects_unknown_key_fields(self) -> None:
        dataset = Dataset([{"id": 1}], fields=("id",))
        with self.assertRaises(ValueError):
            TargetLoadRequest(
                target_id="postgres.demo",
                dataset_id="demo.dataset",
                run_id="run-1",
                dataset=dataset,
                table="demo_dataset",
                key_fields=("missing",),
            )

    def test_require_version_idempotency_policy_rejects_unversioned_request(self) -> None:
        dataset = Dataset([{"id": 1}], fields=("id",))
        with self.assertRaisesRegex(ValueError, "dataset_version_id is required"):
            TargetLoadRequest(
                target_id="postgres.demo",
                dataset_id="demo.dataset",
                run_id="run-1",
                dataset=dataset,
                table="demo_dataset",
                idempotency_policy=IdempotencyPolicy.REQUIRE_VERSION,
            )


if __name__ == "__main__":
    unittest.main()
