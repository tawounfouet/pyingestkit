from __future__ import annotations

import unittest

from pyingestkit import step
from pyingestkit.declarative import StepDefinition


class StepDecoratorTests(unittest.TestCase):
    def test_bare_decorator_creates_definition(self) -> None:
        @step
        def normalize(value: int) -> int:
            return value * 2

        self.assertIsInstance(normalize, StepDefinition)
        self.assertEqual(normalize.name, "normalize")
        self.assertEqual(normalize.fn(3), 6)

    def test_direct_call_outside_job_is_rejected(self) -> None:
        @step
        def normalize(value: int) -> int:
            return value

        with self.assertRaises(RuntimeError):
            normalize(1)


if __name__ == "__main__":
    unittest.main()
