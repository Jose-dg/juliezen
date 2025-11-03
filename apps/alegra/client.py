from __future__ import annotations

import base64
import logging
import uuid
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings
from django.utils import timezone

from apps.integrations.exceptions import AlegraAPIError, AlegraCredentialError
from apps.integrations.models import IntegrationMessage
from apps.integrations.error_codes import extract_error_message, map_status

logger = logging.getLogger(__name__)


class AlegraClient:
    """HTTP client for the Alegra API that logs integration activity."""

    def __init__(
        self,
        organization_id: uuid.UUID,
        base_url: str,
        api_key: str,
        api_secret: str,
        timeout_s: int,
        max_retries: int,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.organization_id = organization_id
        self.base_url = base_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout_s
        self.max_retries = max_retries

        self.session = session or requests.Session()

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        event_type: str = "",
        external_reference: str = "",
    ) -> Dict[str, Any]:
        url = self._build_url(path)
        message = self._log_outbound_message(
            method=method,
            url=url,
            params=params,
            payload=json,
            event_type=event_type,
            external_reference=external_reference,
        )

        started_at = timezone.now()
        latency_ms: Optional[int] = None
        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json,
                headers=self._build_headers(),
                timeout=self.timeout,
            )
            latency_ms = int((timezone.now() - started_at).total_seconds() * 1000)
            message.mark_dispatched(
                attempted_at=started_at,
                http_status=response.status_code,
                latency_ms=latency_ms,
            )
        except requests.RequestException as exc:
            logger.exception("Error de red al llamar a Alegra")
            message.mark_failed(
                "network_error",
                str(exc),
                retryable=True,
            )
            raise AlegraAPIError(
                "Error de red al comunicarse con Alegra",
                status_code=None,
                error_code="network_error",
                retryable=True,
            ) from exc

        body = self._parse_response_body(response)
        if response.ok:
            message.mark_processed(body, http_status=response.status_code, latency_ms=latency_ms)
            return body

        error_code, retryable = map_status(response.status_code)
        error_message = extract_error_message(body)
        message.mark_failed(
            error_code,
            error_message,
            http_status=response.status_code,
            retryable=retryable,
        )
        raise AlegraAPIError(
            f"Alegra respondió {response.status_code}: {error_message}",
            status_code=response.status_code,
            error_code=error_code,
            retryable=retryable,
            payload=body if isinstance(body, dict) else {"raw": body},
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_headers(self) -> Dict[str, str]:
        token_bytes = f"{self.api_key}:{self.api_secret}".encode()
        basic = base64.b64encode(token_bytes).decode()
        return {
            "Authorization": f"Basic {basic}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _build_url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def _log_outbound_message(
        self,
        *,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]],
        payload: Optional[Dict[str, Any]],
        event_type: str,
        external_reference: str,
    ) -> IntegrationMessage:
        request_payload = {
            "method": method.upper(),
            "url": url,
            "params": params or {},
            "body": payload or {},
        }

        if not external_reference and payload and "external_reference" in payload:
            external_reference = str(payload["external_reference"])
        idempotency_key = external_reference or ""
        if not idempotency_key and payload and payload.get("id"):
            idempotency_key = str(payload["id"])

        return IntegrationMessage.objects.create(
            organization_id=self.organization_id,
            integration=IntegrationMessage.INTEGRATION_ALEGRA,
            direction=IntegrationMessage.DIRECTION_OUTBOUND,
            event_type=event_type or method.upper(),
            external_reference=external_reference,
            idempotency_key=idempotency_key,
            payload=request_payload,
        )

    @staticmethod
    def _as_uuid(value):
        if isinstance(value, uuid.UUID):
            return value
        if hasattr(value, "id"):
            return AlegraClient._as_uuid(value.id)
        return uuid.UUID(str(value))

    def _parse_response_body(self, response: requests.Response) -> Dict[str, Any]:
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            return {"raw": response.text}

    # ------------------------------------------------------------------
    # Customer (Contact) Management
    # ------------------------------------------------------------------
    def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single customer by ID."""
        try:
            return self.request("GET", f"contacts/{customer_id}", event_type="customer.get", external_reference=customer_id)
        except AlegraAPIError as e:
            if e.status_code == 404:
                return None
            raise

    def search_customers(self, query: str) -> List[Dict[str, Any]]:
        """Searches for customers by query (e.g., email, identification)."""
        # Alegra's /contacts endpoint supports a 'query' parameter for searching.
        # The documentation implies it searches across various fields.
        return self.request("GET", "contacts", params={"query": query}, event_type="customer.search", external_reference=query)

    def create_customer(self, customer_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new customer in Alegra."""
        return self.request("POST", "contacts", json=customer_payload, event_type="customer.create", external_reference=customer_payload.get("name"))

    def create_invoice(self, invoice_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new sales invoice in Alegra."""
        return self.request("POST", "invoices", json=invoice_payload, event_type="invoice.create", external_reference=invoice_payload.get("client", {}).get("id"))
