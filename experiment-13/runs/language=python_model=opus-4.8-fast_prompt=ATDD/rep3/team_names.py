"""
Team-name normalization for Brazilian soccer data.

The provided datasets name the same club in several incompatible ways:

    "Palmeiras-SP", "Palmeiras", "Sociedade Esportiva Palmeiras"
    "Grêmio"        vs  "Gremio"
    "Nacional (URU)" vs "Nacional"
    "Sport Club Corinthians Paulista" vs "Corinthians"

To match a club consistently across files we reduce every name to a canonical
key: accents removed, state/country suffixes stripped, punctuation dropped,
lower-cased and whitespace-collapsed. A small alias table maps well-known long
form names onto their short canonical key.

This module has no dependencies on the data layer so it can be unit-tested in
isolation.
"""

import re
import unicodedata

# Long-form / idiosyncratic names mapped onto a canonical short key. Keys here
# are themselves already normalized (accent-free, lower-case).
_ALIASES = {
    "sport club corinthians paulista": "corinthians",
    "sociedade esportiva palmeiras": "palmeiras",
    "clube de regatas do flamengo": "flamengo",
    "santos futebol clube": "santos",
    "sao paulo futebol clube": "sao paulo",
    "gremio foot ball porto alegre": "gremio",
    "athletico paranaense": "atletico pr",
    "atletico paranaense": "atletico pr",
    "atletico mineiro": "atletico mg",
}


def strip_accents(text: str) -> str:
    """Remove diacritics (São -> Sao, Grêmio -> Gremio)."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_team(name) -> str:
    """Reduce a raw team name to its canonical matching key.

    Returns an empty string for null/blank input.
    """
    if name is None:
        return ""
    text = str(name).strip()
    if not text:
        return ""

    # Drop parenthetical qualifiers such as "(URU)", "(antigo ...)".
    text = re.sub(r"\([^)]*\)", " ", text)

    # Remove a trailing state / country suffix: "-SP", " - RJ", "-EQU".
    text = re.sub(r"\s*-\s*[A-Za-z]{2,3}\b\s*$", " ", text)

    # Accent-fold and lower-case.
    text = strip_accents(text).lower()

    # Replace any remaining punctuation with spaces and collapse whitespace.
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return _ALIASES.get(text, text)
