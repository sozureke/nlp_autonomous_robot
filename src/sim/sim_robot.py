import math
import time

from src.core.robot_api import BaseRobot, RobotState
from src.sim.world import World

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
		"""
		self._world = world
		self._x = initial_x
		self._y = initial_y
		self._theta = initial_theta
		self._max_linear_velocity = max_linear_velocity
		self._max_angular_velocity = max_angular_velocity
		self._sensor_range = sensor_range
		self._obstacle_threshold = obstacle_threshold
		self._update_period = 1.0 / update_rate

		self._linear_velocity = 0.0
		self._angular_velocity = 0.0
		
		self._last_update_time = time.time()


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

	def _update_physics(self) -> None:
		"""Update robot physics based on current velocities."""
		current_time = time.time()
		dt = current_time - self._last_update_time
		
		if dt < self._update_period:
			return
		
		# Update orientation
		angular_velocity_rad = self._angular_velocity * self._max_angular_velocity
		self._theta += angular_velocity_rad * dt
		self._theta = math.atan2(math.sin(self._theta), math.cos(self._theta))  # Normalize to [-pi, pi]
		
		# Update position
		linear_velocity_ms = self._linear_velocity * self._max_linear_velocity
		dx = linear_velocity_ms * math.cos(self._theta) * dt
		dy = linear_velocity_ms * math.sin(self._theta) * dt
		
		self._x += dx
		self._y += dy
		
		self._last_update_time = current_time

	def get_position(self) -> tuple[float, float, float]:
		"""
		Get current robot position and orientation.
		
		Returns:
			Tuple of (x, y, theta) in meters and radians.
		"""
		self._update_physics()
		return (self._x, self._y, self._theta)
