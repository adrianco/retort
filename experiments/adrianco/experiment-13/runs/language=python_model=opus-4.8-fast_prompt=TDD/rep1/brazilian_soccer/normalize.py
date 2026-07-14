"""Normalization helpers for team names, dates and scores.

The bundled datasets use inconsistent conventions (state suffixes such as
``-SP``, country tags such as ``(URU)``, full club names, mixed date formats
and ``-`` for unplayed matches).  These helpers turn the raw values into a
consistent form so the rest of the system can match and compare reliably.
"""
from __future__ import annotations

import datetime
import re
import unicodedata
from typing import Optional

# Trailing country tag, e.g. "Nacional (URU)".
_PAREN_TAG_RE = re.compile(r"\s*\(([A-Za-z]{2,4})\)\s*$")
# Trailing state/country code, e.g. "Palmeiras-SP" or "América - MG".
_DASH_TAG_RE = re.compile(r"\s*-\s*([A-Za-z]{2,3})\s*$")

# Map of well-known full / alternate names to a canonical short name.  Keyed by
# the accent-stripped, lower-cased full name (see :func:`_basic_key`).
_ALIASES = {
    "sport club corinthians paulista": "Corinthians",
    "sociedade esportiva palmeiras": "Palmeiras",
    "clube de regatas do flamengo": "Flamengo",
    "santos futebol clube": "Santos",
    "sao paulo futebol clube": "São Paulo",
    "fortaleza esporte clube": "Fortaleza",
    "gremio foot-ball porto alegrense": "Grêmio",
}


def strip_accents(text: str) -> str:
    """Return ``text`` with diacritics removed (São -> Sao, Grêmio -> Gremio)."""
    if text is None:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(text))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _strip_tags(name: str) -> str:
    """Remove trailing state/country suffixes, repeatedly if stacked."""
    previous = None
    current = name.strip()
    while previous != current:
        previous = current
        current = _PAREN_TAG_RE.sub("", current).strip()
        current = _DASH_TAG_RE.sub("", current).strip()
    return current


def _basic_key(name: str) -> str:
    return strip_accents(name).lower().strip()


# Club-type abbreviations / words and Brazilian state codes that appear as noise
# tokens in team names (e.g. "Cuiaba FC", "EC Juventude", "Botafogo RJ").
_NOISE_TOKENS = {
    # club-type abbreviations
    "fc", "ec", "sc", "cf", "ac", "aa", "se", "ca", "cr", "cd", "afc", "fbc",
    # club-type words
    "club", "clube", "futebol", "esporte", "esportivo", "regatas", "atletico",
    # Brazilian state codes
    "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms", "mg",
    "pa", "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sp", "to",
}
# Words intentionally excluded from removal because they are also real names
# on their own: "sport" (Sport Recife), "atletico" handled cautiously above.
_NOISE_TOKENS.discard("atletico")


def normalize_team_name(raw: str) -> str:
    """Return a clean display name for a raw team string.

    Strips state/country suffixes and maps known full names to their common
    short form.  Accents are preserved for display.
    """
    if raw is None:
        return ""
    cleaned = _strip_tags(str(raw))
    alias = _ALIASES.get(_basic_key(cleaned))
    if alias:
        return alias
    return cleaned


def team_key(raw: str) -> str:
    """Return an accent/case-insensitive key used for matching team names.

    Strips club-type tokens (FC, EC, Clube, ...) and Brazilian state codes so
    that variants like "Cuiaba FC", "EC Juventude" and "Botafogo RJ" match
    their plain forms.  If filtering would remove every token, the unfiltered
    key is kept so short names (e.g. "Sport") are not lost.
    """
    base = _basic_key(normalize_team_name(raw))
    tokens = base.split()
    filtered = [t for t in tokens if t not in _NOISE_TOKENS]
    if not filtered:
        return base
    return " ".join(filtered)


def parse_date(value) -> Optional[datetime.date]:
    """Parse the various date formats found in the datasets into a date."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none"}:
        return None
    # Drop any time component.
    text = text.split(" ")[0].split("T")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y.%m.%d", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_goal(value) -> Optional[int]:
    """Parse a goal count; returns ``None`` for unplayed/blank values."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"-", "nan", "NaN", "None"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None
