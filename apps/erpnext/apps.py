from django.apps import AppConfig


class ErpnextConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.erpnext"

    def ready(self) -> None:
        super().ready()
        from .handlers import register_handlers
        register_handlers()
