from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from apps.integrations.exceptions import (
    BackorderPending,
    FulfillmentConfigurationError,
    FulfillmentError,
)
from apps.integrations.models import FulfillmentItemMap, FulfillmentOrder, IntegrationMessage
from apps.organizations.models import Organization
from apps.erpnext.models import ERPNextCredential
from apps.erpnext.services.client import ERPNextClient, ERPNextClientError

from .dto import OrderDTO
from .executor import FulfillmentExecutor, FulfillmentResult
from .exceptions import GatewayConfigurationError
from .mapper import LineMapper
from .normalizer import OrderNormalizer
from .returns import FulfillmentReturnService
from .settings import GatewaySettings

logger = logging.getLogger(__name__)


class FulfillmentGatewayService:
    """High-level orchestrator for multi-company fulfillment in ERPNext."""

    def __init__(self, message: IntegrationMessage) -> None:
        self.message = message
        self.organization = self._load_organization(message.organization_id)
        try:
            self.settings = GatewaySettings(getattr(self.organization, "metadata", {}))
        except GatewayConfigurationError as exc:
            raise FulfillmentConfigurationError(str(exc)) from exc
        if not self.settings.distributor_company:
            raise FulfillmentConfigurationError(
                "metadata.fulfillment_gateway.distributor_company es obligatorio."
            )

        self.source = self._resolve_source()
        self.payload = message.payload or {}
        self.fulfillment_order = self._ensure_fulfillment_order()
        self.distributor_credential = self._resolve_distributor_credential()
        if not self.distributor_credential:
            raise FulfillmentConfigurationError(
                f"No hay credenciales activas para la compañía distribuidora "
                f"{self.fulfillment_order.distributor_company}."
            )
        self.distributor_client = ERPNextClient(self.distributor_credential)

        self.normalizer = OrderNormalizer(self.organization.id, self.settings)
        self.line_mapper = LineMapper(self.organization.id, self.settings)
        self.executor = FulfillmentExecutor(self.distributor_client, self.settings)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def process(self) -> Dict[str, Any]:
        if self.fulfillment_order.status == FulfillmentOrder.STATUS_FULFILLED:
            logger.info(
                "[FULFILLMENT] Order %s already fulfilled via DN %s",
                self.fulfillment_order.order_id,
                self.fulfillment_order.delivery_note_name,
            )
            return {
                "delivery_note": self.fulfillment_order.delivery_note_name,
                "sales_order": self.fulfillment_order.sales_order_name,
                "serials": self.fulfillment_order.serial_numbers,
                "status": "already_fulfilled",
            }

        self.fulfillment_order.mark_status(FulfillmentOrder.STATUS_PROCESSING)

        try:
            order = self._normalize_order()
            mapped_lines, snapshot = self.line_mapper.map_lines(order)
            self._store_mapping_snapshot(snapshot)

            self.executor.assign_serials(mapped_lines)
            result = self._create_documents(order, mapped_lines)

            self.fulfillment_order.record_fulfillment(
                delivery_note=result.delivery_note,
                serials=result.serials,
                sales_order=result.sales_order,
                result_payload={
                    "delivery_note": result.delivery_note,
                    "sales_order": result.sales_order,
                    "serials": result.serials,
                    "line_serials": result.line_serials,
                },
            )
            self._propagate_status(order, result.delivery_note)
            return {
                "delivery_note": result.delivery_note,
                "sales_order": result.sales_order,
                "serials": result.serials,
                "line_serials": result.line_serials,
            }
        except BackorderPending as exc:
            logger.info(
                "[FULFILLMENT] Order %s waiting for stock: %s",
                self.fulfillment_order.order_id,
                exc,
            )
            self.fulfillment_order.mark_waiting_stock(
                error_message=str(exc),
                delay_seconds=self.settings.backorder_retry_seconds,
            )
            raise
        except FulfillmentError as exc:
            logger.exception("[FULFILLMENT] Error processing order %s", self.fulfillment_order.order_id)
            self.fulfillment_order.mark_status(
                FulfillmentOrder.STATUS_FAILED,
                error_code=exc.error_code,
                error_message=str(exc),
                next_attempt_at=None,
            )
            raise
        except ERPNextClientError as exc:
            logger.exception("[FULFILLMENT] ERPNext client error processing order %s", self.fulfillment_order.order_id)
            self.fulfillment_order.mark_status(
                FulfillmentOrder.STATUS_FAILED,
                error_code="erpnext_error",
                error_message=str(exc),
                next_attempt_at=None,
            )
            raise FulfillmentError(str(exc), error_code="erpnext_error", retryable=True, status_code=502) from exc
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.exception("[FULFILLMENT] Unexpected error processing order %s", self.fulfillment_order.order_id)
            self.fulfillment_order.mark_status(
                FulfillmentOrder.STATUS_FAILED,
                error_code="unexpected_error",
                error_message=str(exc),
                next_attempt_at=None,
            )
            raise

    # ------------------------------------------------------------------
    # Pipeline helpers
    # ------------------------------------------------------------------
    def process_return(self, *, reason: str = "", warehouse: Optional[str] = None) -> Dict[str, Any]:
        """Generate a Delivery Note Return for the fulfilled order."""
        return FulfillmentReturnService(self.fulfillment_order).process(reason=reason, warehouse=warehouse)

    def _normalize_order(self) -> OrderDTO:
        seller_company = self.fulfillment_order.seller_company
        distributor_company = self.fulfillment_order.distributor_company
        order = self.normalizer.normalize(
            source=self.source,
            payload=self.payload,
            seller_company=seller_company,
            distributor_company=distributor_company,
        )
        self.fulfillment_order.normalized_order = {
            "order_id": order.order_id,
            "source": order.source,
            "seller_company": order.seller_company,
            "distributor_company": order.distributor_company,
            "customer_email": order.customer_email,
            "totals": order.totals,
        }
        self.fulfillment_order.save(update_fields=["normalized_order", "updated_at"])
        return order

    def _store_mapping_snapshot(self, snapshot: Dict[str, Any]) -> None:
        self.fulfillment_order.fulfillment_payload = snapshot
        self.fulfillment_order.save(update_fields=["fulfillment_payload", "updated_at"])

    def _create_documents(self, order: OrderDTO, mapped_lines) -> FulfillmentResult:
        sales_order_name = self.executor.create_sales_order(order, mapped_lines)
        result = self.executor.create_delivery_note(order, mapped_lines, sales_order_name)
        return result

    def _propagate_status(self, order: OrderDTO, delivery_note_name: str) -> None:
        if order.source == FulfillmentItemMap.SOURCE_ERPNEXT:
            self._update_erpnext_source(order, delivery_note_name)
        elif order.source == FulfillmentItemMap.SOURCE_SHOPIFY:
            self._record_shopify_feedback(delivery_note_name)

    def _update_erpnext_source(self, order: OrderDTO, delivery_note_name: str) -> None:
        credential = ERPNextCredential.objects.for_company(
            organization_id=self.organization.id,
            company=order.seller_company,
        )
        if not credential:
            logger.warning(
                "[FULFILLMENT] No ERPNext credential available for seller %s to propagate status.",
                order.seller_company,
            )
            return
        client = ERPNextClient(credential)
        try:
            client.update_doc(
                "Sales Invoice",
                order.order_id,
                {
                    "custom_fulfillment_status": "fulfilled",
                    "custom_external_ref": delivery_note_name,
                },
            )
        except ERPNextClientError as exc:
            logger.warning(
                "[FULFILLMENT] Failed to update Sales Invoice %s: %s",
                order.order_id,
                exc,
            )

    def _record_shopify_feedback(self, delivery_note_name: str) -> None:
        payload = self.fulfillment_order.result_payload or {}
        payload["shopify_feedback"] = {
            "status": "pending",
            "delivery_note": delivery_note_name,
            "note": "Pending Shopify fulfillment update (token not configurado).",
        }
        self.fulfillment_order.result_payload = payload
        self.fulfillment_order.save(update_fields=["result_payload", "updated_at"])

    # ------------------------------------------------------------------
    # Data loading/helpers
    # ------------------------------------------------------------------
    def _ensure_fulfillment_order(self) -> FulfillmentOrder:
        seller_company = self.settings.resolve_seller_company(self.source, self.payload)
        distributor_company = self.settings.distributor_company

        defaults = {
            "seller_company": seller_company,
            "distributor_company": distributor_company,
            "payload": self.payload,
            "status": FulfillmentOrder.STATUS_PENDING,
        }
        order, created = FulfillmentOrder.objects.get_or_create(
            organization_id=self.message.organization_id,
            source=self.source,
            order_id=self._resolve_order_id(),
            defaults=defaults,
        )
        if created:
            return order

        updates = {
            "payload": self.payload,
            "seller_company": seller_company or order.seller_company,
            "distributor_company": distributor_company or order.distributor_company,
        }
        for attr, value in updates.items():
            setattr(order, attr, value)
        order.save(update_fields=list(updates.keys()) + ["updated_at"])
        return order

    def _resolve_distributor_credential(self) -> Optional[ERPNextCredential]:
        return ERPNextCredential.objects.for_company(
            organization_id=self.organization.id,
            company=self.fulfillment_order.distributor_company,
        )

    def _load_organization(self, organization_id) -> Organization:
        organization = Organization.objects.filter(id=organization_id).first()
        if not organization:
            raise FulfillmentConfigurationError(f"Organización {organization_id} no encontrada.")
        return organization

    def _resolve_source(self) -> str:
        if self.message.integration == IntegrationMessage.INTEGRATION_SHOPIFY:
            return FulfillmentItemMap.SOURCE_SHOPIFY
        if self.message.integration == IntegrationMessage.INTEGRATION_ERPNEXT_POS:
            return FulfillmentItemMap.SOURCE_ERPNEXT
        return str(self.message.integration or "").lower()

    def _resolve_order_id(self) -> str:
        for key in ("order_id", "id", "name", "external_reference"):
            value = self.payload.get(key)
            if value:
                return str(value)
        return str(self.message.external_reference or self.message.id)


def process_fulfillment_message(message: IntegrationMessage) -> Dict[str, Any]:
    service = FulfillmentGatewayService(message)
    return service.process()
