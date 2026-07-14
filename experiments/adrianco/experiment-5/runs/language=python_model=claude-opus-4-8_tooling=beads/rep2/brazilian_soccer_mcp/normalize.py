"""
================================================================================
normalize.py - Team-name canonicalisation and multi-format date parsing
================================================================================

CONTEXT
-------
The provided datasets describe the same clubs in many different ways:

    "Palmeiras-SP"              (Brasileirao_Matches.csv, state suffix)
    "Palmeiras"                 (novo_campeonato_brasileiro.csv, no suffix)
    "Atletico-MG" vs "Atlético Mineiro"   (match data vs FIFA club)
    "Nacional (URU)"            (Libertadores, parenthetical country code)

To answer cross-file questions ("which players play for Flamengo?", head-to-head
records spanning multiple competitions) every team string must collapse to one
canonical key. This module provides:

    normalize_team(name) -> canonical lookup key (accent-free, suffix-free)
    team_display(name)   -> human friendly display name (keeps accents)

Dates also appear in several formats (ISO, ISO+time, Brazilian DD/MM/YYYY); they
are all parsed to ``datetime.date`` via ``parse_date``.

This module has no third-party dependencies so it can be imported anywhere.
================================================================================
"""

from __future__ import annotations

import datetime
import re
import unicodedata
from typing import Optional

# Brazilian state (UF) abbreviations and a few foreign country codes that appear
# as suffixes in the Libertadores file. Used to strip "-SP" / "(URU)" style tags.
_STATES = {
    "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms",
    "mg", "pa", "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc",
    "sp", "se", "to",
}
_COUNTRY_CODES = {
    "uru", "arg", "par", "bra", "bol", "chi", "col", "ecu", "per", "ven",
    "mex", "eq", "equ",
}

# Canonical key -> nicely accented display name for the best-known clubs.
_DISPLAY = {
    "flamengo": "Flamengo",
    "fluminense": "Fluminense",
    "corinthians": "Corinthians",
    "palmeiras": "Palmeiras",
    "santos": "Santos",
    "sao paulo": "São Paulo",
    "gremio": "Grêmio",
    "internacional": "Internacional",
    "atletico mineiro": "Atlético Mineiro",
    "athletico paranaense": "Athletico Paranaense",
    "atletico goianiense": "Atlético Goianiense",
    "cruzeiro": "Cruzeiro",
    "botafogo": "Botafogo",
    "vasco da gama": "Vasco da Gama",
    "bahia": "Bahia",
    "fortaleza": "Fortaleza",
    "ceara": "Ceará",
    "sport recife": "Sport Recife",
    "goias": "Goiás",
    "coritiba": "Coritiba",
    "chapecoense": "Chapecoense",
    "vitoria": "Vitória",
    "avai": "Avaí",
    "figueirense": "Figueirense",
    "ponte preta": "Ponte Preta",
    "america mineiro": "América-MG",
    "red bull bragantino": "Red Bull Bragantino",
    "cuiaba": "Cuiabá",
    "juventude": "Juventude",
    "parana": "Paraná",
    "csa": "CSA",
    "nautico": "Náutico",
    "guarani": "Guarani",
    "vasco": "Vasco da Gama",
}

# Variant (already accent-stripped, lower-cased, suffix-aware) -> canonical key.
# These resolve the ambiguous / multi-word names that simple suffix stripping
# cannot, e.g. the three different "Atlético" clubs.
_ALIASES = {
    "atletico mg": "atletico mineiro",
    "atletico mineiro": "atletico mineiro",
    "clube atletico mineiro": "atletico mineiro",
    "atletico pr": "athletico paranaense",
    "athletico pr": "athletico paranaense",
    "atletico paranaense": "athletico paranaense",
    "athletico paranaense": "athletico paranaense",
    "atletico go": "atletico goianiense",
    "atletico goianiense": "atletico goianiense",
    "america mg": "america mineiro",
    "america mineiro": "america mineiro",
    "america fc minas gerais": "america mineiro",
    "vasco": "vasco da gama",
    "vasco da gama": "vasco da gama",
    "sport": "sport recife",
    "sport recife": "sport recife",
    "sport club do recife": "sport recife",
    "bragantino": "red bull bragantino",
    "red bull bragantino": "red bull bragantino",
    "rb bragantino": "red bull bragantino",
    "sao paulo": "sao paulo",
    "sao paulo fc": "sao paulo",
    "gremio": "gremio",
    "ceara sporting club": "ceara",
}


def strip_accents(text: str) -> str:
    """Return *text* with diacritics removed (São -> Sao, Grêmio -> Gremio)."""
    if text is None:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text))
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _clean(name: str) -> str:
    """Lower-case, strip accents and punctuation, collapse whitespace."""
    s = strip_accents(name).lower()
    s = re.sub(r"\(.*?\)", " ", s)          # drop parenthetical country codes
    s = s.replace("-", " ")                  # "atletico-mg" -> "atletico mg"
    s = re.sub(r"[^a-z0-9 ]", " ", s)        # drop stray punctuation
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_team(name: Optional[str]) -> str:
    """Collapse any spelling of a club to a single canonical lookup key.

    The key is accent-free and suffix-free, so "Palmeiras-SP", "Palmeiras" and
    "São Paulo"/"Sao Paulo-SP" all map consistently and can be compared across
    datasets. Unknown clubs simply return their cleaned form.
    """
    if not name:
        return ""
    s = _clean(name)
    if not s:
        return ""
    if s in _ALIASES:
        return _ALIASES[s]

    toks = s.split()
    # Strip a trailing state / country code suffix when it is not the whole name.
    if len(toks) > 1 and (toks[-1] in _STATES or toks[-1] in _COUNTRY_CODES):
        stripped = " ".join(toks[:-1])
        if stripped in _ALIASES:
            return _ALIASES[stripped]
        s = stripped

    return _ALIASES.get(s, s)


def team_display(name: Optional[str]) -> str:
    """Return a human-friendly, accented display name for *name*."""
    key = normalize_team(name)
    if key in _DISPLAY:
        return _DISPLAY[key]
    # Fall back to a tidied version of the original (drop suffix, keep accents).
    if not name:
        return ""
    base = re.sub(r"\s*\(.*?\)\s*", "", str(name)).strip()
    base = re.sub(r"-[A-Z]{2}$", "", base).strip()      # "Palmeiras-SP" -> "Palmeiras"
    base = re.sub(r"\s+-\s+[A-Z]{2}$", "", base).strip()
    return base or str(name)


def teams_match(a: Optional[str], b: Optional[str]) -> bool:
    """True when two team strings refer to the same club after normalisation."""
    ka, kb = normalize_team(a), normalize_team(b)
    return bool(ka) and ka == kb


def team_matches_query(team_value: Optional[str], query: Optional[str]) -> bool:
    """True when *team_value* matches a user *query*.

    Accepts an exact canonical match or a substring match on the canonical key
    so that partial names ("Atletico" -> "Atlético Mineiro") still resolve in a
    friendly way for free-text questions.
    """
    if not query:
        return True
    kv = normalize_team(team_value)
    kq = normalize_team(query)
    if not kv or not kq:
        return False
    return kv == kq or kq in kv or kv in kq


def parse_date(value: Optional[str]) -> Optional[datetime.date]:
    """Parse the several date formats found in the datasets to a ``date``.

    Handles ISO ("2023-09-24"), ISO+time ("2012-05-19 18:30:00") and Brazilian
    ("29/03/2003"). Returns ``None`` when the value is empty or unparseable.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.upper() in {"NA", "NAN", "NONE", ""}:
        return None
    # Take the date portion if a time component is attached.
    s = s.split(" ")[0].split("T")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_int(value) -> Optional[int]:
    """Parse goals/ratings that may arrive as "", "3", "3.0" or floats."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.upper() in {"NA", "NAN", "NONE"}:
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None
