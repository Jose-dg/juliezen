import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class AlegraCredentialQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def for_company(self, organization_id, company: str | None = None):
        qs = self.active().filter(organization_id=organization_id)
        if company:
            normalized = str(company).strip()
            credential = qs.filter(company__iexact=normalized).order_by("-updated_at").first()
            if credential:
                return credential
        return qs.order_by("-updated_at").first()


class AlegraCredential(models.Model):
    """Credential bundle used to authenticate against Alegra on behalf of an organisation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=120)
    company = models.CharField(
        max_length=140,
        blank=True,
        default="",
        help_text="Compañía de ERPNext asociada a estas credenciales de Alegra.",
    )
    email = models.CharField(max_length=255)
    token = models.TextField()
    base_url = models.URLField(default="https://api.alegra.com/api/v1")
    webhook_secret = models.TextField(blank=True, null=True)
    number_template_id = models.PositiveIntegerField(blank=True, null=True)
    auto_stamp_on_create = models.BooleanField(default=True)
    timeout_s = models.PositiveIntegerField(default=30)
    max_retries = models.PositiveIntegerField(default=3)
    metadata = models.JSONField(default=dict, blank=True)
    e_provider_api_key = models.TextField(blank=True, null=True)
    e_provider_base_url = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(blank=True, null=True)
    valid_until = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AlegraCredentialQuerySet.as_manager()

    class Meta:
        app_label = "alegra"
        indexes = [
            models.Index(fields=("organization_id", "is_active"), name="idx_alegra_company_active"),
            models.Index(fields=("organization_id", "company"), name="idx_alegra_org_company"),
        ]
        ordering = ("organization_id", "name")
        constraints = [
            models.UniqueConstraint(fields=("organization_id", "name"), name="uniq_alegra_credential_name"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        suffix = f" · {self.company}" if self.company else ""
        return f"{self.organization_id}{suffix} · {self.name}"

    def is_valid(self) -> bool:
        """Check if credential is currently active and not expired."""
        if not self.is_active:
            return False
        now = timezone.now()
        if self.valid_from and self.valid_from > now:
            return False
        if self.valid_until and self.valid_until < now:
            return False
        return True

    def get_basic_auth_token(self) -> str:
        return f"{self.email}:{self.token}"

    def clean(self):
        if not self.email:
            raise ValidationError({"email": "El email es obligatorio."})
        if not self.token:
            raise ValidationError({"token": "El token API es obligatorio."})
        if self.timeout_s <= 0:
            raise ValidationError({"timeout_s": "El timeout debe ser mayor a cero."})
        if self.max_retries < 0:
            raise ValidationError({"max_retries": "Los reintentos no pueden ser negativos."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
