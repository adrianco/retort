"""
Context
=======
Module: bsoccer.normalize
Purpose: Normalize Brazilian soccer team names so that the many spelling and
         formatting variations found across the provided Kaggle datasets resolve
         to a single canonical key.

Why this is needed
------------------
The datasets use inconsistent naming conventions for the same club, e.g.:
  - "Palmeiras-SP", "Palmeiras", "SE Palmeiras"
  - "Athletico-PR" vs "Atletico-PR" vs "Atletico Paranaense"
  - "Sao Paulo", "São Paulo", "Sao Paulo-SP"
  - Country tags for Libertadores: "Nacional (URU)", "Barcelona-EQU"

The query layer matches teams by their *normalized key* (accent-folded,
lowercased, state/country suffix stripped, alias-mapped) while still showing a
human-friendly display name to the user.

This module has no third-party dependencies so it is trivially testable.
"""

from __future__ import annotations

import re
import unicodedata

# Two-letter Brazilian state (UF) codes used as suffixes like "Flamengo-RJ".
_BR_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

# Country tags that appear in the Libertadores dataset (continental cup).
_COUNTRY_CODES = {
    "URU", "ARG", "EQU", "COL", "PAR", "BOL", "CHI", "PER", "VEN", "BRA",
    "MEX", "USA",
}

# Words that carry no discriminating value once names are compared. These are
# stripped from the normalized key so "Sport Club Corinthians Paulista" and
# "Corinthians" collapse together.
_NOISE_WORDS = {
    "fc", "ec", "sc", "ac", "se", "cr", "ca", "esporte", "clube", "club",
    "futebol", "sport", "regatas", "do", "de", "da", "associacao",
    "atletica", "sociedade", "gremio",  # 'gremio' handled via alias below
}

# Canonical alias map keyed by a *pre-normalized* simplified token string.
# Maps messy variants to a single canonical key. Values are canonical keys.
_ALIASES = {
    "athletico": "athletico paranaense",
    "athletico pr": "athletico paranaense",
    "atletico pr": "athletico paranaense",
    "atletico paranaense": "athletico paranaense",
    "atletico mg": "atletico mineiro",
    "atletico mineiro": "atletico mineiro",
    "atletico go": "atletico goianiense",
    "atletico goianiense": "atletico goianiense",
    "vasco": "vasco da gama",
    "vasco da gama": "vasco da gama",
    "corinthians paulista": "corinthians",
    "sao paulo": "sao paulo",
    "red bull bragantino": "bragantino",
    "rb bragantino": "bragantino",
    "bragantino": "bragantino",
    "gremio": "gremio",
    "america mg": "america mineiro",
    "america mineiro": "america mineiro",
    "america rn": "america rn",
}

# Bare base names that are ambiguous on their own — several distinct clubs share
# them and the state/country suffix is the only discriminator. For these we keep
# the suffix in the normalized key (e.g. "Atletico-MG" -> "atletico mg") instead
# of collapsing to "atletico".
_AMBIGUOUS_BASES = {"atletico", "america"}


def strip_accents(text: str) -> str:
    """Return *text* with diacritics removed (São -> Sao, Grêmio -> Gremio)."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _split_suffix(name: str) -> tuple[str, str]:
    """Split a trailing state/country tag from *name*.

    Returns (base, suffix) where suffix is the uppercase state/country code
    ("" if none). Handles "-SP", " - RJ" and parenthetical "(URU)" forms.
    """
    suffix = ""
    # Parenthetical country code, e.g. "Nacional (URU)".
    m = re.search(r"\s*\(([A-Za-z]{2,4})\)\s*$", name)
    if m:
        token = m.group(1).upper()
        if token in _BR_STATES or token in _COUNTRY_CODES:
            suffix = token
            name = name[: m.start()].strip()
    # Trailing " - XX" or "-XX" state/country suffix.
    m = re.search(r"[\s\-]+([A-Za-z]{2,3})\s*$", name)
    if m:
        token = m.group(1).upper()
        if token in _BR_STATES or token in _COUNTRY_CODES:
            suffix = token
            name = name[: m.start()].strip()
    return name, suffix


def _strip_suffix(name: str) -> str:
    """Remove a trailing state/country tag such as '-SP', ' - RJ', '(URU)'."""
    return _split_suffix(name)[0]


def normalize_team(name: str) -> str:
    """Return the canonical lookup key for a team name.

    The key is lowercase, accent-free, suffix-free, noise-word-free and
    alias-resolved. Returns an empty string for blank input.
    """
    if name is None:
        return ""
    name = str(name).strip()
    if not name:
        return ""

    base, suffix = _split_suffix(name)
    base = strip_accents(base).lower()
    # Replace any non-alphanumeric run with a single space.
    base = re.sub(r"[^a-z0-9]+", " ", base).strip()

    # First, try a direct alias hit on the whole simplified string.
    if base in _ALIASES:
        return _ALIASES[base]

    tokens = [t for t in base.split() if t]
    # Drop noise words but keep at least one token.
    meaningful = [t for t in tokens if t not in _NOISE_WORDS]
    if not meaningful:
        meaningful = tokens
    key = " ".join(meaningful).strip()

    # For ambiguous single-word clubs (e.g. "Atletico", "America"), keep the
    # state/country suffix so distinct clubs do not collapse together.
    if key in _AMBIGUOUS_BASES and suffix:
        key = f"{key} {suffix.lower()}"

    # Alias resolution on the cleaned key as well.
    return _ALIASES.get(key, key)


def display_name(name: str) -> str:
    """Return a cleaned, human-friendly display form of *name*.

    Keeps original accents/casing but strips a state/country suffix so the UI
    shows "Palmeiras" rather than "Palmeiras-SP". For ambiguous single-word
    clubs (e.g. "Atletico-MG" vs "Atletico-GO") the suffix is kept so the two
    remain visually distinct.
    """
    if not name:
        return ""
    name = str(name).strip()
    base, suffix = _split_suffix(name)
    if suffix:
        simple = re.sub(r"[^a-z0-9]+", " ", strip_accents(base).lower()).strip()
        if simple in _AMBIGUOUS_BASES:
            return f"{base}-{suffix}"
    return base
