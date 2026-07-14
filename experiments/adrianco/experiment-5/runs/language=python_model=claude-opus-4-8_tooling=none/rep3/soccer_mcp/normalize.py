# =============================================================================
# Context
# -----------------------------------------------------------------------------
# Project : Brazilian Soccer MCP Server
# Module  : soccer_mcp.normalize
# Purpose : Normalisation helpers used everywhere matching happens. The source
#           datasets are inconsistent: team names carry state suffixes
#           ("Palmeiras-SP"), country codes ("Nacional (URU)"), accents
#           ("São Paulo" vs "Sao Paulo") and long official forms ("Sport Club
#           Corinthians Paulista"). These helpers collapse all of that into a
#           single comparable key, and parse the several date formats present.
# Public  :
#   normalize_team(name)  -> canonical lowercase ascii key for matching
#   strip_suffix(name)    -> raw name with state/country suffix removed
#   strip_accents(text)   -> ascii-folded text
#   parse_date(value)     -> ISO "YYYY-MM-DD" or None
#   team_matches(query, candidate_norm) -> bool (loose substring/alias match)
# =============================================================================

from __future__ import annotations

import re
import unicodedata
from typing import Optional

# Common club aliases -> canonical normalised key. Keeps loose matching honest
# for clubs that appear under long official names in some datasets.
_ALIASES = {
    "sport club corinthians paulista": "corinthians",
    "sociedade esportiva palmeiras": "palmeiras",
    "clube de regatas do flamengo": "flamengo",
    "fluminense football club": "fluminense",
    "sao paulo futebol clube": "sao paulo",
    "santos futebol clube": "santos",
    "gremio foot-ball porto alegrense": "gremio",
    "sport club internacional": "internacional",
    "cruzeiro esporte clube": "cruzeiro",
    "clube atletico mineiro": "atletico mineiro",
    "atletico-mg": "atletico mineiro",
    "athletico-pr": "athletico paranaense",
    "atletico-pr": "athletico paranaense",
    "vasco da gama": "vasco",
    "club de regatas vasco da gama": "vasco",
}

# Trailing state/country suffix patterns, e.g. "-SP", " - MG", " (URU)", "-EQU".
_SUFFIX_RE = re.compile(
    r"\s*[-–]\s*[A-Za-z]{2,3}$"            # "-SP", " - MG", "-EQU"
    r"|\s*\([A-Za-z]{2,3}\)$",             # " (URU)"
)


def strip_accents(text: str) -> str:
    """Fold accented characters down to ASCII (São -> Sao, Grêmio -> Gremio)."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def strip_suffix(name: str) -> str:
    """Remove a single trailing state/country suffix from a raw team name."""
    if not name:
        return ""
    cleaned = name.strip()
    # Apply repeatedly in case of doubled suffixes (rare but cheap).
    prev = None
    while prev != cleaned:
        prev = cleaned
        cleaned = _SUFFIX_RE.sub("", cleaned).strip()
    return cleaned


def normalize_team(name: str) -> str:
    """Return a canonical lowercase, accent-free, suffix-free key for a team."""
    if not name:
        return ""
    base = strip_suffix(name)
    key = strip_accents(base).lower().strip()
    key = re.sub(r"[.\-_]+", " ", key)        # punctuation -> space
    key = re.sub(r"\s+", " ", key).strip()
    return _ALIASES.get(key, key)


def normalize_text(text: str) -> str:
    """Generic lowercase + accent-fold for player / club / position matching."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", strip_accents(text).lower()).strip()


def team_matches(query: str, candidate_norm: str) -> bool:
    """Loose match: does the (normalised) query refer to this normalised team?

    Matching is symmetric-substring so "flamengo" matches "flamengo" and a
    query for the full official name matches the short stored key and vice
    versa.
    """
    q = normalize_team(query)
    if not q or not candidate_norm:
        return False
    return q == candidate_norm or q in candidate_norm or candidate_norm in q


def parse_date(value: str) -> Optional[str]:
    """Parse the various source date formats into ISO 'YYYY-MM-DD'.

    Handles:
      - "2023-09-24" / "2012-05-19 18:30:00"  (ISO, optional time)
      - "29/03/2003"                          (Brazilian DD/MM/YYYY)
      - "2003.01.0001"-style ids are NOT dates and return None.
    """
    if not value:
        return None
    value = value.strip()
    if not value:
        return None

    # ISO, possibly with a trailing time component.
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", value)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # Brazilian DD/MM/YYYY.
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", value)
    if m:
        day, month, year = m.group(1), m.group(2), m.group(3)
        return f"{year}-{int(month):02d}-{int(day):02d}"

    return None


def year_from_date(iso_date: Optional[str]) -> Optional[int]:
    """Extract the year as an int from an ISO date string."""
    if not iso_date:
        return None
    try:
        return int(iso_date[:4])
    except (ValueError, TypeError):
        return None


def to_int(value) -> Optional[int]:
    """Best-effort int conversion tolerant of floats / blanks / quotes."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    s = str(value).strip().strip('"')
    if s == "" or s.lower() in ("nan", "none", "null"):
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None
