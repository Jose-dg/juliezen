from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from django.utils import timezone
from django.utils.dateparse import parse_datetime as django_parse_datetime


def to_decimal(value: Any, default: str = "0") -> Decimal:
    """Convert arbitrary input to Decimal without raising."""
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = str(value).strip()
    if not text:
        return Decimal(default)
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return Decimal(default)


def parse_dt(value: Any) -> Optional[datetime]:
    """Parse a datetime keeping timezone awareness consistent."""
    if isinstance(value, datetime):
        return value if timezone.is_aware(value) else timezone.make_aware(value, timezone.get_default_timezone())
    if not value:
        return None
    parsed = None
    try:
        parsed = django_parse_datetime(str(value))
    except (TypeError, ValueError):
        parsed = None
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_default_timezone())
    return parsed

