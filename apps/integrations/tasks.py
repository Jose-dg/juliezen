from typing import Any, List

from celery import shared_task
from django.utils import timezone

from events import event_bus
from events.events import IntegrationInboundEvent, IntegrationOutboundEvent

from apps.integrations.models import IntegrationMessage
from apps.integrations.router import registry
from apps.integrations.error_codes import classify_exception


@shared_task(bind=True, autoretry_for=(), max_retries=5, retry_backoff=True)
def process_integration_message(self, message_id: str) -> str:
    print(f"\n{'--'*20} [TASK] Processing integration message ID: {message_id} {'--'*20}")
    message = IntegrationMessage.objects.filter(id=message_id).first()
    if not message:
        return message_id

    if message.status not in {IntegrationMessage.STATUS_DISPATCHED, IntegrationMessage.STATUS_RECEIVED}:
        return message_id

    if message.direction == IntegrationMessage.DIRECTION_INBOUND:
        return _process_inbound_message(self, message)

    return _process_outbound_message(message)


def _process_inbound_message(task, message: IntegrationMessage) -> str:
    event = IntegrationInboundEvent(
        company_id=str(message.organization_id),
        integration=message.integration,
        message_id=str(message.id),
        payload=message.payload,
        external_reference=message.external_reference,
        metadata={"received_at": message.received_at.isoformat()},
    )

    try:
        results: List[Any] = event_bus.publish(event)
        results.extend(registry.dispatch(message.integration, message.event_type or None, message))
        message.mark_acknowledged()
        message.mark_processed(
            response={"handlers": len(results), "results": [repr(r) for r in results]},
            http_status=202,
            latency_ms=None,
        )
        return str(message.id)
    except Exception as exc:
        error_code, retryable, status_code = classify_exception(exc)
        message.mark_acknowledged()
        summary = {
            "status": "failed",
            "error_code": error_code,
            "retryable": retryable,
        }
        next_attempt_id = None
        if retryable and message.retries < IntegrationMessage.MAX_AUTO_RETRIES:
            message.retries = message.retries + 1
            message.save(update_fields=["retries"])
            clone = message.schedule_retry()
            summary["next_attempt_id"] = str(clone.id)
            if clone.next_attempt_at:
                summary["next_attempt_at"] = clone.next_attempt_at.isoformat()
        message.mark_processed(response=summary, http_status=status_code)
        return str(message.id)


def _process_outbound_message(message: IntegrationMessage) -> str:
    event = IntegrationOutboundEvent(
        company_id=str(message.organization_id),
        integration=message.integration,
        message_id=str(message.id),
        payload=message.payload,
        response=message.response_payload,
        external_reference=message.external_reference,
        metadata={"processed_at": timezone.now().isoformat()},
    )
    event_bus.publish(event)
    if message.status != IntegrationMessage.STATUS_PROCESSED:
        message.mark_processed(message.response_payload or {}, http_status=200)
    return str(message.id)
