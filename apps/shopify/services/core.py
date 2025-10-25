import json
import logging

from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from events import event_bus
from events.events.integration_events import ShopifyWebhookReceivedEvent

logger = logging.getLogger(__name__)

def process_shopify_webhook(request: HttpRequest) -> Response:
    """
    Processes an incoming Shopify webhook request by publishing an event.
    """
    logger.info("[%s] Shopify Webhook Received", "SERVICE")
    shopify_domain = request.headers.get("X-Shopify-Shop-Domain")
    if not shopify_domain:
        logger.warning("[%s] Missing X-Shopify-Shop-Domain header.", "SERVICE")
        return Response(
            {"detail": "Missing X-Shopify-Shop-Domain header."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    logger.info("[%s] From domain: %s", "SERVICE", shopify_domain)

    raw_body = request.body
    try:
        body = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError:
        logger.error("[%s] Failed to decode JSON body for domain: %s", "SERVICE", shopify_domain)
        body = {}

    event = ShopifyWebhookReceivedEvent(
        shopify_domain=shopify_domain,
        headers=dict(request.headers),
        body=body,
        raw_body=raw_body,
    )
    event_bus.publish(event)
    logger.info("[%s] Published ShopifyWebhookReceivedEvent for domain: %s", "SERVICE", shopify_domain)

    return Response({"detail": "Webhook received successfully."}, status=status.HTTP_202_ACCEPTED)