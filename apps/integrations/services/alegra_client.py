import base64
import logging
import uuid
from typing import Any, Dict, Optional

import requests
from django.conf import settings
from django.utils import timezone

from apps.integrations.exceptions import AlegraAPIError, AlegraCredentialError
from apps.alegra.models import AlegraCredential
from apps.integrations.models import IntegrationMessage

logger = logging.getLogger(__name__)


class AlegraClient:
    """HTTP client for the Alegra API that logs integration activity."""

    def __init__(
        self,
        organization,
        *,
        credential: Optional[AlegraCredential] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.organization_id = self._as_uuid(organization)
        self.credential = credential or self._get_active_credential()
        if not self.credential or not self.credential.is_valid():
            raise AlegraCredentialError("No hay credenciales de Alegra válidas para la organización")

        self.session = session or requests.Session()
        self.base_url = getattr(settings, "ALEGRA_API_BASE_URL", self.credential.base_url)
        self.timeout = getattr(settings, "ALEGRA_API_TIMEOUT", self.credential.timeout_s)
        self.max_retries = getattr(settings, "ALEGRA_API_MAX_RETRIES", self.credential.max_retries)

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
            message.mark_failed("network_error", str(exc))
            raise AlegraAPIError("Error de red al comunicarse con Alegra") from exc

        body = self._parse_response_body(response)
        if response.ok:
            message.mark_processed(body, http_status=response.status_code, latency_ms=latency_ms)
            return body

        error_message = body if isinstance(body, str) else str(body)
        message.mark_failed(str(response.status_code), error_message, http_status=response.status_code)
        raise AlegraAPIError(f"Alegra respondió {response.status_code}: {error_message}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get_active_credential(self) -> Optional[AlegraCredential]:
        return (
            AlegraCredential.objects.active()
            .filter(organization_id=self.organization_id)
            .order_by("-updated_at")
            .first()
        )

    def _build_headers(self) -> Dict[str, str]:
        token_bytes = self.credential.get_basic_auth_token().encode()
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
