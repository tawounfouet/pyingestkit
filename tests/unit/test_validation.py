import unittest

from pyingestkit.validation import MinimumRows, RequiredField, UniqueField, validate


class ValidationTests(unittest.TestCase):
    def test_valid_rows(self) -> None:
        rows = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        report = validate(rows, [MinimumRows(2), RequiredField("name"), UniqueField("id")])
        self.assertTrue(report.is_valid)
        self.assertEqual(report.error_count, 0)

    def test_duplicate_fails(self) -> None:
        rows = [{"id": 1}, {"id": 1}]
        report = validate(rows, [UniqueField("id")])
        self.assertFalse(report.is_valid)
        self.assertEqual(report.error_count, 1)


if __name__ == "__main__":
    unittest.main()
