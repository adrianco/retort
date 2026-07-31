"""Text, name, date and number normalisation helpers.

Context
-------
The six Kaggle CSV files that back this MCP server were produced by different
people at different times and disagree about almost every surface detail:

* Team names appear as ``"Palmeiras-SP"``, ``"América - MG"``, ``"America MG"``,
  ``"Sport Club do Recife"`` and ``"A.b.c. - RN"``.
* Dates appear as ``"2023-09-24"``, ``"2012-05-19 18:30:00"``, ``"29/03/2003"``
  and occasionally as the literal string ``"NA"``.
* Scores appear as ``"2"``, ``"2.0"``, ``"-"`` and ``""``.

Everything downstream (loaders, knowledge graph, query layer) assumes it is
working with already-normalised values, so this module is the single place
where the messiness is absorbed.  It deliberately has no dependencies beyond
the standard library.
"""

from __future__ import annotations

import datetime as _dt
import re
import unicodedata
from typing import Iterable

__all__ = [
    "BRAZILIAN_STATES",
    "strip_accents",
    "normalize_text",
    "name_variants",
    "split_state_suffix",
    "slugify",
    "parse_date",
    "parse_int",
    "parse_float",
    "parse_season",
]


#: The 26 Brazilian states plus the Federal District.  Used to recognise (and
#: strip) the state suffix that several datasets append to club names.
BRAZILIAN_STATES = frozenset(
    """ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn
       rs ro rr sc sp se to""".split()
)

#: Tokens that carry no discriminating information in Brazilian club names.
#: ``Esporte Clube Bahia``/``EC Bahia``/``Bahia`` must all collapse to the same
#: base name.  Note that these are only stripped as a *fallback* -- an exact
#: alias match is always tried first so that e.g. ``Sport Recife`` survives.
FILLER_TOKENS = frozenset(
    """ec fc sc se ac cr cf clube club de do da das dos e
       esporte esportivo esportiva futebol futbol regatas recreativo
       sociedade associacao sporting""".split()
)

_COMBINING = unicodedata.combining
_PARENS_RE = re.compile(r"\(.*?\)")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_INITIALISM_RE = re.compile(r"(?<![a-z0-9])(?:[a-z]\.){2,}", re.IGNORECASE)


def strip_accents(text: str) -> str:
    """Return *text* with combining accents removed (``Grêmio`` -> ``Gremio``).

    The CSV files are UTF-8 and full of ``ã``/``é``/``ç``; comparing names only
    works reliably once the diacritics are folded away.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not _COMBINING(ch))


def normalize_text(text: str, *, drop_parentheticals: bool = True) -> str:
    """Fold *text* to a lowercase, accent-free, punctuation-free token string.

    ``"Boavista Sport Club (antigo EC Barreira) - RJ"`` becomes
    ``"boavista sport club rj"``.
    """
    if text is None:
        return ""
    value = str(text)
    if drop_parentheticals:
        value = _PARENS_RE.sub(" ", value)
    value = strip_accents(value).lower()
    value = _NON_ALNUM_RE.sub(" ", value)
    return " ".join(value.split())


def name_variants(text: str) -> list[str]:
    """Return the plausible normalised spellings of *text*, most specific first.

    Two transformations matter:

    * Parentheses often carry the only distinguishing information -- the
      Libertadores file writes ``"Nacional (URU)"`` and ``"Nacional-URU"`` for
      the same club, and ``"Nacional (PAR)"`` for a different one.  The
      parenthesis-preserving spelling is therefore emitted *first* so an alias
      table can claim it before the ambiguous bare form is tried.
    * Datasets abbreviate clubs both as ``"ABC - RN"`` and ``"A.b.c. - RN"``.
      Replacing punctuation with spaces turns the latter into ``"a b c"``,
      so a variant with dotted initialisms glued back together is emitted too.
    """
    if not text:
        return [""]
    variants: list[str] = []
    glued = _INITIALISM_RE.sub(lambda m: m.group(0).replace(".", ""), str(text))
    for candidate in (glued, str(text)):
        norm = normalize_text(candidate, drop_parentheticals=False)
        if norm and norm not in variants:
            variants.append(norm)
    for candidate in (glued, str(text)):
        norm = normalize_text(candidate)
        if norm and norm not in variants:
            variants.append(norm)
    return variants or [""]


def split_state_suffix(normalized: str) -> tuple[str, str | None]:
    """Split a trailing two-letter state code off an already-normalised name.

    >>> split_state_suffix("palmeiras sp")
    ('palmeiras', 'sp')
    >>> split_state_suffix("santos")
    ('santos', None)
    """
    tokens = normalized.split()
    if len(tokens) > 1 and tokens[-1] in BRAZILIAN_STATES:
        return " ".join(tokens[:-1]), tokens[-1]
    return " ".join(tokens), None


def drop_filler(normalized: str) -> str:
    """Remove club-type filler tokens, keeping the result non-empty."""
    tokens = [t for t in normalized.split() if t not in FILLER_TOKENS]
    return " ".join(tokens) if tokens else normalized


def slugify(*parts: Iterable[str] | str) -> str:
    """Build a stable ``kebab-case`` identifier from the given parts."""
    flat: list[str] = []
    for part in parts:
        if part is None:
            continue
        if isinstance(part, str):
            flat.append(part)
        else:  # pragma: no cover - defensive, callers pass strings today
            flat.extend(str(p) for p in part)
    joined = normalize_text(" ".join(p for p in flat if p))
    return "-".join(joined.split())


_DATE_PATTERNS = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d/%m/%y",
    "%b %d, %Y",
)

_MISSING = frozenset({"", "-", "na", "n/a", "nan", "none", "null", "?"})


def parse_date(value: str | None) -> _dt.date | None:
    """Parse the several date spellings used across the datasets.

    Handles ISO dates, ISO datetimes, Brazilian ``DD/MM/YYYY`` and the FIFA
    ``"Jul 1, 2004"`` style.  Returns ``None`` for missing/sentinel values
    rather than raising, because a handful of rows genuinely have no date.
    """
    if value is None:
        return None
    text = str(value).strip().strip('"')
    if text.lower() in _MISSING:
        return None
    # Datetime columns are "YYYY-MM-DD HH:MM:SS"; keep only the date part.
    head = text.split(" ")[0] if re.match(r"^\d{4}-\d{2}-\d{2}[ T]", text) else text
    for pattern in _DATE_PATTERNS:
        try:
            return _dt.datetime.strptime(head, pattern).date()
        except ValueError:
            continue
    try:
        return _dt.datetime.fromisoformat(text).date()
    except ValueError:
        return None


def parse_time(value: str | None) -> str | None:
    """Extract a ``HH:MM`` kick-off time from a datetime or time column."""
    if value is None:
        return None
    text = str(value).strip().strip('"')
    if text.lower() in _MISSING:
        return None
    match = re.search(r"(\d{1,2}):(\d{2})", text)
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def parse_int(value: str | None) -> int | None:
    """Parse an integer that may be written as ``"2"``, ``"2.0"``, ``"-"`` ..."""
    if value is None:
        return None
    if isinstance(value, (int,)) and not isinstance(value, bool):
        return int(value)
    text = str(value).strip().strip('"')
    if text.lower() in _MISSING:
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return int(float(text))
    except ValueError:
        return None


def parse_float(value: str | None) -> float | None:
    """Parse a float, tolerating the same sentinels as :func:`parse_int`."""
    if value is None:
        return None
    text = str(value).strip().strip('"')
    if text.lower() in _MISSING:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_season(value: str | None) -> int | None:
    """Parse a season year, accepting ``2019``, ``"2019"`` and ``"2019/20"``."""
    if value is None:
        return None
    text = str(value).strip().strip('"')
    if text.lower() in _MISSING:
        return None
    match = re.search(r"(19|20)\d{2}", text)
    return int(match.group(0)) if match else None
