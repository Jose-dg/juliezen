from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List, Tuple

from apps.integrations.exceptions import FulfillmentError
from apps.integrations.models import FulfillmentItemMap

from .dto import MappedOrderLineDTO, OrderDTO
from .settings import GatewaySettings


class LineMapper:
    """Resolve placeholder items from source companies into serialized items for Company A."""

    def __init__(self, organization_id, settings: GatewaySettings):
        self.organization_id = organization_id
        self.settings = settings

    def map_lines(self, order: OrderDTO) -> Tuple[List[MappedOrderLineDTO], Dict[str, List[Dict[str, str]]]]:
        item_maps = FulfillmentItemMap.objects.for_source(
            organization_id=self.organization_id,
            source=order.source,
            source_company=order.seller_company,
        )
        map_index = {entry.source_item_code: entry for entry in item_maps}

        mapped_lines: List[MappedOrderLineDTO] = []
        target_companies = set()

        for line in order.lines:
            mapped = self._map_line(line.source_item_code, line, map_index, order)
            target_companies.add(mapped.target_company)
            mapped_lines.append(mapped)

        if len(target_companies) > 1:
            raise FulfillmentError(
                f"El pedido mapea a múltiples compañías de destino: {', '.join(sorted(target_companies))}",
                error_code="multiple_target_companies",
            )

        snapshot = self._build_snapshot(mapped_lines)
        return mapped_lines, snapshot

    def _map_line(
        self,
        source_code: str,
        line,
        map_index: Dict[str, FulfillmentItemMap],
        order: OrderDTO,
    ) -> MappedOrderLineDTO:
        entry = map_index.get(source_code)
        if entry:
            target_company = entry.target_company or order.distributor_company
            target_item_code = entry.target_item_code
            warehouse = entry.warehouse or entry.metadata.get("warehouse") if isinstance(entry.metadata, dict) else None
        else:
            meta_entry = self.settings.metadata_item_mapping(
                source=order.source,
                seller_company=order.seller_company,
                source_item_code=source_code,
            )
            if meta_entry:
                target_company = meta_entry.get("target_company") or order.distributor_company
                target_item_code = meta_entry.get("target_item_code")
                warehouse = meta_entry.get("warehouse")
            else:
                # If no mapping is found, assume source SKU = target item code
                target_company = order.distributor_company
                target_item_code = source_code
                warehouse = None

        if not target_item_code:
            raise FulfillmentError(
                f"El item_map de {source_code} no define target_item_code.",
                error_code="invalid_item_map",
            )

        return MappedOrderLineDTO(
            **asdict(line),
            target_item_code=str(target_item_code),
            target_company=str(target_company or order.distributor_company),
            warehouse=str(warehouse) if warehouse else self.settings.default_warehouse,
        )

    @staticmethod
    def _build_snapshot(mapped_lines: List[MappedOrderLineDTO]) -> Dict[str, List[Dict[str, str]]]:
        return {
            "lines": [
                {
                    "source_item_code": line.source_item_code,
                    "target_item_code": line.target_item_code,
                    "warehouse": line.warehouse,
                    "quantity": str(line.quantity),
                    "unit_price": str(line.unit_price),
                }
                for line in mapped_lines
            ]
        }

