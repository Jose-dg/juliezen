from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "last_login",
    )
    list_filter = ("is_active", "is_staff", "is_superuser", "groups")
    ordering = ("email",)
    search_fields = ("email", "first_name", "last_name", "username")
    readonly_fields = ("id", "date_joined", "last_login")
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Información personal"),
            {"fields": ("first_name", "last_name", "username")},
        ),
        (
            "Preferencias",
            {
                "fields": ("style_preferences", "size_profile", "shopping_behavior"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Permisos"),
            {
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            },
        ),
        (
            _("Fechas relevantes"),
            {
                "fields": ("last_login", "date_joined", "id"),
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "username",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
    )
