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
    INTEGRATION_SHOPIFY = "shopify"
    INTEGRATION_ERPNEXT_POS = "erpnext_pos"

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

    MAX_AUTO_RETRIES = 3

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
        if self.status not in {self.STATUS_RECEIVED, self.STATUS_DISPATCHED}:
            return

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

    def mark_failed(
        self,
        error_code: str,
        error_message: str,
        *,
        http_status: int | None = None,
        retryable: bool = True,
    ):
        now = timezone.now()
        updates = {
            "error_code": error_code,
            "error_message": error_message,
            "processed_at": now,
            "last_attempt_at": now,
            "retries": self.retries + 1,
        }
        if retryable:
            delay = self._backoff_delay(self.retries)
            updates["next_attempt_at"] = now + timedelta(seconds=delay)
        else:
            updates["next_attempt_at"] = None
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
        from apps.integrations.tasks import process_integration_message

        process_integration_message.apply_async((str(clone.id),), countdown=delay)
        return clone

    @staticmethod
    def _backoff_delay(retries: int) -> int:
        base = 5 * (2 ** min(retries, 6))
        return min(base, 3600)
    

# {
#        "integrations": {
#          "shopify_to_erpnext": {
#            "company_selector": {
#              "tag_prefix": "cia:",
#              "domain_map": {
#                "229f93-2.myshopify.com": "TST",
#                "22sde3-2.myshopify.com": "M4G",
#                "229f23sd3-2.myshopify.com": "LAB"
#             },
#             "default_company": "TST"
#           },
#           "territory": "Colombia",
#           "currency": "COP",
#           "naming_series": "SINV-",
#           "set_posting_time": true,
#           "update_stock": true,
#           "due_days": 0,
#           "price_list": "Tarifa Estándar de Venta",
#           "price_list_currency": "COP",
#           "default_customer": "Cliente Contado",
#           "default_uom": "Unidad",
#           "shipping_item_code": "ENVIO",
#           "shipping_item_name": "Costo de Envío",
#           "item_code_map": {
#             "SKU_PRODUCTO_A": "ERP_CODIGO_A",
#             "SKU_PRODUCTO_B": "ERP_CODIGO_B",
#             "711719510674": "PS-GIFT-CARD-50",
#             "799366664771": "PS-GIFT-CARD-25",
#             "14633376753": "JUEGO-FIFA-22-PS4"
#           },
#           "receivable_account": "130505 - Clientes Nacionales - TST",
#           "debit_to": "130505 - Clientes Nacionales - TST",
#           "default_income_account": "4135 - Comercio al por mayor y al por menor - TST",
#           "default_cost_center": "Principal - TST",
#           "default_warehouse": "Almacén Principal - TST",
#           "tax_charge_type": "On Net Total",
#           "default_tax_account": "240801 - Impuesto sobre las ventas por pagar - TST",
#           "tax_account_map": {
#             "IVA 19%": "24080101 - IVA Generado 19% - TST",
#             "IVA 5%": "24080102 - IVA Generado 5% - TST"
#           }
#         }
#       }
#     }


class FulfillmentItemMapQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def for_source(self, *, organization_id, source: str, source_company: str):
        return (
            self.active()
            .filter(
                organization_id=organization_id,
                source=source,
                source_company=source_company,
            )
        )


class FulfillmentItemMap(models.Model):
    SOURCE_ERPNEXT = "erpnext"
    SOURCE_SHOPIFY = "shopify"
    SOURCE_CHOICES = (
        (SOURCE_ERPNEXT, "ERPNext"),
        (SOURCE_SHOPIFY, "Shopify"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    source = models.CharField(max_length=32, choices=SOURCE_CHOICES)
    source_company = models.CharField(max_length=140)
    source_item_code = models.CharField(max_length=140)
    target_company = models.CharField(max_length=140)
    target_item_code = models.CharField(max_length=140)
    warehouse = models.CharField(max_length=140, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = FulfillmentItemMapQuerySet.as_manager()

    class Meta:
        app_label = "integrations"
        ordering = ("organization_id", "source", "source_company", "source_item_code")
        constraints = [
            models.UniqueConstraint(
                fields=("organization_id", "source", "source_company", "source_item_code"),
                name="uniq_fmap_source_item",
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover - debug aid
        return (
            f"{self.organization_id} · {self.source}/{self.source_company}:{self.source_item_code}"
            f" → {self.target_company}:{self.target_item_code}"
        )


class FulfillmentOrderQuerySet(models.QuerySet):
    def for_order(self, *, organization_id, source: str, order_id: str):
        return self.filter(organization_id=organization_id, source=source, order_id=order_id)

    def needing_retry(self):
        now = timezone.now()
        return self.filter(status=self.model.STATUS_WAITING_STOCK).filter(
            models.Q(next_attempt_at__isnull=True) | models.Q(next_attempt_at__lte=now)
        )


class FulfillmentOrder(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_WAITING_STOCK = "waiting_stock"
    STATUS_FULFILLED = "fulfilled"
    STATUS_FAILED = "failed"
    STATUS_RETURNED = "returned"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_WAITING_STOCK, "Waiting Stock"),
        (STATUS_FULFILLED, "Fulfilled"),
        (STATUS_FAILED, "Failed"),
        (STATUS_RETURNED, "Returned"),
    )

    SOURCE_CHOICES = FulfillmentItemMap.SOURCE_CHOICES

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    source = models.CharField(max_length=32, choices=SOURCE_CHOICES)
    order_id = models.CharField(max_length=191)
    seller_company = models.CharField(max_length=140)
    distributor_company = models.CharField(max_length=140)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payload = models.JSONField(default=dict, blank=True)
    normalized_order = models.JSONField(default=dict, blank=True)
    fulfillment_payload = models.JSONField(default=dict, blank=True)
    result_payload = models.JSONField(default=dict, blank=True)
    serial_numbers = models.JSONField(default=list, blank=True)
    sales_order_name = models.CharField(max_length=140, blank=True)
    delivery_note_name = models.CharField(max_length=140, blank=True)
    delivery_note_submitted_at = models.DateTimeField(blank=True, null=True)
    return_delivery_note_name = models.CharField(max_length=140, blank=True)
    return_delivery_note_submitted_at = models.DateTimeField(blank=True, null=True)
    return_payload = models.JSONField(default=dict, blank=True)
    backorder_attempts = models.PositiveIntegerField(default=0)
    last_error_code = models.CharField(max_length=64, blank=True)
    last_error_message = models.TextField(blank=True)
    next_attempt_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = FulfillmentOrderQuerySet.as_manager()

    class Meta:
        app_label = "integrations"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization_id", "source", "order_id"),
                name="uniq_fulfillment_order",
            )
        ]

    def mark_status(self, status: str, *, error_code: str = "", error_message: str = "", next_attempt_at=None):
        updates = {"status": status}
        if error_code is not None:
            updates["last_error_code"] = error_code
        if error_message is not None:
            updates["last_error_message"] = error_message
        updates["updated_at"] = timezone.now()
        updates["next_attempt_at"] = next_attempt_at
        for field, value in updates.items():
            setattr(self, field, value)
        self.save(
            update_fields=list(updates.keys())
        )

    def record_fulfillment(
        self,
        *,
        delivery_note: str,
        serials: list[str],
        sales_order: str | None = None,
        result_payload: dict | None = None,
    ):
        self.delivery_note_name = delivery_note
        self.sales_order_name = sales_order or ""
        self.serial_numbers = serials
        self.result_payload = result_payload or {}
        self.delivery_note_submitted_at = timezone.now()
        self.status = self.STATUS_FULFILLED
        self.last_error_code = ""
        self.last_error_message = ""
        self.next_attempt_at = None
        self.save(
            update_fields=[
                "delivery_note_name",
                "sales_order_name",
                "serial_numbers",
                "result_payload",
                "delivery_note_submitted_at",
                "status",
                "last_error_code",
                "last_error_message",
                "next_attempt_at",
                "updated_at",
            ]
        )

    def record_return(
        self,
        *,
        delivery_note: str,
        payload: dict | None = None,
    ):
        self.return_delivery_note_name = delivery_note
        self.return_delivery_note_submitted_at = timezone.now()
        self.return_payload = payload or {}
        self.status = self.STATUS_RETURNED
        self.last_error_code = ""
        self.last_error_message = ""
        self.next_attempt_at = None
        self.save(
            update_fields=[
                "return_delivery_note_name",
                "return_delivery_note_submitted_at",
                "return_payload",
                "status",
                "last_error_code",
                "last_error_message",
                "next_attempt_at",
                "updated_at",
            ]
        )

    def mark_waiting_stock(self, *, error_message: str = "", delay_seconds: int = 900):
        self.status = self.STATUS_WAITING_STOCK
        self.backorder_attempts += 1
        self.last_error_code = "waiting_stock"
        self.last_error_message = error_message
        self.next_attempt_at = timezone.now() + timedelta(seconds=delay_seconds)
        self.updated_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "backorder_attempts",
                "last_error_code",
                "last_error_message",
                "next_attempt_at",
                "updated_at",
            ]
        )
