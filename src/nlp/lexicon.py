from src.core.types import Condition, TurnDirection


MOVEMENT_VERBS = {
    "move", "go", "drive", "travel", "advance", "proceed", "head"
}

STOP_WORDS = {"stop", "halt", "cease"}

OBSTACLE_WORDS = {
    "obstacle", "wall", "barrier", "block", "object", "thing"
}

UNTIL_WORDS = {"until", "before", "when"}

DISTANCE_UNITS = {
    "meter": 1.0, "meters": 1.0, "m": 1.0,
    "centimeter": 0.01, "centimeters": 0.01, "cm": 0.01,
    "foot": 0.3048, "feet": 0.3048, "ft": 0.3048,
    "inch": 0.0254, "inches": 0.0254, "in": 0.0254,
}

FRACTIONS = {
    "half": 0.5,
    "quarter": 0.25,
    "third": 1.0 / 3.0,
}

SPEED_WORDS = {
    "slow": 0.3, "slowly": 0.3,
    "fast": 0.8, "quickly": 0.8,
    "normal": 0.5, "medium": 0.5,
}

DIRECTION_WORDS = {
    "left": TurnDirection.LEFT,
    "right": TurnDirection.RIGHT,
}

CONDITION_KEYWORDS = {
    Condition.FRONT_BLOCKED: {"front", "ahead", "forward", "straight"},
    Condition.LEFT_BLOCKED: {"left"},
    Condition.RIGHT_BLOCKED: {"right"},
}
