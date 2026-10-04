"""Normalisation of team names, competition names and dates.

The six CSV files spell the same club in many ways ("Palmeiras-SP",
"Palmeiras - SP", "Palmeiras", "Sociedade Esportiva Palmeiras") and, worse, use
the same short name for different clubs ("Atlético - MG" / "Atlético - GO",
"Botafogo - RJ" / "Botafogo - PB").  ``TeamRegistry`` maps every spelling to a
single display name while keeping genuinely different clubs apart.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime

UFS = frozenset(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)

# (display name, state, aliases).  An alias ending in "*" is ambiguous on its
# own and only matches when the state suffix is present as well.
_CLUBS = [
    ("Flamengo", "RJ", ["flamengo", "clube de regatas do flamengo", "cr flamengo"]),
    ("Fluminense", "RJ", ["fluminense"]),
    ("Vasco da Gama", "RJ", ["vasco", "vasco da gama", "cr vasco da gama"]),
    ("Botafogo", "RJ", ["botafogo", "botafogo de futebol e regatas"]),
    ("Palmeiras", "SP", ["palmeiras", "sociedade esportiva palmeiras"]),
    ("Corinthians", "SP", ["corinthians", "sport club corinthians paulista", "corinthians paulista"]),
    ("São Paulo", "SP", ["sao paulo", "sao paulo futebol clube"]),
    ("Santos", "SP", ["santos", "santos futebol clube"]),
    ("Grêmio", "RS", ["gremio", "gremio foot ball porto alegrense"]),
    ("Internacional", "RS", ["internacional", "sport club internacional"]),
    ("Atlético Mineiro", "MG", ["atletico mineiro", "clube atletico mineiro", "atletico*"]),
    ("Cruzeiro", "MG", ["cruzeiro", "cruzeiro esporte clube"]),
    ("América Mineiro", "MG", ["america mineiro", "america minas gerais", "america fc minas gerais", "america*"]),
    ("Athletico Paranaense", "PR", ["athletico paranaense", "atletico paranaense", "athletico",
                                    "club athletico paranaense", "atletico*"]),
    ("Coritiba", "PR", ["coritiba"]),
    ("Paraná", "PR", ["parana", "parana clube"]),
    ("Atlético Goianiense", "GO", ["atletico goianiense", "atletico*"]),
    ("Goiás", "GO", ["goias"]),
    ("Bahia", "BA", ["bahia"]),
    ("Vitória", "BA", ["vitoria"]),
    ("Sport Recife", "PE", ["sport", "sport recife", "sport club do recife"]),
    ("Náutico", "PE", ["nautico", "nautico capibaribe"]),
    ("Santa Cruz", "PE", ["santa cruz"]),
    ("Fortaleza", "CE", ["fortaleza", "fortaleza esporte clube"]),
    ("Ceará", "CE", ["ceara", "ceara sporting club"]),
    ("Chapecoense", "SC", ["chapecoense"]),
    ("Figueirense", "SC", ["figueirense"]),
    ("Avaí", "SC", ["avai"]),
    ("Criciúma", "SC", ["criciuma"]),
    ("Joinville", "SC", ["joinville"]),
    ("Juventude", "RS", ["juventude"]),
    ("Red Bull Bragantino", "SP", ["red bull bragantino", "rb bragantino", "bragantino"]),
    ("Ponte Preta", "SP", ["ponte preta"]),
    ("Portuguesa", "SP", ["portuguesa", "portuguesa desportos", "portuguesa de desportos"]),
    ("Guarani", "SP", ["guarani"]),
    ("Cuiabá", "MT", ["cuiaba"]),
    ("CSA", "AL", ["csa", "cs alagoano"]),
    ("CRB", "AL", ["crb"]),
    ("Paysandu", "PA", ["paysandu"]),
    ("Remo", "PA", ["remo", "clube do remo"]),
    ("América de Natal", "RN", ["america de natal", "america fc natal", "america natal", "america*"]),
]

_BY_PAIR: dict[tuple[str, str], str] = {}
_BY_NAME: dict[str, str] = {}
_TABLE_BASES: set[str] = set()
CLUB_STATE: dict[str, str] = {}
for _display, _state, _aliases in _CLUBS:
    CLUB_STATE[_display] = _state
    for _alias in _aliases:
        _needs_state = _alias.endswith("*")
        _alias = _alias.rstrip("*")
        _TABLE_BASES.add(_alias)
        _BY_PAIR[(_alias, _state)] = _display
        if not _needs_state:
            _BY_NAME[_alias] = _display

_LEADING_NOISE = {"fc", "ec", "ad", "ae", "ca", "sc", "se", "ce", "cs", "ge"}
_TRAILING_NOISE = {"fc", "ec"}

_PAREN_CODE = re.compile(r"^(.*?)\s*\(([A-Z]{2,3})\)$")
_DASH_CODE = re.compile(r"^(.*?)\s*-\s*([A-Z]{2,3})$")
_SPACE_CODE = re.compile(r"^(.*\S)\s+([A-Z]{2})$")


def fold(text: str) -> str:
    """Lower-case ``text`` and strip accents so 'Grêmio' == 'gremio'."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower().strip()


def split_team_name(raw: str) -> tuple[str, str | None, str]:
    """Split a raw team name into (folded base, state/country code, pretty base)."""
    name = re.sub(r"\s+", " ", raw).strip()
    name = re.sub(r"\s*\(antigo[^)]*\)", "", name, flags=re.IGNORECASE)
    code = None
    for pattern in (_PAREN_CODE, _DASH_CODE, _SPACE_CODE):
        found = pattern.match(name)
        if found and (pattern is not _SPACE_CODE or found.group(2) in UFS):
            name, code = found.group(1).strip(), found.group(2)
            break
    pretty = name
    base = fold(name).replace(".", " ")
    base = re.sub(r"[()\-/,]", " ", base)
    tokens = base.split()
    if len(tokens) > 1 and all(len(t) == 1 for t in tokens):
        tokens = ["".join(tokens)]  # "C. R. B." -> "crb"
    base = " ".join(tokens)
    if base not in _TABLE_BASES:
        stripped = list(tokens)
        while len(stripped) > 1 and stripped[0] in _LEADING_NOISE:
            stripped.pop(0)
        while len(stripped) > 1 and stripped[-1] in _TRAILING_NOISE:
            stripped.pop()
        base = " ".join(stripped)
    return base, code, pretty


def known_club(raw: str) -> str | None:
    """Return the display name if ``raw`` is one of the well-known clubs."""
    base, code, _ = split_team_name(raw)
    if code is not None:
        return _BY_PAIR.get((base, code))
    return _BY_NAME.get(base)


class TeamRegistry:
    """Maps raw team names to canonical display names.

    Usage is two-pass: ``observe`` every raw name first (so the registry learns
    which short names are shared by clubs from several states), then
    ``canonical`` to translate.
    """

    def __init__(self) -> None:
        self._codes: dict[str, set[str]] = defaultdict(set)
        self._pretty: dict[tuple[str, str | None], Counter] = defaultdict(Counter)
        self._cache: dict[str, str] = {}
        self.names: set[str] = set()

    def observe(self, raw: str) -> None:
        base, code, pretty = split_team_name(raw)
        if code is not None:
            self._codes[base].add(code)
        self._pretty[(base, code)][pretty] += 1
        self._cache.clear()

    def _key(self, base: str, code: str | None) -> tuple[str, str | None]:
        if code is None:
            return base, None
        if base in _TABLE_BASES or len(self._codes[base]) > 1:
            return base, code
        return base, None  # only one state ever seen: "Caxias RS" == "Caxias"

    def _display(self, base: str, code: str | None, fallback: str) -> str:
        key = self._key(base, code)
        variants: Counter = Counter()
        if key[1] is None:
            for (b, _c), counter in self._pretty.items():
                if b == base and self._key(b, _c) == key:
                    variants.update(counter)
        else:
            variants.update(self._pretty.get(key, {}))
        if variants:
            # Prefer accented spellings ("Avaí" over "Avai"), then the commonest.
            pretty = max(variants, key=lambda v: (not v.isascii(), variants[v], v))
        else:
            pretty = fallback
        return f"{pretty}-{key[1]}" if key[1] else pretty

    def canonical(self, raw: str) -> str:
        """Canonical display name for a raw team name (known or not)."""
        cached = self._cache.get(raw)
        if cached is None:
            base, code, pretty = split_team_name(raw)
            cached = known_club(raw) or self._display(base, code, pretty)
            self._cache[raw] = cached
        return cached

    def add(self, raw: str) -> str:
        name = self.canonical(raw)
        self.names.add(name)
        return name

    def find(self, query: str) -> list[str]:
        """Teams matching a user query: exact canonical match, else substring."""
        if not query or not query.strip():
            return []
        exact = self.canonical(query)
        if exact in self.names:
            return [exact]
        base, code, _ = split_team_name(query)
        needle = fold(query)
        hits = [
            n for n in self.names
            if needle in fold(n) or (base and code is None and base in split_team_name(n)[0])
        ]
        return sorted(hits)


# --------------------------------------------------------------------------- #
# Competitions
# --------------------------------------------------------------------------- #

BRASILEIRAO = "Brasileirão"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"
SERIE_B = "Série B"
SERIE_C = "Série C"
COMPETITIONS = (BRASILEIRAO, COPA_DO_BRASIL, LIBERTADORES, SERIE_B, SERIE_C)
LEAGUES = (BRASILEIRAO, SERIE_B, SERIE_C)


def normalize_competition(query: str | None) -> str | None:
    """Map free text ('serie a', 'Brazilian Cup', 'libertadores') to a competition."""
    if query is None or not str(query).strip():
        return None
    q = fold(str(query))
    if "libertadores" in q:
        return LIBERTADORES
    if "copa do brasil" in q or "cup" in q or q == "copa":
        return COPA_DO_BRASIL
    if re.search(r"serie b\b", q) or "segunda divis" in q:
        return SERIE_B
    if re.search(r"serie c\b", q) or "terceira divis" in q:
        return SERIE_C
    if "brasileir" in q or "serie a" in q or "campeonato" in q or q in ("league", "a"):
        return BRASILEIRAO
    raise ValueError(
        f"Unknown competition {query!r}. Known competitions: {', '.join(COMPETITIONS)}"
    )


# --------------------------------------------------------------------------- #
# Dates
# --------------------------------------------------------------------------- #

_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d",
                 "%d/%m/%Y %H:%M", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d")


def parse_datetime(text: str | None) -> datetime | None:
    """Parse ISO, ISO-with-time and Brazilian DD/MM/YYYY dates; None if unparseable."""
    if text is None:
        return None
    text = str(text).strip()
    if not text or text.upper() in ("NA", "NAN", "NONE"):
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def parse_date(text: str | None) -> date | None:
    parsed = parse_datetime(text)
    return parsed.date() if parsed else None
