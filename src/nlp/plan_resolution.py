from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, TYPE_CHECKING

import requests

from src.nlp.intent_to_json_plan import intent_to_json_steps

if TYPE_CHECKING:
    from src.nlp.intent_parser import IntentParser
    from src.nlp.llm_agent import LLMIntentTranslator

logger = logging.getLogger(__name__)


@dataclass
class CommandPlanResult:
    steps: List[Dict[str, Any]]
    source: Literal["llm", "rules", "heuristic", "none"]
    message: str
    llm_error: Optional[str] = None
    rules_error: Optional[str] = None


def _http_error_message(exc: Exception) -> str:
    if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None:
        r = exc.response
        try:
            body = r.json()
            err = body.get("error")
            if isinstance(err, dict):
                detail = err.get("message") or err.get("code") or json.dumps(err)[:500]
            else:
                detail = str(err) if err else r.text[:500]
        except Exception:
            detail = (r.text or "")[:500]
        return f"HTTP {r.status_code}: {detail}"
    return f"{type(exc).__name__}: {exc}"


def _try_rules(parser: Optional["IntentParser"], command: str) -> tuple[List[Dict[str, Any]], Optional[str]]:
    if parser is None:
        return [], "Rule parser not available in this context"
    try:
        intent = parser.parse(command)
    except Exception as e:
        return [], str(e)
    try:
        return intent_to_json_steps(intent), None
    except ValueError as e:
        return [], str(e)


def _heuristic(
    translator: "LLMIntentTranslator",
    command: str,
    llm_error: Optional[str],
    rules_error: Optional[str],
) -> CommandPlanResult:
    h = translator._rule_based_fallback_plan(command)  # noqa: SLF001
    parts: list[str] = []
    if llm_error:
        parts.append(f"LLM failed: {llm_error}")
    if rules_error:
        parts.append(f"NLP rules failed: {rules_error}")
    sub = " ".join(parts) if parts else "No higher-level model produced a plan"
    return CommandPlanResult(
        steps=h,
        source="heuristic",
        message=f"Using keyword-only fallback. {sub}.",
        llm_error=llm_error,
        rules_error=rules_error,
    )


def resolve_command_plan(
    translator: "LLMIntentTranslator",
    parser: Optional["IntentParser"],
    command: str,
    world_state: Optional[Dict[str, Any]] = None,
    memory: Optional[Dict[str, Any]] = None,
    command_mode: str = "llm",
) -> CommandPlanResult:
    mode = (command_mode or "llm").strip().lower()
    if mode not in ("llm", "rules", "direct"):
        mode = "llm"

    if mode == "rules":
        steps, re = _try_rules(parser, command)
        if steps:
            return CommandPlanResult(
                steps=steps,
                source="rules",
                message="Plan from rule-based parser (NLP, no LLM).",
            )
        return _heuristic(translator, command, None, re)

    phrase_plan = translator._parse_forward_then_turn_repeat_plan(command)
    if phrase_plan:
        return CommandPlanResult(
            steps=phrase_plan,
            source="heuristic",
            message="Plan from phrase pattern (forward, then turn, repeated); LLM skipped for this shape.",
        )

    # llm, direct: OpenRouter first
    try:
        messages = translator.build_plan_messages(command, world_state, memory)
        raw = translator.client.complete(messages)
    except Exception as e:
        llm_error = _http_error_message(e)
        logger.warning("LLM request failed, trying NLP rules: %s", llm_error, exc_info=True)
        steps, re = _try_rules(parser, command)
        if steps:
            return CommandPlanResult(
                steps=steps,
                source="rules",
                message=f"LLM request failed. Using NLP rules fallback. ({llm_error})",
                llm_error=llm_error,
            )
        return _heuristic(translator, command, llm_error, re)

    steps = translator.parse_plan_json_content(raw)
    if steps:
        return CommandPlanResult(
            steps=steps,
            source="llm",
            message="Plan from LLM (OpenRouter).",
        )

    llm_error = f"Unusable LLM output (not valid plan JSON; preview: {raw[:200]!r}…)" if raw else "Empty LLM response"
    logger.warning("LLM output did not parse as a plan: %s", llm_error)
    steps, re = _try_rules(parser, command)
    if steps:
        return CommandPlanResult(
            steps=steps,
            source="rules",
            message=f"LLM output was unparseable. Using NLP rules fallback. ({llm_error})",
            llm_error=llm_error,
        )
    return _heuristic(translator, command, llm_error, re)
