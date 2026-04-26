class SearedError(ValueError):
    """Base exception for all seared load/dump failures."""


class ValidationError(SearedError):
    """Raised when a value fails schema validation (missing required key, type mismatch, bad enum member, etc.)."""
