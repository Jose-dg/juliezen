from django.contrib import admin

from .models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (None, {"fields": ("name", "slug", "is_active")}),
        ("Metadatos", {"fields": ("metadata",), "classes": ("collapse",)}),
        ("Auditoría", {"fields": ("id", "created_at", "updated_at")}),
    )
