from events.events.alegra_events import ErpnextPosInvoiceSubmitted, ErpnextSalesInvoiceSubmitted
from apps.alegra.services.erpnext_invoice import process_erpnext_pos_invoice
from apps.alegra.services.erpnext_sales_invoice import process_erpnext_sales_invoice
from events.bus import event_bus

def handle_erpnext_pos_invoice_submitted(event: ErpnextPosInvoiceSubmitted):
    print("--- PASO 16: HANDLER handle_erpnext_pos_invoice_submitted INICIADO ---")
    print(f"--- PASO 17: LLAMANDO AL SERVICIO process_erpnext_pos_invoice ---\nEVENTO: {event}")
    process_erpnext_pos_invoice(event.payload, event.organization_id, str(event.message_id))

def handle_erpnext_sales_invoice_submitted(event: ErpnextSalesInvoiceSubmitted):
    print("--- PASO 16: HANDLER handle_erpnext_sales_invoice_submitted INICIADO ---")
    print(f"--- PASO 17: LLAMANDO AL SERVICIO process_erpnext_sales_invoice ---\nEVENTO: {event}")
    process_erpnext_sales_invoice(event.payload, event.organization_id, str(event.message_id))

def register_handlers():
    event_bus.subscribe(ErpnextPosInvoiceSubmitted.event_type, handle_erpnext_pos_invoice_submitted)
    event_bus.subscribe(ErpnextSalesInvoiceSubmitted.event_type, handle_erpnext_sales_invoice_submitted)

register_handlers()
