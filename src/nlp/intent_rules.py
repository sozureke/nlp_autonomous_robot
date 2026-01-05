from abc import ABC, abstractmethod
from typing import List

from src.core.planner import IntentType
from .lexicon import (
    MOVEMENT_VERBS,
    OBSTACLE_WORDS,
    UNTIL_WORDS,
    STOP_WORDS,
    DISTANCE_UNITS,
)


class IntentRule(ABC):
    @abstractmethod
    def matches(self, doc) -> bool:
        pass

    @abstractmethod
    def intent_type(self) -> IntentType:
        pass


class ConditionalTurnRule(IntentRule):
    def matches(self, doc) -> bool:
        lemmas = {t.lemma_ for t in doc}
        has_if = any(t.text == "if" for t in doc)
        has_turn = any(t.lemma_ in {"turn", "rotate"} for t in doc)
        has_blocked = any(w in lemmas for w in OBSTACLE_WORDS)
        return has_if and has_turn and has_blocked

    def intent_type(self) -> IntentType:
        return IntentType.CONDITIONAL_TURN


class StopAtDistanceRule(IntentRule):
    def matches(self, doc) -> bool:
        lemmas = {t.lemma_ for t in doc}
        has_stop = any(w in STOP_WORDS for w in lemmas)
        has_number = any(t.like_num or t.pos_ == "NUM" for t in doc)
        has_unit = any(t.text in DISTANCE_UNITS for t in doc)
        return has_stop and has_number and has_unit

    def intent_type(self) -> IntentType:
        return IntentType.STOP_AT_DISTANCE


class MoveUntilObstacleRule(IntentRule):
    def matches(self, doc) -> bool:
        lemmas = {t.lemma_ for t in doc}
        tokens = {t.text for t in doc}

        has_movement = any(
            t.lemma_ in MOVEMENT_VERBS and t.pos_ == "VERB"
            for t in doc
        )
        has_until = any(w in UNTIL_WORDS for w in tokens)
        has_obstacle = any(w in OBSTACLE_WORDS for w in lemmas)

        return has_movement and (has_until or has_obstacle)

    def intent_type(self) -> IntentType:
        return IntentType.MOVE_UNTIL_OBSTACLE


RULES: List[IntentRule] = [
    ConditionalTurnRule(),
    StopAtDistanceRule(),
    MoveUntilObstacleRule(),
]


def classify_intent(doc) -> IntentType:
    for rule in RULES:
        if rule.matches(doc):
            return rule.intent_type()
    raise ValueError(f"Could not classify intent: '{doc.text}'")
