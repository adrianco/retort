"""
Context
=======
Module: brazilian_soccer_mcp.normalize
Purpose: Normalisation helpers for the Brazilian Soccer knowledge graph.

The provided Kaggle datasets use several different conventions for team names
(``"Palmeiras-SP"``, ``"Palmeiras"``, ``"São Paulo"`` vs ``"Sao Paulo"``,
``"América - MG"``, ``"Nacional (URU)"``) and for dates (ISO, Brazilian
``DD/MM/YYYY`` and ISO-with-time).  Every other module relies on the helpers in
here so that matching is consistent across files.

Key functions
-------------
* ``strip_accents`` - remove diacritics for accent-insensitive comparison.
* ``clean_team_name`` - human readable name without state/country suffix.
* ``team_key`` - canonical, accent/case-insensitive key used for matching.
* ``parse_date`` - parse the three date formats into ``datetime.date``.
* ``parse_int`` - tolerant int parser (handles ``"1.0"`` style values).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Optional

# Trailing state (UF) or country code such as "-SP", " - MG", "-EQU".
_SUFFIX_RE = re.compile(r"\s*-\s*[A-Za-z]{2,3}\s*$")
# Same, but capturing the code so it can be extracted.
_SUFFIX_CAPTURE_RE = re.compile(r"-\s*([A-Za-z]{2,3})\s*$")
# Parenthetical qualifiers such as "(URU)" or "(antigo ...)".
_PAREN_RE = re.compile(r"\([^)]*\)")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def strip_accents(text: str) -> str:
    """Return ``text`` with diacritics removed (São -> Sao, Grêmio -> Gremio)."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def clean_team_name(name: Optional[str]) -> str:
    """Return a readable team name with parenthetical/state suffixes removed.

    ``"Palmeiras-SP"`` -> ``"Palmeiras"``; ``"América - MG"`` -> ``"América"``;
    ``"Nacional (URU)"`` -> ``"Nacional"``.  Accents and casing are preserved so
    the value is suitable for display.
    """
    if not name:
        return ""
    cleaned = _PAREN_RE.sub("", name)
    cleaned = _SUFFIX_RE.sub("", cleaned)
    return cleaned.strip()


def team_key(name: Optional[str]) -> str:
    """Return a canonical matching key for a team name.

    The key is lower-cased, accent-stripped and free of state/country suffixes
    so that ``"Palmeiras-SP"``, ``"Palmeiras"`` and ``"palmeiras"`` collapse to
    the same value (``"palmeiras"``).
    """
    cleaned = clean_team_name(name)
    cleaned = strip_accents(cleaned).lower()
    cleaned = _NON_ALNUM_RE.sub(" ", cleaned).strip()
    return cleaned


def extract_state(name: Optional[str]) -> str:
    """Return the trailing state/country code of a team name, lower-cased.

    ``"Atletico-MG"`` -> ``"mg"``; ``"Nacional (URU)"`` -> ``""`` (the code is
    parenthetical, not a suffix); ``"Palmeiras"`` -> ``""``.  Used to tell apart
    clubs that share a base name but differ by state (Atlético-MG vs
    Atlético-PR).
    """
    if not name:
        return ""
    cleaned = _PAREN_RE.sub("", name).strip()
    match = _SUFFIX_CAPTURE_RE.search(cleaned)
    return match.group(1).lower() if match else ""


def normalize_text(text: Optional[str]) -> str:
    """Lower-case, accent-stripped, whitespace-collapsed text for searching."""
    if not text:
        return ""
    text = strip_accents(text).lower()
    return _NON_ALNUM_RE.sub(" ", text).strip()


def parse_int(value) -> Optional[int]:
    """Parse an int from values that may be ``"1"``, ``"1.0"``, ``1`` or empty."""
    if value is None:
        return None
    if isinstance(value, (int,)):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d/%m/%y",
)


def parse_date(value) -> Optional[date]:
    """Parse a date from the formats used across the datasets.

    Handles ISO (``2023-09-24``), ISO with time (``2012-05-19 18:30:00``) and
    Brazilian (``29/03/2003``).  Returns ``None`` when the value is missing or
    cannot be parsed.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    # Last resort: pull the leading YYYY-MM-DD if present.
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        try:
            return date(int(match[1]), int(match[2]), int(match[3]))
        except ValueError:
            return None
    return None
