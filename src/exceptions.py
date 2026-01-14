"""Custom exceptions for the Zendesk AI Agent."""


class ZendeskAIAgentError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(ZendeskAIAgentError):
    """Raised when there's a configuration problem."""

    pass


class ZendeskAPIError(ZendeskAIAgentError):
    """Raised when Zendesk API operations fail."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ):
        super().__init__(
            message,
            details={
                "status_code": status_code,
                "response_body": response_body,
            },
        )
        self.status_code = status_code
        self.response_body = response_body


class ZendeskRateLimitError(ZendeskAPIError):
    """Raised when Zendesk rate limit is hit."""

    def __init__(self, retry_after: int | None = None):
        super().__init__(
            message="Zendesk API rate limit exceeded",
            status_code=429,
        )
        self.retry_after = retry_after


class ZendeskAuthenticationError(ZendeskAPIError):
    """Raised when Zendesk authentication fails."""

    def __init__(self, message: str = "Zendesk authentication failed"):
        super().__init__(message=message, status_code=401)


class OpenAIAPIError(ZendeskAIAgentError):
    """Raised when OpenAI API operations fail."""

    def __init__(
        self,
        message: str,
        error_type: str | None = None,
        status_code: int | None = None,
    ):
        super().__init__(
            message,
            details={
                "error_type": error_type,
                "status_code": status_code,
            },
        )
        self.error_type = error_type
        self.status_code = status_code


class OpenAIRateLimitError(OpenAIAPIError):
    """Raised when OpenAI rate limit is hit."""

    def __init__(self, retry_after: int | None = None):
        super().__init__(
            message="OpenAI API rate limit exceeded",
            error_type="rate_limit_error",
            status_code=429,
        )
        self.retry_after = retry_after


class OpenAIContextLengthError(OpenAIAPIError):
    """Raised when input exceeds model context length."""

    def __init__(self, message: str = "Input exceeds maximum context length"):
        super().__init__(
            message=message,
            error_type="context_length_exceeded",
            status_code=400,
        )


class TicketProcessingError(ZendeskAIAgentError):
    """Raised when ticket processing fails."""

    def __init__(self, ticket_id: int, message: str, cause: Exception | None = None):
        super().__init__(
            message,
            details={
                "ticket_id": ticket_id,
                "cause": str(cause) if cause else None,
            },
        )
        self.ticket_id = ticket_id
        self.cause = cause
