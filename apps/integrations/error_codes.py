"""Utilities to classify Alegra API errors and decide retry strategy."""

from __future__ import annotations

from typing import Any, Tuple

from apps.integrations.exceptions import (
    AlegraAPIError,
    AlegraCredentialError,
    FulfillmentError,
)

ALEGRA_STATUS_MAP: dict[int, tuple[str, bool]] = {
    400: ("validation_error", False),
    401: ("authentication_error", False),
    403: ("forbidden", False),
    404: ("resource_not_found", False),
    409: ("conflict_error", False),
    422: ("validation_error", False),
    429: ("rate_limited", True),
}


def map_status(status_code: int | None) -> Tuple[str, bool]:
    if status_code is None:
        return "network_error", True
    if status_code >= 500:
        return "server_error", True
    code, retryable = ALEGRA_STATUS_MAP.get(status_code, ("unknown_error", False))
    return code, retryable


def extract_error_message(body: Any) -> str:
    if isinstance(body, str):
        return body
    if isinstance(body, dict):
        for key in ("message", "error", "detail"):
            if body.get(key):
                return str(body[key])
        return str(body)
    return str(body)


def classify_exception(exc: Exception) -> tuple[str, bool, int | None]:
    if isinstance(exc, AlegraAPIError):
        error_code = exc.error_code or map_status(exc.status_code)[0]
        retryable = exc.retryable
        return error_code, retryable, exc.status_code
    if isinstance(exc, AlegraCredentialError):
        return "credential_error", False, None
    if isinstance(exc, FulfillmentError):
        return exc.error_code, exc.retryable, exc.status_code
    return "unexpected_error", False, None
