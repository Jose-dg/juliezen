from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils.translation import gettext_lazy as _

from .models import User


class UserCreationAdminForm(forms.ModelForm):
    """Form de creación que usa email como campo principal."""

    password1 = forms.CharField(label=_("Password"), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password confirmation"), widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "username")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeAdminForm(forms.ModelForm):
    """Form de edición que mantiene el hash de la contraseña."""

    password = ReadOnlyPasswordHashField(label=_("Password"))

    class Meta:
        model = User
        fields = (
            "email",
            "password",
            "first_name",
            "last_name",
            "username",
            "style_preferences",
            "size_profile",
            "shopping_behavior",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )

    def clean_password(self):
        return self.initial.get("password")


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = UserCreationAdminForm
    form = UserChangeAdminForm
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
            {
                "fields": ("first_name", "last_name", "username"),
            },
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
