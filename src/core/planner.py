from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable
import time
import logging

from src.core.robot_api import BaseRobot
from src.core.world_model import WorldModel
from src.core.types import Condition, TurnDirection

logger = logging.getLogger(__name__)


class IntentType(Enum):
    STOP_AT_DISTANCE = "stop_at_distance"
    CONDITIONAL_TURN = "conditional_turn"
    MOVE_UNTIL_OBSTACLE = "move_until_obstacle"


@dataclass
class Intent:
    type: IntentType
    speed: float = 0.5

    # distance-based
    target_distance: Optional[float] = None
    distance_threshold: float = 0.3

    # conditional turn
    condition: Optional[Condition] = None
    direction: Optional[TurnDirection] = None
    angular_speed: float = 0.5

    def __post_init__(self) -> None:
        if not 0.0 <= self.speed <= 1.0:
            raise ValueError("speed must be in [0.0, 1.0]")
        if not 0.0 <= self.angular_speed <= 1.0:
            raise ValueError("angular_speed must be in [0.0, 1.0]")

        if self.type == IntentType.STOP_AT_DISTANCE:
            if self.target_distance is None or self.target_distance <= 0:
                raise ValueError("STOP_AT_DISTANCE requires positive target_distance")

        if self.type == IntentType.MOVE_UNTIL_OBSTACLE:
            if self.distance_threshold <= 0:
                raise ValueError("distance_threshold must be positive")

        if self.type == IntentType.CONDITIONAL_TURN:
            if self.condition is None or self.direction is None:
                raise ValueError("CONDITIONAL_TURN requires condition and direction")


class Planner:
    def __init__(
        self,
        robot: BaseRobot,
        world_model: WorldModel,
        control_rate: float = 10.0,
        default_timeout: float = 10.0,
    ) -> None:
        self._robot = robot
        self._world_model = world_model
        self._control_period = 1.0 / control_rate
        self._default_timeout = default_timeout
        self._is_running = False

    def execute_intent(self, intent: Intent) -> None:
        if self._is_running:
            self.stop()
            time.sleep(0.1)

        self._is_running = True

        try:
            handler = {
                IntentType.STOP_AT_DISTANCE: self._handle_stop_at_distance,
                IntentType.CONDITIONAL_TURN: self._handle_conditional_turn,
                IntentType.MOVE_UNTIL_OBSTACLE: self._handle_move_until_obstacle,
            }.get(intent.type)

            if handler is None:
                raise RuntimeError(f"Unsupported intent type: {intent.type}")

            logger.info(f"Executing intent: {intent.type}")
            handler(intent)

        except KeyboardInterrupt:
            logger.info("Intent interrupted by user")
            raise

        except Exception as e:
            logger.error(f"Error executing intent {intent.type}: {e}")
            raise

        finally:
            self._is_running = False
            try:
                self._robot.stop()
            except Exception as e:
                logger.error(f"Error stopping robot: {e}")

    def _move_forward_until(
        self,
        speed: float,
        stop_condition: Callable[[], bool],
        timeout: Optional[float],
    ) -> None:
        start = time.monotonic()

        while self._is_running:
            if timeout and time.monotonic() - start > timeout:
                logger.warning("Control loop timeout")
                break

            state = self._robot.get_state()
            self._world_model.update(state)

            if stop_condition():
                break

            self._robot.move(linear=speed, angular=0.0)
            time.sleep(self._control_period)

        self._robot.stop()

    def _handle_move_until_obstacle(self, intent: Intent) -> None:
        def should_stop() -> bool:
            return (
                self._world_model.get_distance_to_obstacle()
                <= intent.distance_threshold
            )

        self._move_forward_until(
            speed=intent.speed,
            stop_condition=should_stop,
            timeout=self._default_timeout,
        )

    def _handle_stop_at_distance(self, intent: Intent) -> None:
        original = self._world_model.get_obstacle_threshold()
        self._world_model._obstacle_threshold = intent.target_distance

        try:
            self._move_forward_until(
                speed=intent.speed,
                stop_condition=self._world_model.is_obstacle_ahead,
                timeout=self._default_timeout,
            )
        finally:
            self._world_model._obstacle_threshold = original

    def _handle_conditional_turn(self, intent: Intent) -> None:
        state = self._robot.get_state()
        self._world_model.update(state)

        condition_map = {
            Condition.FRONT_BLOCKED: self._world_model.is_front_blocked,
            Condition.LEFT_BLOCKED: self._world_model.is_left_blocked,
            Condition.RIGHT_BLOCKED: self._world_model.is_right_blocked,
        }

        if not condition_map[intent.condition]():
            return

        angular = (
            intent.angular_speed
            if intent.direction == TurnDirection.LEFT
            else -intent.angular_speed
        )

        self._robot.move(0.0, angular)
        time.sleep(1.0)
        self._robot.stop()

    def stop(self) -> None:
        self._is_running = False
        try:
            self._robot.stop()
        except Exception:
            pass

    def is_running(self) -> bool:
        return self._is_running
