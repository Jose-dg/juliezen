class AlegraCredentialError(Exception):
    """Raised when no valid Alegra credential is available for the company."""


class AlegraAPIError(Exception):
    """Raised when Alegra API returns an error response."""


class WebhookValidationError(Exception):
    """Raised when an inbound webhook fails validation checks."""
