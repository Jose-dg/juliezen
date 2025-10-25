
import logging
from typing import Optional

from celery import shared_task

from apps.integrations.models import IntegrationMessage

from .services import ShopifyToErpNextService

logger = logging.getLogger(__name__)


@shared_task
def process_shopify_order(organization_id: str, order_data: dict, message_id: Optional[str] = None):
    """
    Celery task to process a Shopify order and create a Sales Invoice in ERPNext.
    """
    print(f"\n{'-'*20} [TASK] Celery Task Started {'-'*20}")
    print(f"[TASK] Processing message ID: {message_id}")
    message = None
    if message_id:
        message = IntegrationMessage.objects.filter(id=message_id).first()

    logger.info("Processing Shopify order for organization %s.", organization_id)
    try:
        service = ShopifyToErpNextService(organization_id, order_data)
        result = service.process()
        invoice_name = result.get("invoice_name")

        logger.info("Successfully processed Shopify order for organization %s.", organization_id)
        if message:
            message.mark_acknowledged()
            message.mark_processed(
                response={
                    "status": "processed",
                    "invoice_name": invoice_name,
                    "outbound_request": result.get("outbound_request"),
                    "outbound_response": result.get("submitted_response"),
                },
                http_status=200,
            )
    except Exception as exc:
        logger.exception("Failed to process Shopify order for organization %s", organization_id)
        if message:
            message.mark_failed(
                error_code="shopify_processing_error",
                error_message=str(exc),
                http_status=500,
                retryable=False,
            )
