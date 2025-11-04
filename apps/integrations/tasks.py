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
    event_bus.publish(IntegrationMessageReceived(message_id=str(message.id)))

    try:
        print("--- PASO 9: PUBLICANDO EVENTO EN EVENT BUS ---")
        results: List[Any] = event_bus.publish(event)
        print(f"--- PASO 10: RESULTADOS DEL EVENT BUS ---\n{results}")
        print("--- PASO 11: DESPACHANDO A REGISTRY ---")
        results.extend(registry.dispatch(message.integration, message.event_type or None, message))
        print(f"--- PASO 12: RESULTADOS DEL REGISTRY ---\n{results}")
        message.mark_acknowledged()
        print("--- PASO 13.2: MENSAJE MARCADO COMO ACKNOWLEDGED ---")
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
        print("--- PASO 13.1: EXCEPCION CLASIFICADA ---")
        message.mark_acknowledged()
        summary = {
            "status": "failed",
            "error_code": error_code,
            "retryable": retryable,
            "exception": exc.__class__.__name__,
        }
        message.save(update_fields=["response_payload"])
        print("--- PASO 13.3: PAYLOAD DE RESPUESTA GUARDADO ---")
        message.mark_failed(
            error_code=error_code,
            error_message=str(exc),
            http_status=status_code,
            retryable=retryable,
        )
        print("--- PASO 13.4: MENSAJE MARCADO COMO FALLIDO ---")

        if retryable and message.retries < IntegrationMessage.MAX_AUTO_RETRIES:
            print("--- PASO 13.5: REINTENTO PROGRAMADO ---")
            clone = message.schedule_retry()
            summary["next_attempt_id"] = str(clone.id)
            if clone.next_attempt_at:
                summary["next_attempt_at"] = clone.next_attempt_at.isoformat()
            message.response_payload = summary
            message.save(update_fields=["response_payload"])
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
