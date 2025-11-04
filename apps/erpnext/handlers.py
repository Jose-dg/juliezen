import logging
from typing import Any, Dict

from events.events.erpnext_events import ERPNextFulfillmentRequested, ERPNextFulfillmentProcessRequested, ERPNextInvoiceSyncRequested
from events.events.integration_events import IntegrationMessageReceived
from apps.erpnext.gateway import process_fulfillment_message
from apps.integrations.models import IntegrationMessage
from events.bus import event_bus

logger = logging.getLogger(__name__)

ERPNEXT_EVENTS = {"sales_invoice.on_submit", "sales_invoice.submit", "pos_invoice.on_submit"}

def handle_integration_message_received(event: IntegrationMessageReceived):
    message = IntegrationMessage.objects.get(id=event.message_id)
    if message.integration != IntegrationMessage.INTEGRATION_ERPNEXT_POS:
        return

    if message.event_type and message.event_type not in ERPNEXT_EVENTS:
        logger.info("[ERPNEXT] Received event_type: %s", message.event_type)
        logger.debug("[ERPNEXT] Event %s skipped as not in ERPNEXT_EVENTS.", message.event_type)
        return {"skipped": True, "reason": "unsupported_event"}

    # Check if the event is for Sales Invoice or POS Invoice submission
    if message.event_type in {"sales_invoice.on_submit", "pos_invoice.on_submit"}:
        logger.info("[ERPNEXT] Publishing ERPNextInvoiceSyncRequested event.")
        event = ERPNextInvoiceSyncRequested(
            event_id=str(message.id),
            event_type="ERPNextInvoiceSyncRequested",
            message_id=message.id,
        )
        event_bus.publish(event)
        return {"status": "event_published", "event_type": event.event_type}
    else:
        logger.info("[ERPNEXT] Publishing ERPNextFulfillmentRequested event.")
        event = ERPNextFulfillmentRequested(
            event_id=str(message.id),
            event_type="ERPNextFulfillmentRequested",
            message_id=message.id,
        )
        event_bus.publish(event)
        return {"status": "event_published", "event_type": event.event_type}

def handle_erpnext_fulfillment_requested(event: ERPNextFulfillmentRequested):
    message = IntegrationMessage.objects.get(id=event.message_id)
    process_fulfillment_message(message)

def handle_erpnext_fulfillment_process_requested(event: ERPNextFulfillmentProcessRequested):
    message = IntegrationMessage.objects.get(id=event.message_id)
    process_fulfillment_message(message)

def register_handlers():
    from events import event_bus
    from events.events.erpnext_events import ERPNextFulfillmentRequested, ERPNextFulfillmentProcessRequested
    from events.events.integration_events import IntegrationMessageReceived
    event_bus.subscribe(ERPNextFulfillmentRequested.event_type, handle_erpnext_fulfillment_requested)
    event_bus.subscribe(ERPNextFulfillmentProcessRequested.event_type, handle_erpnext_fulfillment_process_requested)
    event_bus.subscribe(IntegrationMessageReceived.event_type, handle_integration_message_received)

register_handlers()