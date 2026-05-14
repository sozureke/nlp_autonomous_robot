from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from enum import Enum


# Load environment variables from .env if present.
load_dotenv()


class Action(str, Enum):
    """
    High-level actions that the LLM is allowed to emit.
    """

    MOVE_FORWARD = "move_forward"
    STOP = "stop"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    SCAN_360 = "scan_360"


class Until(str, Enum):
    """
    Semantic stop conditions for actions.
    """

    OBSTACLE_DETECTED = "obstacle_detected"


class ExternalIntentModel(BaseModel):
    """
    Strict schema for LLM → robot intent.

    This is intentionally narrow at Priority 2 and can be extended later.
    """

    action: Action = Field(
        description="High-level robot action to execute, e.g. 'move_forward' or 'stop'."
    )
    speed: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional normalized speed in [0.0, 1.0]. If omitted, use a safe default.",
    )
    until: Until | None = Field(
        default=None,
        description="Optional stop condition such as 'obstacle_detected'.",
    )
    duration: float | None = Field(
        default=None,
        gt=0.0,
        le=30.0,
        description="Optional action duration in seconds.",
    )

    def to_command_dict(self) -> Dict[str, Any]:
        """
        Convert to a plain dict compatible with ControlAPI.JsonCommand.
        """
        data = self.model_dump(exclude_none=True)
        # Ensure enum values are plain strings.
        data["action"] = self.action.value
        if "until" in data:
            data["until"] = self.until.value  # type: ignore[assignment]
        return data


def _step_to_command_dict(step: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a raw JSON step into a command dict.
    """
    action = step.get("action")
    if not action:
        raise ValueError("Each step must have 'action'")

    out: Dict[str, Any] = {"action": action}
    if "speed" in step:
        out["speed"] = float(step["speed"])
    if "until" in step:
        out["until"] = step["until"]
    if "duration" in step:
        out["duration"] = float(step["duration"])
    if "repeat" in step:
        out["repeat"] = int(step["repeat"])
    return out


@dataclass
class OpenRouterClient:
    """
    Minimal OpenRouter API client for chat completions.
    """

    api_key: str
    model: str
    timeout: float = 15.0

    def complete(self, messages: list[dict[str, str]]) -> str:
        """
        Call OpenRouter chat completions and return the assistant text.
        """
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Unexpected OpenRouter response format: {data}") from e


@dataclass
class LLMIntentTranslator:
    """
    LLM-based semantic compiler: natural language -> structured ExternalIntentModel.
    """

    client: OpenRouterClient

    def build_messages(
        self,
        command: str,
        world_state: Optional[Dict[str, Any]] = None,
        memory: Optional[Dict[str, Any]] = None,
    ) -> list[dict[str, str]]:
        """
        Construct a strict prompt that forces JSON-only output.
        """
        schema_description = json.dumps(
            {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["move_forward", "stop", "turn_left", "turn_right", "scan_360"],
                    },
                    "speed": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "until": {
                        "type": "string",
                        "enum": ["obstacle_detected"],
                    },
                    "duration": {
                        "type": "number",
                        "exclusiveMinimum": 0.0,
                        "maximum": 30.0,
                    },
                },
                "required": ["action"],
                "additionalProperties": False,
            },
            indent=2,
        )

        system_content = (
            "You are an intent compiler for a small mobile robot.\n"
            "Your ONLY job is to convert natural language commands into "
            "a STRICT JSON object that matches the given JSON Schema.\n\n"
            "Rules:\n"
            "- Respond with JSON ONLY. No explanations, no markdown, no code fences.\n"
            "- Do not include comments or trailing commas.\n"
            "- If the command is ambiguous, pick the safest reasonable interpretation.\n"
            "- If you cannot infer a suitable speed, omit the 'speed' field.\n"
            "- If there is no explicit semantic stop condition, omit the 'until' field.\n\n"
            "- If command contains explicit duration (e.g., 'for 2 seconds'), set 'duration'.\n\n"
            "JSON Schema for the response:\n"
            f"{schema_description}\n"
        )

        user_payload: Dict[str, Any] = {"command": command}
        if world_state is not None:
            user_payload["world_state"] = world_state
        if memory is not None:
            user_payload["memory"] = memory

        user_content = json.dumps(user_payload, ensure_ascii=False)

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def build_plan_messages(
        self,
        command: str,
        world_state: Optional[Dict[str, Any]] = None,
        memory: Optional[Dict[str, Any]] = None,
    ) -> list[dict[str, str]]:
        """
        Prompt for either a single action or a multi-step plan.
        """
        step_schema = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["move_forward", "stop", "turn_left", "turn_right", "scan_360"],
                },
                "speed": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
                "until": {
                    "type": "string",
                    "enum": ["obstacle_detected"],
                },
                "duration": {
                    "type": "number",
                    "exclusiveMinimum": 0.0,
                    "maximum": 30.0,
                },
                "repeat": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 20,
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        }
        schema_description = json.dumps(
            {
                "type": "object",
                "properties": {
                    "action": step_schema["properties"]["action"],
                    "speed": step_schema["properties"]["speed"],
                    "until": step_schema["properties"]["until"],
                    "plan": {
                        "type": "array",
                        "items": step_schema,
                        "minItems": 1,
                    },
                    "repeat": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
                "additionalProperties": False,
            },
            indent=2,
        )

        context_note = (
            "Context: You receive 'world_state' (sensors, derived obstacle/path_clear, internal state) "
            "and 'memory' (recent events and steps). Use them when planning. "
            "If path is blocked, prefer turning or stopping over moving forward.\n\n"
        )
        system_content = (
            "You are a task planner for a small mobile robot.\n"
            "Convert the user's command into a STRICT JSON object.\n\n"
            f"{context_note}"
            "For a SINGLE task, respond with one action:\n"
            '  {"action": "move_forward", "speed": 0.5, "duration": 2.0, "until": "obstacle_detected"}\n\n'
            "For MULTIPLE tasks in one command, respond with a plan:\n"
            '  {"plan": [{"action": "turn_left", "speed": 0.5}, {"action": "move_forward", "speed": 0.3, "duration": 1.5, "until": "obstacle_detected"}]}\n\n'
            "For repetition, use step repeat or top-level repeat:\n"
            '  {"plan": [{"action":"turn_left","repeat":2},{"action":"move_forward","duration":1.0}],"repeat":3}\n\n'
            "CRITICAL for phrases like \"A then B, repeat N times\": the top-level \"repeat\" MUST repeat "
            "the ENTIRE sequence A+B together, NOT only the last step. Put both A and B inside \"plan\", "
            "then set \"repeat\" at the root. Example:\n"
            '  {"plan":[{"action":"move_forward","speed":0.5,"duration":1.0},{"action":"turn_right","speed":0.5,"duration":1.0}],"repeat":3}\n\n'
            "NEVER attach \"repeat\" only to turn_right when the user asked to repeat forward+turn.\n\n"
            "Rules:\n"
            "- Respond with JSON ONLY. No explanations, no markdown, no code fences.\n"
            "- Turn 180 degrees = two turn_left steps (or two turn_right).\n"
            "- If only one step is needed, use the single 'action' form.\n"
            "- If multiple steps are needed, use the 'plan' array.\n"
            "- Omit 'speed', 'duration', or 'until' when not needed.\n\n"
            "JSON shape (use either single action OR plan, not both):\n"
            f"{schema_description}\n"
        )

        user_payload: Dict[str, Any] = {"command": command}
        if world_state is not None:
            user_payload["world_state"] = world_state
        if memory is not None:
            user_payload["memory"] = memory

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]

    def infer_plan(
        self,
        command: str,
        world_state: Optional[Dict[str, Any]] = None,
        memory: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Natural language -> plan (list of commands).
        """
        pre = self._parse_forward_then_turn_repeat_plan(command)
        if pre:
            return pre
        try:
            messages = self.build_plan_messages(command, world_state, memory)
            raw = self.client.complete(messages)
        except Exception:
            return self._rule_based_fallback_plan(command)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = self._extract_json_from_text(raw)

        if not data:
            return self._rule_based_fallback_plan(command)

        if "plan" in data and isinstance(data["plan"], list):
            out: List[Dict[str, Any]] = []
            for step in data["plan"]:
                if not isinstance(step, dict):
                    continue
                try:
                    out.extend(self._expand_step_repeat(_step_to_command_dict(step)))
                except (ValueError, TypeError):
                    continue
            if out:
                return self.expand_plan_repeat(out, data.get("repeat"))

        if "action" in data:
            try:
                out = self._expand_step_repeat(_step_to_command_dict(data))
                return self.expand_plan_repeat(out, data.get("repeat"))
            except (ValueError, TypeError):
                pass

        return self._rule_based_fallback_plan(command)

    def parse_plan_json_content(self, raw: str) -> List[Dict[str, Any]]:
        """
        Parse a model response into executable plan steps.
        """
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = self._extract_json_from_text(raw)
        if not data:
            return []

        if "plan" in data and isinstance(data["plan"], list):
            out: List[Dict[str, Any]] = []
            for step in data["plan"]:
                if not isinstance(step, dict):
                    continue
                try:
                    out.extend(self._expand_step_repeat(_step_to_command_dict(step)))
                except (ValueError, TypeError):
                    continue
            return self.expand_plan_repeat(out, data.get("repeat"))
        if "action" in data:
            try:
                out = self._expand_step_repeat(_step_to_command_dict(data))
                return self.expand_plan_repeat(out, data.get("repeat"))
            except (ValueError, TypeError):
                return []
        return []

    def _expand_step_repeat(self, step: Dict[str, Any]) -> List[Dict[str, Any]]:
        repeat = int(step.get("repeat", 1))
        if repeat < 1:
            repeat = 1
        repeat = min(repeat, 20)
        base = dict(step)
        base.pop("repeat", None)
        return [dict(base) for _ in range(repeat)]

    def expand_plan_repeat(self, plan: List[Dict[str, Any]], repeat_value: Any) -> List[Dict[str, Any]]:
        if repeat_value is None:
            return plan
        try:
            repeat = int(repeat_value)
        except (TypeError, ValueError):
            return plan
        if repeat <= 1:
            return plan
        repeat = min(repeat, 20)
        out: List[Dict[str, Any]] = []
        for _ in range(repeat):
            out.extend(dict(step) for step in plan)
        return out

    def build_replan_messages(
        self,
        *,
        original_command: str,
        obstacle_distance_cm: float,
        failed_attempts: List[Dict[str, Any]],
        world_state: Optional[Dict[str, Any]] = None,
        memory: Optional[Dict[str, Any]] = None,
    ) -> list[dict[str, str]]:
        """
        Specialized prompt for obstacle-avoidance replanning.
        """
        step_schema = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["move_forward", "stop", "turn_left", "turn_right", "scan_360"],
                },
                "speed": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
                "until": {
                    "type": "string",
                    "enum": ["obstacle_detected"],
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        }
        schema_description = json.dumps(
            {
                "type": "object",
                "properties": {
                    "plan": {
                        "type": "array",
                        "items": step_schema,
                        "minItems": 1,
                    },
                },
                "required": ["plan"],
                "additionalProperties": False,
            },
            indent=2,
        )

        system_content = (
            "You are a robot obstacle-avoidance replanning assistant.\n"
            "Your role is to help the robot get around an obstacle and continue the ORIGINAL task.\n\n"
            "Rules:\n"
            "- Respond with JSON ONLY. No explanations, markdown, or code fences.\n"
            "- Return ONLY a `plan` array of actions.\n"
            "- Use ONLY these actions: move_forward, stop, turn_left, turn_right, scan_360.\n"
            "- Do NOT repeat previously failed strategies listed in failed_attempts.\n"
            "- Keep the plan concise and safety-aware.\n\n"
            "JSON Schema:\n"
            f"{schema_description}\n"
        )

        user_payload: Dict[str, Any] = {
            "original_task": original_command,
            "event": f"move_forward interrupted: obstacle detected at {obstacle_distance_cm:.1f} cm",
            "failed_attempts": failed_attempts,
            "available_actions": [
                "move_forward",
                "stop",
                "turn_left",
                "turn_right",
                "scan_360",
            ],
        }
        if world_state is not None:
            user_payload["world_state"] = world_state
        if memory is not None:
            user_payload["memory"] = memory

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]

    def infer_replan(
        self,
        *,
        original_command: str,
        obstacle_distance_cm: float,
        failed_attempts: List[Dict[str, Any]],
        world_state: Optional[Dict[str, Any]] = None,
        memory: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate an obstacle-avoidance plan using a specialized replan prompt.
        """
        try:
            messages = self.build_replan_messages(
                original_command=original_command,
                obstacle_distance_cm=obstacle_distance_cm,
                failed_attempts=failed_attempts,
                world_state=world_state,
                memory=memory,
            )
            raw = self.client.complete(messages)
        except Exception:
            return [{"action": "scan_360", "speed": 0.4}, {"action": "turn_left", "speed": 0.5}]

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = self._extract_json_from_text(raw)

        if not data or "plan" not in data or not isinstance(data["plan"], list):
            return [{"action": "scan_360", "speed": 0.4}, {"action": "turn_left", "speed": 0.5}]

        out: List[Dict[str, Any]] = []
        for step in data["plan"]:
            if not isinstance(step, dict):
                continue
            try:
                out.extend(self._expand_step_repeat(_step_to_command_dict(step)))
            except (ValueError, TypeError):
                continue

        if out:
            return self.expand_plan_repeat(out, data.get("repeat"))
        return [{"action": "scan_360", "speed": 0.4}, {"action": "turn_left", "speed": 0.5}]

    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        fence_match = re.search(r"```(?:json)?(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if fence_match:
            text = fence_match.group(1).strip()

        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                return None
        return None

    def infer_intent(
        self,
        command: str,
        world_state: Optional[Dict[str, Any]] = None,
        memory: Optional[Dict[str, Any]] = None,
    ) -> ExternalIntentModel:
        """
        Main entrypoint: text → ExternalIntentModel, with validation and fallbacks.
        """
        messages = self.build_messages(command, world_state, memory)
        raw = self.client.complete(messages)

        # 1) Strict JSON parse + Pydantic validation.
        try:
            return self._parse_strict(raw)
        except ValidationError:
            # If the model responded with nearly-correct JSON, try to recover.
            pass
        except json.JSONDecodeError:
            pass

        # 2) Fallback: try to recover JSON from within text (code fences / extra text).
        try:
            return self._parse_relaxed(raw)
        except Exception:
            pass

        # 3) Last-resort rule-based fallback.
        return self._rule_based_fallback(command)

    def _parse_strict(self, text: str) -> ExternalIntentModel:
        data = json.loads(text)
        return ExternalIntentModel.model_validate(data)

    def _parse_relaxed(self, text: str) -> ExternalIntentModel:
        """
        Try to extract a JSON object from messy LLM output.
        """
        # Strip common code-fence patterns like ```json ... ```
        fence_match = re.search(r"```(?:json)?(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if fence_match:
            text = fence_match.group(1).strip()

        # Fallback: take the first {...} block.
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            text = brace_match.group(0)

        data = json.loads(text)
        return ExternalIntentModel.model_validate(data)

    def _rule_based_fallback(self, command: str) -> ExternalIntentModel:
        """
        Conservative heuristic mapping when LLM output cannot be trusted.
        """
        text = command.lower()
        duration = self._extract_duration_seconds(text)

        # turning
        if any(phrase in text for phrase in ["turn left", "rotate left", "spin left", "left turn"]):
            return ExternalIntentModel(action=Action.TURN_LEFT, speed=0.5, duration=duration)

        if any(phrase in text for phrase in ["turn right", "rotate right", "spin right", "right turn"]):
            return ExternalIntentModel(action=Action.TURN_RIGHT, speed=0.5, duration=duration)

        # 360 / scan
        if any(phrase in text for phrase in ["scan", "look around", "360", "full turn"]):
            return ExternalIntentModel(action=Action.SCAN_360, speed=0.5, duration=duration)

        # forward / move
        if any(w in text for w in ["forward", "ahead", "go", "move"]):
            until = None
            if any(phrase in text for phrase in ["until obstacle", "until you see something"]):
                until = Until.OBSTACLE_DETECTED

            return ExternalIntentModel(
                action=Action.MOVE_FORWARD,
                speed=0.5,
                until=until,
                duration=duration,
            )

        # stop / halt
        if any(w in text for w in ["stop", "halt", "freeze"]):
            return ExternalIntentModel(action=Action.STOP)

        # Absolute safe default: do nothing (stop).
        return ExternalIntentModel(action=Action.STOP)

    def _extract_duration_seconds(self, text: str) -> Optional[float]:
        patterns = [
            r"for\s+(\d+(?:\.\d+)?)\s*(?:sec|secs|second|seconds|s)\b",
            r"(\d+(?:\.\d+)?)\s*(?:sec|secs|second|seconds|s)\b",
        ]
        for pattern in patterns:
            m = re.search(pattern, text)
            if not m:
                continue
            try:
                value = float(m.group(1))
            except (TypeError, ValueError):
                continue
            if value > 0:
                return min(value, 30.0)
        return None

    def _parse_forward_then_turn_repeat_plan(self, command: str) -> Optional[List[Dict[str, Any]]]:
        """
        Deterministic parse for: move forward … then turn left/right …, repeat N times.

        OpenRouter models often emit repeat only on the last step; this fixes that phrasing
        without relying on the LLM.
        """
        text = command.strip().lower()
        m_rep = re.search(
            r"repeat\s+(\d+)\s+times?\b|(\d+)\s+times?\s+repeat\b",
            text,
        )
        if not m_rep:
            return None
        rep_s = m_rep.group(1) or m_rep.group(2)
        try:
            rep = int(rep_s)
        except (TypeError, ValueError):
            return None
        rep = min(max(rep, 1), 20)

        parts = re.split(r"\bthen\b", text, maxsplit=1)
        if len(parts) < 2:
            return None
        before_then, after_then = parts[0].strip(), parts[1].strip()

        if not re.search(r"(?:move|go|drive)\s+forward|\bforward\b", before_then):
            return None

        d_fwd = self._extract_duration_seconds(before_then)
        if d_fwd is None:
            return None

        after_core = re.sub(
            r",?\s*(?:repeat\s+\d+\s*times?|\d+\s*times?\s+repeat)\s*\.?\s*$",
            "",
            after_then,
        ).strip()

        if re.search(r"turn\s+right", after_core):
            turn_action = "turn_right"
        elif re.search(r"turn\s+left", after_core):
            turn_action = "turn_left"
        else:
            return None

        d_turn = self._extract_duration_seconds(after_core)
        if d_turn is None:
            return None

        block: List[Dict[str, Any]] = [
            {"action": "move_forward", "speed": 0.5, "duration": d_fwd},
            {"action": turn_action, "speed": 0.5, "duration": d_turn},
        ]
        return [dict(step) for _ in range(rep) for step in block]

    def _rule_based_fallback_plan(self, command: str) -> List[Dict[str, Any]]:
        """
        Heuristic multi-step fallback when LLM is unavailable.
        """
        text = command.lower().strip()
        pre = self._parse_forward_then_turn_repeat_plan(command)
        if pre:
            return pre
        duration = self._extract_duration_seconds(text)

        if any(phrase in text for phrase in ["turn 180", "turn around", "180 degrees"]):
            if any(w in text for w in ["forward", "ahead", "go", "move"]):
                return [
                    {"action": "turn_left", "speed": 0.5},
                    {"action": "turn_left", "speed": 0.5},
                    {
                        "action": "move_forward",
                        "speed": 0.5,
                        "until": "obstacle_detected",
                        **({"duration": duration} if duration is not None else {}),
                    },
                ]
            return [
                {"action": "turn_left", "speed": 0.5},
                {"action": "turn_left", "speed": 0.5},
            ]

        return [self._rule_based_fallback(command).to_command_dict()]


def build_default_translator() -> LLMIntentTranslator:
    """
    Convenience factory that reads configuration from environment.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set. Configure it in .env or environment.")

    model = os.getenv("LLM_INTENT_MODEL", "openrouter/auto")

    client = OpenRouterClient(api_key=api_key, model=model)
    return LLMIntentTranslator(client=client)

