"""Team-name and text normalization.

The source CSVs name the same club in several ways:
    "Palmeiras-SP", "Palmeiras", "Sport Club Corinthians Paulista",
    "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "Barcelona-EQU".

`parse_team` reduces any of these to a base key ("palmeiras") plus an optional
state code ("SP"). Matching uses the base key; a state, when supplied, narrows
matches to records whose side-state agrees (or is unknown).
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

# Full official names -> the short form used in the data.
TEAM_ALIASES = {
    "sport club corinthians paulista": "corinthians",
    "sociedade esportiva palmeiras": "palmeiras",
    "clube de regatas do flamengo": "flamengo",
    "sao paulo futebol clube": "sao paulo",
    "gremio foot-ball porto alegrense": "gremio",
    "esporte clube bahia": "bahia",
    "club de regatas vasco da gama": "vasco",
    "vasco da gama": "vasco",
    "clube atletico mineiro": "atletico",
    "atletico mineiro": "atletico",
    "club athletico paranaense": "athletico",
    "athletico paranaense": "athletico",
    "atletico paranaense": "athletico",
    "fluminense football club": "fluminense",
    "botafogo de futebol e regatas": "botafogo",
    "esporte clube internacional": "internacional",
    "sport club do recife": "sport",
}

_SUFFIX_RE = re.compile(r"\s*(?:-|\s-\s|\s\()\s*([A-Za-z]{2,4})\)?\s*$")
_PAREN_RE = re.compile(r"\([^)]*\)")
_BARE_UF_RE = re.compile(r"\s+([A-Za-z]{2})$")
_CLUB_TOKEN_RE = re.compile(r"^(?:ec|fc|ac|sc|afc)\s+|\s+(?:fc|ec|afc)$")
_SPACE_RE = re.compile(r"\s+")
_UF_CODES = frozenset(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)
_NON_KEY_RE = re.compile(r"[^a-z0-9 \-]")


@dataclass(frozen=True)
class Team:
    base: str
    state: Optional[str] = None


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_text(text: str) -> str:
    """Lowercase, strip accents and punctuation, collapse whitespace."""
    lowered = strip_accents(str(text)).lower().strip()
    cleaned = _NON_KEY_RE.sub(" ", lowered)
    return _SPACE_RE.sub(" ", cleaned).strip()


def parse_team(raw: str, state: Optional[str] = None) -> Team:
    """Turn a raw club name from any source into a Team.

    A trailing state code in the name ("-SP", " - RJ", " (MG)") is used as the
    state unless an explicit `state` column value is provided.
    """
    text = strip_accents(str(raw)).strip()
    name_state = None
    match = _SUFFIX_RE.search(text)
    if match:
        name_state = match.group(1).upper()
        text = text[: match.start()]
    text = _PAREN_RE.sub(" ", text)  # "(URU)", "(antigo ...)"
    if name_state is None:
        bare = _BARE_UF_RE.search(text.strip())
        if bare and bare.group(1).upper() in _UF_CODES:
            name_state = bare.group(1).upper()
            text = text.strip()[: bare.start()]
    key = normalize_text(text)
    key = _CLUB_TOKEN_RE.sub("", key).strip()
    key = TEAM_ALIASES.get(key, key)
    resolved_state = (state or name_state or None)
    if resolved_state:
        resolved_state = resolved_state.strip().upper() or None
    if key == "atletico" and resolved_state == "PR":
        key = "athletico"  # Atletico-PR is "Athletico" in some files and "Atletico" in others
    return Team(base=key, state=resolved_state)


def parse_team_query(query: str) -> Team:
    """Parse a user-supplied team reference such as "Atletico-MG" or "Flamengo"."""
    return parse_team(query)


def team_matches(team: Team, query: Team) -> bool:
    """True when a record's team satisfies a query team."""
    if team.base != query.base:
        return False
    if query.state and team.state and team.state != query.state:
        return False
    return True


def contains_text(haystack: str, needle: str) -> bool:
    """Accent- and case-insensitive substring test."""
    return normalize_text(needle) in normalize_text(haystack)
