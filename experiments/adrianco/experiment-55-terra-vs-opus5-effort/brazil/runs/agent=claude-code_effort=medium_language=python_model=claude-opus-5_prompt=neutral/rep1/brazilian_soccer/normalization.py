"""Canonicalisation helpers for messy Brazilian football data.

Context
-------
The six source CSVs disagree about almost everything textual.  The same club
shows up as ``Palmeiras``, ``Palmeiras-SP`` and ``Palmeiras - SP``; ``Atletico
Mineiro``, ``Atlético-MG`` and ``Atlético - MG``; ``A.b.c. - RN`` and ``ABC``.
Dates are ISO, ISO+time or ``DD/MM/YYYY``.  Goals are ints in one file and
quoted strings in another.

This module turns all of that into stable keys:

``normalize_team(raw)`` -> :class:`TeamName` with

* ``key``      canonical graph key, e.g. ``atletico-mg``
* ``base``     region-stripped slug, e.g. ``atletico``
* ``region``   two/three letter state or country code when detectable
* ``display``  a tidy human-readable label

Design notes
------------
* Region suffixes are only recognised when they are *upper case* in the raw
  string, so ``São Paulo`` never loses "Paulo" while ``Botafogo PB`` does lose
  "PB".
* Club-type noise (``FC``, ``EC``, ``Futebol Clube``, ``Esporte``...) is
  dropped, as are Portuguese stop words (``de``, ``do``, ``da``).
* Only genuinely ambiguous bases (``america``, ``botafogo``, ``nautico``, ...)
  keep the region in their key.  Everything else collapses to the bare base so
  that ``Palmeiras`` and ``Palmeiras-SP`` are the *same* node.  Ambiguous bases
  with no region fall back to :data:`DEFAULT_REGION` (plain ``Flamengo`` means
  the Rio club, not Flamengo do Piauí).
* :data:`ALIASES` handles the cases no rule can reach (``Vasco`` ==
  ``Vasco da Gama``, ``Athletico`` == ``Atlético Paranaense``).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache

# --------------------------------------------------------------------------
# vocabularies
# --------------------------------------------------------------------------

#: Brazilian federal units used as team-name suffixes.
STATES = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
}

#: Country codes used for non-Brazilian clubs in the Libertadores file.
COUNTRIES = {
    "ARG", "BOL", "BRA", "CHI", "COL", "EQU", "MEX", "PAR", "PER", "URU",
    "VEN", "USA",
}

REGIONS = STATES | COUNTRIES

#: Tokens that describe the *kind* of club rather than its identity.
_CLUB_TOKENS = {
    "fc", "ec", "cf", "sf", "ad", "ge", "cr", "aa",
    "futebol", "futbol", "clube", "club", "esporte", "esportivo",
    "esportiva", "desportos", "desportivo", "sociedade", "associacao",
    "regatas", "recreativo", "ltda", "antigo",
}

#: Portuguese connectors that add no discriminating power.
_STOPWORDS = {"de", "do", "da", "dos", "das", "e"}

#: Bases that map to more than one real club and therefore keep their region.
AMBIGUOUS_BASES = {
    "america", "atletico", "aguia", "botafogo", "bragantino", "brasil",
    "caxias", "comercial", "confianca", "cordino", "flamengo", "fluminense",
    "guarani", "independente", "internacional", "juventude", "nacional",
    "nautico", "operario", "parnahyba", "penarol", "portuguesa", "real",
    "remo", "rio branco", "river", "santa cruz", "santos", "sao francisco",
    "sao jose", "sao luiz", "sao raimundo", "serra", "sport", "tubarao",
    "uniao", "vitoria", "ypiranga",
}

#: The club meant when an ambiguous base carries no region marker at all.
DEFAULT_REGION = {
    "america": "MG",
    "atletico": "MG",
    "botafogo": "RJ",
    "bragantino": "SP",
    "brasil": "RS",
    "caxias": "RS",
    "flamengo": "RJ",
    "fluminense": "RJ",
    "guarani": "SP",
    "internacional": "RS",
    "juventude": "RS",
    "nautico": "PE",
    "operario": "PR",
    "penarol": "URU",
    "portuguesa": "SP",
    "remo": "PA",
    "rio branco": "AC",
    "santa cruz": "PE",
    "santos": "SP",
    "sao jose": "RS",
    "sport": "PE",
    "vitoria": "BA",
    "ypiranga": "RS",
}

#: Post-normalisation rewrites: base slug -> (base slug, region or None).
ALIASES: dict[str, tuple[str, str | None]] = {
    "atletico mineiro": ("atletico", "MG"),
    "atletico paranaense": ("atletico", "PR"),
    "athletico paranaense": ("atletico", "PR"),
    "athletico": ("atletico", "PR"),
    "atletico goianiense": ("atletico", "GO"),
    "atletico goiania": ("atletico", "GO"),
    "vasco": ("vasco gama", "RJ"),
    "vasco gama": ("vasco gama", "RJ"),
    "sport recife": ("sport", "PE"),
    "nautico capibaribe": ("nautico", "PE"),
    "america natal": ("america", "RN"),
    "flamengo piaui": ("flamengo", "PI"),
    "red bull bragantino": ("bragantino", "SP"),
    "cs alagoano": ("csa", "AL"),
    "abc": ("abc", "RN"),
    "crb": ("crb", "AL"),
    "csa": ("csa", "AL"),
    "asa": ("asa", "AL"),
    "crac": ("crac", "GO"),
    "urt": ("urt", "MG"),
    "gremio novorizontino": ("novorizontino", "SP"),
    "novorizontino": ("novorizontino", "SP"),
    "boavista saquarema": ("boavista", "RJ"),
    "moto sao luis": ("moto", "MA"),
    "moto": ("moto", "MA"),
    "parana": ("parana", "PR"),
    "ca parana": ("parana", "PR"),
    "sao paulo": ("sao paulo", "SP"),
    "corinthians": ("corinthians", "SP"),
    "palmeiras": ("palmeiras", "SP"),
    "gremio": ("gremio", "RS"),
    "cruzeiro": ("cruzeiro", "MG"),
    "coritiba": ("coritiba", "PR"),
    "chapecoense": ("chapecoense", "SC"),
    "figueirense": ("figueirense", "SC"),
    "criciuma": ("criciuma", "SC"),
    "avai": ("avai", "SC"),
    "goias": ("goias", "GO"),
    "ceara": ("ceara", "CE"),
    "bahia": ("bahia", "BA"),
    "fortaleza": ("fortaleza", "CE"),
    "cuiaba": ("cuiaba", "MT"),
    "ponte preta": ("ponte preta", "SP"),
    "sampaio correa": ("sampaio correa", "MA"),
    "xv piracicaba": ("xv piracicaba", "SP"),
    "ind santa fe": ("independiente santa fe", "COL"),
}

#: Traditional derbies, used by the ``derbies`` query.
DERBIES: tuple[tuple[str, str, str], ...] = (
    ("flamengo-rj", "fluminense-rj", "Fla-Flu"),
    ("flamengo-rj", "vasco gama-rj", "Clássico dos Milhões"),
    ("flamengo-rj", "botafogo-rj", "Clássico da Rivalidade"),
    ("botafogo-rj", "vasco gama-rj", "Clássico da Amizade"),
    ("fluminense-rj", "botafogo-rj", "Clássico Vovô"),
    ("fluminense-rj", "vasco gama-rj", "Clássico dos Gigantes"),
    ("corinthians", "palmeiras", "Derby Paulista"),
    ("corinthians", "sao paulo", "Majestoso"),
    ("corinthians", "santos-sp", "Clássico Alvinegro"),
    ("palmeiras", "sao paulo", "Choque-Rei"),
    ("palmeiras", "santos-sp", "Clássico da Saudade"),
    ("sao paulo", "santos-sp", "San-São"),
    ("gremio", "internacional-rs", "Gre-Nal"),
    ("atletico-mg", "cruzeiro", "Clássico Mineiro"),
    ("bahia", "vitoria-ba", "Ba-Vi"),
    ("sport-pe", "nautico-pe", "Clássico dos Clássicos"),
    ("sport-pe", "santa cruz-pe", "Clássico das Multidões"),
    ("nautico-pe", "santa cruz-pe", "Clássico das Emoções"),
    ("ceara-ce", "fortaleza-ce", "Clássico-Rei"),
    ("atletico-pr", "coritiba", "Atletiba"),
    ("goias", "atletico-go", "Clássico Goianiense"),
)

# --------------------------------------------------------------------------
# team names
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TeamName:
    """The canonical decomposition of one raw team string."""

    key: str
    base: str
    region: str | None
    display: str
    raw: str
    #: True when the region came from the raw string or an alias that names a
    #: specific club, False when it was filled in from :data:`DEFAULT_REGION`.
    explicit_region: bool = False


_PAREN_RE = re.compile(r"\(([^)]*)\)")
_NON_ALNUM_RE = re.compile(r"[^0-9a-z ]+")
_MULTISPACE_RE = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    """Fold accents/cedillas: ``Grêmio`` -> ``Gremio``, ``Avaí`` -> ``Avai``."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _extract_region(raw: str) -> tuple[str, str | None]:
    """Pull a trailing state/country marker off *raw*.

    Returns ``(remainder, region)``.  Only upper-case markers count, which is
    what keeps ``São Paulo`` intact while trimming ``Botafogo PB``.
    """
    text = raw.strip()
    region: str | None = None

    # "(URU)" / "(PAR)" style, anywhere in the string.
    for candidate in _PAREN_RE.findall(text):
        token = candidate.strip().upper()
        if token in REGIONS:
            region = token
            text = _PAREN_RE.sub(" ", text, count=1)
            break
    # Any remaining parenthetical is editorial noise ("(antigo ...)").
    text = _PAREN_RE.sub(" ", text)
    text = _MULTISPACE_RE.sub(" ", text).strip()

    # Trailing "-XX", " - XX" or " XX" (possibly repeated: "Rio Branco - Vn - ES").
    pattern = re.compile(r"[\s-]+([A-Z]{2,3})$")
    while True:
        match = pattern.search(text)
        if not match or match.group(1) not in REGIONS:
            break
        region = region or match.group(1)
        text = text[: match.start()].strip()

    return text, region


def _slugify(text: str) -> str:
    """``"Atlético  Paranaense"`` -> ``"atletico paranaense"``."""
    text = strip_accents(text).lower()
    text = text.replace("&", " ")
    text = _NON_ALNUM_RE.sub(" ", text)
    return _MULTISPACE_RE.sub(" ", text).strip()


def _collapse_initials(slug: str) -> str:
    """Join runs of single letters: ``a b c`` -> ``abc``, ``c r b`` -> ``crb``.

    Handles the dotted spellings in the cup file (``A.b.c. - RN``, ``C.s.a. -
    AL``) whose periods :func:`_slugify` has already turned into spaces.
    """
    tokens = slug.split()
    collapsed: list[str] = []
    run: list[str] = []
    for token in tokens:
        if len(token) == 1 and token.isalpha():
            run.append(token)
            continue
        if len(run) >= 2:
            collapsed.append("".join(run))
        else:
            collapsed.extend(run)
        run = []
        collapsed.append(token)
    if len(run) >= 2:
        collapsed.append("".join(run))
    else:
        collapsed.extend(run)
    return " ".join(collapsed)


def _drop_noise(slug: str) -> str:
    """Remove club-type words and Portuguese connectors."""
    # "Sport Club"/"Sporting Club" are noise; a bare "Sport" is Sport Recife.
    slug = re.sub(r"\bsport(ing)? clube?\b", " ", slug)
    tokens = [
        token
        for token in slug.split()
        if token not in _CLUB_TOKENS and token not in _STOPWORDS
    ]
    if not tokens:  # the whole name was noise -- keep the original words
        tokens = slug.split()
    return " ".join(tokens)


@lru_cache(maxsize=8192)
def normalize_team(raw: str | None) -> TeamName:
    """Canonicalise one raw team string.

    >>> normalize_team("Palmeiras-SP").key
    'palmeiras'
    >>> normalize_team("Atlético - MG").key
    'atletico-mg'
    >>> normalize_team("Flamengo").key
    'flamengo-rj'
    """
    raw = (raw or "").strip()
    if not raw:
        return TeamName(key="", base="", region=None, display="", raw="")

    stripped, region = _extract_region(raw)
    base = _drop_noise(_collapse_initials(_slugify(stripped)))
    explicit = region is not None

    aliased = ALIASES.get(base)
    if aliased is not None:
        base, alias_region = aliased
        if region is None and alias_region is not None:
            region = alias_region
            explicit = True

    if base in AMBIGUOUS_BASES:
        if region is None:
            region = DEFAULT_REGION.get(base)
            explicit = False
        key = f"{base}-{region.lower()}" if region else base
    else:
        key = base

    key = key.replace(" ", "-")
    display = _display_name(base, region)
    return TeamName(
        key=key,
        base=base,
        region=region,
        display=display,
        raw=raw,
        explicit_region=explicit,
    )


def _display_name(base: str, region: str | None) -> str:
    """Title-cased label; ``atletico``+``MG`` -> ``Atletico-MG``."""
    pretty = " ".join(
        word.upper() if len(word) <= 3 and word.isalpha() and word in _ACRONYMS
        else word.capitalize()
        for word in base.split()
    )
    if region and base in AMBIGUOUS_BASES:
        return f"{pretty}-{region}"
    return pretty


_ACRONYMS = {"abc", "crb", "csa", "asa", "crac", "urt", "xv", "psv"}


def team_key(raw: str | None) -> str:
    """Shorthand for ``normalize_team(raw).key``."""
    return normalize_team(raw).key


# --------------------------------------------------------------------------
# dates & numbers
# --------------------------------------------------------------------------

_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
)


def parse_date(value: str | None) -> date | None:
    """Parse the ISO / ISO+time / ``DD/MM/YYYY`` variants found in the data."""
    if value is None:
        return None
    text = str(value).strip().strip('"')
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:  # last resort: fromisoformat handles offsets & fractional seconds
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def parse_int(value: str | float | None) -> int | None:
    """Tolerant int parser: handles ``"2"``, ``2.0``, ``""`` and ``"NA"``."""
    if value is None:
        return None
    text = str(value).strip().strip('"')
    if not text or text.lower() in {"nan", "none", "null", "na", "-"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def parse_float(value: str | float | None) -> float | None:
    """Tolerant float parser (used for the shots/corners/attacks columns)."""
    if value is None:
        return None
    text = str(value).strip().strip('"')
    if not text or text.lower() in {"nan", "none", "null", "na", "-"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def normalize_text(value: str | None) -> str:
    """Accent-folded, lower-cased text for free-text search (players, clubs)."""
    return _MULTISPACE_RE.sub(" ", strip_accents(value or "").lower()).strip()
