import json
import uuid
from datetime import timedelta

from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

class IntegrationMessageQuerySet(models.QuerySet):
    def for_company(self, company_id):
        return self.filter(organization_id=company_id)

    def for_organization(self, organization_id):
        return self.filter(organization_id=organization_id)

    def pending(self):
        now = timezone.now()
        return (
            self.filter(status=IntegrationMessage.STATUS_RECEIVED)
            .filter(models.Q(next_attempt_at__isnull=True) | models.Q(next_attempt_at__lte=now))
        )


class IntegrationMessage(models.Model):
    """Registro persistente de mensajes de integraciones."""

    INTEGRATION_ALEGRA = "alegra"

    DIRECTION_INBOUND = "inbound"
    DIRECTION_OUTBOUND = "outbound"
    DIRECTION_CHOICES = (
        (DIRECTION_INBOUND, "Inbound"),
        (DIRECTION_OUTBOUND, "Outbound"),
    )

    STATUS_RECEIVED = "received"
    STATUS_DISPATCHED = "dispatched"
    STATUS_ACK = "acknowledged"
    STATUS_FAILED = "failed"
    STATUS_PROCESSED = "processed"
    STATUS_CHOICES = (
        (STATUS_RECEIVED, "Received"),
        (STATUS_DISPATCHED, "Dispatched"),
        (STATUS_ACK, "Acknowledged"),
        (STATUS_FAILED, "Failed"),
        (STATUS_PROCESSED, "Processed"),
    )

    MAX_PAYLOAD_BYTES = 512 * 1024  # 512 KB por mensaje integrado

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    integration = models.CharField(max_length=50, default=INTEGRATION_ALEGRA)
    direction = models.CharField(max_length=12, choices=DIRECTION_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RECEIVED)
    event_type = models.CharField(max_length=120, blank=True)
    external_reference = models.CharField(max_length=191, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    retries = models.PositiveIntegerField(default=0)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    acknowledged_at = models.DateTimeField(blank=True, null=True)
    dispatched_at = models.DateTimeField(blank=True, null=True)
    last_attempt_at = models.DateTimeField(blank=True, null=True)
    next_attempt_at = models.DateTimeField(blank=True, null=True)
    http_status = models.PositiveIntegerField(blank=True, null=True)
    latency_ms = models.PositiveIntegerField(blank=True, null=True)
    idempotency_key = models.CharField(max_length=191, blank=True)

    objects = IntegrationMessageQuerySet.as_manager()

    ALLOWED_TRANSITIONS = {
        STATUS_RECEIVED: {STATUS_DISPATCHED, STATUS_FAILED},
        STATUS_DISPATCHED: {STATUS_ACK, STATUS_PROCESSED, STATUS_FAILED},
        STATUS_ACK: {STATUS_PROCESSED, STATUS_FAILED},
        STATUS_FAILED: {STATUS_RECEIVED},
        STATUS_PROCESSED: set(),
    }

    class Meta:
        app_label = "integrations"
        ordering = ("-received_at",)
        indexes = [
            models.Index(
                fields=("organization_id", "integration", "external_reference"),
                name="idx_integration_reference",
            ),
            models.Index(fields=("status", "integration"), name="idx_integration_status"),
            models.Index(
                fields=("organization_id", "integration", "status", "received_at"),
                name="idx_integration_company_status",
            ),
            GinIndex(fields=["payload"], name="idx_integration_payload_gin"),
        ]

    def clean(self):
        self._validate_payload_size("payload", self.payload)
        self._validate_payload_size("response_payload", self.response_payload)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def _validate_payload_size(self, field_name: str, value: dict) -> None:
        if not value:
            return
        size = len(json.dumps(value, ensure_ascii=False).encode("utf-8"))
        if size > self.MAX_PAYLOAD_BYTES:
            raise ValidationError({field_name: "Payload demasiado grande; use almacenamiento externo."})

    def _transition(self, target_status: str, updates: dict) -> None:
        previous_status = self.status
        with transaction.atomic():
            current = type(self).objects.select_for_update().get(pk=self.pk)
            if target_status != current.status:
                allowed = self.ALLOWED_TRANSITIONS.get(current.status, set())
                if target_status not in allowed:
                    raise ValidationError(
                        {
                            "status": f"Transición inválida de {current.status} a {target_status}",
                        }
                    )
                current.status = target_status
            for attr, value in updates.items():
                setattr(current, attr, value)
            update_fields = set(updates.keys())
            if target_status != previous_status:
                update_fields.add("status")
            current.save(update_fields=list(update_fields))
            self.refresh_from_db()

    def mark_dispatched(self, *, attempted_at=None, http_status: int | None = None, latency_ms: int | None = None):
        attempted_at = attempted_at or timezone.now()
        updates = {
            "dispatched_at": attempted_at,
            "last_attempt_at": attempted_at,
            "next_attempt_at": None,
        }
        if http_status is not None:
            updates["http_status"] = http_status
        if latency_ms is not None:
            updates["latency_ms"] = latency_ms
        self._transition(self.STATUS_DISPATCHED, updates)

    def mark_processed(self, response=None, *, http_status: int | None = None, latency_ms: int | None = None):
        updates = {
            "processed_at": timezone.now(),
            "next_attempt_at": None,
        }
        if response is not None:
            updates["response_payload"] = response
        if http_status is not None:
            updates["http_status"] = http_status
        if latency_ms is not None:
            updates["latency_ms"] = latency_ms
        self._transition(self.STATUS_PROCESSED, updates)

    def mark_acknowledged(self):
        self._transition(
            self.STATUS_ACK,
            {
                "acknowledged_at": timezone.now(),
            },
        )

    def mark_failed(self, error_code: str, error_message: str, *, http_status: int | None = None):
        now = timezone.now()
        delay = self._backoff_delay(self.retries)
        updates = {
            "error_code": error_code,
            "error_message": error_message,
            "processed_at": now,
            "last_attempt_at": now,
            "next_attempt_at": now + timedelta(seconds=delay),
            "retries": self.retries + 1,
        }
        if http_status is not None:
            updates["http_status"] = http_status
        self._transition(self.STATUS_FAILED, updates)

    def schedule_retry(self, *, force_delay_seconds: int | None = None) -> "IntegrationMessage":
        now = timezone.now()
        delay = force_delay_seconds if force_delay_seconds is not None else self._backoff_delay(self.retries)
        clone = IntegrationMessage.objects.create(
            organization_id=self.organization_id,
            integration=self.integration,
            direction=self.direction,
            event_type=self.event_type,
            external_reference=self.external_reference,
            idempotency_key=self.idempotency_key,
            payload=self.payload,
            status=self.STATUS_RECEIVED,
            retries=self.retries,
            error_code="",
            error_message="",
            next_attempt_at=now + timedelta(seconds=delay),
        )
        return clone

    @staticmethod
    def _backoff_delay(retries: int) -> int:
        base = 5 * (2 ** min(retries, 6))
        return min(base, 3600)
