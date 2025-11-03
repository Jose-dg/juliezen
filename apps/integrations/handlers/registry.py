import logging
from typing import Any, Dict

from events import event_bus
from events.events import AccountingInvoiceSyncedEvent

from events.events.alegra_events import ErpnextPosInvoiceSubmitted, ErpnextSalesInvoiceSubmitted
from apps.erpnext.gateway import process_fulfillment_message
from apps.integrations.models import IntegrationMessage
from apps.integrations.router import registry
from apps.erpnext.services.alegra_invoice_sync import ERPNextToAlegraInvoiceService

logger = logging.getLogger(__name__)

SUPPORTED_DOCTYPES = {"POS Invoice", "Sales Invoice"}
SHOPIFY_EVENTS = {"orders.paid", "orders.updated", "order.paid"}
ERPNEXT_EVENTS = {"sales_invoice.on_submit", "sales_invoice.submit", "pos_invoice.on_submit"}


# ------------------------------------------------------------------
# Alegra
# ------------------------------------------------------------------
@registry.register(IntegrationMessage.INTEGRATION_ALEGRA)
def log_alegra_message(message: IntegrationMessage) -> Dict[str, Any]:
    """Log every Alegra integration message for traceability."""
    logger.info(
        "[ALEGRA][%s] message=%s event=%s retries=%s",
        message.direction,
        message.id,
        message.event_type,
        message.retries,
    )
    return {
        "message_id": str(message.id),
        "direction": message.direction,
        "event_type": message.event_type,
    }


@registry.register(IntegrationMessage.INTEGRATION_ALEGRA, "invoice.created")
@registry.register(IntegrationMessage.INTEGRATION_ALEGRA, "invoice.updated")
@registry.register(IntegrationMessage.INTEGRATION_ALEGRA, "sales.invoice.created")
@registry.register(IntegrationMessage.INTEGRATION_ALEGRA, "sales.invoice.updated")
def propagate_invoice_synced(message: IntegrationMessage) -> Dict[str, Any]:
    invoice = _extract_invoice_payload(message)
    invoice_id = str(invoice.get("id") or invoice.get("number") or invoice.get("name") or "")

    event_bus.publish(
        AccountingInvoiceSyncedEvent(
            company_id=str(message.organization_id),
            invoice_id=invoice_id,
            payload=invoice,
            metadata={
                "source": "alegra",
                "message_id": str(message.id),
                "event_type": message.event_type,
            },
        )
    )
    logger.debug(
        "[ALEGRA] Published AccountingInvoiceSyncedEvent invoice=%s organization=%s",
        invoice_id,
        message.organization_id,
    )
    return {"invoice_id": invoice_id}


@registry.register(IntegrationMessage.INTEGRATION_ALEGRA, "on_submit")
def sync_invoice_to_alegra(message: IntegrationMessage) -> Dict[str, Any]:
    print("--- PASO 13: HANDLER sync_invoice_to_alegra INICIADO ---")
    payload = message.payload or {}
    doctype = payload.get("doctype")
    print(f"--- PASO 14: DOCTYPE ---\n{doctype}")
    if doctype not in SUPPORTED_DOCTYPES:
        return {"skipped": True, "reason": "unsupported_doctype", "doctype": doctype}

    event = None
    if doctype == "POS Invoice":
        event = ErpnextPosInvoiceSubmitted(
            event_id=str(message.id),
            event_type="ErpnextPosInvoiceSubmitted",
            payload=payload,
            organization_id=message.organization_id,
            message_id=message.id,
        )
    elif doctype == "Sales Invoice":
        event = ErpnextSalesInvoiceSubmitted(
            event_id=str(message.id),
            event_type="ErpnextSalesInvoiceSubmitted",
            payload=payload,
            organization_id=message.organization_id,
            message_id=message.id,
        )

    if event:
        print(f"--- PASO 15: PUBLICANDO EVENTO ---\n{event}")
        event_bus.publish(event)
        return {"status": "event_published", "event_type": event.event_type}

    return {"skipped": True, "reason": "unhandled_doctype", "doctype": doctype}


def _extract_invoice_payload(message: IntegrationMessage) -> Dict[str, Any]:
    payload = message.payload or {}
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    if payload.get("invoice"):
        return payload["invoice"]
    return payload


# ------------------------------------------------------------------
# Fulfillment gateway (Shopify / ERPNext POS)
# ------------------------------------------------------------------
@registry.register(IntegrationMessage.INTEGRATION_SHOPIFY)
def handle_shopify_fulfillment(message: IntegrationMessage) -> Dict[str, Any]:
    if message.event_type and message.event_type not in SHOPIFY_EVENTS:
        logger.debug("[FULFILLMENT] Shopify event %s skipped.", message.event_type)
        return {"skipped": True, "reason": "unsupported_event"}
    result = process_fulfillment_message(message)
    return {"status": "processed", "result": result}


@registry.register(IntegrationMessage.INTEGRATION_ERPNEXT_POS)
def handle_erpnext_pos_fulfillment(message: IntegrationMessage) -> Dict[str, Any]:
    if message.event_type and message.event_type not in ERPNEXT_EVENTS:
        logger.info("[ERPNEXT] Received event_type: %s", message.event_type)
        logger.debug("[ERPNEXT] Event %s skipped as not in ERPNEXT_EVENTS.", message.event_type)
        return {"skipped": True, "reason": "unsupported_event"}

    # Check if the event is for Sales Invoice or POS Invoice submission
    if message.event_type in {"sales_invoice.on_submit", "pos_invoice.on_submit"}:
        logger.info("[ERPNEXT] Processing ERPNext invoice submission to Alegra.")
        try:
            service = ERPNextToAlegraInvoiceService(message)
            result = service.process()
            return {"status": "processed_to_alegra", "result": result}
        except Exception as e:
            logger.exception(f"[ERPNEXT] Error processing ERPNext invoice to Alegra: {e}")
            raise # Re-raise for task retry/failure
    else:
        # Existing fulfillment logic for other ERPNext events (if any)
        logger.info("[ERPNEXT] Processing ERPNext event with fulfillment logic.")
        result = process_fulfillment_message(message)
        return {"status": "processed_fulfillment", "result": result}

