"""Normalization helpers for team names, dates, numbers and text matching.

The source CSVs disagree on how a team is written ("Palmeiras-SP",
"Boavista Sport Club (antigo ...) - RJ", "Sport Club Corinthians Paulista")
and on how dates are formatted. Everything that touches those values goes
through this module so the rest of the code can compare plain keys.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

_PARENTHESES = re.compile(r"\([^)]*\)")
_STATE_SUFFIX = re.compile(r"\s*-\s*[A-Za-z]{2,3}$")
_SPACED_STATE = re.compile(r"\s+[A-Z]{2}$")
_CLUB_AFFIX = re.compile(r"(^(EC|FC|SC|AC)\s+)|(\s+(EC|FC|SC|AC)$)")
_NON_ALNUM = re.compile(r"[^a-z0-9]")
_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y")

# Full legal/long names mapped to the short key used everywhere else.
# Keys are produced by ``team_key`` (accent-free, lowercase, alphanumeric).
TEAM_ALIASES = {
    "sportclubcorinthianspaulista": "corinthians",
    "sociedadeesportivapalmeiras": "palmeiras",
    "clubederegatasdoflamengo": "flamengo",
    "saopaulofutebolclube": "saopaulo",
    "athleticoparanaense": "athletico",
    "atleticoparanaense": "athletico",
    "atleticomineiro": "atletico",
    "vasco": "vascodagama",
}
# Same spelling, different clubs: resolved by the state code where known.
STATE_ALIASES = {
    ("atletico", "PR"): "athletico",
}


def strip_accents(text: str) -> str:
    """Return ``text`` with combining accents removed (São -> Sao)."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def display_name(raw: str) -> str:
    """Team name without state suffix or parenthesised notes.

    ``"Palmeiras-SP"`` -> ``"Palmeiras"``;
    ``"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"`` ->
    ``"Boavista Sport Club"``; ``"Vasco Da Gama RJ"`` -> ``"Vasco Da Gama"``;
    ``"EC Bahia"`` -> ``"Bahia"``.
    """
    name = _PARENTHESES.sub("", raw).strip()
    name = _STATE_SUFFIX.sub("", name).strip()
    name = _SPACED_STATE.sub("", name).strip()
    name = _CLUB_AFFIX.sub("", name).strip()
    return re.sub(r"\s+", " ", name)


def state_of(raw: str) -> str | None:
    """Two-letter state code from a ``Name-UF`` suffix, if present."""
    match = re.search(r"-\s*([A-Za-z]{2})$", raw.strip())
    return match.group(1).upper() if match else None


def team_key(raw: str, state: str | None = None) -> str:
    """Stable matching key for a team name, identical across data sources.

    ``state`` (a UF code from a separate column) disambiguates clubs that share
    a name, e.g. Atlético-MG and Athletico-PR, which both appear as "Atletico".
    """
    base = _NON_ALNUM.sub("", strip_accents(display_name(raw)).casefold())
    uf = (state or state_of(raw) or "").upper()
    if (base, uf) in STATE_ALIASES:
        return STATE_ALIASES[(base, uf)]
    return TEAM_ALIASES.get(base, base)


def normalize_text(text: str) -> str:
    """Accent-insensitive, case-insensitive text used for substring search."""
    return strip_accents(text).casefold().strip()


def parse_date(raw: str) -> date:
    """Parse ISO dates, ISO datetimes and Brazilian ``DD/MM/YYYY`` dates.

    Raises ``ValueError`` for placeholders such as ``"NA"`` so callers can skip
    unplayed or unknown fixtures.
    """
    text = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date: {raw!r}")


def parse_int(raw: str | None) -> int | None:
    """Parse ``"2"``, ``"2.0"`` or ``"3"`` to int; anything else is ``None``."""
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None
