"""Normalization helpers for Brazilian soccer data.

The datasets use inconsistent conventions:

* Team names sometimes carry a state/country suffix (``Palmeiras-SP``,
  ``América - MG``, ``Nacional (URU)``) and sometimes do not (``Palmeiras``).
* Some teams share a base name and are only disambiguated by their state
  (``Atletico-MG`` vs ``Atletico-PR`` vs ``Atletico-GO``).
* Portuguese accents and spelling variants appear (``Grêmio`` / ``Gremio``,
  ``Athletico-PR`` / ``Atletico-PR``).
* Dates come in ISO (``2023-09-24``), ISO+time (``2012-05-19 18:30:00``) and
  Brazilian (``29/03/2003``) formats.
* Competitions are named differently across files (``Brazil Serie A`` vs
  ``Brasileirão``, ``Brazil Cup`` vs ``Copa do Brasil``).

This module centralises the logic so that every loader and query path matches
teams, competitions and dates consistently.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Optional

__all__ = [
    "strip_accents",
    "normalize_team",
    "team_key",
    "parse_date",
    "parse_int",
    "canonical_competition",
    "competition_matches",
]

# Brazilian state codes plus country codes that appear as suffixes in the data.
_STATE_CODES = {
    "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mg", "ms",
    "mt", "pa", "pb", "pe", "pi", "pr", "rj", "rn", "ro", "rr", "rs", "sc",
    "se", "sp", "to",
}
_COUNTRY_CODES = {
    "ar", "uy", "py", "cl", "co", "pe", "ec", "bo", "ve", "mx", "us", "wal",
    "br", "equ", "uru", "arg", "par", "bol", "ven", "col", "chi",
}
_SUFFIX_CODES = _STATE_CODES | _COUNTRY_CODES

# Base names that are genuinely shared by more than one club and therefore must
# keep their state suffix to stay distinct.
_AMBIGUOUS_BASES = {"atletico", "america"}

# Aliases mapping a normalized variant -> canonical team key.  Covers full club
# names and common ways a user might phrase a query.
_ALIASES = {
    "sport club corinthians paulista": "corinthians",
    "sociedade esportiva palmeiras": "palmeiras",
    "clube de regatas do flamengo": "flamengo",
    "sao paulo fc": "sao paulo",
    "sao paulo futebol clube": "sao paulo",
    "atletico mineiro": "atletico-mg",
    "clube atletico mineiro": "atletico-mg",
    "atletico paranaense": "atletico-pr",
    "athletico paranaense": "atletico-pr",
    "atletico goianiense": "atletico-go",
    "america mineiro": "america-mg",
    "vasco da gama": "vasco",
    "vasco de gama": "vasco",
    "red bull bragantino": "bragantino",
    "rb bragantino": "bragantino",
}


def strip_accents(text: str) -> str:
    """Remove diacritics, returning an ASCII-comparable string."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _split_suffix(base: str) -> tuple[str, Optional[str]]:
    """Split a normalized name into ``(base, suffix_code)``.

    Handles the several suffix conventions in the data:

    * ``palmeiras-sp``            -> dash, no spaces
    * ``america - mg``           -> dash with surrounding spaces
    * ``america rn``             -> space only (known codes only)
    * ``nacional (uru)``         -> parenthetical country code

    A dash-separated 2-3 letter token is always treated as a suffix (matching
    the dataset convention); a space-only separated token is only treated as a
    suffix when it is a known state/country code.
    """
    # Parenthetical country code, e.g. "nacional (uru)".
    base = re.sub(r"\s*\([^)]*\)\s*$", "", base).strip()

    m = re.search(r"\s*-\s*([a-z]{2,3})$", base)
    if m:
        return base[: m.start()].strip(" -"), m.group(1)
    m = re.search(r"\s+([a-z]{2,3})$", base)
    if m and m.group(1) in _SUFFIX_CODES:
        return base[: m.start()].strip(" -"), m.group(1)
    return base, None


def team_key(name: str) -> str:
    """Return a canonical matching key for a team name.

    Examples::

        team_key("Palmeiras-SP")        == "palmeiras"
        team_key("Grêmio")              == "gremio"
        team_key("Atlético-MG")         == "atletico-mg"
        team_key("Athletico Paranaense")== "atletico-pr"
    """
    if name is None:
        return ""
    s = strip_accents(str(name)).lower().strip()
    s = s.replace("athletico", "atletico")
    s = re.sub(r"\s+", " ", s)
    # Direct alias on the whole string first.
    if s in _ALIASES:
        return _ALIASES[s]

    base, suffix = _split_suffix(s)
    if base in _ALIASES:
        base = _ALIASES[base]
    if suffix and base in _AMBIGUOUS_BASES:
        key = f"{base}-{suffix}"
    else:
        key = base
    return _ALIASES.get(key, key)


def normalize_team(name: str) -> str:
    """Return a clean display name (suffix removed, accents preserved).

    Unlike :func:`team_key` this keeps the original accents so output reads
    naturally (e.g. ``São Paulo``).
    """
    if name is None:
        return ""
    raw = str(name).strip()
    # Remove parenthetical country codes for display too.
    raw_np = re.sub(r"\s*\([^)]*\)\s*$", "", raw).strip()
    ascii_lower = strip_accents(raw_np).lower()
    _, suffix = _split_suffix(re.sub(r"\s+", " ", ascii_lower))
    if suffix:
        # Drop the matching suffix from the original (accented) string.
        display = re.sub(r"\s*-\s*[A-Za-z]{2,3}$", "", raw_np).strip()
        if display == raw_np:  # space-form suffix (no dash)
            display = re.sub(r"\s+[A-Za-z]{2,3}$", "", raw_np).strip()
    else:
        display = raw_np
    return display or raw


def parse_int(value) -> Optional[int]:
    """Parse an integer, tolerating floats/blanks; ``None`` on failure."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        try:
            return int(float(s))
        except ValueError:
            return None


# --------------------------------------------------------------------------- #
# Competition canonicalization
# --------------------------------------------------------------------------- #
# Canonical competition labels used throughout the project.
BRASILEIRAO_A = "Brasileirão Série A"
BRASILEIRAO_B = "Brasileirão Série B"
BRASILEIRAO_C = "Brasileirão Série C"
BRASILEIRAO_D = "Brasileirão Série D"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"
RECOPA = "Recopa Sudamericana"

# Map a normalized free-text competition name to a canonical label.
_COMP_ALIASES = {
    "brasileirao": BRASILEIRAO_A,
    "brasileirao serie a": BRASILEIRAO_A,
    "campeonato brasileiro": BRASILEIRAO_A,
    "serie a": BRASILEIRAO_A,
    "serie a #2": BRASILEIRAO_A,
    "brazil serie a": BRASILEIRAO_A,
    "brasileiro": BRASILEIRAO_A,
    "brasileirao serie b": BRASILEIRAO_B,
    "serie b": BRASILEIRAO_B,
    "brasileirao serie c": BRASILEIRAO_C,
    "serie c": BRASILEIRAO_C,
    "brasileirao serie d": BRASILEIRAO_D,
    "serie d": BRASILEIRAO_D,
    "copa do brasil": COPA_DO_BRASIL,
    "brazil cup": COPA_DO_BRASIL,
    "brazil cup #2": COPA_DO_BRASIL,
    "cup": COPA_DO_BRASIL,
    "libertadores": LIBERTADORES,
    "copa libertadores": LIBERTADORES,
    "recopa": RECOPA,
    "recopa sudamericana": RECOPA,
}


def canonical_competition(name: str) -> Optional[str]:
    """Return the canonical competition label for free text, or ``None`` if it
    cannot be resolved to a known competition."""
    if not name:
        return None
    key = strip_accents(str(name)).lower().strip()
    key = re.sub(r"\s+", " ", key)
    if key in _COMP_ALIASES:
        return _COMP_ALIASES[key]
    # Already a canonical label?
    for canon in (BRASILEIRAO_A, BRASILEIRAO_B, BRASILEIRAO_C, BRASILEIRAO_D,
                  COPA_DO_BRASIL, LIBERTADORES, RECOPA):
        if strip_accents(canon).lower() == key:
            return canon
    return None


def competition_matches(query: str, label: str) -> bool:
    """Return True if a match labelled ``label`` satisfies a competition query.

    Resolves both sides to canonical labels for an exact comparison; falls back
    to a substring test when the query is not a recognised competition.
    """
    if not query:
        return True
    q_canon = canonical_competition(query)
    if q_canon is not None:
        return label == q_canon
    return strip_accents(query).lower().strip() in strip_accents(label).lower()


_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d/%m/%y",
    "%Y/%m/%d",
)


def parse_date(value) -> Optional[date]:
    """Parse the various date formats found in the datasets into a ``date``."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # Last resort: take the leading ISO date if there is trailing noise.
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None
