from dataclasses import dataclass, field, KW_ONLY
from uuid import UUID, uuid4
from events.events.base_event import DomainEvent

@dataclass
class ErpnextPosInvoiceSubmitted(DomainEvent):
    _: KW_ONLY
    payload: dict
    organization_id: UUID
    message_id: UUID

    def get_aggregate_id(self) -> str:
        return str(self.organization_id)

@dataclass
class ErpnextSalesInvoiceSubmitted(DomainEvent):
    _: KW_ONLY
    payload: dict
    organization_id: UUID
    message_id: UUID

    def get_aggregate_id(self) -> str:
        return str(self.organization_id)
