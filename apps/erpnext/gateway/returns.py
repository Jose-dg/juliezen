from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from django.utils import timezone

from apps.integrations.exceptions import FulfillmentConfigurationError, FulfillmentError
from apps.integrations.models import FulfillmentOrder
from apps.organizations.models import Organization
from apps.erpnext.models import ERPNextCredential
from apps.erpnext.services.client import ERPNextClient, ERPNextClientError

from .settings import GatewaySettings

logger = logging.getLogger(__name__)


class FulfillmentReturnService:
    """Generate Delivery Note Returns for previously fulfilled orders."""

    def __init__(self, fulfillment_order: FulfillmentOrder) -> None:
        self.fulfillment_order = fulfillment_order
        self.organization = self._load_organization(fulfillment_order.organization_id)
        self.settings = GatewaySettings(getattr(self.organization, "metadata", {}))
        self.credential = self._resolve_distributor_credential()
        if not self.credential:
            raise FulfillmentConfigurationError(
                f"No hay credenciales de ERPNext para {fulfillment_order.distributor_company}."
            )
        self.client = ERPNextClient(self.credential)

    def process(self, *, reason: str = "", warehouse: Optional[str] = None) -> Dict[str, Any]:
        if not self.fulfillment_order.delivery_note_name:
            raise FulfillmentError(
                "No se puede generar la devolución porque no existe Delivery Note previa.",
                error_code="missing_delivery_note",
            )
        line_serials = self._line_serials()
        if not line_serials:
            raise FulfillmentError(
                "No se encontraron seriales asociados al fulfillment para procesar la devolución.",
                error_code="missing_serials",
            )

        payload = self._build_return_payload(line_serials, warehouse)
        response = self.client.insert_doc("Delivery Note", payload)
        return_dn = response.get("name") if isinstance(response, dict) else None
        if not return_dn:
            raise FulfillmentError("No fue posible crear la Delivery Note de devolución.", error_code="return_creation")

        submit_response = self.client.submit_doc("Delivery Note", return_dn)
        if isinstance(submit_response, dict) and submit_response.get("docstatus") != 1:
            raise FulfillmentError(
                "La Delivery Note de devolución no pudo ser enviada.",
                error_code="return_submit",
            )

        self.fulfillment_order.record_return(
            delivery_note=return_dn,
            payload={
                "reason": reason,
                "line_serials": line_serials,
                "requested_at": timezone.now().isoformat(),
            },
        )
        logger.info(
            "[FULFILLMENT][RETURN] Created DN Return %s for order %s",
            return_dn,
            self.fulfillment_order.order_id,
        )
        return {
            "return_delivery_note": return_dn,
            "original_delivery_note": self.fulfillment_order.delivery_note_name,
            "line_serials": line_serials,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _line_serials(self) -> List[Dict[str, Any]]:
        result_payload = self.fulfillment_order.result_payload or {}
        line_serials = result_payload.get("line_serials")
        if isinstance(line_serials, list) and line_serials:
            return line_serials

        # Fallback: derive from stored snapshot + serial list
        snapshot = (self.fulfillment_order.fulfillment_payload or {}).get("lines", [])
        serials = list(self.fulfillment_order.serial_numbers or [])
        derived: List[Dict[str, Any]] = []
        idx = 0
        for entry in snapshot:
            quantity = int(float(entry.get("quantity") or 0))
            chunk = serials[idx : idx + quantity]
            idx += quantity
            derived.append(
                {
                    "item_code": entry.get("target_item_code"),
                    "warehouse": entry.get("warehouse"),
                    "quantity": quantity,
                    "serials": chunk,
                }
            )
        return derived

    def _build_return_payload(self, line_serials: List[Dict[str, Any]], warehouse_override: Optional[str]) -> Dict[str, Any]:
        items = []
        for entry in line_serials:
            serials = entry.get("serials") or []
            if not serials:
                continue
            items.append(
                {
                    "item_code": entry.get("item_code"),
                    "qty": float(entry.get("quantity") or len(serials)),
                    "serial_no": "\n".join(serials),
                    "warehouse": warehouse_override
                    or entry.get("warehouse")
                    or self.settings.default_warehouse,
                }
            )

        return {
            "doctype": "Delivery Note",
            "company": self.fulfillment_order.distributor_company,
            "customer": self.fulfillment_order.seller_company,
            "posting_date": timezone.now().date().isoformat(),
            "is_return": 1,
            "return_against": self.fulfillment_order.delivery_note_name,
            "items": items,
        }

    def _load_organization(self, organization_id) -> Organization:
        organization = Organization.objects.filter(id=organization_id).first()
        if not organization:
            raise FulfillmentConfigurationError(f"Organización {organization_id} no encontrada.")
        return organization

    def _resolve_distributor_credential(self) -> Optional[ERPNextCredential]:
        return ERPNextCredential.objects.for_company(
            organization_id=self.organization.id,
            company=self.fulfillment_order.distributor_company,
        )
