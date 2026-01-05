from typing import Optional

from src.core.world_model import Condition, TurnDirection
from .lexicon import (
    SPEED_WORDS,
    DISTANCE_UNITS,
    FRACTIONS,
    CONDITION_KEYWORDS,
    DIRECTION_WORDS,
)


def extract_speed(doc) -> float:
    lemmas = {t.lemma_ for t in doc}
    for word, speed in SPEED_WORDS.items():
        if word in lemmas:
            return speed
    return 0.5


def extract_target_distance(doc) -> Optional[float]:
    tokens = list(doc)

    for i, token in enumerate(tokens):
        if token.lemma_ in FRACTIONS:
            fraction = FRACTIONS[token.lemma_]
            for j in range(i + 1, min(i + 4, len(tokens))):
                unit = tokens[j].text
                if unit in DISTANCE_UNITS:
                    return fraction * DISTANCE_UNITS[unit]

    for i, token in enumerate(tokens):
        if token.like_num or token.pos_ == "NUM":
            try:
                value = float(token.text)
            except ValueError:
                value = _word_to_number(token.text)

            if value is None:
                continue

            for j in range(i + 1, min(i + 3, len(tokens))):
                unit = tokens[j].text
                if unit in DISTANCE_UNITS:
                    return value * DISTANCE_UNITS[unit]

    return None


def extract_distance_threshold(doc) -> float:
    return extract_target_distance(doc) or 0.3


def extract_condition(doc) -> Optional[Condition]:
    lemmas = {t.lemma_ for t in doc}
    has_blocked = any(w in lemmas for w in {"block", "blocked", "wall", "obstacle"})

    if not has_blocked:
        return None

    for condition, keywords in CONDITION_KEYWORDS.items():
        if keywords & lemmas:
            return condition

    return Condition.FRONT_BLOCKED


def extract_direction(doc) -> Optional[TurnDirection]:
    lemmas = {t.lemma_ for t in doc}
    for word, direction in DIRECTION_WORDS.items():
        if word in lemmas:
            return direction
    return None


def _word_to_number(word: str) -> Optional[float]:
    mapping = {
        "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
        "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
        "ten": 10, "twenty": 20, "thirty": 30, "forty": 40,
        "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
        "ninety": 90, "hundred": 100,
    }
    return mapping.get(word.lower())
