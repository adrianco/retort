"""Stable normalization helpers for names, competitions, and dates.

The source files mix Portuguese accents, state suffixes, abbreviations, and
full club names.  These helpers make lookups consistent while callers retain
the original source values for display and provenance.
"""

from __future__ import annotations

from datetime import date, datetime
import re
import unicodedata
from typing import Final


BRAZILIAN_STATE_CODES: Final[frozenset[str]] = frozenset(
    {
        "ac",
        "al",
        "ap",
        "am",
        "ba",
        "ce",
        "df",
        "es",
        "go",
        "ma",
        "mt",
        "ms",
        "mg",
        "pa",
        "pb",
        "pr",
        "pe",
        "pi",
        "rj",
        "rn",
        "rs",
        "ro",
        "rr",
        "sc",
        "sp",
        "se",
        "to",
    }
)

_STATE_SUFFIX_RE: Final[re.Pattern[str]] = re.compile(
    r"\s*(?:[-–—,]\s*|\s+)(?:AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)\s*$",
    re.IGNORECASE,
)
_NON_ALNUM_RE: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9]+")
_WHITESPACE_RE: Final[re.Pattern[str]] = re.compile(r"\s+")

# This is deliberately a small, inspectable registry rather than a broad
# substring rewrite.  It handles the variants present in the supplied data
# without silently merging unrelated clubs.
TEAM_ALIASES: Final[dict[str, str]] = {
    "athletico pr": "athletico",
    "atletico pr": "athletico",
    "athletico paranaense": "athletico",
    "atletico paranaense": "athletico",
    "clube atletico paranaense": "athletico",
    "atletico mg": "atletico mineiro",
    "clube atletico mineiro": "atletico mineiro",
    "america mg": "america",
    "america mineiro": "america",
    "america futebol clube": "america",
    "associacao chapecoense de futebol": "chapecoense",
    "botafogo futebol e regatas": "botafogo",
    "club de regatas do flamengo": "flamengo",
    "clube de regatas do flamengo": "flamengo",
    "clube de regatas flamengo": "flamengo",
    "club de regatas vasco da gama": "vasco",
    "cruzeiro esporte clube": "cruzeiro",
    "fluminense football club": "fluminense",
    "gremio fbpa": "gremio",
    "gremio porto alegrense": "gremio",
    "sao paulo futebol clube": "sao paulo",
    "sao paulo fc": "sao paulo",
    "sociedade esportiva palmeiras": "palmeiras",
    "sport club corinthians paulista": "corinthians",
    "corinthians paulista": "corinthians",
    "vasco da gama": "vasco",
}

COMPETITION_ALIASES: Final[dict[str, str]] = {
    "brasileirao": "brasileirao",
    "brasileirao serie a": "brasileirao",
    "campeonato brasileiro": "brasileirao",
    "campeonato brasileiro serie a": "brasileirao",
    "serie a": "brasileirao",
    "brazilian serie a": "brasileirao",
    "copa do brasil": "copa do brasil",
    "copa brasil": "copa do brasil",
    "libertadores": "copa libertadores",
    "copa libertadores": "copa libertadores",
    "copa libertadores da america": "copa libertadores",
}

COMPETITION_DISPLAY: Final[dict[str, str]] = {
    "brasileirao": "Brasileirão",
    "copa do brasil": "Copa do Brasil",
    "copa libertadores": "Copa Libertadores",
}


def clean_text(value: object | None) -> str:
    """Return a stripped source string, converting missing CSV values to empty."""

    if value is None:
        return ""
    return str(value).strip()


def normalize_text(value: object | None) -> str:
    """Create an accent- and punctuation-insensitive lookup key."""

    text = unicodedata.normalize("NFKD", clean_text(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold()
    return _NON_ALNUM_RE.sub(" ", text).strip()


def strip_brazilian_state_suffix(value: object | None) -> str:
    """Remove a terminal Brazilian state suffix while retaining country suffixes."""

    return _STATE_SUFFIX_RE.sub("", clean_text(value)).strip()


def normalize_team(value: object | None) -> str:
    """Return the canonical lookup key for a team or FIFA club name."""

    original = normalize_text(value)
    if original in TEAM_ALIASES:
        return TEAM_ALIASES[original]

    stripped = normalize_text(strip_brazilian_state_suffix(value))
    return TEAM_ALIASES.get(stripped, stripped)


def normalize_competition(value: object | None) -> str:
    """Return a stable competition key while preserving unknown competition names."""

    normalized = normalize_text(value)
    return COMPETITION_ALIASES.get(normalized, normalized)


def display_competition(value: object | None) -> str:
    """Return a user-facing competition name for a canonical or source value."""

    canonical = normalize_competition(value)
    return COMPETITION_DISPLAY.get(canonical, clean_text(value) or "Unknown competition")


def parse_date(value: object | None) -> date | None:
    """Parse the ISO and Brazilian date formats used by the bundled datasets."""

    text = clean_text(value)
    if not text:
        return None

    # `fromisoformat` supports ISO dates and datetimes, including the values in
    # Brasileirao_Matches.csv.  Z is normalized for older Python versions too.
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass

    for pattern in ("%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def parse_query_date(value: str | date | None, *, parameter: str) -> date | None:
    """Parse a tool date parameter, raising a helpful error for invalid input."""

    if value is None or isinstance(value, date):
        return value
    parsed = parse_date(value)
    if parsed is None:
        raise ValueError(
            f"{parameter} must be an ISO date (YYYY-MM-DD) or Brazilian date (DD/MM/YYYY)."
        )
    return parsed


def parse_int(value: object | None) -> int | None:
    """Coerce CSV numeric cells such as `1`, `1.0`, and empty strings."""

    text = clean_text(value)
    if not text or text.casefold() in {"nan", "none", "null", "-"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def parse_float(value: object | None) -> float | None:
    """Coerce an optional numeric CSV cell without treating bad values as zero."""

    text = clean_text(value)
    if not text or text.casefold() in {"nan", "none", "null", "-"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def contains_normalized(haystack: object | None, needle: object | None) -> bool:
    """Case-, accent-, and punctuation-insensitive substring matching."""

    query = normalize_text(needle)
    return bool(query) and query in normalize_text(haystack)

