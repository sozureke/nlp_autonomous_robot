from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict, Optional

from src.core.planner import Planner, Intent, IntentType


class JsonCommand(TypedDict, total=False):
    """
    High-level structured command API for the robot brain.

    This is the ONLY API that higher-level modules (LLM, UI, etc.)
    should use to request actions from the robot.
    """

    action: Literal["move_forward", "stop"]
    speed: float
    # optional semantic modifiers, will expand later
    until: Optional[Literal["obstacle_detected"]]


@dataclass
class ControlAPI:
    """
    Single entrypoint for executing high-level JSON commands.

    This layer ensures:
    - All motor commands pass through a single executor (`Planner`)
    - Higher-level modules never touch low-level robot APIs directly
    """

    planner: Planner

    # Default semantic parameters; can be made configurable later.
    default_distance_threshold: float = 0.3

    def execute_json(self, cmd: JsonCommand) -> None:
        """
        Execute a high-level JSON command via the underlying planner.

        The mapping is intentionally simple at Priority 0 and will be
        extended as higher-level abstractions appear.
        """
        action = cmd.get("action")

        if action == "move_forward":
            self._handle_move_forward(cmd)
        elif action == "stop":
            self.planner.stop()
        else:
            raise ValueError(f"Unsupported action: {action!r}")

    def _handle_move_forward(self, cmd: JsonCommand) -> None:
        speed = float(cmd.get("speed", 0.5))
        until = cmd.get("until")

        # For Priority 0 we only support a single semantic condition:
        # "move_forward until obstacle_detected"
        if until == "obstacle_detected":
            intent = Intent(
                type=IntentType.MOVE_UNTIL_OBSTACLE,
                speed=speed,
                distance_threshold=self.default_distance_threshold,
            )
        else:
            # If no semantic condition specified, we still use the same
            # MOVE_UNTIL_OBSTACLE intent with a conservative threshold.
            intent = Intent(
                type=IntentType.MOVE_UNTIL_OBSTACLE,
                speed=speed,
                distance_threshold=self.default_distance_threshold,
            )

        self.planner.execute_intent(intent)

