"""
================================================================================
Module: brazilian_soccer_mcp.normalize
--------------------------------------------------------------------------------
Context:
    Brazilian soccer datasets use inconsistent naming and date conventions
    (see TASK.md "Data Quality Notes"). The same club may appear as
    "Palmeiras-SP" or "Palmeiras", "São Paulo" vs "Sao Paulo",
    "Nacional (URU)", or as a long official name. Dates appear as ISO datetimes,
    ISO dates and Brazilian DD/MM/YYYY strings.

    IMPORTANT subtlety: the state/country suffix is NOT mere noise — it
    *disambiguates* distinct clubs that share a base name: Atlético-MG vs
    Atlético-GO vs Atlético-PR, América-MG vs América-RN, or Nacional (URU) vs
    Nacional. So normalization keeps the suffix as part of a team's canonical
    identity, while query matching is suffix-tolerant: a user searching
    "Palmeiras" still finds "Palmeiras-SP", and "Atlético" matches every
    Atlético (the caller can disambiguate by passing the suffix).

Responsibility:
    Pure, dependency-free helpers for: accent stripping, canonical team names &
    keys, suffix/base extraction, suffix-tolerant team matching, and multi-format
    date / integer parsing. Side-effect free for easy unit testing.
================================================================================
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Optional

# Trailing "(URU)", "(EQU)" country-code style suffix.
_PAREN_SUFFIX = re.compile(r"\((?P<code>[A-Za-z]{2,3})\)\s*$")
# Trailing "-SP", " - MG", "-EQU" state/country suffix.
_DASH_SUFFIX = re.compile(r"-\s*(?P<code>[A-Za-z]{2,3})\s*$")
_WHITESPACE = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    """Return *text* with diacritics removed (São -> Sao, Grêmio -> Gremio)."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def clean_team_name(raw: str) -> str:
    """Return a canonical, human-readable team name.

    Trims quotes/whitespace and canonicalizes the separator before a
    state/country suffix so spelling variants collapse, while *keeping* the
    suffix (it disambiguates clubs):

        "Palmeiras-SP"   -> "Palmeiras-SP"
        "América - MG"   -> "América-MG"
        "Nacional (URU)" -> "Nacional (URU)"
        '  "Flamengo" '  -> "Flamengo"
    """
    if raw is None:
        return ""
    name = raw.strip().strip('"').strip()
    name = _WHITESPACE.sub(" ", name).strip()
    # Canonicalize "Base - MG" / "Base-MG" -> "Base-MG".
    m = _DASH_SUFFIX.search(name)
    if m:
        base = name[: m.start()].rstrip()
        return f"{base}-{m.group('code')}"
    return name


def team_suffix(raw: str) -> Optional[str]:
    """Return the upper-cased state/country suffix code, or ``None``."""
    name = (raw or "").strip().strip('"').strip()
    m = _DASH_SUFFIX.search(name) or _PAREN_SUFFIX.search(name)
    return m.group("code").upper() if m else None


def base_name(raw: str) -> str:
    """Return the team name with any state/country suffix removed."""
    name = clean_team_name(raw)
    name = _PAREN_SUFFIX.sub("", name).rstrip()
    name = _DASH_SUFFIX.sub("", name).rstrip()
    return name


def team_key(raw: str) -> str:
    """Accent-insensitive lowercase key for the *full* canonical name.

    "Atlético-MG" and "Atletico-MG" both -> "atletico-mg" (same club);
    "Atlético-GO" -> "atletico-go" (different club, distinct key).
    """
    return strip_accents(clean_team_name(raw)).lower().strip()


def base_key(raw: str) -> str:
    """Accent-insensitive lowercase key for the suffix-stripped base name."""
    return strip_accents(base_name(raw)).lower().strip()


def names_match(query: str, candidate: str) -> bool:
    """Suffix-tolerant, accent-insensitive team-name match.

    True when:
      * full keys are equal ("Atlético-MG" == "Atletico-MG"), or
      * the query has no suffix and its base equals the candidate's base
        ("Palmeiras" matches "Palmeiras-SP"; "Atlético" matches "Atlético-MG"), or
      * one base name contains the other as a whole-word run
        ("Corinthians" matches "Sport Club Corinthians Paulista").
    """
    if not query or not candidate:
        return False
    if team_key(query) == team_key(candidate):
        return True

    q_base, c_base = base_key(query), base_key(candidate)
    if not q_base or not c_base:
        return False
    q_suffix, c_suffix = team_suffix(query), team_suffix(candidate)
    # Both carry an explicit, *different* state/country code -> distinct clubs
    # that merely share a base name (Atlético-MG vs Atlético-GO).
    if q_suffix and c_suffix and q_suffix != c_suffix:
        return False
    if q_base == c_base and q_suffix is None:
        return True
    return contains_words(c_base, q_base) or contains_words(q_base, c_base)


def contains_words(haystack: str, needle: str) -> bool:
    """True if *needle* appears as a whole-word run inside *haystack*."""
    if not haystack or not needle:
        return False
    pattern = r"(?:^|\s)" + re.escape(needle) + r"(?:\s|$)"
    return re.search(pattern, haystack) is not None


# Backwards-compatible private alias.
_contains_words = contains_words


_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d/%m/%y",
    "%Y/%m/%d",
)


def parse_date(raw) -> Optional[date]:
    """Parse the many date formats in the datasets into a ``date``.

    Handles ISO datetimes ("2012-05-19 18:30:00"), ISO dates ("2023-09-24")
    and Brazilian "DD/MM/YYYY". Returns ``None`` for missing/unparseable values.
    """
    if not raw:
        return None
    text = str(raw).strip().strip('"').strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def parse_int(raw) -> Optional[int]:
    """Parse a possibly-quoted, possibly-float score cell ("2", "1.0") to int."""
    if raw is None:
        return None
    text = str(raw).strip().strip('"').strip()
    if text == "" or text.lower() in {"nan", "none", "null"}:
        return None
    try:
        return int(float(text))
    except (ValueError, TypeError):
        return None
