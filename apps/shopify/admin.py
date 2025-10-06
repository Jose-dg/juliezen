from django.contrib import admin

from .models import ShopifyStore


@admin.register(ShopifyStore)
class ShopifyStoreAdmin(admin.ModelAdmin):
    """Admin configuration for the ShopifyStore model."""

    list_display = (
        "shopify_domain",
        "organization_id",
        "created_at",
    )
    search_fields = (
        "shopify_domain",
        "organization_id",
    )
    list_filter = ("organization_id",)
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            "Store Details",
            {
                "fields": (
                    "organization_id",
                    "shopify_domain",
                    "webhook_shared_secret",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )