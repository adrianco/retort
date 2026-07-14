"""
================================================================================
 Module: normalization
================================================================================
Context
-------
Brazilian soccer datasets use many naming conventions for the same entity:

    "Palmeiras-SP", "Palmeiras", "São Paulo", "Sao Paulo",
    "América - MG", "Nacional (URU)", "Sport Club Corinthians Paulista"

Dates appear in several formats:

    ISO            -> "2023-09-24"
    ISO + time     -> "2012-05-19 18:30:00"
    Brazilian      -> "29/03/2003"

Goal columns appear as ints ("2"), floats ("1.0") or quoted strings.

This module centralizes all of the normalization logic so the rest of the code
base can rely on consistent, comparable values.  Nothing here has external
dependencies -- it is pure standard-library Python.
================================================================================
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Optional

# Brazilian state (UF) abbreviations used as team-name suffixes.
BRAZILIAN_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}

# Matches a trailing state / country code suffix such as:
#   "-SP"   "- MG"   " - RJ"   "(URU)"   "-EQU"
_SUFFIX_RE = re.compile(r"\s*(?:-\s*|\(\s*)([A-Z]{2,4})\)?\s*$")

# Some base names are shared by several distinct clubs from different states
# (e.g. Atlético-MG / Atlético-GO, Botafogo-RJ / Botafogo-SP, América-MG / -RN).
# For these, the state suffix is *meaningful* and must be kept in the key,
# otherwise the suffix-stripping league files collapse different clubs into one
# row and corrupt the standings.
_AMBIGUOUS_BASES = {"atletico", "athletico", "botafogo", "america", "nacional"}

# Aliases map a canonical lookup key to a set of alternate keys so that the same
# club spelled differently across files (full name vs state suffix vs accents)
# resolves to one Team node.  Keys are in the folded "base [+ state]" form
# produced by ``_raw_key`` below.
_TEAM_ALIASES = {
    "sao paulo": {"sao paulo fc", "sao paulo futebol clube"},
    "atletico mineiro": {"atletico mg", "clube atletico mineiro"},
    "atletico goianiense": {"atletico go"},
    "atletico paranaense": {"athletico pr", "atletico pr", "athletico paranaense"},
    "america mineiro": {"america mg", "america fc minas gerais",
                        "america futebol clube minas gerais"},
    "botafogo": {"botafogo rj"},                 # bare "Botafogo" == the RJ club
    "vasco": {"vasco da gama", "vasco da gama rj", "vasco rj"},
    "corinthians": {"sport club corinthians paulista"},
    "gremio": {"gremio fbpa"},
    "bahia": {"ec bahia", "esporte clube bahia"},
    "fortaleza": {"fortaleza fc", "fortaleza ec", "fortaleza esporte clube"},
    "ceara": {"ceara sporting club", "ceara sc"},
}


def strip_accents(text: str) -> str:
    """Return ``text`` with diacritics removed (NFKD fold)."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _split_suffix(raw: str):
    """Split a raw team name into (clean_name, suffix) where suffix is a
    trailing state/country code if present, else ''."""
    if raw is None:
        return "", ""
    name = raw.strip().strip('"').strip()
    match = _SUFFIX_RE.search(name)
    if match:
        return name[: match.start()].strip(), match.group(1)
    return name, ""


def clean_team_name(raw: str) -> str:
    """Return a human-readable team name with a trailing state/country suffix
    removed.

    Examples
    --------
    >>> clean_team_name("Palmeiras-SP")
    'Palmeiras'
    >>> clean_team_name("América - MG")
    'América'
    >>> clean_team_name("Nacional (URU)")
    'Nacional'
    """
    return _split_suffix(raw)[0]


def _fold(text: str) -> str:
    """Accent-fold, lower-case and collapse to single-spaced alphanumerics."""
    folded = strip_accents(text or "").lower()
    folded = re.sub(r"[^a-z0-9]+", " ", folded).strip()
    return re.sub(r"\s+", " ", folded)


def team_key(raw: str) -> str:
    """Return a canonical lookup key for a team name.

    The key is accent-folded, lower-cased and punctuation-stripped.  For
    ambiguous base names shared by clubs from different states, the state
    suffix is appended so the clubs stay distinct.  Finally aliases collapse the
    various spellings of one club to a single canonical key.
    """
    cleaned, suffix = _split_suffix(raw)
    base = _fold(cleaned)
    if base in _AMBIGUOUS_BASES and suffix:
        candidate = f"{base} {suffix.lower()}"
    else:
        candidate = base
    # Resolve aliases to their canonical key.
    for canonical, alternates in _TEAM_ALIASES.items():
        if candidate == canonical or candidate in alternates:
            return canonical
    return candidate


# Preferred display names for canonical keys whose observed spellings are
# ambiguous or terse (e.g. the bare "Atlético" left after stripping "-MG").
CANONICAL_DISPLAY = {
    "atletico mineiro": "Atlético Mineiro",
    "atletico paranaense": "Athletico Paranaense",
    "atletico goianiense": "Atlético Goianiense",
    "america mineiro": "América Mineiro",
    "botafogo": "Botafogo",
    "vasco": "Vasco da Gama",
}


def display_name_for_key(key: str) -> Optional[str]:
    """Return a preferred display name for a canonical key, or None."""
    return CANONICAL_DISPLAY.get(key)


def team_query_matches(query: str, key: str) -> bool:
    """Return True if a user ``query`` should match a team whose canonical key
    is ``key``.

    Matching is forgiving: an exact key match, or a whole-word containment in
    either direction (so "Corinthians" matches
    "sport club corinthians paulista", and "Atletico Mineiro" matches
    "atletico mineiro").
    """
    q = team_key(query)
    if not q or not key:
        return False
    if q == key:
        return True
    # Whole-word containment guards against "sport" matching everything.
    q_words = q.split()
    k_words = key.split()
    if _is_subsequence_words(q_words, k_words) or _is_subsequence_words(k_words, q_words):
        return True
    return False


def _is_subsequence_words(needle: list[str], haystack: list[str]) -> bool:
    """True if all words in ``needle`` appear in ``haystack`` (as a set subset),
    requiring at least one shared word and that the needle is fully covered."""
    if not needle:
        return False
    hayset = set(haystack)
    return all(w in hayset for w in needle)


def parse_int(value) -> Optional[int]:
    """Parse a goal/score value that may be an int, float, or quoted string."""
    if value is None:
        return None
    if isinstance(value, (int,)):
        return value
    text = str(value).strip().strip('"').strip()
    if text == "" or text.lower() in {"nan", "none", "null"}:
        return None
    try:
        return int(float(text))
    except (ValueError, TypeError):
        return None


def parse_float(value) -> Optional[float]:
    """Parse a float value that may be a quoted string; return None on failure."""
    if value is None:
        return None
    text = str(value).strip().strip('"').strip()
    if text == "" or text.lower() in {"nan", "none", "null"}:
        return None
    try:
        return float(text)
    except (ValueError, TypeError):
        return None


def parse_date(value) -> Optional[date]:
    """Parse a date from any of the supported dataset formats.

    Handles: "2023-09-24", "2012-05-19 18:30:00", "29/03/2003",
    "2003.01.0001"-style is *not* a date (it is an id) and returns None.
    """
    if value is None:
        return None
    text = str(value).strip().strip('"').strip()
    if not text:
        return None
    # Keep only the date portion if a time is appended.
    date_part = text.split(" ")[0].split("T")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_part, fmt).date()
        except ValueError:
            continue
    return None


def iso_date(value) -> Optional[str]:
    """Return an ISO ``YYYY-MM-DD`` string for ``value`` or None."""
    d = parse_date(value)
    return d.isoformat() if d else None


def parse_season(value) -> Optional[int]:
    """Parse a season/year value to an int."""
    return parse_int(value)


def canonical_competition(name: str) -> str:
    """Map competition-name spelling variants onto a single canonical label.

    The datasets disagree on accents and series labels, e.g.
    "Brasileirão Serie A" (BR-Football) vs "Brasileirão Série A"
    (Brasileirao_Matches / historical).  Collapsing them is essential so that
    cross-file deduplication and standings work on one consistent competition.
    """
    if not name:
        return name
    folded = strip_accents(name).lower().strip()
    if "serie a" in folded or folded in {"brasileirao", "brasileirao serie a"}:
        return "Brasileirão Série A"
    if "serie b" in folded:
        return "Brasileirão Série B"
    if "serie c" in folded:
        return "Brasileirão Série C"
    if "copa do brasil" in folded:
        return "Copa do Brasil"
    if "libertadores" in folded:
        return "Copa Libertadores"
    return name.strip()
