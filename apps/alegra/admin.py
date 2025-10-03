from django.contrib import admin

from .models import AlegraCredential


@admin.register(AlegraCredential)
class AlegraCredentialAdmin(admin.ModelAdmin):
    list_display = (
        "organization_id",
        "name",
        "email",
        "is_active",
        "timeout_s",
        "max_retries",
        "valid_from",
        "valid_until",
        "updated_at",
    )
    list_filter = ("is_active", "auto_stamp_on_create")
    search_fields = ("organization_id", "name", "email", "base_url")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("organization_id", "name")
    date_hierarchy = "created_at"
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "organization_id",
                    "name",
                    "email",
                    "is_active",
                )
            },
        ),
        (
            "Credenciales",
            {
                "fields": (
                    "token",
                    "base_url",
                    "webhook_secret",
                    "number_template_id",
                    "auto_stamp_on_create",
                    "timeout_s",
                    "max_retries",
                )
            },
        ),
        (
            "Proveedor electrónico",
            {
                "fields": ("e_provider_api_key", "e_provider_base_url"),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadatos",
            {
                "fields": ("metadata",),
                "classes": ("collapse",),
            },
        ),
        (
            "Vigencia",
            {
                "fields": ("valid_from", "valid_until"),
            },
        ),
        (
            "Auditoría",
            {
                "fields": ("id", "created_at", "updated_at"),
            },
        ),
    )
