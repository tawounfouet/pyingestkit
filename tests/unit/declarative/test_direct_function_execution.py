from __future__ import annotations

import unittest

from pyingestkit import step


class DirectFunctionExecutionTests(unittest.TestCase):
    def test_fn_is_plain_unit_test_surface(self) -> None:
        @step(name="Multiply")
        def multiply(value: int, factor: int = 10) -> int:
            return value * factor

        self.assertEqual(multiply.fn(3), 30)
        self.assertEqual(multiply.fn(3, factor=2), 6)


if __name__ == "__main__":
    unittest.main()
