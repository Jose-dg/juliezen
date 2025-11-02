from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.integrations"
    verbose_name = "Integrations"

    def ready(self) -> None:  # pragma: no cover
        super().ready()
        # Import here to avoid circular dependencies at startup
        from events import event_bus
        from events.events.integration_events import ShopifyWebhookReceivedEvent
        from .handlers.listeners import handle_shopify_webhook_received

        event_bus.subscribe(ShopifyWebhookReceivedEvent.event_type, handle_shopify_webhook_received)
        print("[INTEGRATIONS APP] Subscribed handle_shopify_webhook_received to ShopifyWebhookReceivedEvent")
