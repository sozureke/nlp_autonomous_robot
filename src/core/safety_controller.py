from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class SafetyController:
    """
    Applies safety rules to high-level commands.
    Returns an allowed command (possibly modified or replaced with stop).
    """

    max_speed: float = 0.8
    min_distance_for_move_forward: float = 0.4

    def apply(self, cmd: Dict[str, Any], world_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Return a safe command. May cap speed, or replace move_forward with stop
        when the path is blocked or distance is below threshold.
        """
        if not cmd or cmd.get("action") == "stop":
            return dict(cmd)

        action = cmd.get("action")
        out = dict(cmd)

        if "speed" in out and out["speed"] is not None:
            try:
                speed = float(out["speed"])
                if speed > self.max_speed:
                    out["speed"] = self.max_speed
            except (TypeError, ValueError):
                out["speed"] = 0.5

        if action == "move_forward" and world_state:
            derived = world_state.get("derived") or {}
            sensors = world_state.get("sensors") or {}

            obstacle = derived.get("obstacle", False)
            path_clear = derived.get("path_clear", True)
            distance = sensors.get("distance_front", float("inf"))

            if isinstance(distance, (int, float)) and distance == float("inf"):
                distance = 999.0

            if obstacle or not path_clear or distance < self.min_distance_for_move_forward:
                return {"action": "stop"}

        return out
