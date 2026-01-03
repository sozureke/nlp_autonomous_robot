from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class RobotState:
	"""
	Raw sensor data provided by the robot.

	This class represents unprocessed perception.
  It must not contain any semantic interpretation.
	"""

	distance_front: float
	obstacle_left: bool
	obstacle_right: bool

	def __post_init__(self) -> None:
		"""Validate RobotState fields."""
	
		if self.distance_front < 0:
			raise ValueError("distance_front must be non-negative")
		if not isinstance(self.obstacle_left, bool):
			raise TypeError("obstacle_left must be a boolean")
		if not isinstance(self.obstacle_right, bool):
			raise TypeError("obstacle_right must be a boolean")

class BaseRobot(ABC):
	"""
	Abstract base class defining the robot API contract.
	"""

	@abstractmethod
	def move(self, linear: float, angular: float) -> None:
		"""
		Command the robot to move.

		Parameters:
		- linear: normalized linear velocity in range [-1.0, 1.0]
		- angular: normalized angular velocity in range [-1.0, 1.0]
		"""
		pass

	@abstractmethod
	def stop(self) -> None:
		"""
		Command the robot to stop.
		"""
		pass
	

	@abstractmethod
	def get_state(self) -> RobotState:
		"""
		Get the current state of the robot.

		Returns:
		- RobotState: current sensor data
		"""
		pass