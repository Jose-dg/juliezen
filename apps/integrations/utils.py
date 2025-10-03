from typing import Any, Dict, Optional
import uuid

from apps.integrations.models import IntegrationMessage


def _as_uuid(value) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    if hasattr(value, "id"):
        return _as_uuid(value.id)
    return uuid.UUID(str(value))


def record_integration_message(
    *,
    organization_id,
    direction: str,
    integration: str,
    event_type: str,
    payload: Dict[str, Any],
    external_reference: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    status: str = IntegrationMessage.STATUS_RECEIVED,
) -> IntegrationMessage:
    organization_uuid = _as_uuid(organization_id)
    external_reference = (external_reference or "").strip()
    idempotency_key = (idempotency_key or external_reference).strip()

    return IntegrationMessage.objects.create(
        organization_id=organization_uuid,
        direction=direction,
        integration=integration,
        event_type=event_type,
        external_reference=external_reference,
        idempotency_key=idempotency_key,
        payload=payload,
        status=status,
    )
