
import logging

from celery import shared_task

from .models import ERPNextCredential
from .services import ERPNextClient, ERPNextClientError

logger = logging.getLogger(__name__)


@shared_task(name="erpnext.create_invoices_from_pending_orders")
def create_invoices_from_pending_orders_task(organization_id: str):
    """
    A Celery task to find all Sales Orders 'To Bill' and create Sales Invoices for them.
    """
    logger.info("Starting task to create invoices for organization %s", organization_id)

    credential = ERPNextCredential.objects.active().filter(organization_id=organization_id).first()
    if not credential:
        logger.error("Task failed: No active ERPNext credentials for organization %s", organization_id)
        return {"status": "error", "message": "Credentials not found."}

    try:
        client = ERPNextClient(credential=credential)
        
        # Find all Sales Orders with status "To Bill"
        filters = '[["status","=","To Bill"]]' # Use string representation as expected by the service
        fields = '["name"]'
        pending_orders = client.list_sales_orders(filters=filters, fields=fields, limit=100) # Process 100 at a time

        if not pending_orders:
            logger.info("No pending Sales Orders to process for organization %s", organization_id)
            return {"status": "success", "invoices_created": 0, "details": []}

        logger.info("Found %d pending Sales Orders for organization %s", len(pending_orders), organization_id)
        
        created_invoices = []
        errors = []

        for order in pending_orders:
            order_name = order.get("name")
            if not order_name:
                continue
            
            try:
                invoice_doc = client.create_sales_invoice_from_order(order_name)
                logger.info("Successfully created Sales Invoice %s from Sales Order %s", invoice_doc.get("name"), order_name)
                created_invoices.append(invoice_doc.get("name"))
            except ERPNextClientError as e:
                logger.error("Failed to create invoice for Sales Order %s: %s", order_name, e)
                errors.append({"sales_order": order_name, "error": str(e)})

        result = {
            "status": "partial_success" if errors else "success",
            "invoices_created": len(created_invoices),
            "errors": len(errors),
            "details": {
                "created": created_invoices,
                "failed": errors,
            }
        }
        logger.info("Finished task for organization %s with result: %s", organization_id, result)
        return result

    except ERPNextClientError as e:
        logger.error("Task failed for organization %s during client operation: %s", organization_id, e)
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.exception("An unexpected error occurred in task for organization %s", organization_id)
        return {"status": "error", "message": "An unexpected internal error occurred."}

