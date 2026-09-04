from __future__ import annotations

import math
import unittest
from datetime import UTC, date, datetime
from decimal import Decimal

from pyingestkit import Dataset, DatasetFingerprinter, DatasetFingerprintPolicy


class DatasetFingerprintTests(unittest.TestCase):
    def test_same_dataset_is_deterministic_and_does_not_mutate(self) -> None:
        dataset = Dataset([{"id": 1, "payload": {"b": 2, "a": [1, True]}}])
        before = dataset.to_rows()
        first = DatasetFingerprinter().fingerprint(dataset)
        second = DatasetFingerprinter().fingerprint(dataset)
        self.assertEqual(first, second)
        self.assertEqual(len(first.value), 64)
        self.assertTrue(first.id.startswith("sha256-"))
        self.assertEqual(dataset.to_rows(), before)

    def test_default_is_row_order_insensitive_but_strict_policy_is_not(self) -> None:
        first = Dataset([{"id": 1}, {"id": 2}])
        second = Dataset([{"id": 2}, {"id": 1}])
        self.assertEqual(
            DatasetFingerprinter().fingerprint(first).value,
            DatasetFingerprinter().fingerprint(second).value,
        )
        strict = DatasetFingerprinter(DatasetFingerprintPolicy(order_sensitive=True))
        self.assertNotEqual(strict.fingerprint(first).value, strict.fingerprint(second).value)

    def test_field_order_is_semantic(self) -> None:
        first = Dataset([{"a": 1, "b": 2}], fields=("a", "b"))
        second = Dataset([{"a": 1, "b": 2}], fields=("b", "a"))
        self.assertNotEqual(
            DatasetFingerprinter().fingerprint(first).value,
            DatasetFingerprinter().fingerprint(second).value,
        )

    def test_nested_mapping_order_is_not_semantic(self) -> None:
        first = Dataset([{"payload": {"a": 1, "b": 2}}])
        second = Dataset([{"payload": {"b": 2, "a": 1}}])
        self.assertEqual(
            DatasetFingerprinter().fingerprint(first).value,
            DatasetFingerprinter().fingerprint(second).value,
        )

    def test_type_aware_values_are_distinct(self) -> None:
        bool_dataset = Dataset([{"v": True}])
        int_dataset = Dataset([{"v": 1}])
        float_dataset = Dataset([{"v": 1.0}])
        fingerprinter = DatasetFingerprinter()
        values = {
            fingerprinter.fingerprint(bool_dataset).value,
            fingerprinter.fingerprint(int_dataset).value,
            fingerprinter.fingerprint(float_dataset).value,
        }
        self.assertEqual(len(values), 3)

    def test_supported_non_json_native_values_are_stable(self) -> None:
        values = [
            Decimal("1.2300"),
            b"abc\x00",
            date(2026, 9, 4),
            datetime(2026, 9, 4, 10, 30, tzinfo=UTC),
            float("nan"),
            float("inf"),
            float("-inf"),
            -0.0,
        ]
        for value in values:
            with self.subTest(value=repr(value)):
                first = DatasetFingerprinter().fingerprint(Dataset([{"v": value}])).value
                second = DatasetFingerprinter().fingerprint(Dataset([{"v": value}])).value
                self.assertEqual(first, second)
        self.assertTrue(math.isnan(values[4]))

    def test_unsupported_value_fails_explicitly(self) -> None:
        class Unsupported:
            pass

        with self.assertRaisesRegex(TypeError, "Unsupported canonical value type"):
            DatasetFingerprinter().fingerprint(Dataset([{"v": Unsupported()}]))


if __name__ == "__main__":
    unittest.main()
