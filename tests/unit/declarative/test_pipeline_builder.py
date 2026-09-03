from __future__ import annotations

import unittest

from pyingestkit import job, step


class PipelineBuilderTests(unittest.TestCase):
    def test_preserves_declaration_order(self) -> None:
        @step
        def one(data=None):
            return data

        @step
        def two(data=None):
            return data

        @job(id="demo.order")
        def pipeline() -> None:
            one()
            two()
            one()

        self.assertEqual(
            [item.step_name for item in pipeline.build().pipeline()],
            ["one", "two", "one"],
        )


if __name__ == "__main__":
    unittest.main()
