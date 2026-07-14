"""Normalization helpers for messy Brazilian soccer data.

The provided CSV files disagree with each other on how they spell team
names (accents, casing, punctuation, trailing state suffixes such as
"-SP") and how they format dates (ISO, DD/MM/YYYY, with/without time).
Every other module in this package routes team names and dates through
here so matching stays consistent across files.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from datetime import datetime
from typing import Iterable

import pandas as pd

# Brazilian state (UF) abbreviations used as suffixes on team names,
# e.g. "Palmeiras-SP", "Flamengo-RJ", "América - MG".
BRAZILIAN_STATE_CODES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

# Hyphenated ("Flamengo-RJ", "Boavista ... - RJ") and bare space-separated
# ("Botafogo RJ", used by BR-Football-Dataset.csv) state suffix forms.
_STATE_SUFFIX_HYPHEN_RE = re.compile(r"^(.*\S)\s*-\s*([A-Za-z]{2})$")
_STATE_SUFFIX_SPACE_RE = re.compile(r"^(.*\S)\s+([A-Za-z]{2})$")

# Full/alternate club names that need to collapse onto the same key as the
# short names used elsewhere in the datasets. Keys are the *fully folded*
# raw name (accents/case/punctuation removed, but state suffix NOT yet
# split off - see _fold/normalize_key). Values are either a short
# "<club> <state>" form (fed back through state-splitting/disambiguation,
# e.g. so "Atletico Mineiro" lines up with "Atletico-MG") or, for
# unambiguous names, the final key directly.
TEAM_KEY_ALIASES = {
    # Atlético-MG: full name, and the "Atlético Mineiro - MG" form seen
    # in the Cup dataset.
    "atletico mineiro": "atletico mg",
    "clube atletico mineiro": "atletico mg",
    "atletico mineiro mg": "atletico mg",
    # Athletico Paranaense (rebranded with the historic "th" spelling in
    # 2019) and its many older/alternate spellings all mean the same club.
    "athletico": "atletico pr",
    "athletico pr": "atletico pr",
    "athletico paranaense": "atletico pr",
    "athletico paranaense pr": "atletico pr",
    "club athletico paranaense": "atletico pr",
    "atletico paranaense": "atletico pr",
    "atletico paranaense pr": "atletico pr",
    "atletico goianiense": "atletico go",
    "clube atletico goianiense": "atletico go",
    "america fc minas gerais": "america mg",
    "america futebol clube mg": "america mg",
    "america mineiro": "america mg",
    "america futebol clube minas gerais": "america mg",
    "gremio foot ball porto alegrense": "gremio",
    "sport club corinthians paulista": "corinthians",
    "sport clube corinthians paulista": "corinthians",
    "sociedade esportiva palmeiras": "palmeiras",
    "clube de regatas do flamengo": "flamengo",
    "fluminense football club": "fluminense",
    "fluminense futebol clube": "fluminense",
    "santos futebol clube": "santos",
    "sao paulo futebol clube": "sao paulo",
    "cruzeiro esporte clube": "cruzeiro",
    "clube de regatas vasco da gama": "vasco da gama",
    "vasco": "vasco da gama",
    "botafogo de futebol e regatas": "botafogo",
    "botafogo futebol e regatas": "botafogo",
    "sport club internacional": "internacional",
    "esporte clube bahia": "bahia",
    "sport club do recife": "sport",
    "fortaleza esporte clube": "fortaleza",
    "ceara sporting club": "ceara",
    "coritiba foot ball club": "coritiba",
    "goias esporte clube": "goias",
    "esporte clube vitoria": "vitoria",
    "clube nautico capibaribe": "nautico",
    "avai futebol clube": "avai",
    "associacao chapecoense de futebol": "chapecoense",
    "criciuma esporte clube": "criciuma",
    "figueirense futebol clube": "figueirense",
    "associacao atletica ponte preta": "ponte preta",
    "guarani futebol clube": "guarani",
    "associacao portuguesa de desportos": "portuguesa",
    "red bull bragantino": "bragantino",
    "clube atletico bragantino": "bragantino",
    "cuiaba esporte clube": "cuiaba",
    "esporte clube juventude": "juventude",
}

# Curated display names for well-known clubs (with correct accents/casing).
# Anything not listed here falls back to the most common spelling seen
# across the source files (see data_loader.build_display_names).
TEAM_DISPLAY_NAMES = {
    "flamengo": "Flamengo",
    "fluminense": "Fluminense",
    "palmeiras": "Palmeiras",
    "corinthians": "Corinthians",
    "santos": "Santos",
    "sao paulo": "São Paulo",
    "gremio": "Grêmio",
    # Bare "atletico"/"america" resolve to the club whose state dominates
    # top-flight data (see build_known_club_states); other same-named
    # clubs get disambiguated to e.g. "atletico (pr)", "atletico (go)".
    "atletico": "Atlético-MG",
    "america": "América-MG",
    "vasco da gama": "Vasco da Gama",
    "botafogo": "Botafogo",
    "cruzeiro": "Cruzeiro",
    "internacional": "Internacional",
    "bahia": "Bahia",
    "sport": "Sport",
    "fortaleza": "Fortaleza",
    "ceara": "Ceará",
    "coritiba": "Coritiba",
    "goias": "Goiás",
    "vitoria": "Vitória",
    "nautico": "Náutico",
    "avai": "Avaí",
    "chapecoense": "Chapecoense",
    "criciuma": "Criciúma",
    "figueirense": "Figueirense",
    "ponte preta": "Ponte Preta",
    "guarani": "Guarani",
    "portuguesa": "Portuguesa",
    "bragantino": "Bragantino",
    "cuiaba": "Cuiabá",
    "juventude": "Juventude",
    "csa": "CSA",
    "parana": "Paraná",
}


def strip_accents(text: str) -> str:
    """Return `text` with combining accent marks removed (café -> cafe)."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def strip_state_suffix(name: str) -> tuple[str, str | None]:
    """Split a trailing Brazilian state code off a team name.

    "Flamengo-RJ" -> ("Flamengo", "RJ"); "Boavista ... - RJ" -> ("Boavista ...", "RJ").
    Names without a recognized state suffix are returned unchanged.
    """
    name = name.strip()
    for pattern in (_STATE_SUFFIX_HYPHEN_RE, _STATE_SUFFIX_SPACE_RE):
        match = pattern.match(name)
        if match and match.group(2).upper() in BRAZILIAN_STATE_CODES:
            return match.group(1).strip(), match.group(2).upper()
    return name, None


def _fold(text: str) -> str:
    """Accent/case/punctuation-fold `text`, turning hyphens into spaces but
    otherwise preserving word boundaries (so a trailing state code stays a
    separate token that can be split off later).
    """
    folded = strip_accents(text).lower()
    folded = re.sub(r"[^\w\s]", " ", folded)
    return re.sub(r"\s+", " ", folded).strip()


def _split_trailing_state(folded: str) -> tuple[str, str | None]:
    """Split a trailing "<name> <state>" token pair, e.g. "atletico mg" ->
    ("atletico", "MG"). Only splits if the last token is a real state code.
    """
    base, _, last = folded.rpartition(" ")
    if base and last.upper() in BRAZILIAN_STATE_CODES:
        return base, last.upper()
    return folded, None


def normalize_key(name: str | None) -> str:
    """Collapse a raw team/club name into a stable, comparable key.

    Folds accents/punctuation/case, resolves known alternate spellings
    (TEAM_KEY_ALIASES) and strips a trailing state code, so "Palmeiras-SP",
    "PALMEIRAS" and "Sociedade Esportiva Palmeiras" all resolve to the same
    key. Does not disambiguate same-named clubs from different states -
    see disambiguate_key for that.
    """
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    folded = _fold(str(name))
    folded = TEAM_KEY_ALIASES.get(folded, folded)
    base, _state = _split_trailing_state(folded)
    return base


def display_name_for_key(key: str, fallback: str | None = None) -> str:
    """Return a curated display name for `key`, or `fallback` if unknown."""
    return TEAM_DISPLAY_NAMES.get(key, fallback if fallback else key.title())


def build_known_club_states(pairs: Iterable[tuple[str, str | None]]) -> dict[str, str]:
    """Learn each club's "home" state from a trusted, top-flight-only
    source (one club per name, e.g. Brasileirao_Matches.csv), so that
    disambiguate_key can tell "Flamengo-RJ" (the famous club) apart from
    an unrelated lower-league "Flamengo-PI" that only shows up in the
    much larger, messier Copa do Brasil dataset.
    """
    counters: dict[str, Counter] = {}
    for raw, state in pairs:
        if not state or raw is None or (isinstance(raw, float) and pd.isna(raw)):
            continue
        key = normalize_key(raw)
        if not key:
            continue
        counters.setdefault(key, Counter())[str(state).upper()] += 1
    return {key: counter.most_common(1)[0][0] for key, counter in counters.items()}


def disambiguate_key(raw_name: str | None, known_states: dict[str, str]) -> str:
    """Like normalize_key, but keeps a team distinct from a known club of
    the same base name if its state suffix doesn't match that club's
    known home state (see build_known_club_states). E.g. "Flamengo-RJ"
    (the famous club, known_states["flamengo"] == "RJ") stays "flamengo",
    while an unrelated "Flamengo-PI" becomes "flamengo (pi)".
    """
    if raw_name is None or (isinstance(raw_name, float) and pd.isna(raw_name)):
        return ""
    folded = _fold(str(raw_name))
    folded = TEAM_KEY_ALIASES.get(folded, folded)
    base, state = _split_trailing_state(folded)
    if state and base in known_states and known_states[base] != state:
        return f"{base} ({state.lower()})"
    return base


_DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
)


def parse_datetime(value) -> pd.Timestamp:
    """Parse a date/datetime that may be ISO, Brazilian (DD/MM/YYYY), with
    or without a time component. Returns `pd.NaT` if unparseable.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return pd.NaT
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return pd.NaT
    for fmt in _DATETIME_FORMATS:
        try:
            return pd.Timestamp(datetime.strptime(text, fmt))
        except ValueError:
            continue
    parsed = pd.to_datetime(text, dayfirst=True, errors="coerce")
    if isinstance(parsed, pd.Timestamp) or parsed is pd.NaT:
        return parsed
    return pd.NaT


def parse_datetime_column(series: pd.Series, dayfirst: bool = False) -> pd.Series:
    """Vectorized datetime parsing with a per-row fallback for stragglers."""
    parsed = pd.to_datetime(series, errors="coerce", dayfirst=dayfirst)
    missing = parsed.isna() & series.notna()
    if missing.any():
        parsed.loc[missing] = series.loc[missing].map(parse_datetime)
    return parsed


def parse_goal_column(series: pd.Series) -> pd.Series:
    """Coerce a goals column to a nullable integer, treating placeholders
    like "-" (used in the Libertadores dataset for unplayed matches) as
    missing rather than raising.
    """
    return pd.to_numeric(series, errors="coerce").round().astype("Int64")
