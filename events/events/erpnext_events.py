from dataclasses import dataclass, KW_ONLY
from uuid import UUID
from events.events.base_event import DomainEvent

@dataclass
class ERPNextFulfillmentRequested(DomainEvent):
    event_type = "ERPNextFulfillmentRequested"
    _: KW_ONLY
    message_id: UUID

    def get_aggregate_id(self) -> str:
        return str(self.message_id)

@dataclass
class ERPNextFulfillmentProcessRequested(DomainEvent):
    event_type = "ERPNextFulfillmentProcessRequested"
    _: KW_ONLY
    message_id: UUID

    def get_aggregate_id(self) -> str:
        return str(self.message_id)
