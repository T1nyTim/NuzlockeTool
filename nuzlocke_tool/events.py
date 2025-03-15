from collections.abc import Callable
from typing import Any

from nuzlocke_tool.models.models import EventType


class EventManager:
    def __init__(self) -> None:
        self._subscribers = {event_type: [] for event_type in EventType}

    def publish(self, event_type: EventType, data: dict[str, Any] | None = None) -> None:
        event_data = data if data is not None else {}
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                callback(event_data)

    def subscribe(self, event_type: EventType, callback: Callable[[dict[str, Any]], None]) -> None:
        if event_type in self._subscribers:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable[[dict[str, Any]], None]) -> None:
        if event_type in self._subscribers and callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)
