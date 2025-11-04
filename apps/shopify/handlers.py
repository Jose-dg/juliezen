import base64
import hashlib
import hmac

from django.conf import settings

from apps.integrations.models import IntegrationMessage
from apps.integrations.tasks import process_integration_message
from apps.integrations.utils import record_integration_message
from apps.shopify.models import ShopifyStore

def _validate_webhook(secret: str, signature: str, body: bytes) -> bool:
    """Validates the HMAC-SHA256 signature of the webhook."""
    if not signature:
        return False

    computed_hmac = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).digest()
    computed_hmac_b64 = base64.b64encode(computed_hmac)

    return hmac.compare_digest(computed_hmac_b64, signature.encode("utf-8"))

def handle_shopify_webhook_received(event):
    """
    Listener for the ShopifyWebhookReceivedEvent.
    """
    print(f"\n{'--'*20} [LISTENER] Shopify Webhook Event Received {'--'*20}")
    shopify_domain = event.shopify_domain
    headers = event.headers
    payload = event.body
    raw_body = event.raw_body

    print(f"[LISTENER] From domain: {shopify_domain}")

    try:
        store = ShopifyStore.objects.get(shopify_domain=shopify_domain)
    except ShopifyStore.DoesNotExist:
        print(f"[LISTENER] ERROR: Shopify store not found for domain: {shopify_domain}")
        return

    if not store.webhook_shared_secret:
        print(f"[LISTENER] ERROR: Shopify webhook shared secret is not configured for domain: {shopify_domain}")
        return

    if not settings.DEBUG:
        signature = headers.get("X-Shopify-Hmac-Sha256")
        if not _validate_webhook(store.webhook_shared_secret, signature, raw_body):
            print(f"[LISTENER] ERROR: Webhook signature validation failed for domain: {shopify_domain}")
            return
    else:
        print("[LISTENER] WARNING: Webhook signature validation is disabled in DEBUG mode.")

    topic = headers.get("X-Shopify-Topic", "")
    event_type = topic.replace("/", ".") if topic else ""
    webhook_id = headers.get("X-Shopify-Webhook-Id", "")
    external_reference = payload.get("id") or payload.get("name") or payload.get("order_number") or ""
    payload.setdefault("_shopify_domain", store.shopify_domain)
    if event_type:
        payload.setdefault("_event_type", event_type)

    message = record_integration_message(
        organization_id=store.organization_id,
        direction=IntegrationMessage.DIRECTION_INBOUND,
        integration=IntegrationMessage.INTEGRATION_SHOPIFY,
        event_type=event_type,
        payload=payload,
        external_reference=str(external_reference),
        idempotency_key=webhook_id,
    )
    print(f"[LISTENER] IntegrationMessage created with ID: {message.id}")
    message.mark_dispatched()

    print(f"[LISTENER] Queuing integration processor task for message ID: {message.id}")
    process_integration_message.delay(str(message.id))

def register_handlers():
    from events import event_bus
    from events.events.integration_events import ShopifyWebhookReceivedEvent
    event_bus.subscribe(ShopifyWebhookReceivedEvent.event_type, handle_shopify_webhook_received)
    print("[SHOPIFY APP] Subscribed handle_shopify_webhook_received to ShopifyWebhookReceivedEvent")