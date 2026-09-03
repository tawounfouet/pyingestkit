from __future__ import annotations

import unittest

from pyingestkit import job, step
from pyingestkit.declarative import StepInvocation


class StepInvocationTests(unittest.TestCase):
    def test_same_definition_can_have_multiple_invocations(self) -> None:
        captured: list[StepInvocation] = []

        @step
        def echo(value: str, data=None):
            return value

        @job(id="demo.invocations")
        def pipeline() -> None:
            captured.append(echo("a"))
            captured.append(echo("b"))

        pipeline.build()
        self.assertEqual(len(captured), 2)
        self.assertIs(captured[0].definition, captured[1].definition)
        self.assertEqual(captured[0].args, ("a",))
        self.assertEqual(captured[1].args, ("b",))


if __name__ == "__main__":
    unittest.main()
