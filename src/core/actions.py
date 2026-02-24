from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from src.core.robot_api import BaseRobot
from src.core.world_model import WorldModel


@dataclass
class RobotActions:
    """
    High-level, discrete robot actions.

    This layer is intentionally decoupled from any hardware details:
    it only talks to the abstract `BaseRobot` and the `WorldModel`.

    Forbidden here:
    - direct PWM control
    - direct serial / ESP32 access
    - any hardware-specific protocol details
    """

    robot: BaseRobot
    world: WorldModel
    control_rate: float = 10.0

    @property
    def _dt(self) -> float:
        return 1.0 / self.control_rate

    def move_forward(self, speed: float = 0.5, duration: Optional[float] = None) -> None:
        """
        Move forward with a given normalized speed for an optional duration.

        If duration is None, the caller is responsible for stopping later.
        """
        start = time.monotonic()

        while True:
            if duration is not None and time.monotonic() - start >= duration:
                break

            state = self.robot.get_state()
            self.world.update(state)

            self.robot.move(linear=speed, angular=0.0)
            time.sleep(self._dt)

        self.stop()

    def turn_left(self, angular_speed: float = 0.5, duration: float = 1.0) -> None:
        """
        Turn left in place for a fixed duration.
        """
        self.robot.move(linear=0.0, angular=angular_speed)
        time.sleep(duration)
        self.stop()

    def turn_right(self, angular_speed: float = 0.5, duration: float = 1.0) -> None:
        """
        Turn right in place for a fixed duration.
        """
        self.robot.move(linear=0.0, angular=-angular_speed)
        time.sleep(duration)
        self.stop()

    def stop(self) -> None:
        """
        Immediately stop the robot.
        """
        self.robot.stop()

    def scan(self) -> None:
        """
        Simple 360-like scan in place to sample the environment.
        """
        self.turn_left(angular_speed=0.5, duration=1.0)

    def inspect_object(self) -> None:
        """
        Placeholder for a higher-level inspection behavior.

        In the future this will coordinate with vision and memory
        to approach and inspect detected objects.
        """
        pass

