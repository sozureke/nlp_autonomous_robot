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
			Options: Condition Enum (FRONT_BLOCKED, LEFT_BLOCKED, RIGHT_BLOCKED).
		direction: Turn direction (required for CONDITIONAL_TURN).
			Options: TurnDirection Enum (LEFT, RIGHT).
		angular_speed: Angular velocity for turning (default: 0.5, range: 0.0-1.0).
	"""

	type: IntentType
	speed: float = 0.5
	target_distance: Optional[float] = None
	distance_threshold: float = 0.3
	condition: Optional[Condition] = None
	direction: Optional[TurnDirection] = None
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
			if not isinstance(self.condition, Condition):
				raise ValueError(f"condition must be a Condition enum, got {self.condition!r}")
			if self.direction is None:
				raise ValueError("direction is required for CONDITIONAL_TURN intent")
			if not isinstance(self.direction, TurnDirection):
				raise ValueError(f"direction must be a TurnDirection enum, got {self.direction!r}")


class Planner:
	"""Rule-based planner that executes intents by controlling the robot."""

	def __init__(
		self, 
		robot: BaseRobot, 
		world_model: WorldModel, 
		control_rate: float = 10.0,
		default_timeout: float = 10.0,
		stuck_threshold: float = 2.0,
	) -> None:
		"""
		Initialize the planner.

		Parameters:
			robot: Robot instance (must implement BaseRobot interface).
			world_model: World model instance for symbolic reasoning.
			control_rate: Control loop frequency in Hz (default: 10.0).
			default_timeout: Default timeout for control loops in seconds (default: 10.0).
			stuck_threshold: Time in seconds to detect stuck condition (default: 2.0).
		"""

		self._robot = robot
		self._world_model = world_model
		self._control_rate = control_rate
		self._control_period = 1.0 / control_rate
		self._default_timeout = default_timeout
		self._stuck_threshold = stuck_threshold
		self._is_running = False

	def execute_intent(self, intent: Intent) -> None:
		"""
		Execute an intent with error handling and interrupt support.
		
		Parameters:
			intent: Intent to execute.
		"""
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
			logger.info("Intent execution interrupted by user")
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

	def _move_forward_until(self, speed: float, stop_condition: Callable[[], bool], max_duration: Optional[float] = 10.0) -> None:
		"""
		Common control loop for moving forward until a condition is met,
		with a safety break for max_duration (watchdog).

		Parameters:
			speed: Linear velocity to move forward.
			stop_condition: Function that returns True when robot should stop.
			max_duration: Maximum time to spend in the control loop (seconds, default: 10.0).
		"""
		start_time = time.monotonic()
		while self._is_running:
			try:
				cur_time = time.monotonic()
				if max_duration is not None and (cur_time - start_time) > max_duration:
					logger.warning(f"Control loop timeout after {max_duration}s")
					self._robot.stop()
					break

				# Get robot state with error handling
				try:
					robot_state = self._robot.get_state()
				except Exception as e:
					logger.error(f"Failed to get robot state: {e}")
					self._robot.stop()
					break

				# Update world model with error handling
				try:
					self._world_model.update(robot_state)
				except Exception as e:
					logger.error(f"Failed to update world model: {e}")
					self._robot.stop()
					break
				
				# Check stop condition with error handling
				try:
					if stop_condition():
						self._robot.stop()
						break
				except Exception as e:
					logger.error(f"Error in stop condition: {e}")
					self._robot.stop()
					break
				
				# Send movement command with error handling
				try:
					self._robot.move(linear=speed, angular=0.0)
				except Exception as e:
					logger.error(f"Failed to send movement command: {e}")
					self._robot.stop()
					break
				
				time.sleep(self._control_period)
			except KeyboardInterrupt:
				logger.info("Control loop interrupted by user")
				self._robot.stop()
				raise
			except Exception as e:
				logger.error(f"Unexpected error in control loop: {e}")
				self._robot.stop()
				break

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

		# Calculate reasonable timeout based on distance and speed
		# Add buffer for safety
		max_distance = 10.0  # Assume max travel distance
		estimated_time = max_distance / (intent.speed * 1.0) if intent.speed > 0 else self._default_timeout
		timeout = max(estimated_time, self._default_timeout)

		def should_stop() -> bool:
			current_distance = self._world_model.get_distance_to_obstacle()
			return current_distance <= intent.target_distance

		self._move_forward_until(intent.speed, should_stop, max_duration=timeout)

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

		self._move_forward_until(intent.speed, should_stop, max_duration=self._default_timeout)

	def _check_condition(self, condition: Condition) -> bool:
		"""
		Check a condition based on world model state.

		Parameters:
			condition: Condition to check (Condition Enum: FRONT_BLOCKED, LEFT_BLOCKED, RIGHT_BLOCKED).

		Returns:
			True if condition is met, False otherwise.
		"""
		if condition == Condition.FRONT_BLOCKED:
			return self._world_model.is_front_blocked()
		elif condition == Condition.LEFT_BLOCKED:
			return self._world_model.is_left_blocked()
		elif condition == Condition.RIGHT_BLOCKED:
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
		if not isinstance(intent.condition, Condition):
			raise ValueError("condition must be a Condition enum for CONDITIONAL_TURN")
		if not isinstance(intent.direction, TurnDirection):
			raise ValueError("direction must be a TurnDirection enum for CONDITIONAL_TURN")

		try:
			robot_state = self._robot.get_state()
			self._world_model.update(robot_state)
		except Exception as e:
			logger.error(f"Failed to get initial state for conditional turn: {e}")
			self._robot.stop()
			return
		
		try:
			condition_met = self._check_condition(intent.condition)
		except Exception as e:
			logger.error(f"Failed to check condition: {e}")
			self._robot.stop()
			return
		
		if condition_met:
			# Determine angular velocity direction (Positive = left, Negative = right)
			angular_velocity = intent.angular_speed if intent.direction == TurnDirection.LEFT else -intent.angular_speed
			
			try:
				self._robot.move(linear=0.0, angular=angular_velocity)
			except Exception as e:
				logger.error(f"Failed to start turn: {e}")
				self._robot.stop()
				return
			
			turn_duration = 1.0  # seconds
			start_time = time.monotonic()
			
			while self._is_running and (time.monotonic() - start_time) < turn_duration:
				try:
					robot_state = self._robot.get_state()
					self._world_model.update(robot_state)
					
					if not self._check_condition(intent.condition):
						break
				except Exception as e:
					logger.error(f"Error during turn: {e}")
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