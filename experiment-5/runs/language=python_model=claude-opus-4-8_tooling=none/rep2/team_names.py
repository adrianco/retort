"""
Team-name normalization utilities for the Brazilian Soccer MCP server.

Context
-------
The provided Kaggle datasets use inconsistent naming conventions for the same
club, for example:

    - With a state suffix:   "Palmeiras-SP", "Flamengo-RJ"
    - With a country suffix: "Nacional (URU)", "Barcelona-EQU"
    - With spaced suffix:     "America - MG", "Atletico - PR"
    - Accented / unaccented:  "Sao Paulo" vs "Sao Paulo", "Gremio" vs "Gr*emio"

Crucially, the state/country code is part of a club's IDENTITY, not noise:
"Atletico-MG" (Mineiro), "Atletico-GO" (Goianiense) and "Athletico-PR"
(Paranaense) are three different clubs, as are "America-MG" and "America-RN".
So normalization must FOLD accents and spelling while PRESERVING the region.

Every team name is therefore reduced to two parts:

    * base   -- the club name with any trailing region code removed
    * region -- the two/three-letter state or country code (or None)

From these we derive:

    * display_team(base, region) -- canonical "Base-REGION" display string
    * team_key(base, region)     -- accent-free, lower-cased identity key that
                                    includes the region, used for de-duplication
                                    and equality matching across datasets.

This module is dependency-free (standard library only).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional, Tuple

# Brazilian states plus the country codes seen in the Libertadores dataset.
_REGION_CODES = {
    # Brazilian states
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
    # South-American country codes (Libertadores)
    "ARG", "URU", "PAR", "CHI", "BOL", "PER", "EQU", "COL", "VEN", "BRA",
    "MEX",
}

# A few cross-source spelling variants that survive accent folding and so need
# an explicit alias.  Keys are base-only keys (region appended separately).
_BASE_ALIASES = {
    "vasco da gama": "vasco",
    "ec bahia": "bahia",
    "fortaleza fc": "fortaleza",
    "sao paulo fc": "sao paulo",
    # "Athletico" (Paranaense's stylised spelling) folds onto "atletico"; the
    # region code keeps it distinct from Atletico-MG / Atletico-GO.
    "athletico": "atletico",
    "athletico paranaense": "atletico",
    "atletico paranaense": "atletico",
    "atletico mineiro": "atletico",
    "atletico goianiense": "atletico",
}

_SUFFIX_DASH = re.compile(r"\s*-\s*([A-Za-z]{2,3})\s*$")
_SUFFIX_PAREN = re.compile(r"\s*\(([A-Za-z]{2,4})\)\s*$")
_SUFFIX_SPACE = re.compile(r"\s+([A-Z]{2,3})\s*$")


def strip_accents(text: str) -> str:
    """Return ``text`` with diacritics removed (NFKD fold)."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _norm(text: str) -> str:
    """Accent-free, lower-case, punctuation-collapsed form of ``text``."""
    text = strip_accents(text).lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def split_team(raw: str) -> Tuple[str, Optional[str]]:
    """Split a raw team name into ``(base, region)``.

    A trailing region code in any of the supported forms ("-SP", " - SP",
    "(URU)", " RJ") is recognised and returned separately; the base keeps its
    original spelling/accents.  ``region`` is upper-cased, or ``None`` when no
    recognised code is present.
    """
    if raw is None:
        return "", None
    name = re.sub(r"\s+", " ", str(raw)).strip()
    if not name:
        return "", None

    paren = _SUFFIX_PAREN.search(name)
    if paren and paren.group(1).upper() in _REGION_CODES:
        return name[: paren.start()].strip(), paren.group(1).upper()

    dash = _SUFFIX_DASH.search(name)
    if dash and dash.group(1).upper() in _REGION_CODES:
        return name[: dash.start()].strip(), dash.group(1).upper()

    space = _SUFFIX_SPACE.search(name)
    if space and space.group(1).upper() in _REGION_CODES:
        return name[: space.start()].strip(), space.group(1).upper()

    return name, None


def _base_key(base: str) -> str:
    key = _norm(base)
    return _BASE_ALIASES.get(key, key)


def display_team(base: str, region: Optional[str]) -> str:
    """Canonical, human-readable display string ("Base-REGION")."""
    base = re.sub(r"\s+", " ", (base or "").strip())
    if region:
        return f"{base}-{region}"
    return base


def team_key(base: str, region: Optional[str]) -> str:
    """Region-aware identity key used for de-duplication and equality."""
    key = _base_key(base)
    if region:
        return f"{key}-{region.lower()}"
    return key


# ----------------------------------------------------------------------------
# Convenience helpers that operate directly on a raw name string.
# ----------------------------------------------------------------------------
def display_name(raw: str) -> str:
    base, region = split_team(raw)
    return display_team(base, region)


def match_key(raw: str) -> str:
    base, region = split_team(raw)
    return team_key(base, region)


def keys_match(query_base_key: str, query_region: Optional[str],
               cand_base_key: str, cand_region: Optional[str]) -> bool:
    """Match a (base, region) query against a candidate.

    The base names must be equal or one a substring of the other.  A region in
    the query must equal the candidate's region; an absent query region matches
    any region (so "Atletico" matches every Atletico, "Atletico-MG" only the
    Mineiro club).
    """
    if not query_base_key or not cand_base_key:
        return False
    base_ok = (
        query_base_key == cand_base_key
        or query_base_key in cand_base_key
        or cand_base_key in query_base_key
    )
    if not base_ok:
        return False
    if query_region and cand_region and query_region != cand_region:
        return False
    return True


def names_match(query: str, candidate: str) -> bool:
    """True when ``query`` matches ``candidate`` as a club (region-aware)."""
    qb, qr = split_team(query)
    cb, cr = split_team(candidate)
    return keys_match(_base_key(qb), qr, _base_key(cb), cr)
