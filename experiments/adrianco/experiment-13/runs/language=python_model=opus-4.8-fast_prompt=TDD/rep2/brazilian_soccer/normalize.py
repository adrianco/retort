"""
Context
=======
Team-name normalization for the Brazilian Soccer knowledge base.

The provided datasets spell team names in several incompatible ways:

* with a state suffix       -- "Palmeiras-SP", "América - MG"
* with a country suffix     -- "Nacional (URU)", "Barcelona-EQU"
* with Portuguese accents   -- "São Paulo", "Grêmio", "Avaí"
* as full official names    -- "Sport Club Corinthians Paulista"

To match a team consistently across files we reduce every name to a
canonical key: accents stripped, lower-cased, suffixes removed and a small
alias table applied so that well-known clubs collapse to one short name.
"""

from __future__ import annotations

import re
import unicodedata

# Regexes for trailing location suffixes (capture the location code).
_PAREN_SUFFIX = re.compile(r"\s*\(([^)]*)\)\s*$")          # "Nacional (URU)"
_DASH_SUFFIX = re.compile(r"\s*-\s*([A-Za-z]{2,3})\s*$")    # "Palmeiras-SP", "América - MG"

# Base names that are shared by several different clubs distinguished only by
# their state/country code (e.g. Atlético-MG vs Atlético-PR). For these we must
# NOT discard the suffix, or two distinct clubs would merge into one.
_AMBIGUOUS_BASES = {"atletico", "america"}

# Alias table mapping a normalized variant -> canonical normalized key.
# Keys and values are already accent-stripped / lower-cased. For ambiguous
# clubs the key includes the lower-cased state code (e.g. "atletico mg").
_ALIASES = {
    "sport club corinthians paulista": "corinthians",
    "sc corinthians paulista": "corinthians",
    "sociedade esportiva palmeiras": "palmeiras",
    "clube de regatas do flamengo": "flamengo",
    "sao paulo futebol clube": "sao paulo",
    "santos futebol clube": "santos",
    "gremio foot-ball porto alegrense": "gremio",
    "fortaleza esporte clube": "fortaleza",
    # Ambiguous "Atlético" clubs -> canonical full names.
    "atletico mg": "atletico mineiro",
    "clube atletico mineiro": "atletico mineiro",
    "atletico pr": "athletico paranaense",
    "athletico pr": "athletico paranaense",
    "atletico paranaense": "athletico paranaense",
    "atletico go": "atletico goianiense",
    "atletico goianiense": "atletico goianiense",
    # Ambiguous "América" clubs.
    "america mg": "america mineiro",
    "america rn": "america de natal",
    "america rj": "america do rio de janeiro",
}


def strip_accents(text: str) -> str:
    """Return *text* with Portuguese diacritics removed (UTF-8 safe)."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_team(name: str) -> str:
    """Reduce a raw team name to its canonical matching key.

    Strips location suffixes, accents and casing, then applies the alias
    table. Returns an empty string for falsy input.
    """
    if not name:
        return ""
    cleaned = name.strip()
    # Strip trailing location suffixes repeatedly (e.g. "Foo (URU) - SP"),
    # remembering the outermost location code we removed.
    code = ""
    while True:
        mp = _PAREN_SUFFIX.search(cleaned)
        md = _DASH_SUFFIX.search(cleaned)
        if md:
            code = md.group(1)
            cleaned = _DASH_SUFFIX.sub("", cleaned)
        elif mp:
            code = mp.group(1)
            cleaned = _PAREN_SUFFIX.sub("", cleaned)
        else:
            break
    base = re.sub(r"\s+", " ", strip_accents(cleaned).lower().strip())
    # For ambiguous bases, keep the state code so distinct clubs stay distinct.
    if base in _AMBIGUOUS_BASES and code:
        base = f"{base} {strip_accents(code).lower()}"
    return _ALIASES.get(base, base)


def teams_match(a: str, b: str) -> bool:
    """True when two raw team names refer to the same club."""
    na, nb = normalize_team(a), normalize_team(b)
    return bool(na) and na == nb
