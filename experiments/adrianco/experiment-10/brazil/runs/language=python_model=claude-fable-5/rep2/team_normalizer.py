"""Team name normalization for Brazilian soccer datasets.

The six source CSVs spell club names differently:
  - with a state suffix:   "Palmeiras-SP", "America-MG", "ASA AL"
  - with a spaced suffix:  "América - MG"
  - with a country suffix: "Barcelona-EQU", "Nacional (URU)"
  - without accents:       "Sao Paulo", "Gremio"
  - full official names:   "Sport Club do Recife", "Ceará Sporting Club"

This module reduces any spelling to a (base, region) pair, where ``base`` is
an accent-free lowercase club identifier and ``region`` is an optional state
or country code.  Two names refer to the same club when their bases match and
their regions are compatible (equal, or one side unspecified).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional, Tuple

# Brazilian state abbreviations (used to recognise trailing region suffixes).
BR_STATES = {
    "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms",
    "mg", "pa", "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc",
    "sp", "se", "to",
}

# Country codes that appear in the Libertadores dataset, e.g. "Barcelona-EQU".
COUNTRY_CODES = {
    "arg", "bol", "chi", "col", "equ", "mex", "par", "per", "uru", "ven",
    "bra", "ecu",
}

# Full-name aliases, keyed on the accent-free lowercase name (before suffix
# extraction).  Values are canonical "base" or "base-region" strings.
_ALIASES = {
    "sport club corinthians paulista": "corinthians",
    "sao paulo fc": "sao paulo",
    "sao paulo futebol clube": "sao paulo",
    "santos fc": "santos",
    "ceara sporting club": "ceara",
    "sport club do recife": "sport",
    "sport recife": "sport",
    "clube de regatas do flamengo": "flamengo",
    "cr flamengo": "flamengo",
    "fluminense fc": "fluminense",
    "vasco da gama": "vasco",
    "cr vasco da gama": "vasco",
    "club de regatas vasco da gama": "vasco",
    "se palmeiras": "palmeiras",
    "sociedade esportiva palmeiras": "palmeiras",
    "gremio fbpa": "gremio",
    "gremio foot-ball porto alegrense": "gremio",
    "sc internacional": "internacional",
    "atletico mineiro": "atletico-mg",
    "clube atletico mineiro": "atletico-mg",
    "atletico paranaense": "athletico-pr",
    "athletico paranaense": "athletico-pr",
    "atletico-pr": "athletico-pr",
    "atletico pr": "athletico-pr",
    "club athletico paranaense": "athletico-pr",
    "atletico goianiense": "atletico-go",
    "america mineiro": "america-mg",
    "america fc (minas gerais)": "america-mg",
    "america fc natal": "america-rn",
    "america de natal": "america-rn",
    "red bull bragantino": "bragantino",
    "rb bragantino": "bragantino",
    "ec bahia": "bahia",
    "esporte clube bahia": "bahia",
    "ec vitoria": "vitoria",
    "esporte clube vitoria": "vitoria",
    "botafogo fr": "botafogo-rj",
    "botafogo de futebol e regatas": "botafogo-rj",
    "cuiaba esporte clube": "cuiaba",
    "fortaleza esporte clube": "fortaleza",
    "fortaleza ec": "fortaleza",
    "goias esporte clube": "goias",
    "coritiba fc": "coritiba",
    "coritiba foot ball club": "coritiba",
    "csa al": "csa",
    "asa al": "asa",
}

_PAREN_RE = re.compile(r"\(([^)]*)\)")
_WS_RE = re.compile(r"\s+")

# Generic organisational tokens that vary between sources:
# "EC Juventude" vs "Juventude-RS", "Fortaleza FC" vs "Fortaleza-CE".
_LEADING_ORG = {"ec", "sc", "se", "ad", "ae", "aa", "cr"}
_TRAILING_ORG = {"fc", "ec", "sc"}


def _strip_org_tokens(text: str) -> str:
    tokens = text.split()
    if len(tokens) > 1 and tokens[0] in _LEADING_ORG:
        tokens = tokens[1:]
    if len(tokens) > 1 and tokens[-1] in _TRAILING_ORG:
        tokens = tokens[:-1]
    return " ".join(tokens)


def strip_accents(text: str) -> str:
    """Return ``text`` with combining accents removed (São Paulo -> Sao Paulo)."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _clean(text: str) -> str:
    text = strip_accents(text).lower()
    text = text.replace("´", "").replace("`", "").replace("'", "")
    return _WS_RE.sub(" ", text).strip()


def parse_team(name: str) -> Tuple[str, Optional[str]]:
    """Split a raw team name into ``(base, region)``.

    ``base`` is the accent-free lowercase club name; ``region`` is a state or
    country code when one can be recognised, else ``None``.
    """
    if not name:
        return "", None
    text = _clean(name)
    region: Optional[str] = None

    # Parenthetical content: either a region code "Nacional (URU)" or noise
    # such as "(antigo Esporte Clube Barreira)".
    def _paren(match: re.Match) -> str:
        nonlocal region
        inner = match.group(1).strip()
        if inner in COUNTRY_CODES or inner in BR_STATES:
            region = inner
        return " "

    text = _PAREN_RE.sub(_paren, text)
    text = _WS_RE.sub(" ", text).strip(" -")

    # Full-name aliases first (they may embed a region).
    alias = _ALIASES.get(text)
    if alias:
        base, _, alias_region = alias.partition("-")
        if alias_region:
            return alias, alias_region
        return alias, region

    # Trailing region suffix: "-sp", " - sp", " sp", "-equ".
    m = re.search(r"^(.*?)(?:\s*-\s*|\s+)([a-z]{2,3})$", text)
    if m and (m.group(2) in BR_STATES or m.group(2) in COUNTRY_CODES):
        text, region = m.group(1).strip(), m.group(2)

    text = _strip_org_tokens(text)

    alias = _ALIASES.get(text) or _ALIASES.get(
        f"{text}-{region}" if region else text
    )
    if alias:
        base, _, alias_region = alias.partition("-")
        if alias_region:
            return alias, alias_region
        return alias, region

    # Clubs whose identity needs the state to stay unambiguous keep it in the
    # base (e.g. America-MG vs America-RN, Botafogo-RJ vs Botafogo-SP).
    if region in BR_STATES and text in {"america", "botafogo", "atletico", "athletico"}:
        return f"{text}-{region}", region

    return text, region


def team_key(name: str) -> str:
    """Canonical string key for a team name (base plus region when known)."""
    base, region = parse_team(name)
    if region and "-" not in base:
        return f"{base}-{region}"
    return base


def team_matches(query: str, name: str) -> bool:
    """Whether a user-supplied ``query`` refers to the team called ``name``."""
    qbase, qregion = parse_team(query)
    nbase, nregion = parse_team(name)
    if not qbase or not nbase:
        return False
    if qbase != nbase:
        # Allow an unqualified query to match a state-qualified base:
        # "botafogo" -> "botafogo-rj"; and vice versa for FIFA full names.
        if not (nbase.startswith(qbase + "-") or qbase.startswith(nbase + "-")):
            return False
    if qregion and nregion and qregion != nregion:
        return False
    return True


def display_name(name: str) -> str:
    """Human-friendly form of a raw dataset team name (suffix removed)."""
    base, region = parse_team(name)
    pretty = base.title().replace("Fc", "FC").replace("Ec", "EC")
    if "-" in base:
        stem, _, reg = base.rpartition("-")
        pretty = f"{stem.title()}-{reg.upper()}"
    return pretty
