from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from apps.integrations.exceptions import FulfillmentError
from apps.integrations.models import FulfillmentItemMap

from .dto import OrderDTO, OrderLineDTO
from .settings import GatewaySettings
from .utils import parse_dt, to_decimal


class OrderNormalizer:
    """Normalize inbound payloads (Shopify / ERPNext) to OrderDTO."""

    def __init__(self, organization_id, settings: GatewaySettings):
        self.organization_id = organization_id
        self.settings = settings

    def normalize(
        self,
        *,
        source: str,
        payload: Dict[str, Any],
        seller_company: str,
        distributor_company: str,
    ) -> OrderDTO:
        if source == FulfillmentItemMap.SOURCE_SHOPIFY:
            return self._normalize_shopify(payload, seller_company, distributor_company)
        if source == FulfillmentItemMap.SOURCE_ERPNEXT:
            return self._normalize_erpnext(payload, seller_company, distributor_company)
        raise FulfillmentError(f"Fuente {source} no soportada.", error_code="unsupported_source")


    def _normalize_shopify(
        self,
        payload: Dict[str, Any],
        seller_company: str,
        distributor_company: str,
    ) -> OrderDTO:
        order_id = self._resolve_order_id(payload)
        customer_info = payload.get("customer") or {}
        email = (
            payload.get("contact_email")
            or customer_info.get("email")
            or payload.get("email")
            or payload.get("customer_email")
        )
        created_at = parse_dt(payload.get("created_at"))
        paid_at = parse_dt(payload.get("processed_at") or payload.get("closed_at"))
        currency = payload.get("currency") or payload.get("presentment_currency")

        lines: List[OrderLineDTO] = []
        for raw_line in payload.get("line_items") or []:
            if not isinstance(raw_line, dict):
                continue
            source_code = (
                raw_line.get("sku")
                or raw_line.get("variant_id")
                or raw_line.get("product_id")
                or raw_line.get("id")
                or raw_line.get("title")
            )
            qty = to_decimal(raw_line.get("quantity"), "0")
            if qty <= 0:
                continue
            unit_price = to_decimal(raw_line.get("price"), "0")
            description = raw_line.get("title") or raw_line.get("name") or str(source_code)
            lines.append(
                OrderLineDTO(
                    source_item_code=str(source_code),
                    quantity=qty,
                    unit_price=unit_price,
                    description=str(description),
                    raw=raw_line,
                )
            )

        if not lines:
            raise FulfillmentError("El pedido de Shopify no contiene ítems para procesar.", error_code="empty_order")

        totals = {
            "total_price": payload.get("total_price"),
            "subtotal_price": payload.get("subtotal_price"),
            "total_tax": payload.get("total_tax"),
            "total_discount": payload.get("total_discounts"),
        }

        return OrderDTO(
            organization_id=self.organization_id,
            source=FulfillmentItemMap.SOURCE_SHOPIFY,
            order_id=order_id,
            seller_company=seller_company,
            distributor_company=distributor_company,
            customer_email=str(email or ""),
            currency=currency,
            totals=totals,
            raw=payload,
            created_at=created_at,
            paid_at=paid_at,
            lines=lines,
            metadata={"shopify_domain": payload.get("_shopify_domain")},
        )

    def _normalize_erpnext(
        self,
        payload: Dict[str, Any],
        seller_company: str,
        distributor_company: str,
    ) -> OrderDTO:
        order_id = payload.get("name") or self._resolve_order_id(payload)
        email = payload.get("custom_customer_email")
        if not email:
            customer = payload.get("customer_details") or payload.get("customer") or {}
            if isinstance(customer, dict):
                email = customer.get("email_id") or customer.get("email") or customer.get("contact_email")
        if not email:
            email = payload.get("contact_email")

        created_at = parse_dt(payload.get("posting_date"))

        lines: List[OrderLineDTO] = []
        for raw_line in payload.get("items") or []:
            if not isinstance(raw_line, dict):
                continue
            source_code = raw_line.get("item_code") or raw_line.get("item_name")
            qty = to_decimal(raw_line.get("qty"), "0")
            if qty <= 0:
                continue
            rate = to_decimal(raw_line.get("rate"), "0")
            lines.append(
                OrderLineDTO(
                    source_item_code=str(source_code),
                    quantity=qty,
                    unit_price=rate,
                    description=str(raw_line.get("description") or source_code),
                    raw=raw_line,
                )
            )

        if not lines:
            raise FulfillmentError(
                "La factura de ERPNext no contiene ítems válidos para fulfillment.",
                error_code="empty_order",
            )

        totals = {
            "grand_total": payload.get("grand_total"),
            "total": payload.get("total"),
        }

        return OrderDTO(
            organization_id=self.organization_id,
            source=FulfillmentItemMap.SOURCE_ERPNEXT,
            order_id=str(order_id),
            seller_company=seller_company,
            distributor_company=distributor_company,
            customer_email=str(email or ""),
            currency=payload.get("currency"),
            totals=totals,
            raw=payload,
            created_at=created_at,
            lines=lines,
        )

    @staticmethod
    def _resolve_order_id(payload: Dict[str, Any]) -> str:
        candidate_keys = ("order_id", "id", "name", "external_reference")
        for key in candidate_keys:
            value = payload.get(key)
            if value:
                return str(value)
        return ""

