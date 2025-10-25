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


class FulfillmentError(Exception):
    """Generic fulfillment orchestration error."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "fulfillment_error",
        retryable: bool = False,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.retryable = retryable
        self.status_code = status_code


class BackorderPending(FulfillmentError):
    """Raised when fulfillment should wait for stock replenishment."""

    def __init__(self, message: str = "Waiting for available serial numbers", *, status_code: int | None = 409):
        super().__init__(
            message,
            error_code="waiting_stock",
            retryable=True,
            status_code=status_code,
        )


class FulfillmentConfigurationError(FulfillmentError):
    """Raised when configuration is missing or invalid for the gateway."""

    def __init__(self, message: str):
        super().__init__(
            message,
            error_code="configuration_error",
            retryable=False,
            status_code=400,
        )
