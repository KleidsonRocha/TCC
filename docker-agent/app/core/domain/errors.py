class DomainError(Exception):
    """Base class for domain/application errors."""


class UnsupportedSchemaVersionError(DomainError):
    """Raised when the payload uses an unsupported schema version."""


class InvalidMessageError(DomainError):
    """Raised when message.text is empty or invalid."""
