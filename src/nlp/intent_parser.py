import spacy
from typing import Dict, Any

from src.core.planner import Intent, IntentType
from .intent_rules import classify_intent
from .slot_extractors import (
    extract_speed,
    extract_target_distance,
    extract_distance_threshold,
    extract_condition,
    extract_direction,
)


class IntentParser:
	"""
	High-level NLP orchestrator:
	text -> intent classification -> slot extraction -> Intent
	"""

	def __init__(self) -> None:
		try:
				self.nlp = spacy.load("en_core_web_sm")
		except OSError:
				raise RuntimeError("spaCy English model not found")

	def parse(self, text: str) -> Intent:
		doc = self.nlp(text.lower())
		intent_type = classify_intent(doc)
		params = self._extract_parameters(doc, intent_type)
		return Intent(type=intent_type, **params)

	def _extract_parameters(
		self, doc, intent_type: IntentType
	) -> Dict[str, Any]:

		params: Dict[str, Any] = {
				"speed": extract_speed(doc)
		}

		if intent_type == IntentType.MOVE_UNTIL_OBSTACLE:
				params["distance_threshold"] = extract_distance_threshold(doc)

		elif intent_type == IntentType.STOP_AT_DISTANCE:
				distance = extract_target_distance(doc)
				if distance is None:
						raise ValueError("STOP_AT_DISTANCE requires target_distance")
				params["target_distance"] = distance

		elif intent_type == IntentType.CONDITIONAL_TURN:
				condition = extract_condition(doc)
				direction = extract_direction(doc)

				if condition is None or direction is None:
						raise ValueError("CONDITIONAL_TURN requires condition and direction")

				params["condition"] = condition
				params["direction"] = direction
				params["angular_speed"] = params["speed"]

		return params
