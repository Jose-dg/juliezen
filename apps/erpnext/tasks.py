# tasks.py
import math
import logging
from celery import shared_task
from .services import ERPNextClient, ERPNextClientError
from .models import ERPNextCredential

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def create_invoices_from_pending_orders_task(self, organization_id: str):
    cred = ERPNextCredential.objects.active().filter(organization_id=organization_id).first()
    if not cred:
        logger.error("No ERPNextCredential for org %s", organization_id)
        return

    client = ERPNextClient(cred)

    # 1) contar y paginar
    limit = 50
    offset = 0

    common_filters = [
        ["Sales Order", "docstatus", "=", 1],
        ["Sales Order", "status", "in", ["To Bill", "To Deliver and Bill"]],
        ["Sales Order", "per_billed", "<", 100],
        ["Sales Order", "status", "!=", "Closed"],
        ["Sales Order", "status", "!=", "Stopped"],
    ]
    fields = ["name", "customer", "grand_total", "per_billed"]

    while True:
        sos = client.list_sales_orders(filters=common_filters, fields=fields, limit=limit, offset=offset)
        if not sos:
            break

        for so in sos:
            so_name = so["name"]
            try:
                # Si necesitas due_date = posting_date (contado) o regla de crédito, calcula aquí
                client.create_and_submit_invoice_from_order(so_name, update_stock=False)
                logger.info("Submitted SI from SO %s", so_name)
            except ERPNextClientError as e:
                logger.exception("Failed SI for SO %s: %s", so_name, e)
                # continúa con el siguiente (no abortar el batch)
                continue

        if len(sos) < limit:
            break
        offset += limit
