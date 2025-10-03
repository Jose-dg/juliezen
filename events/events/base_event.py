from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict


@dataclass
class DomainEvent(ABC):
    event_id: str
    event_type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @abstractmethod
    def get_aggregate_id(self) -> str:
        raise NotImplementedError
