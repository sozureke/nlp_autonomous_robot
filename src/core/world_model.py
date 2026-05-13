from __future__ import annotations
from typing import Any, Dict, Optional
from src.core.robot_api import RobotState


class WorldModel:
    """
    Representation of the robot's local world.
    """

    def __init__(self, obstacle_threshold: float = 0.08) -> None:
        """
        Initialize world model.

        Parameters:
            obstacle_threshold: Distance threshold for obstacle detection in meters.
        """
        self._obstacle_threshold = obstacle_threshold
        self._current_state = RobotState(
            distance_front=float("inf"),
            obstacle_left=False,
            obstacle_right=False,
        )

        # Internal robot state (non-sensor information)
        self._is_moving: bool = False
        self._last_action: Optional[str] = None

    def update(self, robot_state: RobotState) -> None:
        """
        Update the world model with new sensor data.

        Parameters:
            robot_state: Current raw sensor data from the robot.
        """
        self._current_state = robot_state


    def set_internal_state(self, *, moving: Optional[bool] = None, last_action: Optional[str] = None) -> None:
        """
        Update internal robot state such as movement flag and last action label.
        """
        if moving is not None:
            self._is_moving = moving
        if last_action is not None:
            self._last_action = last_action

    def is_obstacle_ahead(self) -> bool:
        """
        Check if there is an obstacle ahead.
        """
        return (
            self._current_state.distance_front != float("inf")
            and self._current_state.distance_front <= self._obstacle_threshold
        )

    def get_distance_to_obstacle(self) -> float:
        """
        Get the distance to the nearest obstacle.
        """
        return self._current_state.distance_front

    def is_front_blocked(self) -> bool:
        """
        Check if the front is blocked.
        """
        return self.is_obstacle_ahead()

    def is_left_blocked(self) -> bool:
        """
        Check if the left is blocked.
        """
        return self._current_state.obstacle_left

    def is_right_blocked(self) -> bool:
        """
        Check if the right is blocked.
        """
        return self._current_state.obstacle_right

    def is_path_clear(self) -> bool:
        """
        Check if the path is clear.
        """
        return (
            not self.is_obstacle_ahead()
            and not self.is_left_blocked()
            and not self.is_right_blocked()
        )

    def get_obstacle_threshold(self) -> float:
        """
        Get the obstacle threshold.

        Returns:
            float: obstacle threshold
        """
        return self._obstacle_threshold

    def to_dict(self) -> Dict[str, Any]:
        """
        Export the current world state as a JSON-serializable dict suitable for LLM context.
        """
        return {
            # raw sensor data
            "sensors": {
                "distance_front": self._current_state.distance_front,
                "obstacle_left": self._current_state.obstacle_left,
                "obstacle_right": self._current_state.obstacle_right,
            },
            # derived flags
            "derived": {
                "obstacle": self.is_obstacle_ahead(),
                "path_clear": self.is_path_clear(),
                "front_blocked": self.is_front_blocked(),
                "left_blocked": self.is_left_blocked(),
                "right_blocked": self.is_right_blocked(),
                "obstacle_threshold": self._obstacle_threshold,
            },
            # internal robot state
            "internal": {
                "moving": self._is_moving,
                "last_action": self._last_action,
            },
        }