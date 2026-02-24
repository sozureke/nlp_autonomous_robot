from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from src.core.control_api import ControlAPI, JsonCommand
from src.nlp.llm_agent import ExternalIntentModel


@dataclass
class RobotExecutor:
    """
    High-level robot executive layer.

    Responsibility:
    - Accept structured intents from LLM or other modules.
    - Map them to concrete robot actions.
    - Delegate low-level motion to the existing Planner / ControlAPI.
    """

    control: ControlAPI

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

