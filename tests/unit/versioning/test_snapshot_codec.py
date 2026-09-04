from __future__ import annotations

import math
import unittest
from datetime import UTC, date, datetime
from decimal import Decimal

from pyingestkit.core.exceptions import SnapshotError
from pyingestkit.dataset import Dataset
from pyingestkit.versioning import DatasetFingerprinter, SnapshotCodec


class SnapshotCodecTests(unittest.TestCase):
    def test_round_trip_supported_values_and_sparse_rows(self) -> None:
        dataset = Dataset(
            [
                {
                    "none": None,
                    "bool": True,
                    "int": 1,
                    "float": -0.0,
                    "nan": float("nan"),
                    "str": "é",
                    "bytes": b"abc",
                    "decimal": Decimal("10.2300"),
                    "date": date(2026, 9, 4),
                    "datetime": datetime(2026, 9, 4, 10, 0, tzinfo=UTC),
                    "list": [1, "x"],
                    "tuple": (1, False),
                    "mapping": {"a": 1, 2: "b"},
                },
                {"none": None, "int": 2},
            ],
            fields=("none", "bool", "int", "float", "nan", "str", "bytes", "decimal", "date", "datetime", "list", "tuple", "mapping"),
        )
        codec = SnapshotCodec()
        restored = codec.decode(codec.encode(dataset))
        self.assertEqual(restored.fields, dataset.fields)
        self.assertEqual(set(restored[1]), {"none", "int"})
        self.assertEqual(restored[0]["decimal"], Decimal("10.2300"))
        self.assertEqual(restored[0]["bytes"], b"abc")
        self.assertTrue(math.isnan(restored[0]["nan"]))
        self.assertEqual(
            DatasetFingerprinter().fingerprint(restored).id,
            DatasetFingerprinter().fingerprint(dataset).id,
        )

    def test_unsupported_value_fails_explicitly(self) -> None:
        with self.assertRaises(SnapshotError):
            SnapshotCodec().encode(Dataset([{"value": object()}]))
