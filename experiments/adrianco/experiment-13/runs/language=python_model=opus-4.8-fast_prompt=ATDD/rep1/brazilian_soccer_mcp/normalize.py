"""
Context
=======
Team-name and text normalization for the Brazilian Soccer MCP server.

The provided datasets name the same team in many ways:
  * with a state suffix       -> "Palmeiras-SP", "Flamengo-RJ", "Grêmio - RS"
  * with a country suffix      -> "Nacional (URU)", "Boca Juniors (ARG)"
  * with embedded parentheses  -> "Boavista Sport Club (antigo ...) - RJ"
  * with full club names       -> "Sport Club Corinthians Paulista"
  * with / without accents     -> "São Paulo" vs "Sao Paulo"

``normalize_team`` returns a clean *display* name (accents preserved). ``key``
returns an accent-insensitive, case-insensitive comparison key so that user
queries match regardless of how the team is spelled in the data. A small alias
table folds well-known full names onto their common short form.
"""

from __future__ import annotations

import re
import unicodedata

# Trailing " - SP", "-SP" style state suffixes (capture the 2-letter UF).
_STATE_SUFFIX = re.compile(r"\s*-\s*([A-Za-z]{2})\s*$")

# Base names shared by several distinct clubs in different states. For these the
# state suffix is meaningful (Atlético-MG vs Atlético-PR are different clubs), so
# it is retained — in a normalized "Base-UF" form — instead of being stripped.
_AMBIGUOUS_BASES = {"atletico", "america", "nacional"}
# Any parenthetical group, e.g. "(URU)", "(antigo ...)".
_PARENS = re.compile(r"\s*\([^)]*\)")
_WS = re.compile(r"\s+")

# Canonical short names for well-known clubs that appear under long names.
# Keys are comparison keys (see ``key``) of the long form.
_ALIASES = {
    "sport club corinthians paulista": "Corinthians",
    "sociedade esportiva palmeiras": "Palmeiras",
    "clube de regatas do flamengo": "Flamengo",
    "sao paulo futebol clube": "São Paulo",
    "fluminense football club": "Fluminense",
    "santos futebol clube": "Santos",
    "gremio foot-ball porto alegrense": "Grêmio",
}


def strip_accents(text: str) -> str:
    """Return ``text`` with diacritics removed (São -> Sao, Grêmio -> Gremio)."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def normalize_team(raw: str) -> str:
    """Return a clean display name for a raw team string from the data.

    Removes parenthetical groups and trailing state suffixes, collapses
    whitespace, and folds known long names onto their canonical short form.
    """
    if raw is None:
        return ""
    name = _PARENS.sub("", str(raw))
    match = _STATE_SUFFIX.search(name)
    uf = match.group(1).upper() if match else None
    base = _WS.sub(" ", _STATE_SUFFIX.sub("", name)).strip()
    if uf and key(base) in _AMBIGUOUS_BASES:
        name = f"{base}-{uf}"
    else:
        name = base
    alias = _ALIASES.get(key(name))
    return alias if alias else name


def key(name: str) -> str:
    """Return the accent/case-insensitive comparison key for a (display) name."""
    return _WS.sub(" ", strip_accents(str(name)).lower()).strip()


def team_key(raw: str) -> str:
    """Comparison key for a *raw* team string (normalize first, then key)."""
    return key(normalize_team(raw))
