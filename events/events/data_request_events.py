from dataclasses import dataclass
from typing import Any, Dict, Optional

from .base_event import DomainEvent


@dataclass
class DataRequestEvent(DomainEvent):
    source_app: str = ""
    target_app: str = ""
    requested_by: str = ""
    request_id: str = ""

    def get_aggregate_id(self) -> str:
        return self.request_id or self.event_id


@dataclass
class DataResponseEvent(DomainEvent):
    original_request_id: str = ""
    source_app: str = ""
    target_app: str = ""
    data: Dict[str, Any] = None
    success: bool = True
    error_message: Optional[str] = None

    def get_aggregate_id(self) -> str:
        return self.original_request_id
