from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict, Optional

from src.core.planner import Planner, Intent, IntentType
from src.core.actions import RobotActions


class JsonCommand(TypedDict, total=False):
    """
    High-level structured command API for the robot brain.

    This is the ONLY API that higher-level modules (LLM, UI, etc.)
    should use to request actions from the robot.
    """

    action: Literal["move_forward", "stop", "turn_left", "turn_right", "scan_360"]
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

    @property
    def _actions(self) -> RobotActions:
        """
        Lazy-initialized high-level action layer bound to the same robot/world
        as the underlying planner.
        """
        # We deliberately reach into planner internals here to avoid changing
        # its public API while still keeping a single source of truth for the
        # robot and world model.
        if not hasattr(self, "__actions"):
            self.__actions = RobotActions(
                robot=self.planner._robot,  # type: ignore[attr-defined]
                world=self.planner._world_model,  # type: ignore[attr-defined]
            )
        return self.__actions

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
        elif action == "turn_left":
            self._handle_turn(left=True, cmd=cmd)
        elif action == "turn_right":
            self._handle_turn(left=False, cmd=cmd)
        elif action == "scan_360":
            self._handle_scan_360(cmd)
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

    def _handle_turn(self, left: bool, cmd: JsonCommand) -> None:
        speed = float(cmd.get("speed", 0.5))
        duration = 1.0

        if left:
            self._actions.turn_left(angular_speed=speed, duration=duration)
        else:
            self._actions.turn_right(angular_speed=speed, duration=duration)

    def _handle_scan_360(self, cmd: JsonCommand) -> None:
        speed = float(cmd.get("speed", 0.5))
        self._actions.scan_360(angular_speed=speed)

