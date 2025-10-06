
from celery import shared_task
import logging

from .services import ShopifyToErpNextService

logger = logging.getLogger(__name__)


@shared_task
def process_shopify_order(organization_id: str, order_data: dict):
    """
    Celery task to process a Shopify order and create a Sales Invoice in ERPNext.
    """
    logger.info(
        f"Processing Shopify order for organization {organization_id}."
    )
    try:
        service = ShopifyToErpNextService(organization_id, order_data)
        service.process()
        logger.info(
            f"Successfully processed Shopify order for organization {organization_id}."
        )
    except Exception as e:
        logger.error(
            f"Failed to process Shopify order for organization {organization_id}: {e}"
        )
