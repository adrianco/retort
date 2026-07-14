"""Team-name normalization.

The provided datasets use inconsistent team naming:

    "Palmeiras-SP"                  (state suffix)
    "Palmeiras"                     (bare)
    "América - MG"                  (whitespace around the dash)
    "Sport Club Corinthians Paulista" (full corporate name)
    "Sao Paulo"                     (no accents in one dataset, "São Paulo" in another)

State suffixes matter for disambiguation: there are several "Atlético"
clubs (MG/PR/GO/ES) and they are NOT the same team.  We therefore:

    1. Strip accents and lowercase.
    2. Normalize whitespace and dashes.
    3. Look up the full string in an alias table FIRST (state-aware).
    4. Otherwise strip a known state suffix and look up the bare name.
    5. As a last resort drop generic noise words ("FC", "Esporte Clube",
       ...) and return the residue.

`teams_match` returns True when two raw names refer to the same club.
"""

from __future__ import annotations

import re
import unicodedata

_BR_STATES = (
    "sp rj mg rs pr sc ba pe ce go df am pa ma al pb rn se pi mt ms es ro rr ac to df"
).split()
_INTL_TAGS = "equ arg uru chi bol per col ven par bra mex usa par ecu".split()
_ALL_STATE_TAGS = set(_BR_STATES + _INTL_TAGS)

# State-aware alias map.  Keys are normalized (accent-free, lowercase) raw
# names; values are the canonical short form used everywhere downstream.
_ALIASES = {
    # Big six and other recurring Serie A clubs.
    "flamengo": "flamengo",
    "flamengo rj": "flamengo",
    "clube de regatas do flamengo": "flamengo",
    "cr flamengo": "flamengo",
    "fluminense": "fluminense",
    "fluminense rj": "fluminense",
    "fluminense football club": "fluminense",
    "palmeiras": "palmeiras",
    "palmeiras sp": "palmeiras",
    "se palmeiras": "palmeiras",
    "sociedade esportiva palmeiras": "palmeiras",
    "corinthians": "corinthians",
    "corinthians sp": "corinthians",
    "sc corinthians paulista": "corinthians",
    "sport club corinthians paulista": "corinthians",
    "sao paulo": "sao paulo",
    "sao paulo sp": "sao paulo",
    "sao paulo fc": "sao paulo",
    "sao paulo futebol clube": "sao paulo",
    "santos": "santos",
    "santos sp": "santos",
    "santos fc": "santos",
    "santos futebol clube": "santos",
    "gremio": "gremio",
    "gremio rs": "gremio",
    "gremio foot-ball porto alegrense": "gremio",
    "gremio foot ball porto alegrense": "gremio",
    "internacional": "internacional",
    "internacional rs": "internacional",
    "sc internacional": "internacional",
    "sport club internacional": "internacional",
    "vasco da gama": "vasco da gama",
    "vasco": "vasco da gama",
    "vasco rj": "vasco da gama",
    "club de regatas vasco da gama": "vasco da gama",
    "cr vasco da gama": "vasco da gama",
    # Atléticos -- state suffix is *required* to disambiguate.
    "atletico mg": "atletico mineiro",
    "atletico mineiro": "atletico mineiro",
    "clube atletico mineiro": "atletico mineiro",
    "cam": "atletico mineiro",
    "atletico pr": "athletico paranaense",
    "athletico pr": "athletico paranaense",
    "athletico paranaense": "athletico paranaense",
    "atletico paranaense": "athletico paranaense",
    "club athletico paranaense": "athletico paranaense",
    "atletico go": "atletico goianiense",
    "atletico goianiense": "atletico goianiense",
    "atletico clube goianiense": "atletico goianiense",
    # Other recurring clubs.
    "botafogo": "botafogo",
    "botafogo rj": "botafogo",
    "botafogo de futebol e regatas": "botafogo",
    "botafogo pb": "botafogo pb",   # distinct Paraíba club
    "botafogo sp": "botafogo sp",   # distinct São Paulo club
    "cruzeiro": "cruzeiro",
    "cruzeiro mg": "cruzeiro",
    "cruzeiro esporte clube": "cruzeiro",
    "bahia": "bahia",
    "bahia ba": "bahia",
    "ec bahia": "bahia",
    "esporte clube bahia": "bahia",
    "ceara": "ceara",
    "ceara ce": "ceara",
    "ceara sporting club": "ceara",
    "fortaleza": "fortaleza",
    "fortaleza ce": "fortaleza",
    "fortaleza esporte clube": "fortaleza",
    "sport recife": "sport recife",
    "sport pe": "sport recife",
    "sport": "sport recife",
    "sport club do recife": "sport recife",
    "coritiba": "coritiba",
    "coritiba pr": "coritiba",
    "coritiba foot ball club": "coritiba",
    "chapecoense": "chapecoense",
    "chapecoense sc": "chapecoense",
    "associacao chapecoense de futebol": "chapecoense",
    "goias": "goias",
    "goias go": "goias",
    "goias esporte clube": "goias",
    "vitoria": "vitoria",
    "vitoria ba": "vitoria",
    "esporte clube vitoria": "vitoria",
    "ponte preta": "ponte preta",
    "ponte preta sp": "ponte preta",
    "aa ponte preta": "ponte preta",
    "associacao atletica ponte preta": "ponte preta",
    "figueirense": "figueirense",
    "figueirense sc": "figueirense",
    "figueirense fc": "figueirense",
    "figueirense futebol clube": "figueirense",
    "avai": "avai",
    "avai sc": "avai",
    "avai futebol clube": "avai",
    "america mg": "america mineiro",
    "america mineiro": "america mineiro",
    "america fc": "america mineiro",
    "red bull bragantino": "red bull bragantino",
    "rb bragantino": "red bull bragantino",
    "bragantino": "red bull bragantino",
    "bragantino sp": "red bull bragantino",
    "cuiaba": "cuiaba",
    "cuiaba mt": "cuiaba",
    "cuiaba esporte clube": "cuiaba",
    "juventude": "juventude",
    "juventude rs": "juventude",
    "esporte clube juventude": "juventude",
    "nautico": "nautico",
    "nautico pe": "nautico",
    "nautico capibaribe": "nautico",
    "portuguesa": "portuguesa",
    "portuguesa sp": "portuguesa",
    "associacao portuguesa de desportos": "portuguesa",
    "parana": "parana",
    "parana pr": "parana",
    "parana clube": "parana",
    "csa": "csa",
    "csa al": "csa",
    "centro sportivo alagoano": "csa",
    "guarani": "guarani",
    "guarani sp": "guarani",
}

# Final-stage filler tokens removed only if no alias matched.
_GENERIC_TOKENS = {
    "fc",
    "sc",
    "ec",
    "ac",
    "cf",
    "cr",
    "se",
    "clube",
    "club",
    "futebol",
    "football",
    "esporte",
    "sport",
    "sporting",
    "esportes",
    "associacao",
    "association",
    "sociedade",
    "regatas",
    "de",
    "do",
    "da",
}


def _strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn"
    )


def _preclean(name: str) -> str:
    s = _strip_accents(name)
    # Drop parenthetical country tags such as "Nacional (URU)".
    s = re.sub(r"\([^)]*\)", " ", s)
    s = s.lower()
    s = s.replace("_", " ")
    s = re.sub(r"[\-/]+", " ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _strip_state_suffix(s: str) -> str:
    parts = s.split()
    if len(parts) > 1 and parts[-1] in _ALL_STATE_TAGS:
        return " ".join(parts[:-1])
    return s


def _strip_generic_tokens(s: str) -> str:
    parts = [t for t in s.split() if t not in _GENERIC_TOKENS]
    return " ".join(parts) if parts else s


def normalize_team_name(name: str | None) -> str:
    """Reduce a team name to a canonical lowercase form for matching."""
    if not name:
        return ""
    cleaned = _preclean(str(name))
    if not cleaned:
        return ""

    # 1. Full state-aware alias lookup.
    if cleaned in _ALIASES:
        return _ALIASES[cleaned]

    # 2. Strip state suffix and look up the bare name.
    bare = _strip_state_suffix(cleaned)
    if bare in _ALIASES:
        return _ALIASES[bare]

    # 3. Try stripping generic tokens (FC, Esporte Clube, ...) then alias.
    stripped = _strip_generic_tokens(bare)
    if stripped in _ALIASES:
        return _ALIASES[stripped]

    # 4. Fall back to the bare name (still useful for unknown clubs).
    return bare


def teams_match(a: str | None, b: str | None) -> bool:
    """True when two raw team names refer to the same club."""
    na, nb = normalize_team_name(a), normalize_team_name(b)
    if not na or not nb:
        return False
    return na == nb
