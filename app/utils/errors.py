class DomainError(RuntimeError):
    """Base class for application-specific errors."""


class PortalBlockedError(DomainError):
    """Raised when the target portal blocks the automation."""


class NoResultsError(DomainError):
    """Raised when the portal returns zero results for a search term."""


class SearchTimeoutError(DomainError):
    """Raised when the portal does not respond within the configured timeout."""


class ScrapingValidationError(DomainError):
    """Raised when the collected values do not match the expected structure."""
