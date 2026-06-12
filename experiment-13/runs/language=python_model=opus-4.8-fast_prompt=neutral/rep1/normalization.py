"""
================================================================================
Module: normalization.py
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
CONTEXT
-------
Brazilian soccer datasets use many different conventions for the same team:

    "Palmeiras-SP"      (state suffix, hyphen)
    "Palmeiras"         (bare)
    "Sao Paulo"         (ASCII)
    "São Paulo"         (UTF-8 accents)
    "América - MG"      (spaced state suffix)
    "Nacional (URU)"    (country code in parentheses)

To answer natural-language questions such as "Show me all Flamengo matches" we
must collapse these variants onto a single canonical key so that the same club
matches regardless of how it is spelled in a given CSV file.

This module provides two pure functions:

  * ``strip_accents``      - remove diacritics (São -> Sao, Grêmio -> Gremio)
  * ``normalize_team_name``- produce a lowercase, accent-free, suffix-free key
                             used for *matching* (e.g. "flamengo")
  * ``clean_display_name`` - produce a human-friendly display name that keeps
                             accents/case but drops noisy suffixes
  * ``team_matches``       - test whether a user query refers to a team cell

Design choice: normalization is intentionally *conservative*.

  * We strip accents, lowercase, drop parenthetical country codes and punctuation.
  * We DO keep the trailing state code as a separate word ("atletico mg"),
    because in Brazil the state suffix disambiguates genuinely different clubs
    that share a base name: Atlético-MG vs Atlético-GO vs Athletico-PR, or
    América-MG vs América-RN.  Stripping it would merge them.

A bare query such as "Flamengo" still matches the stored key "flamengo rj"
because :func:`team_matches` uses whole-word containment, so the extra trailing
state word does not block the match.  This gives us the best of both: precise
identity for state-suffixed clubs, and forgiving matching for casual queries.
================================================================================
"""

from __future__ import annotations

import re
import unicodedata

# The 27 Brazilian federative units (states + Distrito Federal). These appear as
# suffixes such as "Palmeiras-SP". Lower-cased for comparison after stripping.
BRAZILIAN_STATES = {
    "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms",
    "mg", "pa", "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc",
    "sp", "se", "to",
}

_PAREN_RE = re.compile(r"\(.*?\)")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9 ]+")
_WS_RE = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    """Return *text* with all combining diacritical marks removed."""
    if text is None:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(text))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_team_name(name: str) -> str:
    """Canonical matching key for a team name.

    Steps: strip accents -> lowercase -> drop parenthetical codes -> replace
    punctuation with spaces -> collapse whitespace.  The trailing state code is
    kept (as a separate word) because it disambiguates distinct clubs.

    Examples
    --------
    >>> normalize_team_name("Palmeiras-SP")
    'palmeiras sp'
    >>> normalize_team_name("São Paulo")
    'sao paulo'
    >>> normalize_team_name("Nacional (URU)")
    'nacional'
    >>> normalize_team_name("América - MG")
    'america mg'
    """
    if name is None:
        return ""
    text = strip_accents(name).lower()
    text = _PAREN_RE.sub(" ", text)          # remove "(uru)", "(antigo ...)"
    text = text.replace("-", " ")
    text = _NON_ALNUM_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    return text


def clean_display_name(name: str) -> str:
    """Human-friendly team name: keeps accents/case, tidies the state suffix.

    Removes parenthetical codes and normalises a trailing state suffix to the
    compact ``Name-UF`` form, while preserving the original capitalisation and
    accents.  The state is kept (not dropped) so that distinct clubs sharing a
    base name remain distinguishable in output.

    >>> clean_display_name("Flamengo-RJ")
    'Flamengo-RJ'
    >>> clean_display_name("América - MG")
    'América-MG'
    >>> clean_display_name("Nacional (URU)")
    'Nacional'
    """
    if name is None:
        return ""
    text = _PAREN_RE.sub("", str(name)).strip()
    # Normalise a trailing " - UF" / " UF" state suffix to "-UF".
    m = re.search(r"[\s\-]+([A-Za-z]{2})$", text)
    if m and m.group(1).lower() in BRAZILIAN_STATES:
        text = text[: m.start()] + "-" + m.group(1).upper()
    return _WS_RE.sub(" ", text).strip()


def _contains_word(haystack: str, needle: str) -> bool:
    """True if *needle* occurs as a whole word-sequence inside *haystack*."""
    return re.search(rf"\b{re.escape(needle)}\b", haystack) is not None


def team_matches(query: str, cell: str) -> bool:
    """Return True if user *query* refers to the team named in *cell*.

    Matching is bidirectional whole-word containment, so it is forgiving of the
    state-suffix variation in both directions:

      * "flamengo"     matches "Flamengo-RJ"   (bare query  -> suffixed cell)
      * "Flamengo-RJ"  matches "Flamengo"      (suffixed query -> bare cell)
      * "vasco"        matches "Vasco da Gama"

    while still keeping distinct clubs apart:

      * "Atletico-MG"  does NOT match "Atletico-GO"
    """
    nq = normalize_team_name(query)
    nc = normalize_team_name(cell)
    if not nq or not nc:
        return False
    return nq == nc or _contains_word(nc, nq) or _contains_word(nq, nc)
