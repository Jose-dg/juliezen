from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from django.utils import timezone

from apps.erpnext.services.client import ERPNextClient
from apps.integrations.exceptions import BackorderPending, FulfillmentError

from .dto import MappedOrderLineDTO, OrderDTO
from .settings import GatewaySettings


@dataclass
class FulfillmentResult:
    delivery_note: str
    serials: List[str]
    line_serials: List[Dict[str, List[str]]]
    sales_order: Optional[str] = None


class SerialAllocator:
    """Load serial numbers from ERPNext for a given item/warehouse."""

    def __init__(self, client: ERPNextClient, status: str):
        self.client = client
        self.status = status

    def allocate(self, *, item_code: str, quantity: int, warehouse: Optional[str]) -> List[str]:
        serials: List[str] = []
        offset = 0
        page_size = max(quantity * 2, 20)
        while len(serials) < quantity:
            batch = self.client.list_serial_numbers(
                item_code=item_code,
                warehouse=warehouse,
                status=self.status,
                limit=page_size,
                offset=offset,
            )
            if not batch:
                break
            for row in batch:
                serial = row.get("serial_no") or row.get("name")
                if serial and serial not in serials:
                    serials.append(serial)
                    if len(serials) == quantity:
                        break
            offset += len(batch)
            if len(batch) < page_size:
                break
        return serials


class FulfillmentExecutor:
    """Create ERPNext documents (SO/DN) with serial assignments."""

    def __init__(self, client: ERPNextClient, settings: GatewaySettings):
        self.client = client
        self.settings = settings
        self.serial_allocator = SerialAllocator(client, status=settings.serial_status)

    def assign_serials(self, lines: List[MappedOrderLineDTO]) -> None:
        insufficient: List[str] = []
        for line in lines:
            quantity = int(line.quantity)
            serials = self.serial_allocator.allocate(
                item_code=line.target_item_code,
                quantity=quantity,
                warehouse=line.warehouse,
            )
            if len(serials) < quantity:
                insufficient.append(line.target_item_code)
            else:
                line.serial_numbers = serials
        if insufficient:
            raise BackorderPending(
                f"No hay seriales suficientes para: {', '.join(sorted(set(insufficient)))}"
            )

    def create_sales_order(self, order: OrderDTO, mapped_lines: List[MappedOrderLineDTO]) -> Optional[str]:
        if not self.settings.create_sales_order:
            return None

        payload = {
            "doctype": "Sales Order",
            "company": order.distributor_company,
            "customer": order.seller_company,
            "delivery_date": self._delivery_date(order),
            "po_no": order.order_id,
            "custom_customer_email": order.customer_email,
            "custom_order_ref": order.order_id,
            "items": [
                {
                    "item_code": line.target_item_code,
                    "qty": float(line.quantity),
                    "warehouse": line.warehouse,
                    "rate": float(line.unit_price),
                }
                for line in mapped_lines
            ],
        }

        response = self.client.insert_doc("Sales Order", payload)
        name = response.get("name") if isinstance(response, dict) else None
        if not name:
            raise FulfillmentError("No se pudo crear la Sales Order en ERPNext.", error_code="sales_order_creation")
        return name

    def _delivery_date(self, order: OrderDTO) -> str:
        reference = order.created_at or order.paid_at or timezone.now()
        if isinstance(reference, str):
            return reference
        return reference.date().isoformat()

    def create_delivery_note(
        self,
        order: OrderDTO,
        mapped_lines: List[MappedOrderLineDTO],
        sales_order_name: Optional[str],
    ) -> FulfillmentResult:
        items_payload = []
        line_serials: List[Dict[str, List[str]]] = []
        for line in mapped_lines:
            serial_field = "\n".join(line.serial_numbers)
            item_entry = {
                "item_code": line.target_item_code,
                "qty": float(line.quantity),
                "serial_no": serial_field,
                "warehouse": line.warehouse,
            }
            if sales_order_name:
                item_entry["against_sales_order"] = sales_order_name
            items_payload.append(item_entry)
            line_serials.append(
                {
                    "item_code": line.target_item_code,
                    "serials": list(line.serial_numbers),
                    "warehouse": line.warehouse,
                    "quantity": float(line.quantity),
                }
            )

        payload = {
            "doctype": "Delivery Note",
            "company": order.distributor_company,
            "customer": order.seller_company,
            "posting_date": self._posting_date(order),
            "custom_customer_email": order.customer_email,
            "custom_order_ref": order.order_id,
            "items": items_payload,
        }
        response = self.client.insert_doc("Delivery Note", payload)
        delivery_note_name = response.get("name") if isinstance(response, dict) else None
        if not delivery_note_name:
            raise FulfillmentError("No se pudo crear la Delivery Note en ERPNext.", error_code="delivery_note_creation")

        submit_response = self.client.submit_doc("Delivery Note", delivery_note_name)
        if isinstance(submit_response, dict) and submit_response.get("docstatus") != 1:
            raise FulfillmentError("No fue posible enviar la Delivery Note.", error_code="delivery_note_submit")

        serials = [serial for line in mapped_lines for serial in line.serial_numbers]
        return FulfillmentResult(
            delivery_note=delivery_note_name,
            serials=serials,
            line_serials=line_serials,
            sales_order=sales_order_name,
        )

    def _posting_date(self, order: OrderDTO) -> Optional[str]:
        if order.created_at:
            return order.created_at.date().isoformat()
        posting_date = order.raw.get("posting_date")
        return posting_date
