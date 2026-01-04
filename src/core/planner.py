from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable
import time

from src.core.robot_api import BaseRobot
from src.core.world_model import WorldModel

class IntentType(Enum):
	"""Types of supported intents types."""

	STOP_AT_DISTANCE = "stop_at_distance"
	CONDITIONAL_TURN = "conditional_turn"
	MOVE_UNTIL_OBSTACLE = "move_until_obstacle"


@dataclass
class Intent:
	"""
	User intent with type and parameters.

	Parameters:
		type: The type of intent to execute.
		speed: Linear velocity (default: 0.5, range: 0.0-1.0).
		target_distance: Target distance to obstacle in meters (required for STOP_AT_DISTANCE).
		condition: Condition to check (required for CONDITIONAL_TURN).
			Options: "front_blocked", "left_blocked", "right_blocked".
		direction: Turn direction (required for CONDITIONAL_TURN).
			Options: "left", "right".
		angular_speed: Angular velocity for turning (default: 0.5, range: 0.0-1.0).
	"""

	type: IntentType
	speed: float = 0.5
	target_distance: Optional[float] = None
	distance_threshold: float = 0.3
	condition: Optional[str] = None
	direction: Optional[str] = None
	angular_speed: float = 0.5

	def __post_init__(self) -> None:
		"""Validate intent parameters."""
	
		if not 0.0 <= self.speed <= 1.0:
			raise ValueError(f"speed must be in [0.0, 1.0], got {self.speed}")
		if not 0.0 <= self.angular_speed <= 1.0:
			raise ValueError(f"angular_speed must be in [0.0, 1.0], got {self.angular_speed}")
		if self.distance_threshold <= 0:
			raise ValueError("distance_threshold must be positive")
		
		if self.type == IntentType.STOP_AT_DISTANCE:
			if self.target_distance is None:
				raise ValueError("target_distance is required for STOP_AT_DISTANCE intent")
			if self.target_distance <= 0:
				raise ValueError("target_distance must be positive")
		
		if self.type == IntentType.CONDITIONAL_TURN:
			if self.condition is None:
				raise ValueError("condition is required for CONDITIONAL_TURN intent")
			if self.condition not in ["front_blocked", "left_blocked", "right_blocked"]:
				raise ValueError(f"condition must be one of: front_blocked, left_blocked, right_blocked, got {self.condition}")
			if self.direction is None:
				raise ValueError("direction is required for CONDITIONAL_TURN intent")
			if self.direction not in ["left", "right"]:
				raise ValueError(f"direction must be 'left' or 'right', got {self.direction}")


class Planner:
	"""Rule-based planner that executes intents by controlling the robot."""

	def __init__(self, robot: BaseRobot, world_model: WorldModel, control_rate: float = 10.0) -> None:
		"""
		Initialize the planner.

		Parameters:
			robot: Robot instance (must implement BaseRobot interface).
			world_model: World model instance for symbolic reasoning.
			control_rate: Control loop frequency in Hz (default: 10.0).
		"""

		self._robot = robot
		self._world_model = world_model
		self._control_rate = control_rate
		self._control_period = 1.0 / control_rate
		self._is_running = False


	def execute_intent(self, intent: Intent) -> None:
		self._is_running = True

		try:
			handler = {
				IntentType.STOP_AT_DISTANCE: self._handle_stop_at_distance,
				IntentType.CONDITIONAL_TURN: self._handle_conditional_turn,
				IntentType.MOVE_UNTIL_OBSTACLE: self._handle_move_until_obstacle,
			}.get(intent.type)
			if handler is None:
				raise RuntimeError(f"Unsupported intent type: {intent.type}")
			handler(intent)
		finally:
			self._is_running = False
			self._robot.stop()

	def _move_forward_until(self, speed: float, stop_condition: Callable[[], bool]) -> None:
		"""
		Common control loop for moving forward until a condition is met.

		Parameters:
			speed: Linear velocity to move forward.
			stop_condition: Function that returns True when robot should stop.
		"""
		while self._is_running:
			robot_state = self._robot.get_state()
			self._world_model.update(robot_state)
			
			if stop_condition():
				self._robot.stop()
				break
			
			self._robot.move(linear=speed, angular=0.0)
			time.sleep(self._control_period)

	def _handle_stop_at_distance(self, intent: Intent) -> None:
		"""
		Handle STOP_AT_DISTANCE intent.

		Rule: Move forward at specified speed until distance to obstacle
		is less than or equal to target_distance, then stop.

		Parameters:
			intent: Intent with type STOP_AT_DISTANCE.
		"""
		if intent.target_distance is None:
			raise ValueError("target_distance is required for STOP_AT_DISTANCE")

		def should_stop() -> bool:
			current_distance = self._world_model.get_distance_to_obstacle()
			return current_distance <= intent.target_distance

		self._move_forward_until(intent.speed, should_stop)

	def _handle_move_until_obstacle(self, intent: Intent) -> None:
		"""
		Handle MOVE_UNTIL_OBSTACLE intent.

		Rule: Move forward at specified speed, constantly checking world state.
		When obstacle is detected closer than distance_threshold, stop.

		Parameters:
			intent: Intent with type MOVE_UNTIL_OBSTACLE.
		"""
		def should_stop() -> bool:
			current_distance = self._world_model.get_distance_to_obstacle()
			return current_distance != float('inf') and current_distance <= intent.distance_threshold

		self._move_forward_until(intent.speed, should_stop)

	def _check_condition(self, condition: str) -> bool:
		"""
		Check a condition based on world model state.

		Parameters:
			condition: Condition to check ("front_blocked", "left_blocked", "right_blocked").

		Returns:
			True if condition is met, False otherwise.
		"""
		if condition == "front_blocked":
			return self._world_model.is_front_blocked()
		elif condition == "left_blocked":
			return self._world_model.is_left_blocked()
		elif condition == "right_blocked":
			return self._world_model.is_right_blocked()
		else:
			raise ValueError(f"Unknown condition: {condition}")

	def _handle_conditional_turn(self, intent: Intent) -> None:
		"""
		Handle CONDITIONAL_TURN intent.

		Rule: Check condition. If condition is true, turn in specified
		direction at specified angular speed. Otherwise, do nothing.

		Parameters:
			intent: Intent with type CONDITIONAL_TURN.
		"""
		if intent.condition is None or intent.direction is None:
			raise ValueError("condition and direction are required for CONDITIONAL_TURN")

		robot_state = self._robot.get_state()
		self._world_model.update(robot_state)
		
		condition_met = self._check_condition(intent.condition)
		
		if condition_met:
			# Determine angular velocity direction (Positive = left, Negative = right)
			angular_velocity = intent.angular_speed if intent.direction == "left" else -intent.angular_speed
			
			self._robot.move(linear=0.0, angular=angular_velocity)
			
			turn_duration = 1.0  # seconds
			start_time = time.time()
			
			while self._is_running and (time.time() - start_time) < turn_duration:
				robot_state = self._robot.get_state()
				self._world_model.update(robot_state)
				
				if not self._check_condition(intent.condition):
					break
				
				time.sleep(self._control_period)
			
			self._robot.stop()
		else:
			self._robot.stop()

	def stop(self) -> None:
		"""Stop the planner and halt robot movement."""
		self._is_running = False
		self._robot.stop()

	def is_running(self) -> bool:
		"""Check if planner is currently executing an intent."""
		return self._is_running