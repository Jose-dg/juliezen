from dataclasses import dataclass, field
from typing import Any, Dict
from uuid import uuid4

from .base_event import DomainEvent


@dataclass
class IntegrationInboundEvent(DomainEvent):
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = "integration.inbound"
    company_id: str = ""
    integration: str = ""
    message_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    external_reference: str = ""

    def get_aggregate_id(self) -> str:
        return self.message_id or self.external_reference or self.company_id


@dataclass
class IntegrationOutboundEvent(DomainEvent):
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = "integration.outbound"
    company_id: str = ""
    integration: str = ""
    message_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    response: Dict[str, Any] = field(default_factory=dict)
    external_reference: str = ""

    def get_aggregate_id(self) -> str:
        return self.message_id or self.external_reference or self.company_id


@dataclass
class ShopifyWebhookReceivedEvent(DomainEvent):
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = "shopify.webhook.received"
    shopify_domain: str = ""
    headers: Dict[str, Any] = field(default_factory=dict)
    body: Dict[str, Any] = field(default_factory=dict)
    raw_body: bytes = b""

    def get_aggregate_id(self) -> str:
        return self.shopify_domain
