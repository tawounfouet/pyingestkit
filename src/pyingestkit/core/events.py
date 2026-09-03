from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from .exceptions import HookError


class EventType(StrEnum):
    RUN_STARTED = "RUN_STARTED"
    STEP_STARTED = "STEP_STARTED"
    STEP_SUCCEEDED = "STEP_SUCCEEDED"
    STEP_FAILED = "STEP_FAILED"
    VALIDATION_COMPLETED = "VALIDATION_COMPLETED"
    PUBLISH_STARTED = "PUBLISH_STARTED"
    PUBLISH_SUCCEEDED = "PUBLISH_SUCCEEDED"
    PUBLISH_FAILED = "PUBLISH_FAILED"
    RUN_SUCCEEDED = "RUN_SUCCEEDED"
    RUN_FAILED = "RUN_FAILED"


class HookPolicy(StrEnum):
    BEST_EFFORT = "BEST_EFFORT"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class Event:
    type: EventType
    run_id: str
    job_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = field(default_factory=dict)


EventCallback = Callable[[Event], None]


@dataclass(frozen=True, slots=True)
class _Subscription:
    callback: EventCallback
    policy: HookPolicy


class EventBus:
    def __init__(self) -> None:
        self._subscriptions: dict[EventType, list[_Subscription]] = defaultdict(list)

    def subscribe(
        self,
        event_type: EventType,
        callback: EventCallback,
        *,
        policy: HookPolicy = HookPolicy.BEST_EFFORT,
    ) -> None:
        self._subscriptions[event_type].append(_Subscription(callback, policy))

    def emit(self, event: Event) -> tuple[str, ...]:
        warnings: list[str] = []
        for subscription in self._subscriptions.get(event.type, []):
            try:
                subscription.callback(event)
            except Exception as exc:  # noqa: BLE001 - user hook isolation boundary
                if subscription.policy is HookPolicy.CRITICAL:
                    raise HookError(f"Critical hook failed for {event.type}: {exc}") from exc
                warnings.append(f"Best-effort hook failed for {event.type}: {exc}")
        return tuple(warnings)
