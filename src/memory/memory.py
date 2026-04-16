from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional


Event = Dict[str, Any]


@dataclass
class ShortTermMemory:
    """
    Short-term memory for the robot.
    """

    max_events: int = 50
    _events: Deque[Event] = field(init=False)

    def __post_init__(self) -> None:
        self._events = deque(maxlen=self.max_events)

    def add_event(self, event: Event) -> None:
        """
        Append a new event to memory.

        """
        self._events.append(event)

    def last_event(self) -> Optional[Event]:
        """
        Return the most recent event, if any.
        """
        return self._events[-1] if self._events else None

    def last_object_event(self) -> Optional[Event]:
        """
        Return the most recent perception event related to an object, if any.
        """
        for ev in reversed(self._events):
            if ev.get("type") == "perception" and ev.get("name") == "object_detected":
                return ev
        return None

    def to_dict(self) -> Dict[str, Any]:
        """
        Export memory contents as a JSON-serializable dict for LLM context.
        """
        return {
            "events": list(self._events),
            "summary": {
                "total_events": len(self._events),
            },
        }

    def add_action_event(self, name: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a high-level action execution.
        """
        self.add_event(
            {
                "type": "action",
                "name": name,
                "payload": payload or {},
            }
        )

    def add_perception_event(self, name: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a perception-related event (e.g., vision or fused detection).
        """
        self.add_event(
            {
                "type": "perception",
                "name": name,
                "payload": payload or {},
            }
        )

    def events_since(self, offset: int = 0, limit: Optional[int] = None) -> List[Event]:
        """
        Return events from offset with optional limit.
        """
        events = list(self._events)
        if offset < 0:
            offset = 0
        sliced = events[offset:]
        if limit is not None:
            return sliced[:limit]
        return sliced

