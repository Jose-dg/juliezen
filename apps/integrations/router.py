from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

from apps.integrations.models import IntegrationMessage

Handler = Callable[[IntegrationMessage], Any]


class IntegrationHandlerRegistry:
    def __init__(self) -> None:
        self._handlers: Dict[str, Dict[Optional[str], List[Handler]]] = defaultdict(lambda: defaultdict(list))

    def register(self, integration: str, event_type: Optional[str] = None, handler: Optional[Handler] = None):
        if handler is None:
            return lambda fn: self.register(integration, event_type, fn)
        bucket = self._handlers[integration][event_type]
        if handler not in bucket:
            bucket.append(handler)
        return handler

    def dispatch(self, integration: str, event_type: Optional[str], message: IntegrationMessage) -> List[Any]:
        handlers = []
        integration_handlers = self._handlers.get(integration, {})
        handlers.extend(integration_handlers.get(event_type, []))
        handlers.extend(integration_handlers.get(None, []))
        results: List[Any] = []
        for handler in handlers:
            result = handler(message)
            results.append(result)
        return results


registry = IntegrationHandlerRegistry()
