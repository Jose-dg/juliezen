from django.contrib import admin

from .models import IntegrationMessage


@admin.register(IntegrationMessage)
class IntegrationMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "integration",
        "direction",
        "status",
        "organization_id",
        "event_type",
        "external_reference",
        "http_status",
        "retries",
        "received_at",
        "short_error",
    )
    list_filter = ("integration", "status", "direction")
    search_fields = (
        "id",
        "external_reference",
        "event_type",
        "organization_id",
        "error_code",
        "idempotency_key",
    )
    readonly_fields = (
        "id",
        "received_at",
        "processed_at",
        "dispatched_at",
        "acknowledged_at",
        "last_attempt_at",
        "next_attempt_at",
        "payload",
        "response_payload",
    )
    date_hierarchy = "received_at"
    ordering = ("-received_at",)
    list_per_page = 50
    fieldsets = (
        (None, {"fields": ("id", "organization_id", "integration", "direction", "status")}),
        (
            "Identificadores",
            {
                "fields": (
                    "event_type",
                    "external_reference",
                    "idempotency_key",
                )
            },
        ),
        (
            "Payload",
            {
                "fields": ("payload", "response_payload"),
                "classes": ("collapse",),
            },
        ),
        (
            "Errores y reintentos",
            {
                "fields": (
                    "error_code",
                    "error_message",
                    "retries",
                    "http_status",
                    "latency_ms",
                    "last_attempt_at",
                    "next_attempt_at",
                )
            },
        ),
        (
            "Tiempos",
            {
                "fields": (
                    "received_at",
                    "dispatched_at",
                    "processed_at",
                    "acknowledged_at",
                )
            },
        ),
    )

    actions = ("resend_selected",)

    @admin.action(description="Reenviar mensajes seleccionados")
    def resend_selected(self, request, queryset):
        from apps.integrations.tasks import process_integration_message

        count = 0
        for message in queryset:
            process_integration_message.delay(str(message.id))
            count += 1
        self.message_user(request, f"Se reenviaron {count} mensajes a la cola de Celery.")

    @admin.display(description="Error")
    def short_error(self, obj):
        if not obj.error_message:
            return ""
        return (obj.error_message[:75] + "…") if len(obj.error_message) > 75 else obj.error_message
