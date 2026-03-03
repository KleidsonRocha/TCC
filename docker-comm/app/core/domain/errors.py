class DomainError(Exception):
    """Base class for domain/application errors."""


class InvalidMessageError(DomainError):
    """Raised when user input is invalid."""


class AgentTimeoutError(DomainError):
    """Raised when the docker-agent call exceeds timeout."""


class AgentUnavailableError(DomainError):
    """Raised when docker-agent is unavailable or returns 5xx."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AgentBadResponseError(DomainError):
    """Raised when docker-agent returns an invalid payload or 4xx."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code

