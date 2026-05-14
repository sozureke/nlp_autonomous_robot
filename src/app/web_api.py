from __future__ import annotations

import threading
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.app.runtime import RobotRuntime, build_runtime_with_mode
from src.nlp.plan_resolution import resolve_command_plan


class CommandRequest(BaseModel):
    command: str = Field(min_length=1)
    mode: str = Field(default="llm", description="llm | rules | direct")


class ConnectRequest(BaseModel):
    method: str = Field(min_length=1, description="real")
    serial_port: Optional[str] = None


class WebRuntimeState:
    def __init__(self) -> None:
        self.runtime: Optional[RobotRuntime] = None
        self.init_error: Optional[str] = None
        self.last_error: Optional[str] = None
        self.last_plan: list[Dict[str, Any]] = []
        self.last_plan_command: Optional[str] = None
        self.connection_method: Optional[str] = None
        self.serial_port: Optional[str] = None
        self._lock = threading.Lock()
        self._command_thread: Optional[threading.Thread] = None

    def connect(self, *, method: str, serial_port: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            if self.is_busy():
                raise HTTPException(status_code=409, detail="Robot is busy executing another command")
            self._clear_runtime()
            self.last_error = None
            self.last_plan = []
            self.last_plan_command = None
            self.init_error = None
            method_norm = method.strip().lower()
            serial_norm = serial_port.strip() if serial_port else None
            if serial_norm == "":
                serial_norm = None
        try:
            runtime = build_runtime_with_mode(method=method_norm, serial_port=serial_norm)
        except Exception as exc:
            self.runtime = None
            self.init_error = str(exc)
            self.connection_method = method_norm
            self.serial_port = serial_norm
            return {"connected": False, "error": self.init_error, "method": method_norm}

        self.runtime = runtime
        self.connection_method = method_norm
        self.serial_port = serial_norm
        return {"connected": True, "method": method_norm, "serial_port": serial_norm}

    def disconnect(self) -> Dict[str, Any]:
        with self._lock:
            if self.is_busy():
                raise HTTPException(status_code=409, detail="Robot is busy executing another command")
            self._clear_runtime()
            self.runtime = None
            self.connection_method = None
            self.serial_port = None
            return {"connected": False}

    def _clear_runtime(self) -> None:
        if self.runtime is None:
            return
        try:
            self.runtime.planner.stop()
        except Exception:
            pass
        self.runtime = None

    def is_busy(self) -> bool:
        thread = self._command_thread
        return thread is not None and thread.is_alive()

    def launch_command(self, command: str, mode: str = "llm") -> Dict[str, Any]:
        if self.runtime is None:
            raise HTTPException(status_code=409, detail="Robot is not connected. Connect first.")

        with self._lock:
            if self.is_busy():
                raise HTTPException(status_code=409, detail="Robot is busy executing another command")

            thread = threading.Thread(
                target=self._execute_command,
                args=(command, mode),
                daemon=True,
            )
            self._command_thread = thread
            thread.start()
            return {"accepted": True, "mode": mode}

    def _execute_command(self, command: str, command_mode: str) -> None:
        if self.runtime is None:
            return

        try:
            mode_norm = (command_mode or "llm").strip().lower()
            self.runtime.metrics.record_command(
                command=command,
                mode=mode_norm,
                source="web_ui",
            )
            world_state = self.runtime.world.to_dict()
            memory_state = self.runtime.memory.to_dict()
            resolved = resolve_command_plan(
                translator=self.runtime.translator,
                parser=self.runtime.parser,
                command=command,
                world_state=world_state,
                memory=memory_state,
                command_mode=mode_norm,
            )
            plan = resolved.steps
            self.last_plan = plan
            self.last_plan_command = command
            if not plan:
                self.runtime.memory.add_action_event(
                    "ui_no_plan",
                    payload={
                        "command": command,
                        "execution_mode": mode_norm,
                        "plan_source": resolved.source,
                        "plan_message": resolved.message,
                    },
                )
                self.runtime.metrics.record_result(status="failed", error="no_plan")
                return

            self.runtime.world.set_internal_state(moving=True, last_action="plan")

            self.runtime.memory.add_action_event(
                "command_plan_ready",
                payload={
                    "command": command,
                    "execution_mode": mode_norm,
                    "plan_source": resolved.source,
                    "plan_message": resolved.message,
                    "llm_error": resolved.llm_error,
                    "rules_error": resolved.rules_error,
                    "step_count": len(plan),
                    "steps": plan,
                    "source_channel": "web_ui",
                },
            )
            self.runtime.memory.add_action_event(
                "llm_plan",
                payload={
                    "source": "web_ui",
                    "command": command,
                    "steps": plan,
                    "mode": mode_norm,
                    "plan_source": resolved.source,
                },
            )

            if mode_norm == "direct":
                direct_result = self.runtime.direct_executor.execute_plan(plan)
                status = "completed" if direct_result.get("success") else "failed"
                self.runtime.metrics.record_result(
                    status=status,
                    safety_violations=int(direct_result.get("safety_violations", 0)),
                )
                self.runtime.memory.add_action_event(
                    "execution_finished",
                    payload={
                        "command": command,
                        "execution_mode": mode_norm,
                        "executor": "direct_executor",
                        "plan_source": resolved.source,
                        "runtime_status": status,
                        "direct_result": direct_result,
                    },
                )
            else:
                self.runtime.executor.execute_task(raw_command=command, plan=plan)
                final_status = "interrupted" if self.runtime.executor.runtime_status == "interrupted" else "completed"
                self.runtime.metrics.record_result(status=final_status)
                self.runtime.memory.add_action_event(
                    "execution_finished",
                    payload={
                        "command": command,
                        "execution_mode": mode_norm,
                        "executor": "robot_executor",
                        "plan_source": resolved.source,
                        "runtime_status": self.runtime.executor.runtime_status,
                        "runtime": self.runtime.executor.get_runtime_status_snapshot(),
                    },
                )
        except Exception as exc:
            self.last_error = str(exc)
            if self.runtime is not None:
                self.runtime.memory.add_action_event(
                    "ui_execution_error",
                    payload={
                        "command": command,
                        "error": str(exc),
                        "execution_mode": (command_mode or "llm").strip().lower(),
                    },
                )
                self.runtime.metrics.record_result(status="failed", error=str(exc))
        finally:
            if self.runtime is not None:
                self.runtime.world.set_internal_state(moving=False)


app = FastAPI(title="Robot Control UI")
cors_origins = os.getenv("WEB_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
allowed_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
state = WebRuntimeState()


@app.get("/")
def root() -> Dict[str, Any]:
    return {"service": "Robot Control API", "docs": "/docs"}


@app.get("/api/health")
def health() -> Dict[str, Any]:
    if state.runtime is None:
        return {
            "connected": False,
            "ready": False,
            "busy": False,
            "method": state.connection_method,
            "error": state.init_error or state.last_error,
        }

    try:
        robot_state = state.runtime.robot.get_state()
        state.runtime.world.update(robot_state)
    except Exception as exc:
        return {"connected": False, "ready": False, "error": str(exc)}

    return {
        "connected": True,
        "ready": not state.is_busy(),
        "busy": state.is_busy(),
        "method": state.connection_method,
        "error": state.last_error,
    }


@app.get("/api/state")
def api_state() -> Dict[str, Any]:
    if state.runtime is None:
        return {
            "connected": False,
            "runtime_status": {"status": "idle", "has_active_task": False, "has_waiting_task": False},
            "active_task": None,
            "waiting_task": None,
            "world": None,
            "busy": False,
            "last_plan_command": state.last_plan_command,
            "last_plan": state.last_plan,
            "last_error": state.init_error or state.last_error,
            "method": state.connection_method,
        }

    return {
        "connected": True,
        "runtime_status": state.runtime.executor.get_runtime_status_snapshot(),
        "active_task": state.runtime.executor.get_active_task_snapshot(),
        "waiting_task": state.runtime.executor.get_waiting_task_snapshot(),
        "world": state.runtime.world.to_dict(),
        "busy": state.is_busy(),
        "last_plan_command": state.last_plan_command,
        "last_plan": state.last_plan,
        "last_error": state.last_error,
        "method": state.connection_method,
    }


@app.post("/api/plan")
def plan_command(req: CommandRequest) -> Dict[str, Any]:
    if state.runtime is None:
        raise HTTPException(status_code=409, detail="Robot is not connected. Connect first.")

    command = req.command.strip()
    if not command:
        raise HTTPException(status_code=400, detail="Empty command")

    world_state = state.runtime.world.to_dict()
    memory_state = state.runtime.memory.to_dict()
    resolved = resolve_command_plan(
        translator=state.runtime.translator,
        parser=state.runtime.parser,
        command=command,
        world_state=world_state,
        memory=memory_state,
        command_mode=req.mode,
    )
    plan = resolved.steps
    state.last_plan = plan
    state.last_plan_command = command
    state.runtime.memory.add_action_event(
        "plan_preview",
        payload={
            "command": command,
            "execution_mode": (req.mode or "llm").strip().lower(),
            "plan_source": resolved.source,
            "plan_message": resolved.message,
            "llm_error": resolved.llm_error,
            "rules_error": resolved.rules_error,
            "step_count": len(plan),
            "steps": plan,
        },
    )
    return {
        "command": command,
        "plan": plan,
        "mode": req.mode,
        "source": resolved.source,
        "message": resolved.message,
        "manual_assist_mode": False,
    }


@app.post("/api/execute")
def execute_command(req: CommandRequest) -> Dict[str, Any]:
    command = req.command.strip()
    if not command:
        raise HTTPException(status_code=400, detail="Empty command")
    return state.launch_command(command, mode=req.mode)


@app.post("/api/connect")
def connect(req: ConnectRequest) -> Dict[str, Any]:
    return state.connect(method=req.method, serial_port=req.serial_port)


@app.post("/api/disconnect")
def disconnect() -> Dict[str, Any]:
    return state.disconnect()


@app.get("/api/events")
def events(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> Dict[str, Any]:
    if state.runtime is None:
        return {"offset": offset, "next_offset": offset, "events": []}

    items = state.runtime.memory.events_since(offset=offset, limit=limit)
    next_offset = offset + len(items)
    return {"offset": offset, "next_offset": next_offset, "events": items}


@app.get("/api/metrics")
def api_metrics() -> Dict[str, Any]:
    if state.runtime is None:
        return {"connected": False, "metrics": None}
    return {"connected": True, "metrics": state.runtime.metrics.snapshot()}


@app.post("/api/metrics/reset")
def api_metrics_reset() -> Dict[str, Any]:
    if state.runtime is None:
        return {"connected": False, "metrics": None}
    return {"connected": True, "metrics": state.runtime.metrics.reset()}


def main() -> None:
    import uvicorn

    uvicorn.run("src.app.web_api:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
