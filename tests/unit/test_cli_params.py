from __future__ import annotations

import unittest

from pyingestkit.cli.common import parse_param_assignments


class CliParameterTests(unittest.TestCase):
    def test_repeatable_param_parses_typed_values(self) -> None:
        parsed = parse_param_assignments(
            [
                "path=sample.txt",
                "retries=3",
                "enabled=true",
            ]
        )
        self.assertEqual(parsed["path"], "sample.txt")
        self.assertEqual(parsed["retries"], 3)
        self.assertIs(parsed["enabled"], True)


if __name__ == "__main__":
    unittest.main()
