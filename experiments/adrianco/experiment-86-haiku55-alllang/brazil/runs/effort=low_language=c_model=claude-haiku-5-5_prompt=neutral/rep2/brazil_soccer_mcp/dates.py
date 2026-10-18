"""Date parsing for the mixed formats found in the CSVs.

Handles ISO dates, ISO datetimes ("2012-05-19 18:30:00"), and Brazilian
day-first dates ("29/03/2003" or "08/12/2019"). Returns None for blanks and
placeholders such as "NA" rather than raising.
"""

from datetime import date, datetime
from typing import Optional

_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d/%m/%Y %H:%M",
)


def parse_date(value) -> Optional[date]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in {"NA", "N/A", "NAN", "NONE"}:
        return None
    for fmt in _FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_date_arg(value: Optional[str]) -> Optional[date]:
    """Parse a date supplied by a caller (tool argument). Raises ValueError."""
    if value in (None, ""):
        return None
    parsed = parse_date(value)
    if parsed is None:
        raise ValueError(f"Unrecognized date '{value}'. Use YYYY-MM-DD or DD/MM/YYYY.")
    return parsed
