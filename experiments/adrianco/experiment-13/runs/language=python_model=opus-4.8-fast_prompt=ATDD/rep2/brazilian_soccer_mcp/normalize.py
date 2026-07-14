"""Normalization helpers for Brazilian soccer data.

The provided datasets use inconsistent naming and formatting conventions:

* Team names may carry a state/country suffix ("Palmeiras-SP", "America - MG",
  "Nacional (URU)") or none at all ("Palmeiras").
* Portuguese text uses accents and cedillas ("Sao Paulo" vs "São Paulo",
  "Gremio" vs "Grêmio").
* Dates appear as ISO ("2023-09-24"), Brazilian ("29/03/2003") or with a time
  component ("2012-05-19 18:30:00").

These helpers produce stable, comparable keys and canonical display names so
that the same real-world entity matches regardless of which file it came from.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

# A trailing Brazilian state or country code, e.g. "-SP", " - RJ", "-EQU".
_SUFFIX_RE = re.compile(r"\s*[-–]\s*[A-Za-z]{2,3}\s*$")
# A parenthetical qualifier, e.g. "Nacional (URU)" or "Boavista (antigo ...)".
_PAREN_RE = re.compile(r"\s*\([^)]*\)")
_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]")


def strip_accents(text: str) -> str:
    """Remove diacritics, mapping e.g. 'São' -> 'Sao', 'Grêmio' -> 'Gremio'."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def clean_team_name(name: str) -> str:
    """Return a human-friendly canonical team name (suffixes/qualifiers removed).

    Accents are preserved so the display name still reads naturally.
    """
    if name is None:
        return ""
    cleaned = _PAREN_RE.sub("", str(name))
    # Strip a trailing state/country code suffix if present.
    cleaned = _SUFFIX_RE.sub("", cleaned)
    cleaned = _WS_RE.sub(" ", cleaned).strip()
    return cleaned or str(name).strip()


def team_key(name: str) -> str:
    """Return a normalized matching key for a team name.

    Accent-folded, lower-cased, punctuation-stripped and whitespace-collapsed so
    that "São Paulo-SP", "Sao Paulo" and "São Paulo" all map to "sao paulo".
    """
    if name is None:
        return ""
    cleaned = clean_team_name(name)
    folded = strip_accents(cleaned).lower()
    folded = _PUNCT_RE.sub(" ", folded)
    folded = _WS_RE.sub(" ", folded).strip()
    return folded


def text_key(text: str) -> str:
    """Accent-folded, lower-cased key for free text (player/club/nationality)."""
    if text is None:
        return ""
    folded = strip_accents(str(text)).lower()
    folded = _PUNCT_RE.sub(" ", folded)
    return _WS_RE.sub(" ", folded).strip()


# Canonical competition names keyed by a folded alias.
_COMPETITION_ALIASES = {
    "brasileirao": "Brasileirão",
    "brasileirao serie a": "Brasileirão",
    "serie a": "Brasileirão",
    "campeonato brasileiro": "Brasileirão",
    "serie b": "Brasileirão Série B",
    "brasileirao serie b": "Brasileirão Série B",
    "serie c": "Brasileirão Série C",
    "brasileirao serie c": "Brasileirão Série C",
    "copa do brasil": "Copa do Brasil",
    "brazilian cup": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
    "copa libertadores": "Copa Libertadores",
}


def canonical_competition(name: str) -> str:
    """Map any competition spelling to a canonical display name."""
    if name is None:
        return ""
    key = text_key(name)
    return _COMPETITION_ALIASES.get(key, str(name).strip())


def competition_key(name: str) -> str:
    """Folded key for a competition, resolved through canonical aliases."""
    return text_key(canonical_competition(name))


def parse_date(value: str) -> date | None:
    """Parse a date from the several formats present in the datasets.

    Returns a ``datetime.date`` or ``None`` when the value cannot be parsed.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none"}:
        return None
    # Drop a trailing time component if present.
    text = text.split(" ")[0]
    text = text.replace("T", " ").split(" ")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None
