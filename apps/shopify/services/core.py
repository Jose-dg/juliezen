import json

from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from events import event_bus
from events.events.integration_events import ShopifyWebhookReceivedEvent


def process_shopify_webhook(request: HttpRequest) -> Response:
    """
    Processes an incoming Shopify webhook request by publishing an event.
    """
    print(f"\n{'--'*20} [SERVICE] Shopify Webhook Received {'--'*20}")
    shopify_domain = request.headers.get("X-Shopify-Shop-Domain")
    if not shopify_domain:
        return Response(
            {"detail": "Missing X-Shopify-Shop-Domain header."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    print(f"[SERVICE] From domain: {shopify_domain}")

    raw_body = request.body
    try:
        body = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError:
        body = {}

    event = ShopifyWebhookReceivedEvent(
        shopify_domain=shopify_domain,
        headers=dict(request.headers),
        body=body,
        raw_body=raw_body,
    )
    event_bus.publish(event)
    print(f"[SERVICE] Published ShopifyWebhookReceivedEvent for domain: {shopify_domain}")

    return Response({"detail": "Webhook received successfully."}, status=status.HTTP_202_ACCEPTED)