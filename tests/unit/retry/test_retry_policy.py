from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

from pyingestkit.retry import RetryPolicy, parse_retry_after


class RetryPolicyTests(unittest.TestCase):
    def test_default_retry_is_conservative(self) -> None:
        policy = RetryPolicy()
        self.assertTrue(policy.is_method_retryable("GET"))
        self.assertTrue(policy.is_method_retryable("head"))
        self.assertFalse(policy.is_method_retryable("POST"))
        self.assertTrue(policy.is_status_retryable(429))
        self.assertTrue(policy.is_status_retryable(503))
        self.assertFalse(policy.is_status_retryable(404))

    def test_invalid_policy_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            RetryPolicy(max_attempts=0)
        with self.assertRaises(ValueError):
            RetryPolicy(initial_delay_seconds=2, max_delay_seconds=1)

    def test_retry_after_delta_seconds(self) -> None:
        self.assertEqual(parse_retry_after("7"), 7.0)
        self.assertEqual(parse_retry_after("-1"), 0.0)
        self.assertIsNone(parse_retry_after("not-a-date"))

    def test_retry_after_http_date(self) -> None:
        now = datetime(2026, 9, 3, 20, 0, tzinfo=UTC)
        target = now + timedelta(seconds=12)
        value = format_datetime(target, usegmt=True)
        delay = parse_retry_after(value, now=now)
        self.assertIsNotNone(delay)
        assert delay is not None
        self.assertAlmostEqual(delay, 12.0, places=3)

    def test_execute_retries_without_real_sleep(self) -> None:
        sleeps: list[float] = []
        attempts = 0
        policy = RetryPolicy(
            max_attempts=3,
            initial_delay_seconds=0.25,
            max_delay_seconds=1,
            jitter=False,
            sleep=sleeps.append,
        )

        def operation() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise RuntimeError("temporary")
            return "ok"

        result = policy.execute(operation, should_retry=lambda exc: isinstance(exc, RuntimeError))
        self.assertEqual(result, "ok")
        self.assertEqual(attempts, 3)
        self.assertEqual(sleeps, [0.25, 0.5])

    def test_retry_after_overrides_backoff_and_is_bounded(self) -> None:
        sleeps: list[float] = []
        attempts = 0
        policy = RetryPolicy(
            max_attempts=2,
            initial_delay_seconds=1,
            max_delay_seconds=4,
            jitter=False,
            sleep=sleeps.append,
        )

        def operation() -> str:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RuntimeError("retry")
            return "ok"

        self.assertEqual(
            policy.execute(
                operation,
                should_retry=lambda exc: True,
                retry_after=lambda exc: 30.0,
            ),
            "ok",
        )
        self.assertEqual(sleeps, [4.0])


if __name__ == "__main__":
    unittest.main()
