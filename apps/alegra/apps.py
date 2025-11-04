from django.apps import AppConfig


class AlegraConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.alegra"
    verbose_name = "Alegra"

    def ready(self) -> None:
        super().ready()
        from .handlers import register_handlers
        register_handlers()
