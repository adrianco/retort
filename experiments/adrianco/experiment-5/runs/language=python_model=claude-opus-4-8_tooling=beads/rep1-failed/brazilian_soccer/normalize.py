"""
================================================================================
Context
================================================================================
Project   : Brazilian Soccer MCP Server
Module    : brazilian_soccer.normalize
Purpose   : Normalization helpers for the messy, multi-source datasets.

The source CSVs disagree on how they spell teams, format dates and encode
accented Portuguese text. This module centralises all the cleaning logic so the
rest of the codebase can rely on canonical forms:

  * normalize_team_name  -> strips state suffixes ("-SP", " - RJ", "(URU)"),
                            accents and punctuation, lowercases, and maps known
                            aliases ("Athletico-PR" -> "atletico paranaense",
                            "Sao Paulo"/"São Paulo FC" -> "sao paulo") so the
                            same club always matches regardless of source file.
  * display_team_name    -> a clean, human-friendly label for output.
  * parse_date           -> handles ISO ("2023-09-24"), datetime
                            ("2012-05-19 18:30:00") and Brazilian DD/MM/YYYY.
  * strip_accents        -> ASCII-folds accents/cedillas for matching.
================================================================================
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Optional


# --------------------------------------------------------------------------- #
# Accent / unicode handling
# --------------------------------------------------------------------------- #
def strip_accents(text: str) -> str:
    """Fold accents and cedillas to plain ASCII (São -> Sao, Grêmio -> Gremio)."""
    if text is None:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# Brazilian state abbreviations used as suffixes in the match datasets.
_BR_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

# Country codes that appear in Libertadores data, e.g. "Nacional (URU)".
_COUNTRY_PARENS = re.compile(r"\s*\([A-Za-z]{2,4}\)\s*$")


def _split_state(name: str) -> tuple[str, Optional[str]]:
    """Split a team name into (basename, state_abbrev_or_None).

    Handles "Palmeiras-SP", "América - MG", "Nacional (URU)" and long parenthetical
    descriptors like "Boavista Sport Club (antigo ...) - RJ".
    """
    name = _COUNTRY_PARENS.sub("", name)
    # Remove parenthetical descriptions anywhere (e.g. "(antigo ...)").
    name = re.sub(r"\([^)]*\)", " ", name)
    state: Optional[str] = None
    # "Team - SP" or "Team-SP" (Brazilian state abbreviation only).
    m = re.search(r"[\s\-]+([A-Za-z]{2})\s*$", name)
    if m and m.group(1).upper() in _BR_STATES:
        state = m.group(1).upper()
        name = name[: m.start()]
    return name.strip(" -"), state


def _strip_state_suffix(name: str) -> str:
    """Return just the basename, with any trailing state/country suffix removed."""
    return _split_state(name)[0]


# Base names that are ambiguous without a state, because several distinct clubs
# share them (Atlético-MG vs Athletico-PR vs Atlético-GO; América-MG vs América-RN).
# For these the state suffix is preserved when building the canonical key.
_AMBIGUOUS_BASES = {"atletico", "athletico", "america"}

# Generic club-type tokens that carry no identity (e.g. "Ceará SC" == "Ceará-CE",
# "Fortaleza EC" == "Fortaleza-CE"). Stripped so full-name and suffixed variants
# collapse to the same key. Deliberately excludes words like "sport" (Sport Recife).
_CLUB_TOKENS = {"fc", "ec", "sc", "ac", "cf", "aa", "fr", "cr", "afc", "se"}


def _strip_club_tokens(folded: str) -> str:
    """Drop standalone generic club-type tokens from an already-folded name."""
    parts = [t for t in folded.split() if t not in _CLUB_TOKENS]
    return " ".join(parts) if parts else folded


# Canonical alias map: normalized variant -> canonical normalized key.
# Built from a small table of {canonical: [variants...]} for readability.
_ALIAS_SOURCE = {
    # Ambiguous clubs: keyed by "base state" once the state is preserved.
    "atletico paranaense": [
        "athletico pr", "athletico paranaense", "atletico pr",
        "club athletico paranaense", "athletico",
    ],
    "atletico mineiro": ["atletico mg", "atletico mineiro"],
    "atletico goianiense": ["atletico go", "atletico goianiense"],
    "america mineiro": ["america mg", "america mineiro"],
    "america rn": ["america rn", "america fc natal", "america natal"],
    # Unambiguous clubs: collapse full names / abbreviations to one key.
    "sao paulo": ["sao paulo fc", "sao paulo", "sp fc"],
    "vasco da gama": ["vasco", "vasco da gama", "cr vasco da gama"],
    "vitoria": ["vitoria ba", "ec vitoria"],
    "botafogo": ["botafogo rj", "botafogo fr"],
    "gremio": ["gremio", "gremio fbpa"],
    "corinthians": [
        "corinthians", "sport club corinthians paulista", "sc corinthians paulista",
    ],
    "flamengo": ["flamengo", "cr flamengo", "clube de regatas do flamengo"],
    "fluminense": ["fluminense", "fluminense fc"],
    "palmeiras": ["palmeiras", "se palmeiras", "sociedade esportiva palmeiras"],
    "santos": ["santos", "santos fc"],
    "cruzeiro": ["cruzeiro", "cruzeiro ec"],
    "internacional": ["internacional", "sc internacional", "inter"],
    # Clubs that have been renamed / shortened across the datasets.
    "bragantino": [
        "bragantino", "red bull bragantino", "rb bragantino", "rb bragantino sp",
    ],
    "sport recife": ["sport recife", "sport"],
}

_ALIAS_MAP: dict[str, str] = {}
for _canon, _variants in _ALIAS_SOURCE.items():
    _canon_key = _canon.strip()
    for _v in _variants:
        _ALIAS_MAP[_v.strip()] = _canon_key


def normalize_team_name(name: Optional[str]) -> str:
    """Return a canonical, comparable key for a team name.

    Lowercased, accent-free, suffix-free, punctuation-collapsed, with known
    aliases mapped to a single canonical form. Returns "" for empty input.
    """
    if not name:
        return ""
    raw = str(name).strip()
    base, state = _split_state(raw)
    folded = strip_accents(base).lower()
    # Collapse punctuation to spaces, squeeze whitespace.
    folded = re.sub(r"[^a-z0-9 ]+", " ", folded)
    folded = re.sub(r"\s+", " ", folded).strip()
    # Drop generic club-type tokens ("FC", "EC", ...) so name variants collapse.
    folded = _strip_club_tokens(folded)
    # Keep the state for ambiguous bases so distinct clubs stay distinct.
    if state and folded in _AMBIGUOUS_BASES:
        folded = f"{folded} {state.lower()}"
    return _ALIAS_MAP.get(folded, folded)


def display_team_name(name: Optional[str]) -> str:
    """A cleaned, human-friendly version of a team name (suffix removed)."""
    if not name:
        return ""
    cleaned = _strip_state_suffix(str(name).strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")
    return cleaned or str(name).strip()


# --------------------------------------------------------------------------- #
# Date handling
# --------------------------------------------------------------------------- #
_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%Y.%m.%d",
    "%Y/%m/%d",
    "%d-%m-%Y",
)


def parse_date(value: Optional[str]) -> Optional[date]:
    """Parse a date from any of the formats used across the datasets.

    Returns a datetime.date, or None if the value cannot be parsed.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in ("nan", "none"):
        return None
    # Fast path: take just the date portion if a time is attached.
    head = text.split(" ")[0]
    for candidate in (text, head):
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                continue
    return None


def to_int(value, default: Optional[int] = None) -> Optional[int]:
    """Best-effort int conversion tolerating floats/strings/blank cells."""
    if value is None:
        return default
    text = str(value).strip()
    if not text or text.lower() in ("nan", "none"):
        return default
    try:
        return int(float(text))
    except (ValueError, TypeError):
        return default
