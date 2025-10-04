class AlegraCredentialError(Exception):
    """Raised when no valid Alegra credential is available for the company."""


class AlegraAPIError(Exception):
    """Raised when Alegra API returns an error response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        retryable: bool = True,
        payload: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.retryable = retryable
        self.payload = payload or {}


class WebhookValidationError(Exception):
    """Raised when an inbound webhook fails validation checks."""
