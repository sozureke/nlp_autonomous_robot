from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from src.core.control_api import ControlAPI, JsonCommand
from src.core.safety_controller import SafetyController
from src.nlp.llm_agent import ExternalIntentModel

if TYPE_CHECKING:
    from src.core.world_model import WorldModel
    from src.memory.memory import ShortTermMemory


@dataclass
class RobotExecutor:
    """
    High-level robot executive layer.

    Responsibility:
    - Accept structured intents or plans from LLM or other modules.
    - Map them to concrete robot actions.
    - Delegate low-level motion to the existing Planner / ControlAPI.
    - Optionally record executed steps to memory.
    - Optionally apply safety checks before each step.
    """

    control: ControlAPI
    memory: Optional["ShortTermMemory"] = None
    safety_controller: Optional[SafetyController] = None
    world_model: Optional["WorldModel"] = None

    def execute_plan(self, plan: List[Dict[str, Any]]) -> None:
        """
        Execute a sequence of high-level commands (task plan).
        """
        for i, cmd in enumerate(plan):
            safe_cmd = dict(cmd)
            if self.safety_controller is not None and self.world_model is not None:
                safe_cmd = self.safety_controller.apply(safe_cmd, self.world_model.to_dict())

            self.execute_json_command(safe_cmd)  # type: ignore[arg-type]

            if self.memory is not None:
                self.memory.add_action_event(
                    "step_done",
                    payload={
                        "step_index": i,
                        "step_total": len(plan),
                        "command": safe_cmd,
                    },
                )

    def execute_llm_intent(self, intent: ExternalIntentModel) -> None:
        """
        Entry point for LLM-produced intents.

        Converts the validated Pydantic model into a JsonCommand and
        executes it via the single underlying executor (Planner).
        """
        cmd: Dict[str, Any] = intent.to_command_dict()
        self.execute_json_command(cmd)  # type: ignore[arg-type]

    def execute_json_command(self, cmd: JsonCommand) -> None:
        """
        Entry point for already-structured JSON commands.

        This is the main integration point for non-LLM modules that
        want to drive the robot using the same high-level API.
        """
        self.control.execute_json(cmd)

