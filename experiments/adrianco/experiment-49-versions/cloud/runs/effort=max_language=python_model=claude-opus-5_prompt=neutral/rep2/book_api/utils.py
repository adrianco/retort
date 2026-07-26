"""Small helpers shared across the package."""

from __future__ import annotations

from datetime import datetime, timezone


def utcnow_iso() -> str:
    """Return the current UTC time as an ISO-8601 string, e.g. ``2024-05-01T10:00:00.000Z``."""
    now = datetime.now(timezone.utc)
    return now.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def current_year() -> int:
    """Return the current year in UTC."""
    return datetime.now(timezone.utc).year
