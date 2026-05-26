"""Application exception hierarchy."""


class AuditEngineError(Exception):
    """Base exception for all application errors."""


class ConfigurationError(AuditEngineError):
    """Invalid or missing configuration."""


class DatabaseError(AuditEngineError):
    """Database operation failure."""


class ValidationError(AuditEngineError):
    """Input validation failure."""


class GenerationError(AuditEngineError):
    """PDF or report generation failure."""


class UpdateError(AuditEngineError):
    """Auto-update failure."""


class DialogError(AuditEngineError):
    """File dialog failure."""
