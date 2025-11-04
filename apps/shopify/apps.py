from django.apps import AppConfig


class ShopifyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.shopify"

    def ready(self) -> None:
        super().ready()
        from .handlers import register_handlers
        register_handlers()
