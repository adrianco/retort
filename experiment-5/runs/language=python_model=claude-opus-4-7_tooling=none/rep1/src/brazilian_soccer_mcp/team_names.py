"""Team name normalization for the Brazilian soccer datasets.

The CSV files use different naming conventions for the same team:
"Palmeiras-SP", "Palmeiras", "Sao Paulo", "São Paulo", "Athletico-PR".
``normalize`` collapses these variants to a stable key for matching.
"""

from __future__ import annotations

import re
import unicodedata

_STATE_SUFFIX_RE = re.compile(
    r"\s*[-/]\s*(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|"
    r"RN|RS|RO|RR|SC|SP|SE|TO|URU|EQU|ARG|COL|CHI|BOL|PER|VEN|MEX|PAR)\s*$",
    re.IGNORECASE,
)
_PAREN_RE = re.compile(r"\s*\([^)]*\)\s*$")
_WS_RE = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    """Remove accents/diacritics from text."""
    if not isinstance(text, str):
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def normalize(name: str) -> str:
    """Normalize a team name to a comparable key.

    Keeps state suffixes so that Atlético-MG and Atlético-PR stay distinct.
    Lowercases, strips accents, drops parenthetical annotations, and
    collapses whitespace. Use :func:`loose_key` for dedup/search where
    "Palmeiras" and "Palmeiras-SP" should fold together.
    """
    if name is None:
        return ""
    s = str(name).strip()
    if not s:
        return ""
    s = _PAREN_RE.sub("", s)
    s = strip_accents(s).lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


_STATE_TOKEN_RE = re.compile(
    r"\b(ac|al|ap|am|ba|ce|df|es|go|ma|mt|ms|mg|pa|pb|pr|pe|pi|rj|"
    r"rn|rs|ro|rr|sc|sp|se|to|uru|equ|arg|col|chi|bol|per|ven|mex|par)\b"
)


_ALIASES = {
    "athletico": "atletico",
    "atlhetico": "atletico",
    "vasco da gama": "vasco",
    "atletico mineiro": "atletico",  # only safe as a loose alias when paired with "mg" elimination
    "atletico paranaense": "atletico",
    "america mineiro": "america",
    "gremio prudente": "gremio",
}


def loose_key(name: str) -> str:
    """A coarser key that also strips state suffix tokens and filler words.

    Useful for matching variants like "Palmeiras" / "Palmeiras-SP" /
    "Sport Club Corinthians Paulista" to a single identity. Applies a
    small alias table for known spelling variants.
    """
    s = normalize(name)
    if not s:
        return ""
    s = re.sub(r"\b(esporte clube|sport club|futebol clube|clube|fc|sc|ec)\b", " ", s)
    s = _STATE_TOKEN_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    for variant, canonical in _ALIASES.items():
        if variant in s:
            s = s.replace(variant, canonical)
    s = _WS_RE.sub(" ", s).strip()
    return s


def _state_tokens(text: str) -> set[str]:
    return set(_STATE_TOKEN_RE.findall(text))


def matches(query: str, name: str) -> bool:
    """Return True when a query loosely matches a team name.

    Refuses to match when both sides carry distinct state-suffix tokens
    (so "Atletico-MG" does not match "Atletico-PR").
    """
    q = normalize(query)
    n = normalize(name)
    if q and n and (q == n or q in n or n in q):
        return True
    q_states = _state_tokens(q)
    n_states = _state_tokens(n)
    if q_states and n_states and q_states.isdisjoint(n_states):
        return False
    lq, ln = loose_key(query), loose_key(name)
    if lq and ln and (lq == ln or lq in ln or ln in lq):
        return True
    return False
