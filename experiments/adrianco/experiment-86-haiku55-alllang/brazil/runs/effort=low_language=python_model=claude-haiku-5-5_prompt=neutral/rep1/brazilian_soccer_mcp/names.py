# Context: Team and competition name normalization for the Brazilian soccer MCP server.
# Datasets spell the same club differently ("Palmeiras-SP", "Palmeiras", "Sport Club Corinthians
# Paulista", "América - MG", "Nacional (URU)"). This module reduces every spelling to a stable key
# plus an optional state code so that matching, grouping and head-to-head work across all files.

import re
import unicodedata

BRAZIL_STATES = frozenset(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)

# "Palmeiras-SP", "América - MG" -> trailing state code after a dash
_STATE_SUFFIX = re.compile(r"\s*-\s*([A-Za-z]{2})$")
# "Vasco (RJ)" -> state in trailing parentheses
_STATE_PARENTHESES = re.compile(r"\s*\(\s*([A-Za-z]{2})\s*\)$")
# "Vasco Da Gama RJ" -> bare upper-case state code at the end
_STATE_BARE = re.compile(r"\s+([A-Z]{2})$")
_PARENTHESES = re.compile(r"\([^)]*\)")
_NON_ALNUM = re.compile(r"[^a-z0-9 ]+")

_LEADING_NOISE = (
    "sociedade esportiva ",
    "sport club ",
    "esporte clube ",
    "associacao atletica ",
    "clube de regatas ",
    "club ",
)
_TRAILING_NOISE = (" futebol clube", " paulista", " fc", " ec", " sc", " afc")

# Known clubs whose dataset spelling is far from the common short name.
_ALIASES = {
    "atletico paranaense": "athletico",
    "athletico pr": "athletico",
    "atletico mineiro": "atletico",
    "vasco da gama": "vasco",
    "sport club do recife": "sport",
    "gremio foot ball porto alegrense": "gremio",
}

# Same club spelled differently by different files, disambiguated by state.
_STATE_ALIASES = {
    ("atletico", "PR"): "athletico",
}

_COMPETITION_ALIASES = (
    ("libertadores", "Copa Libertadores"),
    ("copa do brasil", "Copa do Brasil"),
    ("cup", "Copa do Brasil"),
    ("serie b", "Brasileirão Série B"),
    ("serie c", "Brasileirão Série C"),
    ("serie a", "Brasileirão Série A"),
    ("brasileirao", "Brasileirão Série A"),
    ("brasileiro", "Brasileirão Série A"),
)


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def fold(text: str) -> str:
    """Lowercase, accent-free, punctuation-free, single-spaced text for comparisons."""
    text = _NON_ALNUM.sub(" ", strip_accents(text).lower())
    return " ".join(text.split())


def _split_state(raw: str) -> tuple[str, str | None]:
    """Remove a trailing state code from a raw name; return (remaining name, state or None)."""
    name = raw.strip()
    for pattern in (_STATE_SUFFIX, _STATE_PARENTHESES, _STATE_BARE):
        found = pattern.search(name)
        if found and found.group(1).upper() in BRAZIL_STATES:
            return name[: found.start()], found.group(1).upper()
    return name, None


def parse_team(raw: str) -> tuple[str, str | None]:
    """Return (team key, state code or None) for a raw dataset team name."""
    name, state = _split_state(raw)
    key = fold(_PARENTHESES.sub(" ", name))
    key = _ALIASES.get(key, key)  # aliases are checked before and after noise removal
    for prefix in _LEADING_NOISE:
        if key.startswith(prefix):
            key = key[len(prefix):]
            break
    for suffix_text in _TRAILING_NOISE:
        if key.endswith(suffix_text):
            key = key[: -len(suffix_text)]
    key = " ".join(key.split())
    key = _ALIASES.get(key, key)
    if (key, state) in _STATE_ALIASES:
        return _STATE_ALIASES[(key, state)], state
    return key, state


def display_name(raw: str) -> str:
    """Human-friendly team name: the raw name without state suffix or parenthetical notes."""
    name, _ = _split_state(raw)
    return " ".join(_PARENTHESES.sub(" ", name).split())


def resolve_competition(query: str) -> str | None:
    """Map a free-text competition ("serie a", "libertadores") to its canonical label."""
    folded = fold(query)
    if not folded:
        return None
    for alias, canonical in _COMPETITION_ALIASES:
        if alias in folded:
            return canonical
    return query.strip()
