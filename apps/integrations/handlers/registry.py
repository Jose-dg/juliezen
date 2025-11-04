import logging
from typing import Any, Dict

from apps.integrations.models import IntegrationMessage
from apps.integrations.router import registry

logger = logging.getLogger(__name__)

@registry.register(IntegrationMessage.INTEGRATION_ALEGRA)
def log_alegra_message(message: IntegrationMessage) -> Dict[str, Any]:
    """Log every Alegra integration message for traceability."""
    logger.info(
        "[ALEGRA][%s] message=%s event=%s retries=%s",
        message.direction,
        message.id,
        message.event_type,
        message.retries,
    )
    return {
        "message_id": str(message.id),
        "direction": message.direction,
        "event_type": message.event_type,
    }