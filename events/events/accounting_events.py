from dataclasses import dataclass, field
from typing import Any, Dict
from uuid import uuid4

from .base_event import DomainEvent


@dataclass
class AccountingInvoiceSyncedEvent(DomainEvent):
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = "accounting.invoice.synced"
    company_id: str = ""
    invoice_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def get_aggregate_id(self) -> str:
        return self.invoice_id or self.company_id
