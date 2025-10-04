import logging
from typing import Any, Dict

from apps.integrations.models import IntegrationMessage
from apps.integrations.router import registry
from apps.alegra.services import process_erpnext_pos_invoice
from events import event_bus
from events.events import AccountingInvoiceSyncedEvent

logger = logging.getLogger(__name__)


@registry.register("alegra")
def log_integration_message(message: IntegrationMessage) -> Dict[str, Any]:
    """Default handler that logs inbound/outbound Alegra messages."""
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


@registry.register("alegra", "invoice.created")
@registry.register("alegra", "invoice.updated")
@registry.register("alegra", "sales.invoice.created")
@registry.register("alegra", "sales.invoice.updated")
def propagate_invoice_synced(message: IntegrationMessage) -> Dict[str, Any]:
    invoice = _extract_invoice_payload(message)
    invoice_id = str(invoice.get("id") or invoice.get("number") or invoice.get("name") or "")

    event = AccountingInvoiceSyncedEvent(
        company_id=str(message.organization_id),
        invoice_id=invoice_id,
        payload=invoice,
        metadata={
            "source": "alegra",
            "message_id": str(message.id),
            "event_type": message.event_type,
        },
    )
    event_bus.publish(event)
    logger.debug(
        "[ALEGRA] Published AccountingInvoiceSyncedEvent invoice=%s organization=%s",
        invoice_id,
        message.organization_id,
    )
    return {"invoice_id": invoice_id}


def _extract_invoice_payload(message: IntegrationMessage) -> Dict[str, Any]:
    payload = message.payload or {}
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    if payload.get("invoice"):
        return payload["invoice"]
    return payload


SUPPORTED_DOCTYPES = {"POS Invoice", "Sales Invoice"}


@registry.register("alegra", "on_submit")
def process_erpnext_invoice(message: IntegrationMessage) -> Dict[str, Any]:
    payload = message.payload or {}
    doctype = payload.get("doctype")
    if doctype not in SUPPORTED_DOCTYPES:
        return {"skipped": True, "reason": "unsupported_doctype", "doctype": doctype}
    return process_erpnext_pos_invoice(message)
