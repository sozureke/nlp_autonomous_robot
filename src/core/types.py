from enum import Enum

class Condition(Enum):
    """
    Symbolic conditions used by the planner to query the world model.
    """
    FRONT_BLOCKED = "front_blocked"
    LEFT_BLOCKED = "left_blocked"
    RIGHT_BLOCKED = "right_blocked"


class TurnDirection(Enum):
    """
    Symbolic turn directions used by the planner.
    """
    LEFT = "left"
    RIGHT = "right"
