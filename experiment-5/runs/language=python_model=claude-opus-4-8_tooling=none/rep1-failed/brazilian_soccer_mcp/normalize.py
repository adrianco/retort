"""
================================================================================
Brazilian Soccer MCP Server - Normalisation Helpers
================================================================================

CONTEXT
-------
The provided datasets use inconsistent conventions for team names, dates and
competition labels (documented in ``brazilian-soccer-mcp-guide.md``):

  * Team names may carry a state suffix ("Palmeiras-SP", "América - MG"),
    appear bare ("Palmeiras") or use a long official name ("Sport Club
    Corinthians Paulista").
  * Dates appear as ISO ("2023-09-24"), ISO+time ("2012-05-19 18:30:00") or
    Brazilian ("29/03/2003").
  * Portuguese text contains accents/cedilla ("São Paulo", "Grêmio", "Avaí").

This module centralises the logic used to *normalise* those values so that
matching across files is consistent. Two notions are produced for team names:

  * a **display name** - cleaned but human readable ("Flamengo");
  * a **match key**    - accent-stripped, lower-cased, alphanumeric only
                         ("flamengo") used for robust equality / substring
                         comparisons.

No third-party dependencies - standard library only.
================================================================================
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Optional

# Trailing Brazilian state suffix, e.g. "-SP", "-RJ", " - MG".
_STATE_SUFFIX_RE = re.compile(r"\s*-\s*[A-Za-z]{2}\s*$")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def strip_accents(text: str) -> str:
    """Return *text* with diacritics removed (São -> Sao, Grêmio -> Gremio)."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def clean_team_name(name: str) -> str:
    """Return a human-readable display name with the state suffix removed.

    "Palmeiras-SP"  -> "Palmeiras"
    "América - MG"  -> "América"
    "  Grêmio  "    -> "Grêmio"  (accents preserved for display)
    """
    if name is None:
        return ""
    cleaned = name.strip()
    cleaned = _STATE_SUFFIX_RE.sub("", cleaned).strip()
    return cleaned


def team_key(name: str) -> str:
    """Return the canonical match key for *name*.

    Accent-stripped, lower-cased, alphanumeric only. The state suffix is
    removed first so "Flamengo-RJ" and "Flamengo" collapse to "flamengo".
    """
    if not name:
        return ""
    cleaned = clean_team_name(name)
    folded = strip_accents(cleaned).lower()
    return _NON_ALNUM_RE.sub("", folded)


def names_match(query: str, candidate: str) -> bool:
    """True when *query* refers to *candidate* team.

    Matching is symmetric-substring on the normalised keys so that a short
    user query ("Corinthians") matches a long official name ("Sport Club
    Corinthians Paulista"), and a bare name matches a suffixed one.
    """
    q = team_key(query)
    c = team_key(candidate)
    if not q or not c:
        return False
    return q == c or q in c or c in q


# Accepted input date formats, tried in order.
_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
)


def parse_date(value: str) -> Optional[datetime]:
    """Parse a date string in any of the dataset formats. Returns ``None`` on
    failure or empty input."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in ("nan", "none", "null"):
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    # Last resort: take the leading 10 chars if they look like a date.
    head = text[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(head, fmt)
        except ValueError:
            continue
    return None


def iso_date(value: str) -> Optional[str]:
    """Return the ISO ``YYYY-MM-DD`` form of *value*, or ``None``."""
    dt = parse_date(value)
    return dt.strftime("%Y-%m-%d") if dt else None


def to_int(value) -> Optional[int]:
    """Best-effort integer conversion; tolerates floats / blanks. Returns
    ``None`` when the value cannot be interpreted."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text or text.lower() in ("nan", "none", "null", "-"):
        return None
    try:
        return int(float(text))
    except (ValueError, TypeError):
        return None


def to_float(value) -> Optional[float]:
    """Best-effort float conversion; tolerates blanks. Returns ``None`` when
    the value cannot be interpreted."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in ("nan", "none", "null", "-"):
        return None
    try:
        return float(text)
    except (ValueError, TypeError):
        return None


# --- Competition aliasing -------------------------------------------------

# Canonical competition labels used throughout the knowledge graph.
COMP_BRASILEIRAO = "Brasileirão Série A"
COMP_COPA_BRASIL = "Copa do Brasil"
COMP_LIBERTADORES = "Copa Libertadores"

# Alias keyword -> canonical label. Keys are accent-stripped lower-case
# fragments that may appear in a user query.
_COMP_ALIASES = {
    "brasileirao": COMP_BRASILEIRAO,
    "brasileirão": COMP_BRASILEIRAO,
    "serie a": COMP_BRASILEIRAO,
    "série a": COMP_BRASILEIRAO,
    "campeonato brasileiro": COMP_BRASILEIRAO,
    "brazilian league": COMP_BRASILEIRAO,
    "copa do brasil": COMP_COPA_BRASIL,
    "brazilian cup": COMP_COPA_BRASIL,
    "cup": COMP_COPA_BRASIL,
    "libertadores": COMP_LIBERTADORES,
    "copa libertadores": COMP_LIBERTADORES,
}


def canonical_competition(query: str) -> Optional[str]:
    """Map a free-text competition query to a canonical label, or ``None``."""
    if not query:
        return None
    folded = strip_accents(query).lower().strip()
    # Exact alias first.
    if folded in _COMP_ALIASES:
        return _COMP_ALIASES[folded]
    # Then substring containment on aliases.
    for alias, label in _COMP_ALIASES.items():
        alias_folded = strip_accents(alias).lower()
        if alias_folded in folded or folded in alias_folded:
            return label
    return None


def competition_matches(query: str, competition: str) -> bool:
    """True when a competition *query* refers to a match's *competition*.

    Handles canonical aliases (e.g. "Serie A" -> "Brasileirão Série A") and
    falls back to substring matching on accent-stripped text.
    """
    if not query:
        return True
    if not competition:
        return False
    canon = canonical_competition(query)
    comp_folded = strip_accents(competition).lower()
    if canon is not None:
        canon_folded = strip_accents(canon).lower()
        return canon_folded in comp_folded or comp_folded in canon_folded
    q_folded = strip_accents(query).lower().strip()
    return q_folded in comp_folded or comp_folded in q_folded
