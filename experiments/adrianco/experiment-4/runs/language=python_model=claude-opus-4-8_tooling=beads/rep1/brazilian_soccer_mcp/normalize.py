"""
================================================================================
Module: brazilian_soccer_mcp.normalize
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
CONTEXT
  Team names across the six provided Kaggle CSV datasets use inconsistent
  conventions:
    * with a state suffix      -> "Palmeiras-SP", "Flamengo-RJ"
    * with a spaced suffix      -> "America - MG"
    * with a country code        -> "Nacional (URU)", "Barcelona-EQU"
    * with parenthetical notes   -> "Boavista Sport Club (antigo ...) - RJ"
    * plain                      -> "Palmeiras", "Sao Paulo"
    * with Portuguese accents    -> "Sao Paulo" vs "São Paulo", "Gremio" vs "Grêmio"

  This module normalizes raw names into a stable canonical key plus a clean
  human-readable display name so that the same club is matched consistently
  regardless of which dataset a record came from.

WHY A CURATED MAP
  Naively stripping the state suffix would merge genuinely different clubs that
  share a base name (Atletico-MG / Atletico-GO / Atletico-PR are three distinct
  clubs). We therefore treat a small set of base names as "ambiguous" and keep
  their state in the canonical key, while a curated alias map gives the major
  clubs clean display names and unifies plain/suffixed spellings.

PUBLIC API
  strip_accents(text)        -> ascii-folded text
  normalize_tokens(name)     -> list[str] of cleaned lowercase tokens
  resolve_team(raw)          -> (canonical_key, display_name)
  team_matches(query, key)   -> bool, fuzzy membership test for search
================================================================================
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

# Brazilian state (UF) abbreviations plus a handful of South-American country
# codes that appear as suffixes in the Libertadores dataset.
_UF_CODES = {
    "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms",
    "mg", "pa", "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc",
    "sp", "se", "to",
}
_COUNTRY_CODES = {
    "uru", "equ", "arg", "par", "bol", "col", "ven", "chi", "per", "bra",
    "mex", "ecu",
}
_SUFFIX_CODES = _UF_CODES | _COUNTRY_CODES

# Generic club-type tokens that add noise to names ("EC Bahia", "Fortaleza
# FC", "America FC Natal"). These are stripped before keying. They are chosen
# to NOT overlap with any UF code so state detection still works (e.g. "SC" is
# left intact because it is the UF for Santa Catarina).
_FILLER_TOKENS = {
    "fc", "ec", "cf", "fr", "clube", "club", "futebol", "esporte",
    "esportes", "esportivo", "associacao", "sociedade",
}

# Base names that collide across distinct clubs and therefore must keep their
# state/country code as part of the canonical identity.
_AMBIGUOUS_BASES = {
    "atletico", "america", "nacional", "san lorenzo",
}

# Post-key aliases: collapse known alternate spellings of the major clubs onto
# a single canonical key. Without this, date-offset duplicates across datasets
# (and standings team counts) would not reconcile.
_KEY_ALIASES = {
    "bahia": "bahia",
    "ec bahia": "bahia",
    "fortaleza ec": "fortaleza",
    "fortaleza fc": "fortaleza",
    "athletico": "atletico pr",
    "athletico paranaense": "atletico pr",
    "atletico paranaense": "atletico pr",
    "atletico mineiro": "atletico mg",
    "atletico goianiense": "atletico go",
    "red bull bragantino": "bragantino",
    "america natal": "america rn",
    "america fc natal": "america rn",
    "america de natal": "america rn",
    "vasco da gama": "vasco",
    "sport recife": "sport",
}

# Curated display names. Keys are canonical keys (see resolve_team). Including
# both the plain and a few common variants keeps cross-dataset records unified.
_DISPLAY_NAMES = {
    "flamengo": "Flamengo",
    "fluminense": "Fluminense",
    "palmeiras": "Palmeiras",
    "santos": "Santos",
    "corinthians": "Corinthians",
    "sao paulo": "São Paulo",
    "gremio": "Grêmio",
    "internacional": "Internacional",
    "cruzeiro": "Cruzeiro",
    "vasco": "Vasco da Gama",
    "vasco da gama": "Vasco da Gama",
    "botafogo": "Botafogo",
    "bahia": "Bahia",
    "fortaleza": "Fortaleza",
    "ceara": "Ceará",
    "sport": "Sport Recife",
    "sport recife": "Sport Recife",
    "goias": "Goiás",
    "coritiba": "Coritiba",
    "chapecoense": "Chapecoense",
    "avai": "Avaí",
    "figueirense": "Figueirense",
    "ponte preta": "Ponte Preta",
    "vitoria": "Vitória",
    "parana": "Paraná",
    "portuguesa": "Portuguesa",
    "guarani": "Guarani",
    "juventude": "Juventude",
    "bragantino": "Red Bull Bragantino",
    "red bull bragantino": "Red Bull Bragantino",
    "cuiaba": "Cuiabá",
    "atletico mg": "Atlético Mineiro",
    "atletico pr": "Athletico Paranaense",
    "atletico go": "Atlético Goianiense",
    "america mg": "América-MG",
    "america rn": "América-RN",
}

# Some datasets use long official names (e.g. "Sport Club Corinthians
# Paulista"). When a base name is not recognized but contains one of these
# unambiguous signature tokens, fold it onto the canonical club. Order matters
# only in that each token must be globally unambiguous among the major clubs.
_SIGNATURE_TOKENS = {
    "corinthians": ("corinthians", "Corinthians"),
    "fluminense": ("fluminense", "Fluminense"),
    "palmeiras": ("palmeiras", "Palmeiras"),
    "gremio": ("gremio", "Grêmio"),
    "internacional": ("internacional", "Internacional"),
    "cruzeiro": ("cruzeiro", "Cruzeiro"),
    "botafogo": ("botafogo", "Botafogo"),
    "fluminense": ("fluminense", "Fluminense"),
}


def strip_accents(text: str) -> str:
    """Fold accented Portuguese characters down to plain ASCII."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


@lru_cache(maxsize=4096)
def normalize_tokens(name: str) -> tuple[str, ...]:
    """Reduce a raw team name to a tuple of clean lowercase tokens.

    Parenthetical notes are dropped, accents are folded, and punctuation is
    converted to spaces before tokenizing.
    """
    if not name:
        return tuple()
    text = strip_accents(name).lower()
    text = re.sub(r"\([^)]*\)", " ", text)          # drop "(antigo ...)" / "(uru)"
    text = re.sub(r"[^a-z0-9]+", " ", text)          # punctuation -> space
    tokens = [t for t in text.split() if t]
    # Drop generic club-type tokens, but never reduce a name to nothing.
    filtered = [t for t in tokens if t not in _FILLER_TOKENS]
    return tuple(filtered or tokens)


def _split_state(tokens: tuple[str, ...]) -> tuple[tuple[str, ...], str | None]:
    """Separate a trailing state/country code token from the base tokens."""
    if len(tokens) >= 2 and tokens[-1] in _SUFFIX_CODES:
        return tokens[:-1], tokens[-1]
    return tokens, None


@lru_cache(maxsize=4096)
def resolve_team(raw: str) -> tuple[str, str]:
    """Resolve a raw team name to (canonical_key, display_name).

    The canonical key is stable across datasets so the same club always maps to
    the same identity. The display name is human-readable, preferring the
    curated form when available.
    """
    tokens = normalize_tokens(raw)
    if not tokens:
        return "", (raw or "").strip()

    base_tokens, state = _split_state(tokens)
    base = " ".join(base_tokens)

    if base in _AMBIGUOUS_BASES and state:
        key = f"{base} {state}"
    else:
        key = base

    # Collapse known alternate spellings (checked on both the state-qualified
    # key and the bare base) onto a single canonical key.
    key = _KEY_ALIASES.get(key, _KEY_ALIASES.get(base, key))

    # Fold long official names onto a canonical club via a signature token,
    # but only when the base isn't already a recognized standalone club.
    if key not in _DISPLAY_NAMES and base not in _DISPLAY_NAMES:
        for tok in base_tokens:
            sig = _SIGNATURE_TOKENS.get(tok)
            if sig:
                return sig[0], sig[1]

    display = (
        _DISPLAY_NAMES.get(key)
        or _DISPLAY_NAMES.get(base)
        or _prettify(base or " ".join(tokens))
    )
    return key, display


def _prettify(base: str) -> str:
    """Title-case fallback display name for clubs not in the curated map."""
    small = {"de", "do", "da", "dos", "das", "e"}
    parts = base.split()
    out = []
    for i, p in enumerate(parts):
        if i and p in small:
            out.append(p)
        else:
            out.append(p.capitalize())
    return " ".join(out) if out else base


def canonical_key(raw: str) -> str:
    """Convenience accessor returning only the canonical key."""
    return resolve_team(raw)[0]


def team_matches(query: str, team_key: str) -> bool:
    """Fuzzy membership test: does a search `query` match a team's key?

    Matches when the query resolves to the same key, when the team key is a
    state-qualified variant of the query (e.g. "atletico" -> "atletico mg"),
    or when every query token is present in the team key tokens.
    """
    if not query or not team_key:
        return False
    q_key = canonical_key(query)
    if not q_key:
        return False
    if q_key == team_key:
        return True
    if team_key.startswith(q_key + " "):
        return True
    q_tokens = set(q_key.split())
    t_tokens = set(team_key.split())
    return q_tokens.issubset(t_tokens)
