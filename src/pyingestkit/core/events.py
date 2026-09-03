from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .exceptions import HookError


class EventType(str, Enum):
    RUN_STARTED = "RUN_STARTED"
    STEP_STARTED = "STEP_STARTED"
    STEP_SUCCEEDED = "STEP_SUCCEEDED"
    STEP_FAILED = "STEP_FAILED"
    RUN_SUCCEEDED = "RUN_SUCCEEDED"
    RUN_FAILED = "RUN_FAILED"


class HookPolicy(str, Enum):
    BEST_EFFORT = "BEST_EFFORT"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class Event:
    type: EventType
    run_id: str
    job_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
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
            except Exception as exc:  # hook boundary
                if subscription.policy is HookPolicy.CRITICAL:
                    raise HookError(f"Critical hook failed for {event.type}: {exc}") from exc
                warnings.append(f"Best-effort hook failed for {event.type}: {exc}")
        return tuple(warnings)
