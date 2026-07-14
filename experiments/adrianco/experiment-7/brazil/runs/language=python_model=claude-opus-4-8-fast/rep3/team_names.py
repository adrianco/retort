"""
================================================================================
Context
================================================================================
Module:   team_names.py
Project:  Brazilian Soccer MCP Server
Purpose:  Normalize the many inconsistent Brazilian club naming conventions that
          appear across the six source datasets into a single canonical form so
          that matches, teams and players can be cross-referenced reliably.

Why this exists:
    The datasets spell the same club in mutually incompatible ways, e.g.
        "Palmeiras-SP"     (Brasileirao_Matches.csv  -> name + state suffix)
        "América - MG"     (Brazilian_Cup_Matches.csv -> spaced state suffix)
        "Atlético-MG"      (novo_campeonato.csv       -> accented + state)
        "Sao Paulo"        (BR-Football-Dataset.csv    -> ASCII, no state)
        "Nacional (URU)"   (Libertadores_Matches.csv   -> parenthetical country)
        "São Paulo"        (FIFA club column           -> accented full name)
    All of these must collapse to one normalized key so head-to-head and
    team-history queries work regardless of which file a row came from.

Public API:
    normalize_team(name)      -> canonical lookup key (ascii, lowercase)
    display_team(name)        -> human friendly canonical display name
    strip_state_suffix(name)  -> name with trailing state/country code removed
    teams_match(a, b)         -> True if two raw names refer to the same club

Dependencies: standard library only (re, unicodedata).
================================================================================
"""

from __future__ import annotations

import re
import unicodedata

# Trailing state / country qualifiers we want to remove.
#   "Palmeiras-SP", "América - MG", "Barcelona-EQU", "Nacional (URU)"
# Capture group 1 holds the bare 2-3 letter code (without punctuation/parens).
_STATE_SUFFIX_RE = re.compile(
    r"""
    \s*
    (?:
        \(\s*(?P<code>[A-Za-z]{2,3})\s*\)   # parenthetical code  "(URU)"
        |
        [-/]\s*(?P<code2>[A-Z]{2,3})        # dashed code         "-SP" / "- MG"
    )
    \s*$
    """,
    re.VERBOSE,
)

# Base club names that are shared by several distinct clubs, where the trailing
# state code is the only disambiguator (e.g. Atlético-MG vs Atlético-GO).  For
# these the state code is *retained* as part of the canonical key instead of
# being stripped away.
_AMBIGUOUS_BASES = {"atletico", "athletico", "america"}

# Parenthetical asides that are not country codes, e.g.
# "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
_PAREN_ASIDE_RE = re.compile(r"\s*\([^)]*\)")

_WHITESPACE_RE = re.compile(r"\s+")

# Canonical aliases: map a normalized variant -> canonical normalized key.
# Keys and values are both already run through the base normalization
# (ascii, lowercase, collapsed whitespace).  This resolves spelling/branding
# differences that cannot be derived mechanically.
_ALIASES = {
    # Athletico Paranaense is written many ways across the datasets.
    "atletico paranaense": "athletico pr",
    "athletico paranaense": "athletico pr",
    "atletico pr": "athletico pr",
    "athletico pr": "athletico pr",
    # Atlético clubs spelled out in full (BR-Football dataset).
    "atletico mineiro": "atletico mg",
    "atletico goianiense": "atletico go",
    # América clubs spelled out in full.
    "america mineiro": "america mg",
    "america de natal": "america rn",
    "america rn": "america rn",
    "america mg": "america mg",
    # Other branding / suffix differences.
    "vasco da gama": "vasco",
    "sport recife": "sport",
    "sport club do recife": "sport",
    "red bull bragantino": "bragantino",
    "rb bragantino": "bragantino",
    "ec bahia": "bahia",
    "sao paulo fc": "sao paulo",
}

# Preferred display spellings for canonical keys.  Falls back to a title-cased
# version of the first raw name seen when a key is missing here.
_DISPLAY = {
    "athletico pr": "Athletico-PR",
    "atletico mg": "Atlético-MG",
    "atletico go": "Atlético-GO",
    "america mg": "América-MG",
    "america rn": "América-RN",
    "sao paulo": "São Paulo",
    "gremio": "Grêmio",
    "vasco": "Vasco da Gama",
    "bragantino": "Bragantino",
    "sport": "Sport Recife",
    "avai": "Avaí",
    "ceara": "Ceará",
    "goias": "Goiás",
    "cuiaba": "Cuiabá",
    "vitoria": "Vitória",
    "parana": "Paraná",
    "criciuma": "Criciúma",
}


def _strip_accents(text: str) -> str:
    """Transliterate accented Latin characters to plain ASCII."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _split_state_suffix(name: str) -> tuple[str, str]:
    """
    Split a raw name into (base, state_code).

    state_code is the lower-cased 2-3 letter trailing qualifier if present,
    otherwise ''.  Any non-code parenthetical aside is also removed from base.
    """
    if not name:
        return "", ""
    stripped = name.strip()
    match = _STATE_SUFFIX_RE.search(stripped)
    code = ""
    if match:
        code = (match.group("code") or match.group("code2") or "").lower()
        stripped = stripped[: match.start()]
    base = _PAREN_ASIDE_RE.sub("", stripped).strip(" -/").strip()
    return base, code


def strip_state_suffix(name: str) -> str:
    """Remove a trailing state/country qualifier, e.g. '-SP' or '(URU)'."""
    base, _ = _split_state_suffix(name)
    return base


def normalize_team(name: str) -> str:
    """
    Return a canonical lookup key for a raw club name.

    The key is accent-free, lower-case and run through the alias table.  The
    trailing state/country code is stripped for unambiguous names, but retained
    for clubs whose base name is shared (Atlético-MG vs Atlético-GO), so that
    distinct clubs never collapse together while spelling variants of the same
    club always do.
    """
    if not name:
        return ""
    base, code = _split_state_suffix(name)
    base = _strip_accents(base).lower().replace(".", " ")
    base = _WHITESPACE_RE.sub(" ", base).strip()
    if code and base in _AMBIGUOUS_BASES:
        base = f"{base} {code}"
    return _ALIASES.get(base, base)


def display_team(name: str) -> str:
    """Return a human-friendly canonical display name for a raw club name."""
    key = normalize_team(name)
    if key in _DISPLAY:
        return _DISPLAY[key]
    # Title-case the cleaned (accent-preserving) name as a sensible default.
    cleaned = strip_state_suffix(name)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned.title() if cleaned else name


def teams_match(a: str, b: str) -> bool:
    """True when two raw club names refer to the same club."""
    return bool(a) and bool(b) and normalize_team(a) == normalize_team(b)
