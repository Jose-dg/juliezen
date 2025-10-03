from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.integrations"
    verbose_name = "Integrations"

    def ready(self) -> None:  # pragma: no cover
        from . import handlers  # noqa: F401
        return super().ready()
