from typing import Dict, Any

from events.events.alegra_events import ErpnextPosInvoiceSubmitted, ErpnextSalesInvoiceSubmitted, ERPNextInvoiceSyncRequested
from apps.alegra.services.erpnext_invoice_sync import ERPNextToAlegraInvoiceService
from apps.integrations.models import IntegrationMessage
from events.bus import event_bus

from apps.integrations.router import registry

SUPPORTED_DOCTYPES = {"POS Invoice", "Sales Invoice"}

@registry.register(IntegrationMessage.INTEGRATION_ALEGRA, "on_submit")
def sync_invoice_to_alegra(message: IntegrationMessage):
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

def handle_erpnext_pos_invoice_submitted(event: ErpnextPosInvoiceSubmitted):
    print("--- PASO 16: HANDLER handle_erpnext_pos_invoice_submitted INICIADO ---")
    message = IntegrationMessage.objects.get(id=event.message_id)
    service = ERPNextToAlegraInvoiceService(message)
    service.process()

def handle_erpnext_sales_invoice_submitted(event: ErpnextSalesInvoiceSubmitted):
    print("--- PASO 16: HANDLER handle_erpnext_sales_invoice_submitted INICIADO ---")
    message = IntegrationMessage.objects.get(id=event.message_id)
    service = ERPNextToAlegraInvoiceService(message)
    service.process()

def handle_erpnext_invoice_sync_requested(event: ERPNextInvoiceSyncRequested):
    message = IntegrationMessage.objects.get(id=event.message_id)
    service = ERPNextToAlegraInvoiceService(message)
    service.process()


def register_handlers():
    from events import event_bus
    from events.events.alegra_events import ErpnextPosInvoiceSubmitted, ErpnextSalesInvoiceSubmitted, ERPNextInvoiceSyncRequested
    event_bus.subscribe(ErpnextPosInvoiceSubmitted.event_type, handle_erpnext_pos_invoice_submitted)
    event_bus.subscribe(ErpnextSalesInvoiceSubmitted.event_type, handle_erpnext_sales_invoice_submitted)
    event_bus.subscribe(ERPNextInvoiceSyncRequested.event_type, handle_erpnext_invoice_sync_requested)

register_handlers()
