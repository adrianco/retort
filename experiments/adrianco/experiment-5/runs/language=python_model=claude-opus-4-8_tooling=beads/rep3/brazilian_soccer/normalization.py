"""
==============================================================================
Module: brazilian_soccer.normalization
==============================================================================
CONTEXT
-------
The Brazilian Soccer datasets use inconsistent naming conventions for the same
team across (and even within) files:

    * State suffix .......... "Palmeiras-SP", "Flamengo-RJ", "América - MG"
    * Country suffix ........ "Nacional (URU)", "Barcelona-EQU"
    * Full legal names ...... "Sport Club Corinthians Paulista"
    * Accented variants ..... "São Paulo", "Grêmio", "Atlético Mineiro"
    * Spelling variants ..... "Athletico-PR" vs "Atletico-PR"

To answer questions like "Show me all Flamengo vs Fluminense matches" we must
collapse all surface forms of the SAME real-world team onto a single canonical
key -- WITHOUT collapsing genuinely different teams that happen to share a base
name.

THE AMBIGUITY PROBLEM
---------------------
Naively stripping the "-XX" suffix is wrong for clubs distinguished ONLY by
state/country:

    * Atlético-MG (Mineiro), Atlético-PR (Paranaense), Atlético-GO (Goianiense)
    * América-MG, América-RN, América-RJ
    * Nacional (URU), Nacional (PAR), ...   (Libertadores)

So the rule is asymmetric:

    * For an AMBIGUOUS base name -> KEEP the state/country code in the key.
    * For every other base name -> STRIP the suffix so e.g. "Flamengo-RJ" and
      the bare "Flamengo" (used in other files) merge into one team.

``ALIASES`` then maps well-known long/full names onto the canonical key (e.g.
"Atlético Mineiro" -> "atletico mg", "Sport Club Corinthians Paulista" ->
"corinthians").
==============================================================================
"""

from __future__ import annotations

import re
import unicodedata

# Brazilian state abbreviations and common country codes seen as suffixes.
_STATE_CODES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

# Base names that are NOT unique on their own -- the suffix disambiguates them
# and MUST be retained in the canonical key. Values are accent-folded lowercase.
AMBIGUOUS_BASES = {"atletico", "america", "nacional"}

# Curated aliases: accent-folded full/long name -> final canonical key.
# (Right-hand sides already include any needed disambiguating suffix token.)
ALIASES = {
    "atletico mineiro": "atletico mg",
    "atletico paranaense": "atletico pr",
    "atletico goianiense": "atletico go",
    "america mineiro": "america mg",
    "america fc (minas gerais)": "america mg",
    "america fc minas gerais": "america mg",
    "sport club corinthians paulista": "corinthians",
    "sao paulo fc": "sao paulo",
    "se palmeiras": "palmeiras",
    "red bull bragantino": "bragantino",
    "rb bragantino": "bragantino",
}


def fold_accents(text: str) -> str:
    """Return ``text`` with accents removed (NFKD ASCII fold)."""
    if text is None:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _split_suffix(name: str):
    """Split ``name`` into ``(base, code)`` where ``code`` is the trailing
    state/country abbreviation (upper-cased) or '' when none is present.
    """
    if name is None:
        return "", ""
    cleaned = name.strip()

    # Parenthetical country/region code, e.g. "Nacional (URU)".
    m = re.search(r"\s*\(([A-Za-z]{2,4})\)\s*$", cleaned)
    if m:
        return cleaned[: m.start()].strip(), m.group(1).upper()

    # Trailing " - XX" / "-XX" where XX is a 2-3 letter code.
    m = re.search(r"\s*-\s*([A-Za-z]{2,3})\s*$", cleaned)
    if m:
        code = m.group(1).upper()
        if code in _STATE_CODES or len(code) in (2, 3):
            return cleaned[: m.start()].strip(), code

    return cleaned, ""


def strip_suffix(name: str) -> str:
    """Return ``name`` with any trailing state/country code removed."""
    base, _ = _split_suffix(name)
    return base or (name or "").strip()


def _fold_base(base: str) -> str:
    folded = fold_accents(base).lower()
    folded = re.sub(r"[.’']", "", folded)
    folded = re.sub(r"\s+", " ", folded).strip()
    # Spelling unification: "Athletico" -> "Atletico".
    folded = folded.replace("athletico", "atletico")
    return folded


def normalize_team(name: str) -> str:
    """Return the canonical lookup key for a team name (see module docstring)."""
    if name is None:
        return ""
    base, code = _split_suffix(name)
    folded = _fold_base(base)

    # Direct alias on the folded base (handles full/long names).
    if folded in ALIASES:
        return ALIASES[folded]
    # Alias on the folded base WITH its code re-attached (e.g. handles inputs
    # already carrying a suffix that an alias also covers).
    if code and f"{folded} {code.lower()}" in ALIASES.values():
        return f"{folded} {code.lower()}"

    if folded in AMBIGUOUS_BASES and code:
        return f"{folded} {code.lower()}"
    return folded


def display_name(name: str) -> str:
    """Human-readable team name.

    Accents are preserved. The state/country suffix is kept for ambiguous base
    names (so 'Atlético-MG' stays distinguishable) and dropped otherwise.
    """
    base, code = _split_suffix(name)
    folded = _fold_base(base)
    if code and folded in AMBIGUOUS_BASES:
        return f"{base}-{code}"
    return base or (name or "").strip()


def names_match(a: str, b: str) -> bool:
    """True when two raw team names refer to the same canonical team."""
    return normalize_team(a) == normalize_team(b)
