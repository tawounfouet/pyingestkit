from __future__ import annotations

import random
import time
from collections.abc import Callable, Collection
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import TypeVar

from tenacity import RetryCallState, Retrying, retry_if_exception, stop_after_attempt

T = TypeVar("T")
SleepFn = Callable[[float], None]
RetryPredicate = Callable[[BaseException], bool]
RetryAfterResolver = Callable[[BaseException], float | None]

DEFAULT_RETRY_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})
DEFAULT_RETRY_METHODS = frozenset({"GET", "HEAD"})


@dataclass(frozen=True, slots=True)
class RetryAttempt:
    """Information emitted immediately before a retry sleep."""

    attempt_number: int
    next_attempt_number: int
    delay_seconds: float
    exception: BaseException


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Conservative synchronous retry policy backed internally by Tenacity.

    The policy owns retry timing and default HTTP idempotency/status allowlists,
    while callers decide which concrete exceptions are retryable. This keeps
    the retry primitive reusable without coupling it to the HTTP package.
    """

    max_attempts: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    jitter: bool = True
    respect_retry_after: bool = True
    retry_status_codes: frozenset[int] = field(default_factory=lambda: DEFAULT_RETRY_STATUS_CODES)
    retry_methods: frozenset[str] = field(default_factory=lambda: DEFAULT_RETRY_METHODS)
    sleep: SleepFn = field(default=time.sleep, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.initial_delay_seconds < 0:
            raise ValueError("initial_delay_seconds must be >= 0")
        if self.max_delay_seconds < 0:
            raise ValueError("max_delay_seconds must be >= 0")
        if self.max_delay_seconds < self.initial_delay_seconds:
            raise ValueError("max_delay_seconds must be >= initial_delay_seconds")
        object.__setattr__(
            self,
            "retry_methods",
            frozenset(method.upper() for method in self.retry_methods),
        )
        object.__setattr__(self, "retry_status_codes", frozenset(self.retry_status_codes))

    def is_method_retryable(self, method: str) -> bool:
        return method.upper() in self.retry_methods

    def is_status_retryable(self, status_code: int) -> bool:
        return status_code in self.retry_status_codes

    def execute(
        self,
        operation: Callable[[], T],
        *,
        should_retry: RetryPredicate,
        retry_after: RetryAfterResolver | None = None,
        on_retry: Callable[[RetryAttempt], None] | None = None,
    ) -> T:
        """Execute an operation using Tenacity with deterministic policy boundaries."""

        if self.max_attempts == 1:
            return operation()

        def wait_strategy(state: RetryCallState) -> float:
            exception = _exception_from_state(state)
            if self.respect_retry_after and retry_after is not None and exception is not None:
                requested = retry_after(exception)
                if requested is not None:
                    return min(self.max_delay_seconds, max(0.0, requested))

            exponent = max(0, state.attempt_number - 1)
            delay = min(
                self.max_delay_seconds,
                self.initial_delay_seconds * (2**exponent),
            )
            if self.jitter and delay > 0:
                delay = min(
                    self.max_delay_seconds,
                    delay + random.uniform(0.0, self.initial_delay_seconds),
                )
            return delay

        def before_sleep(state: RetryCallState) -> None:
            if on_retry is None:
                return
            exception = _exception_from_state(state)
            if exception is None:
                return
            delay = state.next_action.sleep if state.next_action is not None else 0.0
            on_retry(
                RetryAttempt(
                    attempt_number=state.attempt_number,
                    next_attempt_number=state.attempt_number + 1,
                    delay_seconds=float(delay),
                    exception=exception,
                )
            )

        retrying = Retrying(
            stop=stop_after_attempt(self.max_attempts),
            retry=retry_if_exception(should_retry),
            wait=wait_strategy,
            before_sleep=before_sleep,
            sleep=self.sleep,
            reraise=True,
        )
        return retrying(operation)


def parse_retry_after(value: str | None, *, now: datetime | None = None) -> float | None:
    """Parse Retry-After delta-seconds or HTTP-date into a non-negative delay."""

    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None

    try:
        seconds = float(normalized)
    except ValueError:
        seconds = None
    if seconds is not None:
        return max(0.0, seconds)

    try:
        target = parsedate_to_datetime(normalized)
    except (TypeError, ValueError, OverflowError):
        return None
    if target.tzinfo is None:
        target = target.replace(tzinfo=UTC)
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return max(0.0, (target - current).total_seconds())


def _exception_from_state(state: RetryCallState) -> BaseException | None:
    if state.outcome is None or not state.outcome.failed:
        return None
    exception = state.outcome.exception()
    return exception if isinstance(exception, BaseException) else None


def normalize_methods(methods: Collection[str]) -> frozenset[str]:
    """Small public helper useful for configuration adapters."""

    return frozenset(method.upper() for method in methods)
