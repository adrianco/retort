"""
Normalization helpers for Brazilian soccer data.

Context
-------
The provided datasets use inconsistent conventions for team names and dates:

* Team names may carry a state suffix ("Palmeiras-SP", "América - MG"), a
  country parenthetical ("Nacional (URU)"), full official names, and Portuguese
  accents ("São Paulo", "Grêmio").
* Dates appear as ISO dates, ISO datetimes, and Brazilian ``DD/MM/YYYY``.

This module centralises the logic that turns those variants into stable,
comparable forms so the rest of the package can match and group reliably.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

# Trailing " - MG" or "-SP" style Brazilian state abbreviation.
_STATE_SUFFIX = re.compile(r"\s*-\s*[A-Za-z]{2}\s*$")
# Trailing country code in parentheses, e.g. "Nacional (URU)".
_COUNTRY_PAREN = re.compile(r"\s*\([A-Za-z]{2,4}\)\s*$")
# Trailing 3-letter country code attached with a dash, e.g. "Barcelona-EQU".
_COUNTRY_DASH = re.compile(r"\s*-\s*[A-Za-z]{3}\s*$")
_WS = re.compile(r"\s+")
# Any run of non-alphanumeric characters, used to tokenise team keys.
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def strip_accents(text: str) -> str:
    """Return *text* with diacritics removed (São -> Sao, Grêmio -> Gremio)."""
    if not text:
        return text
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_team_name(name: Optional[str]) -> str:
    """Clean a raw team name for display.

    Strips a trailing state/country suffix and collapses whitespace while
    preserving accents and the team's proper (possibly multi-word) name.
    """
    if name is None:
        return ""
    cleaned = str(name).strip()
    cleaned = _COUNTRY_PAREN.sub("", cleaned)
    cleaned = _COUNTRY_DASH.sub("", cleaned)
    cleaned = _STATE_SUFFIX.sub("", cleaned)
    cleaned = _WS.sub(" ", cleaned).strip()
    return cleaned


def team_key(name: Optional[str]) -> str:
    """Return a canonical match key: lowercase, accentless, tokenised.

    The key intentionally *retains* a state/country suffix as a trailing token
    ("Atletico-MG" -> ``"atletico mg"``) so that distinct clubs that share a
    base name (Atlético-MG vs Atlético-PR) do not collide. Looseness across the
    "with suffix" / "without suffix" conventions is handled by
    :func:`key_matches` / :func:`names_match`, not by discarding the suffix.
    """
    if name is None:
        return ""
    s = strip_accents(str(name)).lower()
    s = _NON_ALNUM.sub(" ", s)
    return _WS.sub(" ", s).strip()


def key_matches(query: Optional[str], key: str) -> bool:
    """True if *query* refers to a team whose canonical key is *key*.

    A match holds when the query's key equals *key*, or when either is a
    substring of the other. So a suffix-less "Flamengo" matches the stored
    ``"flamengo rj"``, while "Atletico-MG" does not match ``"atletico pr"``.
    """
    qk = team_key(query)
    if not qk or not key:
        return False
    return qk == key or qk in key or key in qk


def names_match(query: Optional[str], candidate: Optional[str]) -> bool:
    """Loose, accent- and suffix-insensitive match of two raw team names."""
    return key_matches(query, team_key(candidate))


def state_suffix(name: Optional[str]) -> Optional[str]:
    """Return the trailing two-letter state/country token uppercased, if any.

    Used to disambiguate display names that would otherwise collide
    ("Atletico-MG" vs "Atletico-PR").
    """
    key = team_key(name)
    if not key:
        return None
    last = key.split()[-1]
    if len(last) == 2 and last.isalpha():
        return last.upper()
    return None


def parse_date(value) -> Optional[str]:
    """Normalise a date/datetime string to ISO ``YYYY-MM-DD`` (or ``None``)."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    # ISO date or datetime: take the leading date token.
    iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})", text)
    if iso:
        return f"{iso.group(1)}-{iso.group(2)}-{iso.group(3)}"
    # Brazilian DD/MM/YYYY (optionally with a time component).
    br = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if br:
        day, month, year = br.group(1), br.group(2), br.group(3)
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return None


def year_of(value) -> Optional[int]:
    """Return the four-digit year for a date string, or ``None``."""
    iso = parse_date(value)
    if iso:
        return int(iso[:4])
    return None
