from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

from src.core.control_api import ControlAPI, JsonCommand
from src.core.planner import PlannerExecutionResult
from src.core.safety_controller import SafetyController
from src.nlp.llm_agent import ExternalIntentModel

if TYPE_CHECKING:
    from src.core.world_model import WorldModel
    from src.memory.memory import ShortTermMemory
    from src.nlp.llm_agent import LLMIntentTranslator


TaskStatus = Literal["running", "interrupted", "completed"]
RuntimeStatus = Literal[
    "idle",
    "executing",
    "interrupted",
    "completed",
]


@dataclass
class ActiveTask:
    task_id: int
    raw_command: str
    original_plan: List[Dict[str, Any]]
    status: TaskStatus = "running"
    current_step_index: int = 0
    last_interruption: Optional[Dict[str, Any]] = None


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
    translator: "LLMIntentTranslator"
    memory: Optional["ShortTermMemory"] = None
    safety_controller: Optional[SafetyController] = None
    world_model: Optional["WorldModel"] = None
    active_task: Optional[ActiveTask] = None
    _next_task_id: int = 1
    runtime_status: RuntimeStatus = "idle"
    last_interruption_event: Optional[Dict[str, Any]] = None

    def execute_task(self, raw_command: str, plan: List[Dict[str, Any]]) -> None:
        """
        Start and execute a new operator task.
        """
        self.active_task = ActiveTask(
            task_id=self._next_task_id,
            raw_command=raw_command,
            original_plan=plan,
        )
        self._next_task_id += 1
        self._print_task_status("executing")
        self._execute_active_task()

    def execute_plan(self, plan: List[Dict[str, Any]]) -> None:
        """
        Backward-compatible entrypoint for callers that only provide a plan.
        """
        self.execute_task(raw_command="[plan_only]", plan=plan)

    def has_waiting_task(self) -> bool:
        return False

    def get_active_task_snapshot(self) -> Optional[Dict[str, Any]]:
        if self.active_task is None:
            return None
        return self._task_to_dict(self.active_task)

    def get_waiting_task_snapshot(self) -> Optional[Dict[str, Any]]:
        return None

    def get_runtime_status_snapshot(self) -> Dict[str, Any]:
        return {
            "status": self.runtime_status,
            "has_active_task": self.active_task is not None,
            "has_waiting_task": False,
            "active_task_id": self.active_task.task_id if self.active_task is not None else None,
            "waiting_task_id": None,
            "last_interruption_event": self.last_interruption_event,
        }

    def execute_operator_assist_command(self, raw_command: str, plan: List[Dict[str, Any]]) -> None:
        """
        Compatibility shim: execute as a normal operator command.
        """
        self.execute_task(raw_command=raw_command, plan=plan)

    def execute_llm_intent(self, intent: ExternalIntentModel) -> None:
        """
        Entry point for LLM-produced intents.

        Converts the validated Pydantic model into a JsonCommand and
        executes it via the single underlying executor (Planner).
        """
        cmd: Dict[str, Any] = intent.to_command_dict()
        self.execute_json_command(cmd)  # type: ignore[arg-type]

    def execute_json_command(self, cmd: JsonCommand) -> PlannerExecutionResult:
        """
        Entry point for already-structured JSON commands.

        This is the main integration point for non-LLM modules that
        want to drive the robot using the same high-level API.
        """
        return self.control.execute_json(cmd)

    def _execute_active_task(self) -> None:
        if self.active_task is None:
            return

        while self.active_task.current_step_index < len(self.active_task.original_plan):
            idx = self.active_task.current_step_index
            cmd = self.active_task.original_plan[idx]
            safe_cmd = self._apply_safety(cmd)
            intended_move = cmd.get("action") == "move_forward"
            safety_blocked = intended_move and safe_cmd.get("action") == "stop"
            if safety_blocked:
                self._handle_obstacle_stop(
                    source="safety_controller",
                    step_index=idx,
                    distance_cm=self._current_distance_cm(),
                )
                return
            result = self.execute_json_command(safe_cmd)  # type: ignore[arg-type]

            interrupted = (
                result.status == "interrupted"
                and result.interruption is not None
                and result.interruption.reason == "obstacle_detected"
                and safe_cmd.get("action") == "move_forward"
            )
            if interrupted:
                self._handle_obstacle_stop(
                    source="planner",
                    step_index=idx,
                    distance_cm=result.interruption.distance_m * 100.0,
                )
                return

            self._log_step_done(idx, len(self.active_task.original_plan), safe_cmd)
            self.active_task.current_step_index += 1

        self.active_task.status = "completed"
        self._print_task_status("completed")
        print(f"[task] completed: {self.active_task.raw_command}")
        self._record_memory(
            "task_completed",
            {"task": self.active_task.raw_command, "task_id": self.active_task.task_id},
        )
        self.active_task = None

    def _handle_obstacle_stop(self, *, source: str, step_index: int, distance_cm: float) -> None:
        if self.active_task is None:
            return
        self.active_task.status = "interrupted"
        self.active_task.last_interruption = {
            "reason": "obstacle_detected",
            "distance_cm": distance_cm,
            "source": source,
            "step_index": step_index,
        }
        self.last_interruption_event = {
            "task": self.active_task.raw_command,
            "task_id": self.active_task.task_id,
            "reason": "obstacle_detected",
            "distance_cm": distance_cm,
            "source": source,
            "step_index": step_index,
        }
        self.runtime_status = "interrupted"
        self.execute_json_command({"action": "stop"})
        print(
            f"[task] stopped: obstacle detected at {distance_cm:.1f} cm. "
            "Further movement is not possible until operator sends a new command."
        )
        self._record_memory("task_stopped_obstacle", self.last_interruption_event)

    def _apply_safety(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        safe_cmd = dict(cmd)
        if self.safety_controller is not None and self.world_model is not None:
            safe_cmd = self.safety_controller.apply(safe_cmd, self.world_model.to_dict())
        return safe_cmd

    def _log_step_done(self, idx: int, total: int, safe_cmd: Dict[str, Any]) -> None:
        self._record_memory(
            "step_done",
            payload={
                "step_index": idx,
                "step_total": total,
                "command": safe_cmd,
            },
        )

    def _record_memory(self, name: str, payload: Dict[str, Any]) -> None:
        if self.memory is not None:
            self.memory.add_action_event(name, payload=payload)

    def _print_task_status(self, status: str) -> None:
        status_map: Dict[str, RuntimeStatus] = {
            "executing": "executing",
            "interrupted": "interrupted",
            "completed": "completed",
        }
        for key, mapped in status_map.items():
            if status.startswith(key):
                self.runtime_status = mapped
                break
        else:
            self.runtime_status = "idle" if self.active_task is None else "executing"

        if self.active_task is None:
            print("[task] active: (none)")
            print(f"[task] status: {status}")
            return
        print(f"[task] active #{self.active_task.task_id}: {self.active_task.raw_command}")
        print(f"[task] status: {status}")

    def _current_distance_cm(self) -> float:
        if self.world_model is None:
            return -1.0
        return self.world_model.get_distance_to_obstacle() * 100.0

    def _task_to_dict(self, task: ActiveTask) -> Dict[str, Any]:
        return {
            "task_id": task.task_id,
            "raw_command": task.raw_command,
            "status": task.status,
            "current_step_index": task.current_step_index,
            "original_plan": task.original_plan,
            "last_interruption": task.last_interruption,
        }

