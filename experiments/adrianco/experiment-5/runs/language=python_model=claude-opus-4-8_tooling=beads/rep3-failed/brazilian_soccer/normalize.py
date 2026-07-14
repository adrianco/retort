"""
================================================================================
Context: Brazilian Soccer MCP Server
Module:   brazilian_soccer.normalize
--------------------------------------------------------------------------------
Purpose:
    Pure helpers that turn the messy, inconsistent text in the raw CSV files
    into stable, comparable values. Two problems are solved here:

      1. Team-name variation. The datasets refer to the same club in many ways:
            "Palmeiras-SP", "Palmeiras", "Nacional (URU)",
            "Boavista Sport Club (antigo ...) - RJ"
         normalize_team() produces a clean display name, and team_key()
         produces an accent-free, suffix-free lowercase key used for matching.

      2. Date variation. Dates appear as ISO ("2023-09-24"), ISO+time
            ("2012-05-19 18:30:00") and Brazilian ("29/03/2003").
         parse_date() returns a datetime.date for any of these (or None).

Dependencies: standard library only (re, unicodedata, datetime).
================================================================================
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

# Two-letter Brazilian state codes used as suffixes, plus common country tags
# that appear in the Libertadores file (e.g. "Nacional (URU)").
_STATE_CODES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

# Parenthetical country tags from Libertadores ("(URU)", "(ARG)", "-EQU" ...).
_PAREN_TAG_RE = re.compile(r"\s*\(([^)]*)\)\s*")
# Trailing " - XX" or "-XX" state/country suffix.
_TRAILING_SUFFIX_RE = re.compile(r"\s*-\s*([A-Za-z]{2,4})\s*$")
_WHITESPACE_RE = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    """Return ``text`` with diacritics removed (São -> Sao, Grêmio -> Gremio)."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_team(raw: str) -> str:
    """Return a clean human-readable team name.

    Removes parenthetical tags and a trailing state/country code, collapses
    whitespace, but keeps accents and original casing for display.
    """
    if raw is None:
        return ""
    name = raw.strip().strip('"').strip()
    # Drop parenthetical tags such as "(URU)" or "(antigo ...)".
    name = _PAREN_TAG_RE.sub(" ", name)
    name = _WHITESPACE_RE.sub(" ", name).strip()
    # Drop a trailing "-SP" / " - RJ" / "-EQU" suffix when the tail looks like a
    # state or country code (2-4 letters) rather than part of the club name.
    m = _TRAILING_SUFFIX_RE.search(name)
    if m:
        tail = m.group(1).upper()
        if tail in _STATE_CODES or len(tail) == 3:  # 3 = country code (EQU, URU)
            name = name[: m.start()].strip()
    return name


def team_key(raw: str) -> str:
    """Return the canonical match key for a team name.

    Accent-free, suffix-free, lowercase, single-spaced. Two raw spellings of
    the same club collapse to the same key, which is what every team index in
    the knowledge graph is keyed on.
    """
    return _WHITESPACE_RE.sub(" ", strip_accents(normalize_team(raw)).lower()).strip()


def parse_date(raw: str) -> date | None:
    """Parse the several date formats found across the datasets.

    Handles ISO, ISO+time and Brazilian DD/MM/YYYY. Returns ``None`` when the
    value is empty or unrecognisable rather than raising.
    """
    if not raw:
        return None
    text = str(raw).strip().strip('"')
    if not text:
        return None
    # Keep just the date portion if a time component is present.
    date_part = text.split(" ")[0].split("T")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_part, fmt).date()
        except ValueError:
            continue
    return None


def to_int(raw) -> int | None:
    """Best-effort integer parse (handles "2", "2.0", floats, blanks)."""
    if raw is None or raw == "":
        return None
    try:
        return int(float(str(raw).strip().strip('"')))
    except (ValueError, TypeError):
        return None
