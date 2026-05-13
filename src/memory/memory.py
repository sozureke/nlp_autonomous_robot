from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
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


@dataclass
class MetricsCollector:
    """
    Lightweight in-memory metrics for command execution sessions.
    """

    total_commands: int = 0
    completed_commands: int = 0
    interrupted_commands: int = 0
    failed_commands: int = 0
    total_safety_violations: int = 0
    by_mode: Dict[str, int] = field(default_factory=dict)
    by_source: Dict[str, int] = field(default_factory=dict)
    last_command: Optional[str] = None
    last_error: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def record_command(
        self,
        *,
        command: str,
        mode: str,
        source: str,
    ) -> None:
        self.total_commands += 1
        self.last_command = command
        self.by_mode[mode] = self.by_mode.get(mode, 0) + 1
        self.by_source[source] = self.by_source.get(source, 0) + 1
        self._touch()

    def record_result(
        self,
        *,
        status: str,
        safety_violations: int = 0,
        error: Optional[str] = None,
    ) -> None:
        if status == "completed":
            self.completed_commands += 1
        elif status == "interrupted":
            self.interrupted_commands += 1
        elif status == "failed":
            self.failed_commands += 1
        self.total_safety_violations += max(0, int(safety_violations))
        if error:
            self.last_error = error
        self._touch()

    def snapshot(self) -> Dict[str, Any]:
        return {
            "total_commands": self.total_commands,
            "completed_commands": self.completed_commands,
            "interrupted_commands": self.interrupted_commands,
            "failed_commands": self.failed_commands,
            "total_safety_violations": self.total_safety_violations,
            "by_mode": dict(self.by_mode),
            "by_source": dict(self.by_source),
            "last_command": self.last_command,
            "last_error": self.last_error,
            "updated_at": self.updated_at,
        }

    def reset(self) -> Dict[str, Any]:
        self.total_commands = 0
        self.completed_commands = 0
        self.interrupted_commands = 0
        self.failed_commands = 0
        self.total_safety_violations = 0
        self.by_mode = {}
        self.by_source = {}
        self.last_command = None
        self.last_error = None
        self._touch()
        return self.snapshot()

    def _touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

