"""
================================================================================
brazilian_soccer_mcp.normalize
================================================================================

CONTEXT
-------
Pure helper functions for normalising the messy, multi-source Brazilian soccer
data into consistent *canonical* club identities and comparable values.

The datasets name the same club in many ways:
    "Atletico-MG"  vs  "Atletico Mineiro"          (state suffix vs full name)
    "Sao Paulo-SP" vs  "Sao Paulo"                 (with/without state suffix)
    "Sport-PE"     vs  "Sport Recife"
    "Nacional (URU)"                               (Libertadores country codes)
Dates appear as ISO ("2023-09-24"), ISO+time ("2012-05-19 18:30:00") and the
Brazilian format ("29/03/2003"). Portuguese text uses accents and cedillas.

The key design choice is *canonicalisation*: every raw team string is mapped to
a single canonical display name (and a canonical normalised key). This unifies
cross-source spellings (so "Atletico-MG" and "Atletico Mineiro" are one club)
WITHOUT conflating genuinely different clubs that merely share a base name
(Atlético-MG / Atlético-PR / Atlético-GO stay distinct, América-MG stays
distinct from plain clubs).

This module has NO third-party dependencies and is safe to import anywhere
(including tests) without loading pandas.
================================================================================
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Optional

# Brazilian state abbreviations used as team suffixes (e.g. "Palmeiras-SP").
_STATE_CODES = {
    "ac", "al", "am", "ap", "ba", "ce", "df", "es", "go", "ma", "mg", "ms",
    "mt", "pa", "pb", "pe", "pi", "pr", "rj", "rn", "ro", "rr", "rs", "sc",
    "se", "sp", "to",
}

# Organisation words that add no identity (e.g. "EC Bahia" -> "Bahia").
_ORG_TOKENS = {"ec", "fc", "sc", "afc", "cd", "cr", "ca", "se", "fbc", "sad"}

# Base names that are AMBIGUOUS without their state suffix and must keep it.
_AMBIGUOUS_BASES = {"america", "atletico", "athletico"}

# Map a base key -> canonical display name. Only needed where source spellings
# diverge or where the base name is ambiguous.
_CLUB_CANON = {
    "atletico mg": "Atlético Mineiro",
    "atletico mineiro": "Atlético Mineiro",
    "atletico pr": "Athletico Paranaense",
    "atletico paranaense": "Athletico Paranaense",
    "athletico paranaense": "Athletico Paranaense",
    "atletico go": "Atlético Goianiense",
    "atletico goianiense": "Atlético Goianiense",
    "america mg": "América-MG",
    "america mineiro": "América-MG",
    "sport": "Sport Recife",
    "sport recife": "Sport Recife",
    "bragantino": "Bragantino",
    "red bull bragantino": "Bragantino",
    "vasco da gama": "Vasco",
    "vasco": "Vasco",
}

# Cosmetic display names so accents survive the round-trip (purely visual).
_DISPLAY_MAP = {
    "sao paulo": "São Paulo",
    "gremio": "Grêmio",
    "goias": "Goiás",
    "avai": "Avaí",
    "ceara": "Ceará",
    "parana": "Paraná",
    "vitoria": "Vitória",
    "criciuma": "Criciúma",
    "nautico": "Náutico",
    "cuiaba": "Cuiabá",
    "csa": "CSA",
}


def strip_accents(text) -> str:
    """Return *text* with accents/diacritics removed (São -> Sao, Grêmio -> Gremio)."""
    if text is None:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text))
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _tokens(name) -> list:
    """Accent-stripped, lower-cased alphanumeric tokens of *name*."""
    if name is None:
        return []
    cleaned = strip_accents(name).lower()
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned)
    return cleaned.split()


def base_key(name) -> str:
    """Loose identity key: tokens minus org words and a trailing state suffix.

    The trailing state code is kept when the remaining base would be ambiguous
    (the three Atléticos, América) so distinct clubs are not merged.
    """
    toks = [t for t in _tokens(name) if t not in _ORG_TOKENS]
    if len(toks) >= 2 and toks[-1] in _STATE_CODES:
        candidate = toks[:-1]
        if " ".join(candidate) not in _AMBIGUOUS_BASES:
            toks = candidate
    return " ".join(toks)


def normalize_team(name) -> str:
    """Plain normalised form of a team string (accents/punctuation removed)."""
    return " ".join(_tokens(name))


def canonical_team_name(name) -> str:
    """Best canonical *display* name for a team, unifying source spellings."""
    bk = base_key(name)
    if not bk:
        return str(name).strip() if name else ""
    if bk in _CLUB_CANON:
        return _CLUB_CANON[bk]
    if bk in _DISPLAY_MAP:
        return _DISPLAY_MAP[bk]
    return bk.title()


def canonical_norm(name) -> str:
    """Canonical normalised key used for matching and grouping (one per club)."""
    return normalize_team(canonical_team_name(name))


def clean_team_name(name) -> str:
    """Alias for :func:`canonical_team_name` (kept for readability at call sites)."""
    return canonical_team_name(name)


def team_matches(query: str, name: str) -> bool:
    """True if the user *query* refers to the team *name*.

    Matching is accent-insensitive and tolerant of state suffixes / full names
    via whole-word containment on the canonical normalised keys (so "flamengo"
    matches "Flamengo-RJ" and "vasco" matches "Vasco da Gama").
    """
    q = canonical_norm(query)
    n = canonical_norm(name)
    if not q or not n:
        return False
    if q == n:
        return True
    return f" {q} " in f" {n} "


# Date formats encountered across the datasets, tried in order.
_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d/%m/%y",
)


def parse_date(value) -> Optional[date]:
    """Parse the various dataset date formats into a ``datetime.date``.

    Returns ``None`` for missing / unparseable values.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "na", "none"}:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None
