"""Name, date and competition normalization.

The six source CSVs disagree about almost everything:

* Team names carry state suffixes (``Palmeiras-SP``), spaced state suffixes
  (``América - MG``), country codes (``Nacional (URU)``, ``Guaraní-PAR``), club
  type words (``Fortaleza EC``, ``Nautico Capibaribe``) and may or may not be
  accented (``Gremio-RS`` vs ``Grêmio``).
* Dates come as ISO (``2023-09-24``), ISO + time (``2012-05-19 18:30:00``) or
  Brazilian ``DD/MM/YYYY``.
* Competitions are named ``Serie A`` in one file and implied by the file name in
  another.

This module turns all of that into stable canonical identifiers so the same club
found in five files becomes one node in the knowledge graph.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime

# --------------------------------------------------------------------------- #
# Basic text helpers
# --------------------------------------------------------------------------- #

BRAZIL_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

FOREIGN_CODES = {
    "ARG": "Argentina", "URU": "Uruguay", "PAR": "Paraguay", "CHI": "Chile",
    "COL": "Colombia", "PER": "Peru", "VEN": "Venezuela", "BOL": "Bolivia",
    "EQU": "Ecuador", "ECU": "Ecuador", "MEX": "Mexico", "BRA": "Brazil",
}

#: Standalone tokens that describe the club type rather than identify it.
CLUB_TYPE_TOKENS = {
    "fc", "ec", "sc", "ac", "cr", "ca", "se", "ad", "ge", "cs", "cd", "ce",
    "fr", "sa", "sport club", "esporte", "esportes", "clube", "club",
    "futebol", "desportos", "associacao", "ltda", "de futebol",
}

#: Portuguese/Spanish connective words dropped from slugs.
STOP_TOKENS = {"do", "da", "de", "dos", "das", "del", "the"}

_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WS_RE = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    """Return ``text`` with diacritics removed (``São`` -> ``Sao``)."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def slugify(text: str) -> str:
    """Lowercase, accent-free, punctuation-free version of ``text``."""
    cleaned = _PUNCT_RE.sub(" ", strip_accents(str(text)))
    return _WS_RE.sub(" ", cleaned).strip().lower()


@dataclass(frozen=True)
class ParsedName:
    """A raw team name split into its identifying parts."""

    raw: str
    slug: str            # identifying part, e.g. "sao paulo"
    state: str | None    # "SP" or a foreign code such as "URU"
    country: str         # "Brazil" unless a foreign code was found


def parse_team_name(raw: str) -> ParsedName:
    """Split a raw team name into ``(slug, state)``.

    >>> parse_team_name("Palmeiras-SP").slug, parse_team_name("Palmeiras-SP").state
    ('palmeiras', 'SP')
    >>> parse_team_name("Nacional (URU)").state
    'URU'
    """
    text = str(raw).strip()
    state: str | None = None

    # Trailing "(URU)" / "(PAR)" style country codes.
    paren = re.search(r"\(([A-Za-z]{2,4})\)\s*$", text)
    if paren and paren.group(1).upper() in (set(FOREIGN_CODES) | BRAZIL_STATES):
        state = paren.group(1).upper()
        text = text[: paren.start()].strip()

    # Trailing "-SP", " - MG", " RJ", "-URU" style codes.
    if state is None:
        suffix = re.search(r"[\s\-]+([A-Za-z]{2,3})\.?\s*$", text)
        if suffix:
            code = suffix.group(1).upper()
            known = code in BRAZIL_STATES or code in FOREIGN_CODES
            # Only treat it as a code when the original text was upper case, so
            # that "Boa" or "Sao" style words are never eaten.
            if known and suffix.group(1).isupper() and text[: suffix.start()].strip():
                state = code
                text = text[: suffix.start()].strip()

    slug = _slug_tokens(text)
    country = FOREIGN_CODES.get(state or "", "Brazil")
    return ParsedName(raw=str(raw).strip(), slug=slug, state=state, country=country)


def _slug_tokens(text: str) -> str:
    """Slugify and drop club-type/stop words while never returning empty."""
    slug = slugify(text)
    if not slug:
        return ""
    tokens = slug.split(" ")
    kept = [t for t in tokens if t not in CLUB_TYPE_TOKENS and t not in STOP_TOKENS]
    if not kept:                      # name was entirely type words, e.g. "Sport"
        kept = tokens
    return " ".join(kept)


# --------------------------------------------------------------------------- #
# Curated clubs
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class CuratedClub:
    """A hand-curated canonical club used to bridge naming variants."""

    team_id: str
    display: str
    state: str | None
    country: str = "Brazil"
    aliases: tuple[str, ...] = field(default=())
    primary: bool = True   # wins when an alias is used without a state code


def _c(team_id, display, state, aliases, country="Brazil", primary=True):
    return CuratedClub(team_id, display, state, country, tuple(aliases), primary)


#: Clubs whose names differ enough between files that generic rules are not
#: sufficient, plus the big clubs that must resolve from a bare user query.
CURATED_CLUBS: tuple[CuratedClub, ...] = (
    _c("flamengo", "Flamengo", "RJ", ["flamengo", "cr flamengo", "flamengo rj"]),
    _c("flamengo-pi", "Flamengo-PI", "PI",
       ["flamengo", "flamengo piaui", "flamengo pi"], primary=False),
    _c("palmeiras", "Palmeiras", "SP", ["palmeiras", "se palmeiras"]),
    _c("corinthians", "Corinthians", "SP",
       ["corinthians", "sport club corinthians paulista", "corinthians paulista"]),
    _c("sao-paulo", "São Paulo", "SP", ["sao paulo", "sao paulo futebol"]),
    _c("santos", "Santos", "SP", ["santos", "santos futebol"]),
    _c("santos-ap", "Santos-AP", "AP", ["santos", "santos ap"], primary=False),
    _c("fluminense", "Fluminense", "RJ", ["fluminense"]),
    _c("vasco-da-gama", "Vasco da Gama", "RJ",
       ["vasco", "vasco gama", "vasco gama rj"]),
    _c("botafogo", "Botafogo", "RJ", ["botafogo", "botafogo rj"]),
    _c("botafogo-pb", "Botafogo-PB", "PB", ["botafogo", "botafogo pb"], primary=False),
    _c("botafogo-sp", "Botafogo-SP", "SP", ["botafogo", "botafogo sp"], primary=False),
    _c("gremio", "Grêmio", "RS", ["gremio", "gremio foot ball porto alegrense"]),
    _c("internacional", "Internacional", "RS", ["internacional", "inter"]),
    _c("atletico-mineiro", "Atlético Mineiro", "MG",
       ["atletico", "atletico mineiro", "atletico mg", "galo"]),
    _c("athletico-paranaense", "Athletico Paranaense", "PR",
       ["athletico", "athletico paranaense", "atletico paranaense", "atletico",
        "atletico pr"], primary=False),
    _c("atletico-goianiense", "Atlético Goianiense", "GO",
       ["atletico", "atletico goianiense", "atletico go"], primary=False),
    _c("cruzeiro", "Cruzeiro", "MG", ["cruzeiro"]),
    _c("america-mineiro", "América Mineiro", "MG",
       ["america mineiro", "america mg", "america"]),
    _c("america-rn", "América-RN", "RN",
       ["america", "america rn", "america natal", "america de natal"],
       primary=False),
    _c("bahia", "Bahia", "BA", ["bahia"]),
    _c("vitoria", "Vitória", "BA", ["vitoria"]),
    _c("sport-recife", "Sport Recife", "PE",
       ["sport", "sport recife", "sport recife pe"]),
    _c("nautico", "Náutico", "PE", ["nautico", "nautico capibaribe"]),
    _c("santa-cruz", "Santa Cruz", "PE", ["santa cruz"]),
    _c("ceara", "Ceará", "CE", ["ceara", "ceara sporting"]),
    _c("fortaleza", "Fortaleza", "CE", ["fortaleza"]),
    _c("goias", "Goiás", "GO", ["goias"]),
    _c("coritiba", "Coritiba", "PR", ["coritiba"]),
    _c("parana", "Paraná", "PR", ["parana"]),
    _c("chapecoense", "Chapecoense", "SC", ["chapecoense"]),
    _c("avai", "Avaí", "SC", ["avai"]),
    _c("figueirense", "Figueirense", "SC", ["figueirense"]),
    _c("criciuma", "Criciúma", "SC", ["criciuma"]),
    _c("joinville", "Joinville", "SC", ["joinville"]),
    _c("juventude", "Juventude", "RS", ["juventude"]),
    _c("ponte-preta", "Ponte Preta", "SP", ["ponte preta"]),
    _c("portuguesa", "Portuguesa", "SP", ["portuguesa", "portuguesa desportos"]),
    _c("guarani", "Guarani", "SP", ["guarani", "guarani sp"]),
    _c("guarani-par", "Guaraní (PAR)", "PAR", ["guarani", "guarani par"],
       country="Paraguay", primary=False),
    _c("red-bull-bragantino", "Red Bull Bragantino", "SP",
       ["red bull bragantino", "bragantino", "red bull brasil"]),
    _c("cuiaba", "Cuiabá", "MT", ["cuiaba"]),
    _c("csa", "CSA", "AL", ["csa", "c s a"]),
    _c("crb", "CRB", "AL", ["crb", "c r b"]),
    _c("abc", "ABC", "RN", ["abc", "a b c"]),
    _c("asa", "ASA", "AL", ["asa", "a s a"]),
    _c("sao-caetano", "São Caetano", "SP", ["sao caetano"]),
    _c("santo-andre", "Santo André", "SP", ["santo andre"]),
    _c("ipatinga", "Ipatinga", "MG", ["ipatinga"]),
    _c("brasiliense", "Brasiliense", "DF", ["brasiliense"]),
    _c("paysandu", "Paysandu", "PA", ["paysandu"]),
    _c("remo", "Remo", "PA", ["remo"]),
    _c("barueri", "Grêmio Barueri", "SP",
       ["barueri", "gremio barueri", "gremio prudente"]),
    # Foreign clubs that recur in the Libertadores file.
    _c("river-plate", "River Plate", "ARG", ["river plate"], country="Argentina"),
    _c("river-plate-se", "River Plate-SE", "SE", ["river plate", "river plate se"],
       primary=False),
    _c("boca-juniors", "Boca Juniors", "ARG", ["boca juniors"], country="Argentina"),
    _c("nacional-uru", "Nacional (URU)", "URU", ["nacional", "nacional uru"],
       country="Uruguay", primary=False),
    _c("penarol", "Peñarol", "URU", ["penarol", "penarol uru"], country="Uruguay",
       primary=False),
    _c("olimpia-par", "Olimpia (PAR)", "PAR", ["olimpia", "olimpia par"],
       country="Paraguay"),
    _c("independiente-del-valle", "Independiente del Valle", "EQU",
       ["independiente valle"], country="Ecuador", primary=False),
)


def _build_alias_index() -> dict[str, list[CuratedClub]]:
    index: dict[str, list[CuratedClub]] = {}
    for club in CURATED_CLUBS:
        for alias in club.aliases:
            index.setdefault(_slug_tokens(alias), []).append(club)
    return index


CURATED_ALIAS_INDEX = _build_alias_index()


def lookup_curated(slug: str, state: str | None) -> CuratedClub | None:
    """Return the curated club for ``(slug, state)`` if one matches."""
    candidates = CURATED_ALIAS_INDEX.get(slug)
    if not candidates:
        return None
    if state:
        for club in candidates:
            if club.state == state:
                return club
        # A state we do not know about means a different club with the same name.
        return None
    for club in candidates:
        if club.primary:
            return club
    # No primary claimant: an unambiguous alias such as "atletico paranaense"
    # still identifies exactly one club even without a state code.
    return candidates[0] if len(candidates) == 1 else None


# --------------------------------------------------------------------------- #
# Dates
# --------------------------------------------------------------------------- #

_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
)


def parse_date(value: object) -> date | None:
    """Parse the several date shapes found in the datasets.

    Returns ``None`` for missing/unparseable values rather than raising, because
    a handful of rows in the source data have no usable date.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none", "-"}:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:                                  # last resort: ISO-ish prefix
        return datetime.fromisoformat(text[:19]).date()
    except ValueError:
        return None


def parse_time(value: object) -> str | None:
    """Extract a ``HH:MM`` kick-off time from a datetime string, if present."""
    if value is None:
        return None
    text = str(value).strip()
    match = re.search(r"(\d{2}):(\d{2})", text)
    return f"{match.group(1)}:{match.group(2)}" if match else None


def parse_int(value: object) -> int | None:
    """Parse an integer, tolerating floats, blanks and ``'-'`` placeholders."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"-", "nan", "NaN", "None", "?"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# Competitions
# --------------------------------------------------------------------------- #

BRASILEIRAO = "Brasileirão Série A"
SERIE_B = "Brasileirão Série B"
SERIE_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

COMPETITIONS = (BRASILEIRAO, SERIE_B, SERIE_C, COPA_DO_BRASIL, LIBERTADORES)

_COMPETITION_ALIASES = {
    "serie a": BRASILEIRAO,
    "seria a": BRASILEIRAO,
    "brasileirao": BRASILEIRAO,
    "brasileirao serie a": BRASILEIRAO,
    "campeonato brasileiro": BRASILEIRAO,
    "campeonato brasileiro serie a": BRASILEIRAO,
    "brasileiro": BRASILEIRAO,
    "serie b": SERIE_B,
    "brasileirao serie b": SERIE_B,
    "serie c": SERIE_C,
    "brasileirao serie c": SERIE_C,
    "copa brasil": COPA_DO_BRASIL,
    "copa do brasil": COPA_DO_BRASIL,
    "brazilian cup": COPA_DO_BRASIL,
    "cup": COPA_DO_BRASIL,
    "libertadores": LIBERTADORES,
    "copa libertadores": LIBERTADORES,
    "conmebol libertadores": LIBERTADORES,
}


def normalize_competition(value: object) -> str | None:
    """Map a user or dataset competition label onto a canonical name."""
    if value is None:
        return None
    slug = slugify(value)
    if not slug:
        return None
    if slug in _COMPETITION_ALIASES:
        return _COMPETITION_ALIASES[slug]
    for canonical in COMPETITIONS:
        if slugify(canonical) == slug:
            return canonical
    # Allow partial matches such as "libertadores 2019".
    for alias, canonical in _COMPETITION_ALIASES.items():
        if alias in slug:
            return canonical
    return None
