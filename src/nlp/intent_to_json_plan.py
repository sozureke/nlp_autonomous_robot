from __future__ import annotations

from src.core.planner import Intent, IntentType
from src.core.types import TurnDirection


def intent_to_json_steps(intent: Intent) -> list[dict]:
    t = intent.type
    s = float(intent.speed)

    if t == IntentType.MOVE_UNTIL_OBSTACLE:
        return [{"action": "move_forward", "speed": s, "until": "obstacle_detected"}]

    if t == IntentType.CONDITIONAL_TURN:
        if intent.direction is None:
            raise ValueError("CONDITIONAL_TURN without direction")
        turn = "turn_left" if intent.direction == TurnDirection.LEFT else "turn_right"
        ang = float(intent.angular_speed)
        return [
            {"action": "move_forward", "speed": s, "until": "obstacle_detected"},
            {"action": turn, "speed": ang},
        ]

    if t == IntentType.STOP_AT_DISTANCE:
        raise ValueError(
            "STOP_AT_DISTANCE is not representable in the JSON high-level plan; "
            "extend JsonCommand or call planner.execute_intent(intent) instead"
        )

    raise ValueError(f"Unsupported intent type for JSON plan: {t!r}")
