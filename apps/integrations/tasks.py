from typing import Any, List

from celery import shared_task
from django.utils import timezone

from events import event_bus
from events.events import IntegrationInboundEvent, IntegrationOutboundEvent

from apps.integrations.models import IntegrationMessage
from apps.integrations.router import registry
from apps.integrations.error_codes import classify_exception
from apps.integrations.exceptions import BackorderPending


@shared_task(bind=True, autoretry_for=(BackorderPending,), max_retries=5, retry_backoff=True)
def process_integration_message(self, message_id: str) -> str:
    print(f"\n--- PASO 6: TAREA process_integration_message INICIADA ---\nMESSAGE_ID: {message_id}")
    message = IntegrationMessage.objects.filter(id=message_id).first()
    if not message:
        print("--- ERROR: MENSAJE NO ENCONTRADO ---")
        return message_id

    print(f"--- PASO 7: ESTADO Y DIRECCION DEL MENSAJE ---\nSTATUS: {message.status}\nDIRECTION: {message.direction}")
    if message.status not in {IntegrationMessage.STATUS_DISPATCHED, IntegrationMessage.STATUS_RECEIVED}:
        print("--- MENSAJE YA PROCESADO, SALTANDO ---")
        return message_id

    if message.direction == IntegrationMessage.DIRECTION_INBOUND:
        return _process_inbound_message(self, message)

    return _process_outbound_message(message)


def _process_inbound_message(task, message: IntegrationMessage) -> str:
    print("--- PASO 8: PROCESANDO MENSAJE INBOUND ---")
    event = IntegrationInboundEvent(
        company_id=str(message.organization_id),
        integration=message.integration,
        message_id=str(message.id),
        payload=message.payload,
        external_reference=message.external_reference,
        metadata={"received_at": message.received_at.isoformat()},
    )

    try:
        print("--- PASO 9: PUBLICANDO EVENTO EN EVENT BUS ---")
        results: List[Any] = event_bus.publish(event)
        print(f"--- PASO 10: RESULTADOS DEL EVENT BUS ---\n{results}")
        print("--- PASO 11: DESPACHANDO A REGISTRY ---")
        results.extend(registry.dispatch(message.integration, message.event_type or None, message))
        print(f"--- PASO 12: RESULTADOS DEL REGISTRY ---\n{results}")
        message.mark_acknowledged()
        message.mark_processed(
            response={"handlers": len(results), "results": [repr(r) for r in results]},
            http_status=202,
            latency_ms=None,
        )
        print("--- PASO 13: MENSAJE PROCESADO EXITOSAMENTE ---")
        return str(message.id)
    except BackorderPending as exc:
        print(f"--- INFO: ORDEN EN BACKORDER (ESPERANDO STOCK) ---\n{exc}")
        # The service layer already handled the status change, so we just log and exit gracefully.
        return str(message.id)
    except Exception as exc:
        print(f"--- ERROR DURANTE EL PROCESAMIENTO ---\n{exc}")
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
