import unittest

from pyingestkit.core.events import Event, EventBus, EventType, HookPolicy
from pyingestkit.core.exceptions import HookError


class EventTests(unittest.TestCase):
    def test_best_effort_hook_failure_becomes_warning(self) -> None:
        bus = EventBus()
        bus.subscribe(EventType.RUN_STARTED, lambda event: (_ for _ in ()).throw(RuntimeError("boom")))
        warnings = bus.emit(Event(EventType.RUN_STARTED, "1", "demo.events"))
        self.assertEqual(len(warnings), 1)

    def test_critical_hook_failure_raises(self) -> None:
        bus = EventBus()
        bus.subscribe(
            EventType.RUN_STARTED,
            lambda event: (_ for _ in ()).throw(RuntimeError("boom")),
            policy=HookPolicy.CRITICAL,
        )
        with self.assertRaises(HookError):
            bus.emit(Event(EventType.RUN_STARTED, "1", "demo.events"))


if __name__ == "__main__":
    unittest.main()
