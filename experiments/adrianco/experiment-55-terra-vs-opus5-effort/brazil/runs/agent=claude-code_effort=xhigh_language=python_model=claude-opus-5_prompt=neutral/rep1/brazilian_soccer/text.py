"""
Unicode, date and number helpers.

Context
-------
The six Kaggle CSVs disagree about almost every surface detail, and TASK.md
calls those out explicitly under "Data Quality Notes":

* Accents / cedillas -- "Sao Paulo" vs "São Paulo", "Gremio" vs "Grêmio".
* Punctuation noise -- "A.b.c. - RN", "C. R. B. - AL", "Rentistas " (trailing
  space), "América FC (Minas Gerais)".
* State / country qualifiers written four different ways -- "Palmeiras-SP",
  "América - MG", "America MG", "Nacional (URU)".
* Three date formats -- ``2023-09-24``, ``29/03/2003`` and
  ``2012-05-19 18:30:00``; plus the literal ``NA`` for unknown values.
* Numbers stored as ``"2"``, ``2.0`` or ``NA``.

Everything in this module is pure and side-effect free so it can be unit tested
in isolation; the club-identity logic that builds on it lives in
:mod:`brazilian_soccer.teams`.
"""

from __future__ import annotations

import datetime as dt
import re
import unicodedata
from typing import Iterable

__all__ = [
    "BRAZILIAN_STATES",
    "COUNTRY_CODES",
    "STATE_NAME_TO_CODE",
    "strip_accents",
    "fold",
    "normalize_name",
    "tokenize",
    "slugify",
    "split_qualifier",
    "parse_date",
    "parse_time",
    "parse_int",
    "parse_float",
    "is_missing",
    "titleize",
]

#: The 26 Brazilian states plus the Federal District.
BRAZILIAN_STATES: frozenset[str] = frozenset(
    """AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO""".split()
)

#: Country codes used by the Libertadores dataset for non-Brazilian clubs.
COUNTRY_CODES: frozenset[str] = frozenset(
    """ARG BOL BRA CHI COL ECU EQU MEX PAR PER URU VEN USA CRC HON PAN""".split()
)

#: The Libertadores file writes Ecuador as ``EQU``; fold it onto the ISO code
#: so ``"Delfín-EQU"`` and a curated ``ECU`` spec describe the same club.
QUALIFIER_SYNONYMS: dict[str, str] = {"EQU": "ECU", "PAR": "PAR", "URU": "URU"}

STATE_NAME_TO_CODE: dict[str, str] = {
    "acre": "AC",
    "alagoas": "AL",
    "amapa": "AP",
    "amazonas": "AM",
    "bahia": "BA",
    "ceara": "CE",
    "distrito federal": "DF",
    "espirito santo": "ES",
    "goias": "GO",
    "maranhao": "MA",
    "mato grosso": "MT",
    "mato grosso do sul": "MS",
    "minas gerais": "MG",
    "para": "PA",
    "paraiba": "PB",
    "parana": "PR",
    "pernambuco": "PE",
    "piaui": "PI",
    "rio de janeiro": "RJ",
    "rio grande do norte": "RN",
    "rio grande do sul": "RS",
    "rondonia": "RO",
    "roraima": "RR",
    "santa catarina": "SC",
    "sao paulo": "SP",
    "sergipe": "SE",
    "tocantins": "TO",
}

#: Values that every dataset uses to mean "no data".
_MISSING_TOKENS = frozenset({"", "na", "n/a", "nan", "none", "null", "-", "--", "?"})

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_WHITESPACE = re.compile(r"\s+")
#: Apostrophes join rather than split, so "Newell's" -> "newells" and
#: "O'Higgins" -> "ohiggins" instead of leaving a stray one-letter token.
_APOSTROPHES = re.compile(r"['‘’ʼ`]")


def is_missing(value: object) -> bool:
    """True when ``value`` is one of the many spellings of "no data"."""

    if value is None:
        return True
    if isinstance(value, float) and value != value:  # NaN
        return True
    return str(value).strip().lower() in _MISSING_TOKENS


def strip_accents(text: str) -> str:
    """Remove diacritics: ``"Grêmio" -> "Gremio"``, ``"Avaí" -> "Avai"``."""

    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def fold(text: str) -> str:
    """Lowercase + accent-strip, preserving spacing and punctuation."""

    return strip_accents(text).lower()


def tokenize(text: str) -> list[str]:
    """Split ``text`` into lowercase, accent-free alphanumeric tokens.

    Runs of two or more single-character tokens are glued back together so that
    ``"A.b.c."`` and ``"C. R. B."`` normalise to ``"abc"`` and ``"crb"`` -- both
    spellings occur in the Copa do Brasil dataset alongside ``"ABC"``/``"CRB"``.
    """

    raw = [tok for tok in _NON_ALNUM.split(_APOSTROPHES.sub("", fold(text))) if tok]
    merged: list[str] = []
    index = 0
    while index < len(raw):
        if len(raw[index]) == 1:
            run_end = index
            while run_end < len(raw) and len(raw[run_end]) == 1:
                run_end += 1
            if run_end - index >= 2:
                merged.append("".join(raw[index:run_end]))
                index = run_end
                continue
        merged.append(raw[index])
        index += 1
    return merged


def normalize_name(text: str) -> str:
    """Canonical whitespace-joined token form used as a dictionary key."""

    return " ".join(tokenize(text))


def slugify(text: str, *, separator: str = "-") -> str:
    """URL/id friendly form: ``"São Paulo-SP" -> "sao-paulo-sp"``."""

    return separator.join(tokenize(text))


def _qualifier_from(candidate: str) -> str | None:
    """Map a trailing token to a state/country code, or ``None``."""

    stripped = candidate.strip()
    if not stripped:
        return None
    upper = strip_accents(stripped).upper()
    upper = QUALIFIER_SYNONYMS.get(upper, upper)
    if upper in BRAZILIAN_STATES or upper in COUNTRY_CODES:
        return upper
    return STATE_NAME_TO_CODE.get(normalize_name(stripped))


# "Palmeiras-SP", "América - MG", "Barcelona-EQU"
_DASH_SUFFIX = re.compile(r"\s*[-‐-―]\s*([A-Za-zÀ-ſ]{2,3})\s*$")
# "America MG", "Botafogo RJ" (upper-case only, to avoid eating real words)
_SPACE_SUFFIX = re.compile(r"\s+([A-Z]{2,3})\s*$")
# "Nacional (URU)", "América FC (Minas Gerais)", "Boavista SC (antigo ...)"
_PAREN_SUFFIX = re.compile(r"\s*\(([^()]*)\)\s*$")


def split_qualifier(name: str) -> tuple[str, str | None]:
    """Split a club name into ``(base name, state/country code)``.

    The four spellings seen in the data all collapse to the same result::

        >>> split_qualifier("Palmeiras-SP")
        ('Palmeiras', 'SP')
        >>> split_qualifier("América - MG")
        ('América', 'MG')
        >>> split_qualifier("America MG")
        ('America', 'MG')
        >>> split_qualifier("Nacional (URU)")
        ('Nacional', 'URU')

    Parentheticals that are *not* a place ("(antigo Esporte Clube Barreira)")
    are dropped as editorial noise.  Names without a qualifier are returned
    unchanged with ``None``.
    """

    current = name.strip()
    qualifier: str | None = None

    changed = True
    while changed and current:
        changed = False

        match = _PAREN_SUFFIX.search(current)
        if match:
            found = _qualifier_from(match.group(1))
            remainder = current[: match.start()].strip()
            if remainder:
                qualifier = qualifier or found
                current = remainder
                changed = True
                continue

        for pattern in (_DASH_SUFFIX, _SPACE_SUFFIX):
            match = pattern.search(current)
            if not match:
                continue
            found = _qualifier_from(match.group(1))
            if found is None:
                continue
            remainder = current[: match.start()].strip()
            if not remainder:
                continue
            qualifier = qualifier or found
            current = remainder
            changed = True
            break

    return (current.strip() or name.strip(), qualifier)


_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
    "%d/%m/%y",
    "%Y/%m/%d",
    "%d-%m-%Y",
)


def parse_date(value: object) -> dt.date | None:
    """Parse the ISO, Brazilian and datetime formats found in the CSVs."""

    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if is_missing(value):
        return None
    text = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    # Last resort: ISO parser handles offsets and "T" separators.
    try:
        return dt.datetime.fromisoformat(text).date()
    except ValueError:
        return None


_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})(?::(\d{2}))?")


def parse_time(value: object) -> str | None:
    """Extract a ``HH:MM`` kick-off time from a date-time or time string."""

    if is_missing(value):
        return None
    match = _TIME_RE.search(str(value))
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return f"{hour:02d}:{minute:02d}"


def parse_int(value: object) -> int | None:
    """Parse ``"2"``, ``2.0``, ``" 3 "``; return ``None`` for ``NA``/``""``."""

    if is_missing(value):
        return None
    try:
        return int(round(float(str(value).strip())))
    except (TypeError, ValueError):
        return None


def parse_float(value: object) -> float | None:
    """Parse a float, returning ``None`` for the many "missing" spellings."""

    if is_missing(value):
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


_SMALL_WORDS = frozenset({"de", "da", "do", "das", "dos", "e", "of", "the"})


def titleize(text: str) -> str:
    """Title-case a club name written entirely in one case.

    Portuguese particles stay lowercase ("Vasco da Gama") and short all-caps
    tokens are treated as acronyms and left alone, because several Brazilian
    clubs *are* acronyms: ABC, CRB, CSA, CRAC, ASA.  Words that are already
    mixed case are never touched.
    """

    words = _WHITESPACE.split(text.strip())
    out: list[str] = []
    for index, word in enumerate(words):
        lowered = word.lower()
        if index and lowered in _SMALL_WORDS:
            out.append(lowered)
        elif word.isupper() and len(word) <= 4:
            out.append(word)
        elif word.isupper() or word.islower():
            out.append(word.capitalize())
        else:
            out.append(word)
    return " ".join(out)


def unique(items: Iterable[str]) -> list[str]:
    """Order-preserving de-duplication (used for alias lists)."""

    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
