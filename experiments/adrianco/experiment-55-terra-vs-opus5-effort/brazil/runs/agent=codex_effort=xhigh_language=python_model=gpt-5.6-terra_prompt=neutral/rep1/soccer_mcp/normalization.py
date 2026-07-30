"""Normalization helpers for data supplied by differently formatted CSV files."""

from __future__ import annotations

import re
import unicodedata


_STATE_CODES = {
    "ac", "al", "am", "ap", "ba", "ce", "df", "es", "go", "ma", "mg", "ms",
    "mt", "pa", "pb", "pe", "pi", "pr", "rj", "rn", "ro", "rr", "rs", "sc",
    "se", "sp", "to",
}

# These aliases cover common Brazilian club forms while retaining a conservative
# fallback for clubs that do not appear in this list.
_TEAM_ALIASES = {
    "atletico mg": "atletico mineiro",
    "clube atletico mineiro": "atletico mineiro",
    "atletico mineiro": "atletico mineiro",
    "atletico pr": "athletico paranaense",
    "athletico pr": "athletico paranaense",
    "atletico paranaense": "athletico paranaense",
    "club athletico paranaense": "athletico paranaense",
    "athletico paranaense": "athletico paranaense",
    "america mg": "america mineiro",
    "america mineiro": "america mineiro",
    "ceara sc": "ceara",
    "ceara sporting club": "ceara",
    "cr flamengo": "flamengo",
    "clube de regatas do flamengo": "flamengo",
    "flamengo rj": "flamengo",
    "fluminense football club": "fluminense",
    "botafogo fr": "botafogo",
    "botafogo rj": "botafogo",
    "club de regatas vasco da gama": "vasco",
    "vasco da gama": "vasco",
    "sao paulo fc": "sao paulo",
    "sao paulo futebol clube": "sao paulo",
    "sport club corinthians paulista": "corinthians",
    "corinthians paulista": "corinthians",
    "sc internacional": "internacional",
    "gremio fbpa": "gremio",
    "gremio porto alegrense": "gremio",
    "ec bahia": "bahia",
    "goias ec": "goias",
    "coritiba fc": "coritiba",
    "fortaleza ec": "fortaleza",
    "red bull bragantino": "bragantino",
}


def normalize_text(value: object | None) -> str:
    """Return a case- and accent-insensitive, whitespace-normalized string."""
    if value is None:
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def normalize_team(value: object | None) -> str:
    """Create a stable key for matching a club across source-specific naming."""
    normalized = normalize_text(value)
    if not normalized:
        return ""

    # Check state-qualified aliases before dropping the final state qualifier;
    # otherwise Atletico-MG and Atletico-PR would both become "atletico".
    if normalized in _TEAM_ALIASES:
        return _TEAM_ALIASES[normalized]

    words = normalized.split()
    if len(words) > 1 and words[-1] in _STATE_CODES:
        normalized = " ".join(words[:-1])
    return _TEAM_ALIASES.get(normalized, normalized)


def normalize_competition(value: object | None) -> str:
    """Map common competition spellings to names used in API responses."""
    normalized = normalize_text(value)
    if "libertadores" in normalized:
        return "Copa Libertadores"
    if "copa do brasil" in normalized:
        return "Copa do Brasil"
    if "brasileirao" in normalized or normalized in {"serie a", "serie a brasil"}:
        return "Brasileirão Série A"
    return " ".join(str(value or "").split())


def display_team(value: object | None) -> str:
    """Remove a trailing Brazilian state suffix from a source team label."""
    if value is None:
        return ""
    text = " ".join(str(value).split())
    return re.sub(
        r"\s*-\s*(?:AC|AL|AM|AP|BA|CE|DF|ES|GO|MA|MG|MS|MT|PA|PB|PE|PI|PR|RJ|RN|RO|RR|RS|SC|SE|SP|TO)$",
        "",
        text,
        flags=re.IGNORECASE,
    )
