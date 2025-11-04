from dataclasses import dataclass, KW_ONLY
from uuid import UUID
from events.events.base_event import DomainEvent

@dataclass
class ShopifyFulfillmentRequested(DomainEvent):
    event_type = "ShopifyFulfillmentRequested"
    _: KW_ONLY
    message_id: UUID

    def get_aggregate_id(self) -> str:
        return str(self.message_id)
