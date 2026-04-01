from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List

from src.core.robot_api import BaseRobot
from src.core.world_model import WorldModel


@dataclass
class DirectExecutor:
    """
    Baseline executor that applies commands directly without safety or symbolic control.
    """

    robot: BaseRobot
    world: WorldModel
    move_forward_duration: float = 2.0
    turn_duration: float = 1.0
    scan_360_duration: float = 3.0

    def execute_plan(self, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        safety_violations = 0
        success = True

        try:
            for cmd in plan:
                action = cmd.get("action")
                speed = max(0.0, min(1.0, float(cmd.get("speed", 0.5))))

                state = self.robot.get_state()
                self.world.update(state)

                if action == "move_forward":
                    if self.world.is_obstacle_ahead():
                        safety_violations += 1
                        self.robot.stop()
                    else:
                        self.robot.move(linear=speed, angular=0.0)
                        time.sleep(self.move_forward_duration)
                        self.robot.stop()
                elif action == "turn_left":
                    self.robot.move(linear=0.0, angular=speed)
                    time.sleep(self.turn_duration)
                    self.robot.stop()
                elif action == "turn_right":
                    self.robot.move(linear=0.0, angular=-speed)
                    time.sleep(self.turn_duration)
                    self.robot.stop()
                elif action == "scan_360":
                    self.robot.move(linear=0.0, angular=speed)
                    time.sleep(self.scan_360_duration)
                    self.robot.stop()
                else:
                    self.robot.stop()
        except Exception:
            success = False
        finally:
            try:
                self.robot.stop()
            except Exception:
                pass

        return {
            "safety_violations": safety_violations,
            "success": success,
        }
