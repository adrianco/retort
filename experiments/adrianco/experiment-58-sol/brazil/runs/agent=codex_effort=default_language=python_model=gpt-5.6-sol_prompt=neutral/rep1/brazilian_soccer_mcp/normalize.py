"""Normalization helpers for inconsistent Brazilian football data."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

_STATE_SUFFIX = re.compile(r"\s*-\s*(?:AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)$", re.I)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")

_TEAM_ALIASES = {
    "sport club corinthians paulista": "corinthians",
    "sc corinthians paulista": "corinthians",
    "corinthians paulista": "corinthians",
    "sao paulo fc": "sao paulo",
    "sao paulo futebol clube": "sao paulo",
    "clube de regatas do flamengo": "flamengo",
    "sociedade esportiva palmeiras": "palmeiras",
    "fluminense football club": "fluminense",
    "gremio foot ball porto alegrense": "gremio",
    "club de regatas vasco da gama": "vasco",
    "vasco da gama": "vasco",
    "clube atletico mineiro": "atletico mineiro",
    "atletico mg": "atletico mineiro",
    "atletico pr": "athletico paranaense",
    "athletico pr": "athletico paranaense",
    "atletico paranaense": "athletico paranaense",
}


def fold_text(value: str | None) -> str:
    """Lowercase, remove accents, and collapse punctuation and whitespace."""
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _NON_ALNUM.sub(" ", ascii_text.lower()).strip()


def normalize_team(value: str | None) -> str:
    """Return a stable lookup key for a team name from any bundled source."""
    original_key = fold_text(value)
    if original_key in _TEAM_ALIASES:
        return _TEAM_ALIASES[original_key]
    stripped = _STATE_SUFFIX.sub("", (value or "").strip())
    key = fold_text(stripped)
    return _TEAM_ALIASES.get(key, key)


def team_matches(candidate: str, query: str) -> bool:
    candidate_key = normalize_team(candidate)
    query_key = normalize_team(query)
    if not query_key:
        return False
    return candidate_key == query_key or (
        len(query_key) >= 4 and query_key in candidate_key.split(" (")[0]
    )


def parse_date(value: str) -> date:
    value = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {value!r}")


def parse_int(value: str | int | float | None) -> int | None:
    if value is None or str(value).strip() in {"", "nan", "NaN"}:
        return None
    try:
        return int(float(str(value)))
    except ValueError:
        return None
