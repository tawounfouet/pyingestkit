from __future__ import annotations

import unittest

import pyingestkit
from pyingestkit.profiling import DatasetProfile, DatasetProfiler, FieldProfile
from pyingestkit.quality import QualityReport


class QualityPublicApiTests(unittest.TestCase):
    def test_a2_quality_types_are_top_level_and_namespaced(self) -> None:
        expected = {"DatasetProfile", "DatasetProfiler", "FieldProfile", "QualityReport"}
        self.assertTrue(expected.issubset(set(pyingestkit.__all__)))
        self.assertIs(pyingestkit.DatasetProfiler, DatasetProfiler)
        self.assertIs(pyingestkit.DatasetProfile, DatasetProfile)
        self.assertIs(pyingestkit.FieldProfile, FieldProfile)
        self.assertIs(pyingestkit.QualityReport, QualityReport)


if __name__ == "__main__":
    unittest.main()
