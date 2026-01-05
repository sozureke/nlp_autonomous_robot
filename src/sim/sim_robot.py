import math
import time
import logging

from src.core.robot_api import BaseRobot, RobotState
from src.sim.world import World

logger = logging.getLogger(__name__)


class SimRobot(BaseRobot):
	"""
	Simulated robot with 2D physics and sensor emulation.
	"""

	def __init__(
		self,
		world: World,
		initial_x: float = 0.0,
		initial_y: float = 0.0,
		initial_theta: float = 0.0,
		max_linear_velocity: float = 1.0,
		max_angular_velocity: float = 1.0,
		sensor_range: float = 5.0,
		obstacle_threshold: float = 0.3,
		update_rate: float = 20.0,
		robot_radius: float = 0.1,
	) -> None:
		"""
		Initialize simulated robot.
		
		Parameters:
			world: World instance containing obstacles.
			initial_x: Initial x position in meters.
			initial_y: Initial y position in meters.
			initial_theta: Initial orientation in radians (0 = positive x direction).
			max_linear_velocity: Maximum linear velocity in m/s.
			max_angular_velocity: Maximum angular velocity in rad/s.
			sensor_range: Maximum sensor range in meters.
			obstacle_threshold: Distance threshold for obstacle detection in meters.
			update_rate: Physics update rate in Hz.
			robot_radius: Robot collision radius in meters (for collision detection).
		"""
		self._world = world
		self._x = initial_x
		self._y = initial_y
		self._theta = initial_theta
		self._max_linear_velocity = max_linear_velocity
		self._max_angular_velocity = max_angular_velocity
		self._sensor_range = sensor_range
		self._obstacle_threshold = obstacle_threshold
		self._robot_radius = robot_radius
		self._update_period = 1.0 / update_rate

		self._linear_velocity = 0.0
		self._angular_velocity = 0.0
		
		# Use monotonic time for better precision and immunity to clock adjustments
		self._last_update_time = time.monotonic()
		
		# Check initial position is valid
		if self._check_collision(self._x, self._y):
			logger.warning(
				f"Robot initialized inside obstacle at ({initial_x:.2f}, {initial_y:.2f})"
			)


	def move(self, linear: float, angular: float) -> None:
		"""
		Command the robot to move.
		
		Parameters:
			linear: Normalized linear velocity in range [-1.0, 1.0].
			angular: Normalized angular velocity in range [-1.0, 1.0].
		"""
		if not -1.0 <= linear <= 1.0:
			raise ValueError(f"linear must be in [-1.0, 1.0], got {linear}")
		if not -1.0 <= angular <= 1.0:
			raise ValueError(f"angular must be in [-1.0, 1.0], got {angular}")
		
		self._linear_velocity = linear
		self._angular_velocity = angular
		self._update_physics()

	def stop(self) -> None:
		"""Command the robot to stop."""
		self._linear_velocity = 0.0
		self._angular_velocity = 0.0

	def get_state(self) -> RobotState:
		"""
		Get the current state of the robot.
		
		Returns:
			RobotState: Current sensor data.
		"""
		self._update_physics()
		
		# Ray cast forward
		distance_front = self._world.raycast(
			self._x, self._y, self._theta, self._sensor_range
		)
		
		# Ray cast left (theta + 90 degrees)
		distance_left = self._world.raycast(
			self._x, self._y, self._theta + math.pi / 2, self._sensor_range
		)
		
		# Ray cast right (theta - 90 degrees)
		distance_right = self._world.raycast(
			self._x, self._y, self._theta - math.pi / 2, self._sensor_range
		)
		
		# Convert distances to boolean obstacle flags
		obstacle_left = distance_left < self._obstacle_threshold
		obstacle_right = distance_right < self._obstacle_threshold
		
		# If no obstacle found, set distance to infinity
		if distance_front >= self._sensor_range:
			distance_front = float('inf')
		
		state = RobotState(
			distance_front=distance_front,
			obstacle_left=obstacle_left,
			obstacle_right=obstacle_right,
		)
				
		return state

	def _check_collision(self, x: float, y: float) -> bool:
		"""
		Check if a position would cause a collision with obstacles.
		
		Parameters:
			x: X coordinate to check.
			y: Y coordinate to check.
		
		Returns:
			True if collision detected, False otherwise.
		"""
		# Check collision with all obstacles
		for obstacle in self._world.get_obstacles():
			# Expand obstacle by robot radius for collision detection
			expanded_x_min = obstacle.x_min - self._robot_radius
			expanded_y_min = obstacle.y_min - self._robot_radius
			expanded_x_max = obstacle.x_max + self._robot_radius
			expanded_y_max = obstacle.y_max + self._robot_radius
			
			if (expanded_x_min <= x <= expanded_x_max and 
				expanded_y_min <= y <= expanded_y_max):
				return True
		return False

	def _update_physics(self) -> None:
		"""Update robot physics based on current velocities with collision detection."""
		current_time = time.monotonic()
		dt = current_time - self._last_update_time
		
		if dt < self._update_period:
			return
		
		# Update orientation (rotation doesn't cause collisions)
		angular_velocity_rad = self._angular_velocity * self._max_angular_velocity
		self._theta += angular_velocity_rad * dt
		self._theta = math.atan2(math.sin(self._theta), math.cos(self._theta))  # Normalize to [-pi, pi]
		
		# Calculate new position
		linear_velocity_ms = self._linear_velocity * self._max_linear_velocity
		dx = linear_velocity_ms * math.cos(self._theta) * dt
		dy = linear_velocity_ms * math.sin(self._theta) * dt
		
		new_x = self._x + dx
		new_y = self._y + dy
		
		# Check for collision before updating position
		if self._check_collision(new_x, new_y):
			# Collision detected - stop movement
			logger.warning(
				f"Collision detected at ({new_x:.2f}, {new_y:.2f}). "
				f"Stopping movement from ({self._x:.2f}, {self._y:.2f})"
			)
			self._linear_velocity = 0.0
			self._angular_velocity = 0.0
		else:
			# Safe to move
			self._x = new_x
			self._y = new_y
		
		self._last_update_time = current_time

	def get_position(self) -> tuple[float, float, float]:
		"""
		Get current robot position and orientation.
		
		Returns:
			Tuple of (x, y, theta) in meters and radians.
		"""
		self._update_physics()
		return (self._x, self._y, self._theta)
