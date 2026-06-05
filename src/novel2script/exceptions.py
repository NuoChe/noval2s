"""Custom exceptions for Novel2Script."""


class Novel2ScriptError(Exception):
    """Base exception."""


class ChapterParseError(Novel2ScriptError):
    """Failed to parse chapters from input text."""


class InsufficientChaptersError(ChapterParseError):
    """Input has fewer than the minimum required chapters."""


class LimitExceededError(ChapterParseError):
    """Input exceeds configured chapter or word limits."""


class LLMError(Novel2ScriptError):
    """LLM API or response parsing failed."""


class ValidationError(Novel2ScriptError):
    """Screenplay validation failed."""
