from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID


@dataclass
class OrderLineDTO:
    source_item_code: str
    quantity: Decimal
    unit_price: Decimal
    description: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MappedOrderLineDTO(OrderLineDTO):
    target_item_code: str = ""
    target_company: str = ""
    warehouse: Optional[str] = None
    serial_numbers: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderDTO:
    organization_id: UUID
    source: str
    order_id: str
    seller_company: str
    distributor_company: str
    customer_email: str
    currency: str | None
    totals: Dict[str, Any]
    raw: Dict[str, Any]
    created_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    external_reference: str = ""
    lines: List[OrderLineDTO] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

