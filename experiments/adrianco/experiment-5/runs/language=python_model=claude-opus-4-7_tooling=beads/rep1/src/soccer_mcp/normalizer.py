"""Team and string normalization helpers.

The provided Kaggle datasets refer to the same club under several different
spellings: ``Palmeiras``, ``Palmeiras-SP``, ``SE Palmeiras``,
``Sport Club Corinthians Paulista``, etc. This module collapses those
variations onto a canonical short name so query results can be merged across
files.

Normalisation rules applied here:

* Strip trailing state suffixes such as ``"-SP"`` or ``" - RJ"``.
* Strip trailing country suffixes such as ``" (URU)"``.
* Strip parenthetical and dash annotations (e.g. ``"(antigo ...)"``).
* Case fold, strip diacritics, and collapse whitespace.
* Apply a hand curated alias map for the most common long forms
  (``"Sport Club Corinthians Paulista" -> "corinthians"``).

The canonical form is lowercase and ASCII so it works as a dictionary key.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable

# Brazilian state two-letter codes used as suffixes in the datasets.
_BRAZIL_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}

# Three-letter country codes that occasionally appear inside parentheses, e.g.
# "Nacional (URU)" or "Boca Juniors (ARG)".  Kept here so we can strip them.
_COUNTRY_CODES = {
    "ARG", "URU", "PAR", "CHI", "BOL", "EQU", "PER", "VEN", "COL",
    "MEX", "USA", "CRC", "HON", "PAN", "BRA",
}

# Long form -> canonical short form aliases. Keys must be passed through
# ``_basic_clean`` semantics first (lowercase, stripped of accents).  The
# resolver below takes care of that.
_ALIAS_MAP = {
    "sport club corinthians paulista": "corinthians",
    "sport club do recife": "sport",
    "sport recife": "sport",
    "sc internacional": "internacional",
    "sport club internacional": "internacional",
    "se palmeiras": "palmeiras",
    "sociedade esportiva palmeiras": "palmeiras",
    "clube de regatas do flamengo": "flamengo",
    "fluminense football club": "fluminense",
    "fluminense fc": "fluminense",
    "santos futebol clube": "santos",
    "santos fc": "santos",
    "sao paulo futebol clube": "sao paulo",
    "sao paulo fc": "sao paulo",
    "athletico paranaense": "athletico-pr",
    "atletico paranaense": "athletico-pr",
    "club athletico paranaense": "athletico-pr",
    "clube atletico mineiro": "atletico-mg",
    "atletico mineiro": "atletico-mg",
    "gremio foot-ball porto alegrense": "gremio",
    "gremio porto alegre": "gremio",
    "cruzeiro esporte clube": "cruzeiro",
    "botafogo de futebol e regatas": "botafogo",
    "botafogo fr": "botafogo",
    "boavista sport club": "boavista",
    "associacao chapecoense de futebol": "chapecoense",
    "ec bahia": "bahia",
    "esporte clube bahia": "bahia",
    "fortaleza esporte clube": "fortaleza",
    "fortaleza ec": "fortaleza",
}

_STATE_SUFFIX_RE = re.compile(
    r"\s*[-–—]\s*(?P<state>" + "|".join(sorted(_BRAZIL_STATES)) + r")\b\s*$"
)
_PAREN_RE = re.compile(r"\s*\([^)]*\)\s*")
_TRAILING_DASH_RE = re.compile(r"\s*[-–—]\s*$")
_MULTISPACE_RE = re.compile(r"\s+")


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _basic_clean(text: str) -> str:
    text = _strip_accents(text).lower().strip()
    text = _MULTISPACE_RE.sub(" ", text)
    return text


def _split_state(text: str) -> tuple[str, str | None]:
    """Return ``(name_without_state_suffix, state_code_or_None)``."""
    match = _STATE_SUFFIX_RE.search(text)
    if not match:
        return text, None
    return text[: match.start()].rstrip(), match.group("state")


def normalize_team(name: str | None) -> str:
    """Return the canonical short form of ``name``.

    The canonical form keeps the Brazilian state suffix when present so
    distinct clubs like ``"Atletico-MG"`` (Mineiro) and ``"Atletico-PR"``
    (Paranaense) remain separated. Cross-file matching of the short and long
    forms is handled in :func:`matches_team` via substring matching.

    Empty / falsy input returns the empty string so callers can safely use the
    result as a dict key without branching.
    """
    if not name:
        return ""
    cleaned = name.strip()

    def _paren_replace(match: "re.Match[str]") -> str:
        return " "

    cleaned = _PAREN_RE.sub(_paren_replace, cleaned)
    cleaned, state = _split_state(cleaned)
    cleaned = _TRAILING_DASH_RE.sub("", cleaned)
    base = _basic_clean(cleaned)

    base_alias = _ALIAS_MAP.get(base)
    if base_alias is None:
        base_dashed = base.replace(" pr", "-pr").replace(" mg", "-mg").replace(" rj", "-rj")
        base_alias = _ALIAS_MAP.get(base_dashed)
    if base_alias is not None:
        base = base_alias

    if state and not base.endswith(f"-{state.lower()}"):
        return f"{base}-{state.lower()}"
    return base


def matches_team(candidate: str | None, query: str | None) -> bool:
    """Return True if ``candidate`` refers to the same club as ``query``.

    Cross-file naming variations (``"Palmeiras"`` vs ``"Palmeiras-SP"``) are
    bridged here: equality on the state-stripped base is enough, but when the
    *query* explicitly includes a state suffix it must match the candidate's
    state suffix (so ``"Atletico-MG"`` does not match ``"Atletico-PR"``).
    """
    if not candidate or not query:
        return False
    c = normalize_team(candidate)
    q = normalize_team(query)
    if not c or not q:
        return False

    c_base, c_state = _split_canonical(c)
    q_base, q_state = _split_canonical(q)
    if c_base != q_base:
        # Allow long-form substring matching ("sao paulo futebol clube" -> "sao paulo")
        # but require at least 4 characters so a stub like "fla" does not match
        # every Flamengo / Fluminense row.
        if len(q_base) < 4 or len(c_base) < 4:
            return False
        if not (q_base in c_base or c_base in q_base):
            return False
    if q_state and c_state and q_state != c_state:
        return False
    return True


def _split_canonical(value: str) -> tuple[str, str | None]:
    """Split a normalised value into ``(base, state)``."""
    if not value or "-" not in value:
        return value, None
    base, _, tail = value.rpartition("-")
    if len(tail) == 2 and tail.upper() in _BRAZIL_STATES:
        return base, tail.lower()
    return value, None


def unique_teams(names: Iterable[str | None]) -> list[str]:
    """Return the sorted list of unique canonical team names in ``names``."""
    seen: set[str] = set()
    for n in names:
        norm = normalize_team(n)
        if norm:
            seen.add(norm)
    return sorted(seen)
