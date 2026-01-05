from dataclasses import dataclass
from typing import List, Optional
import math


@dataclass
class Rectangle:
	"""Axis-aligned rectangle obstacle."""
	x_min: float
	y_min: float
	x_max: float
	y_max: float

	def contains_point(self, x: float, y: float) -> bool:
		"""Check if point is inside rectangle."""
		return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max


class World:
	"""
	2D world model with obstacles.
	"""

	def __init__(self, width: float = 10.0, height: float = 10.0) -> None:
		"""
		Initialize world.
		
		Parameters:
			width: World width in meters (for reference, world is unbounded).
			height: World height in meters (for reference, world is unbounded).
		"""
		self._width = width
		self._height = height
		self._obstacles: List[Rectangle] = []

	def add_obstacle(self, x_min: float, y_min: float, x_max: float, y_max: float) -> None:
		"""
		Add a rectangular obstacle to the world.
		
		Parameters:
			x_min: Minimum x coordinate.
			y_min: Minimum y coordinate.
			x_max: Maximum x coordinate.
			y_max: Maximum y coordinate.
		"""
		if x_min >= x_max or y_min >= y_max:
			raise ValueError("Invalid rectangle: min must be less than max")
		self._obstacles.append(Rectangle(x_min, y_min, x_max, y_max))

	def raycast(self, x: float, y: float, angle: float, max_distance: float = 5.0) -> float:
		"""
		Cast a ray from position (x, y) at angle and return distance to first obstacle.
		
		Parameters:
			x: Starting x position.
			y: Starting y position.
			angle: Ray angle in radians (0 = positive x direction).
			max_distance: Maximum ray distance (default: 5.0 meters).
		
		Returns:
			Distance to first obstacle, or max_distance if no obstacle found.
		"""
		dx = math.cos(angle)
		dy = math.sin(angle)
		
		closest_distance = max_distance
		
		for obstacle in self._obstacles:
			# Ray-rectangle intersection using slab method
			t_near = -float('inf')
			t_far = float('inf')
			
			if abs(dx) < 1e-9:  # Ray parallel to y-axis
				if x < obstacle.x_min or x > obstacle.x_max:
					continue
				t1 = (obstacle.y_min - y) / dy if abs(dy) > 1e-9 else 0
				t2 = (obstacle.y_max - y) / dy if abs(dy) > 1e-9 else 0
				t_near = min(t1, t2)
				t_far = max(t1, t2)
			elif abs(dy) < 1e-9:  # Ray parallel to x-axis
				if y < obstacle.y_min or y > obstacle.y_max:
					continue
				t1 = (obstacle.x_min - x) / dx
				t2 = (obstacle.x_max - x) / dx
				t_near = min(t1, t2)
				t_far = max(t1, t2)
			else:
				t1 = (obstacle.x_min - x) / dx
				t2 = (obstacle.x_max - x) / dx
				t3 = (obstacle.y_min - y) / dy
				t4 = (obstacle.y_max - y) / dy
				
				t_near = max(min(t1, t2), min(t3, t4))
				t_far = min(max(t1, t2), max(t3, t4))
			
			if t_near > t_far or t_far < 0:
				continue
			
			if t_near > 0:
				distance = t_near * math.sqrt(dx*dx + dy*dy)
			elif t_far > 0:
				distance = 0.0  # Inside obstacle
			else:
				continue
			
			if 0 <= distance < closest_distance:
				closest_distance = distance
		
		return closest_distance

	def get_obstacles(self) -> List[Rectangle]:
		"""Get list of all obstacles."""
		return self._obstacles.copy()

