from src.core.robot_api import RobotState

class WorldModel:
	"""
	Representation of the robot's local world
	"""

	def __init__(self, obstacle_threshold: float = 0.5) -> None:
		self._obstacle_threshold = obstacle_threshold
		self._current_state: RobotState | None = None

	def update(self, robot_state: RobotState) -> None:
		"""
		Update the world model with new sensor data.

		Parameters:
		robot_state: Current raw sensor data from the robot.
		"""
		self._current_state = robot_state

	def is_obstacle_ahead(self) -> bool:
		"""
		Check if there is an obstacle ahead.
		"""
		if self._current_state is None:
			raise RuntimeError("World model not initialized")

		return (
			self._current_state.distance_front != float("inf") and
			self._current_state.distance_front <= self._obstacle_threshold
		)


	def get_distance_to_obstacle(self) -> float:
		"""
		Get the distance to the nearest obstacle.
		"""
		if self._current_state is None:
			raise RuntimeError("World model not initialized")

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
		if self._current_state is None:
			raise RuntimeError("World model not initialized")

		return self._current_state.obstacle_left

	def is_right_blocked(self) -> bool:
		"""
		Check if the right is blocked.
		"""

		if self._current_state is None:
			raise RuntimeError("World model not initialized")

		return self._current_state.obstacle_right


	def is_path_clear(self) -> bool:
		"""
		Check if the path is clear.
		"""

		return not self.is_obstacle_ahead() and not self.is_left_blocked() and not self.is_right_blocked()


	def get_obstacle_threshold(self) -> float:
		"""
		Get the obstacle threshold.
		
		Returns:
		- float: obstacle threshold
		"""
		return self._obstacle_threshold