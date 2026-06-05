"""Enumerations for screenplay schema."""

from enum import StrEnum


class IntExt(StrEnum):
    INTERIOR = "interior"
    EXTERIOR = "exterior"
    MIXED = "mixed"


class TimeOfDay(StrEnum):
    DAY = "day"
    NIGHT = "night"
    DAWN = "dawn"
    DUSK = "dusk"
    CONTINUOUS = "continuous"
    UNSPECIFIED = "unspecified"


class ElementType(StrEnum):
    ACTION = "action"
    DIALOGUE = "dialogue"
    VOICEOVER = "voiceover"
    TRANSITION = "transition"


class WarningCode(StrEnum):
    LOCATION_INFERRED = "LOCATION_INFERRED"
    TIME_INFERRED = "TIME_INFERRED"
    DIALOGUE_SYNTHESIZED = "DIALOGUE_SYNTHESIZED"
    CHARACTER_MERGED = "CHARACTER_MERGED"
    SCENE_SPLIT = "SCENE_SPLIT"
    SCENE_MERGED = "SCENE_MERGED"
    INNER_MONOLOGUE_OMITTED = "INNER_MONOLOGUE_OMITTED"
    MISSING_SOURCE_REF = "MISSING_SOURCE_REF"
    INVALID_CHARACTER_REF = "INVALID_CHARACTER_REF"


class WarningSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ValidationStatus(StrEnum):
    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    FAIL = "FAIL"
