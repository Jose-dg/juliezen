
from __future__ import annotations

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class ERPNextCredentialManager(models.Manager):
    def active(self):
        return self.get_queryset().filter(is_active=True)


class ERPNextCredential(models.Model):
    """Stores API credentials for connecting to a specific ERPNext site."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(
        db_index=True, verbose_name=_("Organization ID")
    )
    erpnext_url = models.URLField(
        verbose_name=_("ERPNext Site URL"),
        help_text=_("The base URL of the ERPNext instance (e.g., https://mycompany.erpnext.com)"),
    )
    api_key = models.CharField(
        max_length=255,
        verbose_name=_("API Key"),
    )
    api_secret = models.CharField(
        max_length=255,
        verbose_name=_("API Secret"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
        help_text=_("Only active credentials will be used for API calls."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ERPNextCredentialManager()

    class Meta:
        verbose_name = _("ERPNext Credential")
        verbose_name_plural = _("ERPNext Credentials")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=("organization_id", "is_active"), name="idx_erpnext_org_active"),
        ]

    def __str__(self) -> str:
        return f"{self.organization_id} - {self.erpnext_url}"

