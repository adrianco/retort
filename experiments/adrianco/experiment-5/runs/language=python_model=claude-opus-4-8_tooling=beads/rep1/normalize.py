"""
================================================================================
Module: normalize.py
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
Context
-------
The provided Kaggle datasets use many different conventions for the same club:

    "Palmeiras-SP"                 (state suffix)
    "Athletico-PR" / "Atletico Paranaense" / "Athletico"   (spelling + form)
    "America - MG" / "America MG" / "America FC (Minas Gerais)"
    "Nacional (URU)"               (country code)
    "Sao Paulo" / "Sao Paulo FC" / "São Paulo"
    "Internacional" / "Internacional-RS"
    "Sport Club do Recife" / "Sport Recife" / "Sport - PE"

To answer questions like "all Flamengo vs Fluminense matches" across files we
need ONE canonical key per real club so records from every source collapse onto
the same entity.

Most clubs are unique by their base name, so the state suffix is *dropped*
("Palmeiras-SP" == "Palmeiras"). But a handful of base names are shared across
states (Atletico Mineiro/Paranaense/Goianiense, America MG/RN, Botafogo
RJ/PB/SP, Internacional, Nacional, Sport). For those AMBIGUOUS bases the key
*keeps* the disambiguating state, and descriptive names (Mineiro, Paranaense,
Recife, ...) are mapped to their state so every form converges.

This module is pure-stdlib and side-effect free, so it is trivially unit-tested.
================================================================================
"""

from __future__ import annotations

import re
import unicodedata

# Brazilian state abbreviations (UF) that appear as suffixes on club names.
_BR_STATES = {
    "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms",
    "mg", "pa", "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc",
    "sp", "se", "to",
}

# Three-letter country codes seen in the Libertadores file e.g. "Nacional (URU)".
_COUNTRY_CODES = {
    "uru", "arg", "par", "bol", "equ", "ecu", "col", "ven", "per", "chi",
    "bra", "mex", "usa", "pan",
}
_CODES = _BR_STATES | _COUNTRY_CODES

# Base names shared by several distinct clubs -> key must keep the state.
_AMBIGUOUS_BASES = {
    "atletico", "america", "nacional", "botafogo", "internacional", "sport",
}

# Descriptive name fragment -> the state it implies.
_DESCRIPTOR_STATE = {
    "mineiro": "mg", "minas": "mg",
    "paranaense": "pr",
    "goianiense": "go",
    "acreano": "ac",
    "alagoinhas": "ba",
    "recife": "pe",
    "natal": "rn",
}

# For a bare ambiguous base (no state, no descriptor) pick the dominant club.
_DEFAULT_STATE = {
    "internacional": "rs",
    "botafogo": "rj",
    "atletico": "pr",   # bare "Athletico" in the data == Paranaense
    "sport": "pe",      # bare "Sport" == Sport Club do Recife
}

# Noise tokens that never help identify a club.
_NOISE_WORDS = {
    "fc", "ec", "sc", "cf", "ac", "clube", "club", "esporte", "esportivo",
    "esportiva", "futebol", "sociedade", "associacao", "sporting", "gerais",
    "de", "do", "da", "das", "dos", "the",
}

# Single-token spelling aliases (applied after accent stripping + lowercasing).
_TOKEN_ALIASES = {
    "athletico": "atletico",
}

# Final whole-key aliases for multi-word names that should collapse to a short
# canonical form (applied as the very last step of ``normalize_key``).
_KEY_ALIASES = {
    "vasco gama": "vasco",
    "red bull bragantino": "bragantino",
    "rb bragantino": "bragantino",
}

_PAREN_RE = re.compile(r"\(([^)]*)\)")
_NONWORD_RE = re.compile(r"[^a-z0-9\s]")
_WS_RE = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    """Return ``text`` with diacritics removed (São -> Sao, Grêmio -> Gremio)."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _tokenize(name: str) -> list[str]:
    """Lower-case, de-accent, drop punctuation and split into word tokens.

    Parenthetical content (country codes, "(Minas Gerais)") is kept inline so
    its tokens participate in code/descriptor detection.
    """
    text = str(name)
    text = _PAREN_RE.sub(lambda m: " " + m.group(1) + " ", text)
    text = text.replace("-", " ")
    text = strip_accents(text).lower()
    text = _NONWORD_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    return text.split()


def normalize_key(name: str | None) -> str:
    """Collapse a raw team name to a stable cross-dataset comparison key."""
    if not name:
        return ""
    tokens = [_TOKEN_ALIASES.get(t, t) for t in _tokenize(name)]
    if not tokens:
        return ""

    # Extract state/country codes (keep the last one seen as the chosen code).
    code = ""
    kept: list[str] = []
    for tok in tokens:
        if tok in _CODES:
            code = tok
        else:
            kept.append(tok)
    tokens = kept

    # Map descriptive fragments to a state, dropping the descriptor token.
    kept = []
    for tok in tokens:
        if tok in _DESCRIPTOR_STATE:
            code = _DESCRIPTOR_STATE[tok]
        else:
            kept.append(tok)
    tokens = kept

    # Drop noise words but never reduce to nothing.
    meaningful = [t for t in tokens if t not in _NOISE_WORDS]
    if not meaningful:
        meaningful = tokens
    tokens = meaningful
    if not tokens:
        return ""

    # "Atlético Nacional" (Colombia) is its own club, not Nacional.
    if "atletico" in tokens and "nacional" in tokens:
        return "atletico nacional"

    head = tokens[0]
    if head in _AMBIGUOUS_BASES:
        rest = tokens[1:]
        if not rest:
            code = code or _DEFAULT_STATE.get(head, "")
            return f"{head} {code}".strip()
        # A distinctive extra token (e.g. "Sport Boys") -> keep full name.
        return _KEY_ALIASES.get(" ".join(tokens), " ".join(tokens))

    key = " ".join(tokens)
    return _KEY_ALIASES.get(key, key)


def canonical_name(name: str | None) -> str:
    """Return a human-friendly display label for a club key.

    State/country codes are upper-cased ("atletico mg" -> "Atletico MG"); other
    tokens are capitalised.
    """
    key = normalize_key(name)
    if not key:
        return ""
    out = []
    for tok in key.split():
        if tok in _CODES:
            out.append(tok.upper())
        else:
            out.append(tok.capitalize())
    return " ".join(out)
