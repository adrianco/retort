"""Normalization helpers for inconsistent Kaggle text and date formats."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime


_STATE_SUFFIX = re.compile(r"\s*-\s*(?:AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)$", re.I)
_COMPACT_STATE_SUFFIX = re.compile(r"-(?:AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)$", re.I)

_RAW_TEAM_ALIASES = {
    "atletico mg": "atletico mineiro",
    "atletico go": "atletico goianiense",
    "atletico pr": "athletico paranaense",
    "athletico pr": "athletico paranaense",
    "america mg": "america mineiro",
    "america rn": "america rn",
    "botafogo rj": "botafogo",
    "botafogo sp": "botafogo sp",
    "flamengo rj": "flamengo",
    "fluminense rj": "fluminense",
    "sao paulo sp": "sao paulo",
    "corinthians sp": "corinthians",
    "palmeiras sp": "palmeiras",
    "santos sp": "santos",
    "gremio rs": "gremio",
    "internacional rs": "internacional",
}

_TEAM_ALIASES = {
    "clube de regatas do flamengo": "flamengo",
    "flamengo rj": "flamengo",
    "fluminense football club": "fluminense",
    "sport club corinthians paulista": "corinthians",
    "corinthians paulista": "corinthians",
    "sao paulo futebol clube": "sao paulo",
    "sao paulo fc": "sao paulo",
    "sociedade esportiva palmeiras": "palmeiras",
    "santos futebol clube": "santos",
    "santos fc": "santos",
    "club de regatas vasco da gama": "vasco",
    "vasco da gama": "vasco",
    "gremio foot ball porto alegrense": "gremio",
    "gremio fbpa": "gremio",
    "clube atletico mineiro": "atletico mineiro",
    "atletico mg": "atletico mineiro",
    "atletico mineiro": "atletico mineiro",
    "club athletico paranaense": "athletico paranaense",
    "atletico pr": "athletico paranaense",
    "athletico pr": "athletico paranaense",
    "internacional porto alegre": "internacional",
    "sport club internacional": "internacional",
    "botafogo de futebol e regatas": "botafogo",
}

_COMPETITION_ALIASES = {
    "brasileirao": "brasileirao serie a",
    "brasileiro": "brasileirao serie a",
    "serie a": "brasileirao serie a",
    "campeonato brasileiro": "brasileirao serie a",
    "brazilian cup": "copa do brasil",
    "copa brasil": "copa do brasil",
    "libertadores": "copa libertadores",
    "copa libertadores": "copa libertadores",
}


def fold_text(value: str | None) -> str:
    """Return accent-insensitive, whitespace-normalized lowercase text."""
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    asciiish = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(asciiish.casefold().strip().split())


def normalize_team_name(value: str | None) -> str:
    """Create a stable comparison key while retaining names in output objects."""
    text = (value or "").strip()
    raw_key = re.sub(r"[^a-z0-9]+", " ", fold_text(text)).strip()
    if raw_key in _RAW_TEAM_ALIASES:
        return _RAW_TEAM_ALIASES[raw_key]
    text = _STATE_SUFFIX.sub("", text)
    text = _COMPACT_STATE_SUFFIX.sub("", text)
    text = re.sub(r"\s*\([^)]*(?:antigo|former)[^)]*\)\s*", " ", text, flags=re.I)
    key = fold_text(text)
    key = re.sub(r"[^a-z0-9]+", " ", key).strip()
    return _TEAM_ALIASES.get(key, key)


def normalize_competition(value: str | None) -> str:
    key = fold_text(value)
    key = re.sub(r"[^a-z0-9]+", " ", key).strip()
    return _COMPETITION_ALIASES.get(key, key)


def parse_date(value: str) -> datetime:
    value = value.strip()
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, pattern)
        except ValueError:
            pass
    raise ValueError(f"Unsupported date format: {value!r}")


def safe_int(value: object) -> int | None:
    if value is None or str(value).strip() in {"", "nan", "NaN"}:
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def safe_float(value: object) -> float | None:
    if value is None or str(value).strip() in {"", "nan", "NaN"}:
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None
