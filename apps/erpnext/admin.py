
from django.contrib import admin

from .models import ERPNextCredential


@admin.register(ERPNextCredential)
class ERPNextCredentialAdmin(admin.ModelAdmin):
    list_display = ("organization_id", "erpnext_url", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("organization_id", "erpnext_url")
    readonly_fields = ("created_at", "updated_at", "id")
    fieldsets = (
        (None, {"fields": ("id", "organization_id", "erpnext_url")}),
        ("Credentials", {"fields": ("api_key", "api_secret")}),
        ("Status", {"fields": ("is_active",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

