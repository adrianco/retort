"""Normalisation helpers for team names, competition names and dates.

The source datasets disagree on how they write the same club:
  "Palmeiras-SP", "Palmeiras", "América - MG", "Nacional (URU)",
  "Sport Club Corinthians Paulista", "Sao Paulo" vs "São Paulo".
Everything here maps those variants onto one comparable form.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import NamedTuple, Optional

# Trailing upper-case state/country code, e.g. "-SP", " - RJ", " RJ", "-EQU".
_SUFFIX_RE = re.compile(r"\s*(?:-\s*)?([A-Z]{2,3})\s*$")
# Parenthetical notes such as "(URU)" or "(antigo Esporte Clube Barreira)".
_PAREN_RE = re.compile(r"\([^)]*\)")
_SPACE_RE = re.compile(r"\s+")

# Full club names that appear in the data, mapped to the short base name.
TEAM_ALIASES = {
    "sport club corinthians paulista": "corinthians",
    "sociedade esportiva palmeiras": "palmeiras",
    "clube de regatas do flamengo": "flamengo",
    "sao paulo futebol clube": "sao paulo",
    "gremio foot-ball porto alegrense": "gremio",
    "sport club internacional": "internacional",
    "clube atletico mineiro": "atletico",
    "atletico mineiro": "atletico",
    "atletico paranaense": "atletico",
    "vasco da gama": "vasco",
    "red bull bragantino": "bragantino",
    "rb bragantino": "bragantino",
}
# Clubs whose name alone identifies the state, used when a source gives none.
CLUB_STATES = {
    "clube atletico mineiro": "MG",
    "atletico mineiro": "MG",
    "atletico paranaense": "PR",
}
# Club-type words that vary between sources ("EC Bahia" vs "Bahia").
_CLUB_WORDS = {"ec", "fc", "sc", "ac", "club", "clube", "sport", "esporte", "esportivo"}
# Spelling variants of the same word.
_WORD_FIXES = {"athletico": "atletico"}
# Ignored when deciding whether two club names overlap.
STOP_WORDS = {"da", "de", "do", "dos", "das", "e"}

# Canonical competition key -> display name.
COMPETITION_NAMES = {
    "brasileirao_a": "Brasileirão Série A",
    "brasileirao_b": "Brasileirão Série B",
    "brasileirao_c": "Brasileirão Série C",
    "copa_do_brasil": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
}
# Lower-cased search phrases -> canonical competition key.
_COMPETITION_QUERIES = {
    "brasileirao a": "brasileirao_a",
    "brasileirao serie a": "brasileirao_a",
    "brasileirão a": "brasileirao_a",
    "série a": "brasileirao_a",
    "serie a": "brasileirao_a",
    "brasileirao": "brasileirao_a",
    "brasileirão": "brasileirao_a",
    "brasileirao b": "brasileirao_b",
    "brasileirao serie b": "brasileirao_b",
    "serie b": "brasileirao_b",
    "brasileirao c": "brasileirao_c",
    "brasileirao serie c": "brasileirao_c",
    "serie c": "brasileirao_c",
    "copa do brasil": "copa_do_brasil",
    "cup": "copa_do_brasil",
    "libertadores": "libertadores",
    "copa libertadores": "libertadores",
}

_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y")


def strip_accents(text: str) -> str:
    """Remove diacritics: 'São Paulo' -> 'Sao Paulo'."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def simplify(text: str) -> str:
    """Lower-case, accent-free and whitespace-collapsed form of ``text``."""
    return _SPACE_RE.sub(" ", strip_accents(text).lower()).strip()


def _canonical_base(base: str) -> tuple[str, Optional[str]]:
    """Apply spelling fixes, aliases and club-word stripping to a simplified name.

    Returns the comparable base name and the state implied by the name, if any.
    """
    words = [_WORD_FIXES.get(word, word) for word in base.split()]
    fixed = " ".join(words)
    implied_state = CLUB_STATES.get(fixed)
    fixed = TEAM_ALIASES.get(fixed, fixed)
    trimmed = [w for w in fixed.split() if w not in _CLUB_WORDS]
    return " ".join(trimmed or fixed.split()), implied_state


def name_tokens(base: str) -> set[str]:
    """Significant words of a normalised team base name, used to spot the same club."""
    return {word for word in base.split() if word not in STOP_WORDS}


class TeamRef(NamedTuple):
    """A club as it appears in one match row.

    ``base`` is the comparable name ("palmeiras"); ``state`` is the UF/country
    code when the source provides one ("SP"), otherwise None.
    """

    base: str
    state: Optional[str]
    display: str

    @property
    def key(self) -> str:
        return f"{self.base}-{self.state.lower()}" if self.state else self.base


def parse_team(raw: str, state: Optional[str] = None) -> TeamRef:
    """Split a raw team string into a :class:`TeamRef`.

    An explicit ``state`` argument (from a dedicated state column) takes
    precedence; the suffix in the name is only used when no argument is given.
    """
    display = _SPACE_RE.sub(" ", raw).strip()
    text = _PAREN_RE.sub(" ", display)
    suffix = _SUFFIX_RE.search(text)
    if suffix and suffix.start() > 0:  # a bare "CSA" is a club name, not a state
        if not state:
            state = suffix.group(1).upper()
        text = text[: suffix.start()]
    base, implied_state = _canonical_base(simplify(text))
    if not state and implied_state:
        state = implied_state
    state = state.strip().upper() if state and state.strip() else None
    return TeamRef(base=base, state=state, display=display)


def team_matches(team: TeamRef, query: str, state: Optional[str] = None) -> bool:
    """Return True when ``team`` is the club the user asked about.

    ``query`` may be a short name ("Flamengo"), a name with a state suffix
    ("Atletico-MG") or a full name ("Sport Club Corinthians Paulista").
    Matching is on the normalised base name; a state on either side narrows
    the match when both sides have one.
    """
    wanted = parse_team(query, state)
    if wanted.base != team.base:
        return False
    if wanted.state and team.state:
        return wanted.state == team.state
    return True


def resolve_competition(query: str) -> Optional[str]:
    """Map free text such as 'copa do brasil' to a canonical competition key."""
    key = simplify(query)
    if key in _COMPETITION_QUERIES:
        return _COMPETITION_QUERIES[key]
    for phrase, canonical in _COMPETITION_QUERIES.items():
        if phrase in key:
            return canonical
    return None


def parse_date(text: str) -> date:
    """Parse ISO ('2023-09-24', '2012-05-19 18:30:00') or Brazilian ('29/03/2003') dates."""
    value = text.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date format: {text!r}")
