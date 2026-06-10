"""Team name normalization for Brazilian soccer data.

The datasets use wildly inconsistent naming conventions:

- With state suffix:    "Palmeiras-SP", "América - MG", "Botafogo RJ"
- Without suffix:       "Palmeiras", "Flamengo"
- Accented/unaccented:  "São Paulo" vs "Sao Paulo", "Grêmio" vs "Gremio"
- Renamed clubs:        "Athletico Paranaense" == "Atlético-PR" == "Atletico-PR"
- Country suffixes:     "Nacional (URU)", "Guaraní-PAR", "Barcelona-EQU"

This module parses any team string into a ``TeamKey`` of (base, region) where
``base`` is an accent-stripped, lowercased, alias-resolved club name and
``region`` is a Brazilian state code (e.g. "SP") or a country code for
non-Brazilian Libertadores clubs (e.g. "URU"), or ``None`` when unknown.

Two teams are considered the same club when their bases match and their
regions are compatible (equal, or one of them is unknown).  This lets
"Flamengo-RJ", "Flamengo" and a user query "flamengo" all line up, while
keeping "América-MG" and "América-RN" apart.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

# The 27 Brazilian state (UF) codes.
BRAZIL_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

# Country codes seen as suffixes in the Libertadores dataset.
COUNTRY_CODES = {
    "ARG", "BOL", "BRA", "CHI", "COL", "ECU", "EQU", "MEX", "PAR", "PER",
    "URU", "VEN",
}

_REGION_CODES = BRAZIL_STATES | COUNTRY_CODES

# Aliases applied to the cleaned base name.  Maps to (canonical base, region).
# A region of None means "leave whatever region was parsed from the suffix".
_ALIASES: dict[str, tuple[str, Optional[str]]] = {
    # Athletico Paranaense renamed itself from "Atlético Paranaense" in 2018.
    "athletico paranaense": ("atletico", "PR"),
    "atletico paranaense": ("atletico", "PR"),
    "athletico": ("atletico", "PR"),
    "atletico mineiro": ("atletico", "MG"),
    "atletico goianiense": ("atletico", "GO"),
    # América variants.
    "america fc natal": ("america", "RN"),
    "america fc minas gerais": ("america", "MG"),
    "america fc": ("america", "MG"),
    # Vasco da Gama.
    "vasco da gama": ("vasco", "RJ"),
    "vasco": ("vasco", "RJ"),
    # Bragantino was rebranded "Red Bull Bragantino" in 2019 (Bragança-SP).
    "red bull bragantino": ("bragantino", "SP"),
    "bragantino": ("bragantino", "SP"),
    # Famous clubs whose bare names are unambiguous but share a base with
    # small clubs from other states; pin the region.
    "botafogo": ("botafogo", "RJ"),
    "boavista": ("boavista", "RJ"),
    "boavista sc saquarema": ("boavista", "RJ"),
    "boavista sport club antigo esporte clube barreira": ("boavista", "RJ"),
    "guarani": ("guarani", "SP"),
    # Full official names used by some files.
    "sport club do recife": ("sport", "PE"),
    "sport recife": ("sport", "PE"),
    "sport club corinthians paulista": ("corinthians", "SP"),
    "ceara sporting club": ("ceara", "CE"),
    "csa": ("csa", "AL"),
    "cs alagoano": ("csa", "AL"),
    "abc": ("abc", "RN"),
    "asa": ("asa", "AL"),
    "crb": ("crb", "AL"),
    "gremio": ("gremio", "RS"),
    "flamengo": ("flamengo", "RJ"),
    "fluminense": ("fluminense", "RJ"),
    "palmeiras": ("palmeiras", "SP"),
    "corinthians": ("corinthians", "SP"),
    "santos": ("santos", "SP"),
    "sao paulo": ("sao paulo", "SP"),
    "cruzeiro": ("cruzeiro", "MG"),
    "internacional": ("internacional", "RS"),
    "bahia": ("bahia", "BA"),
    "vitoria": ("vitoria", "BA"),
    "chapecoense": ("chapecoense", "SC"),
    "avai": ("avai", "SC"),
    "coritiba": ("coritiba", "PR"),
    "parana": ("parana", "PR"),
    "goias": ("goias", "GO"),
    "fortaleza": ("fortaleza", "CE"),
    "ceara": ("ceara", "CE"),
    "nautico": ("nautico", "PE"),
    "sport": ("sport", "PE"),
    "ponte preta": ("ponte preta", "SP"),
    "portuguesa": ("portuguesa", "SP"),
    "juventude": ("juventude", "RS"),
    "cuiaba": ("cuiaba", "MT"),
    "figueirense": ("figueirense", "SC"),
    "criciuma": ("criciuma", "SC"),
    "joinville": ("joinville", "SC"),
    "santa cruz": ("santa cruz", "PE"),
}


@dataclass(frozen=True)
class TeamKey:
    """Normalized identity of a club: cleaned base name plus region code."""

    base: str
    region: Optional[str] = None

    def matches(self, other: "TeamKey") -> bool:
        """True when both keys plausibly refer to the same club."""
        if self.base != other.base:
            return False
        if self.region is None or other.region is None:
            return True
        return self.region == other.region

    def __str__(self) -> str:  # stable string form, useful for grouping
        return f"{self.base}/{self.region}" if self.region else self.base


def strip_accents(text: str) -> str:
    """Remove diacritics: 'Grêmio' -> 'Gremio', 'São Paulo' -> 'Sao Paulo'."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _clean(text: str) -> str:
    """Lowercase, deaccent and collapse punctuation/whitespace."""
    text = strip_accents(text).lower()
    text = text.replace(".", "").replace("'", "")
    text = re.sub(r"[\s\-_/(),]+", " ", text)
    return text.strip()


# Club-type words that some datasets bolt onto names ("EC Juventude",
# "Fortaleza FC", "Arapongas Esporte Clube").  Stripped so the base matches
# the plain spelling used elsewhere.
_AFFIX_PHRASES = ("esporte clube", "futebol clube")
_AFFIX_TOKENS = {"ec", "fc", "sc", "ac", "ad", "aa"}


def _strip_affixes(base: str) -> str:
    """Drop leading/trailing club-type affixes from a cleaned base name."""
    changed = True
    while changed:
        changed = False
        for phrase in _AFFIX_PHRASES:
            if base.startswith(phrase + " "):
                base, changed = base[len(phrase) + 1:], True
            if base.endswith(" " + phrase):
                base, changed = base[:-len(phrase) - 1], True
        words = base.split()
        if len(words) > 1 and words[0] in _AFFIX_TOKENS:
            base, changed = " ".join(words[1:]), True
        words = base.split()
        if len(words) > 1 and words[-1] in _AFFIX_TOKENS:
            base, changed = " ".join(words[:-1]), True
    return base


def _split_region_suffix(name: str) -> tuple[str, Optional[str]]:
    """Split a trailing state/country marker off a raw team name.

    Handles "Palmeiras-SP", "América - MG", "Botafogo RJ", "Nacional (URU)"
    and "Barcelona-EQU".  Acronym-only names such as "CSA" are left intact.
    """
    name = name.strip()
    patterns = (
        r"^(?P<base>.+?)\s*\(\s*(?P<code>[A-Za-z]{2,3})\s*\)$",   # "(URU)"
        r"^(?P<base>.+?)\s*-\s*(?P<code>[A-Za-z]{2,3})$",          # "-SP"
        r"^(?P<base>.+?)\s+(?P<code>[A-Z]{2,3})$",                 # " RJ"
    )
    for pattern in patterns:
        match = re.match(pattern, name)
        if not match:
            continue
        code = match.group("code").upper()
        base = match.group("base").strip()
        if code in _REGION_CODES and base:
            return base, code
    return name, None


def parse_team(name: str) -> TeamKey:
    """Parse any raw team string (dataset value or user query) to a TeamKey."""
    base_raw, region = _split_region_suffix(name or "")
    base = _clean(base_raw)
    alias = _ALIASES.get(base)
    if alias is None:
        stripped = _strip_affixes(base)
        if stripped:
            base = stripped
            alias = _ALIASES.get(base)
    if alias:
        base, alias_region = alias
        region = region or alias_region
    return TeamKey(base=base, region=region)


def team_matches(name_or_key, query_key: TeamKey) -> bool:
    """True when a dataset team (raw string or TeamKey) matches a query key."""
    key = name_or_key if isinstance(name_or_key, TeamKey) else parse_team(name_or_key)
    return key.matches(query_key)
