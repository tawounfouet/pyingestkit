from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from pyingestkit import CsvParser, DatasetContract, FieldContract, JsonParser
from pyingestkit.artifacts import LocalArtifactStore


class RawParserContractIntegrationTests(unittest.TestCase):
    def test_csv_raw_to_dataset_to_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalArtifactStore(tmp)
            artifact = store.write_raw(
                "demo.csv",
                uuid4(),
                name="people.csv",
                data=b"id,name\n001,Alice\n002,Bob\n",
                source_uri="https://example.test/people.csv",
                content_type="text/csv",
            )

            dataset = CsvParser().parse(artifact)
            result = DatasetContract(
                fields=(
                    FieldContract("id", nullable=False, expected_type=str, unique=True),
                    FieldContract("name", nullable=False, expected_type=str),
                ),
                allow_extra_fields=False,
                min_rows=2,
            ).validate(dataset)

            self.assertEqual(dataset.source_artifact_id, artifact.artifact_id)
            self.assertTrue(result.is_valid)
            self.assertEqual(dataset[0]["id"], "001")

    def test_json_raw_to_dataset_preserves_raw_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalArtifactStore(tmp)
            raw_bytes = b'[{"id": 1, "enabled": true}]'
            artifact = store.write_raw(
                "demo.json",
                uuid4(),
                name="data.json",
                data=raw_bytes,
                source_uri="https://example.test/data.json",
                content_type="application/json",
            )

            dataset = JsonParser().parse(artifact)

            self.assertEqual(dataset.source_artifact_id, artifact.artifact_id)
            self.assertEqual(Path(artifact.path).read_bytes(), raw_bytes)
            self.assertEqual(dataset.to_rows(), [{"id": 1, "enabled": True}])


if __name__ == "__main__":
    unittest.main()
