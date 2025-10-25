import threading
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

from .events.base_event import DomainEvent

Handler = Callable[[DomainEvent], Any]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Handler]] = defaultdict(list)
        self._lock = threading.Lock()
        self._response_events: Dict[str, threading.Event] = {}
        self._responses: Dict[str, Any] = {}

    def subscribe(self, event_type: str, handler: Handler) -> None:
        print(f"[EVENTBUS] Subscribing {handler.__name__} to {event_type}")
        with self._lock:
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Handler) -> None:
        with self._lock:
            handlers = self._subscribers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)

    def publish(self, event: DomainEvent) -> List[Any]:
        handlers = list(self._subscribers.get(event.event_type, []))
        print(f"[EVENTBUS] Publishing {event.event_type} to {len(handlers)} handlers.")
        results: List[Any] = []
        for handler in handlers:
            result = handler(event)
            results.append(result)
        return results

    def publish_and_wait(self, event: DomainEvent, timeout: Optional[float] = None) -> Any:
        waiter = threading.Event()
        self._response_events[event.event_id] = waiter
        try:
            self.publish(event)
            finished = waiter.wait(timeout)
            if not finished:
                raise TimeoutError(f"Timeout esperando respuesta para {event.event_id}")
            return self._responses.pop(event.event_id, None)
        finally:
            self._response_events.pop(event.event_id, None)

    def respond_to_request(self, request_id: str, response: Any) -> None:
        event = self._response_events.get(request_id)
        if event:
            self._responses[request_id] = response
            event.set()


event_bus = EventBus()
