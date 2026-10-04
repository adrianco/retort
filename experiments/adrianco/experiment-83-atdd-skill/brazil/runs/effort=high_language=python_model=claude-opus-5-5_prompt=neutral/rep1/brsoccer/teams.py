"""Team-name normalisation.

The datasets spell clubs in many different ways:

* ``"Palmeiras-SP"``, ``"Palmeiras - SP"``, ``"Palmeiras"``
* ``"Sao Paulo"``, ``"São Paulo - SP"``, ``"Sao Paulo-SP"``
* ``"Athletico-PR"``, ``"Atletico-PR"``, ``"Athletico Paranaense"``, ``"Atlético Paranaense - PR"``
* ``"Vasco"``, ``"Vasco da Gama-RJ"``, ``"Vasco Da Gama RJ"``
* ``"Nacional (URU)"`` / ``"Nacional-URU"`` (Libertadores, foreign clubs)

``normalize_team`` turns any of these into a ``Team`` with a stable ``id``
(used for joining across files) and a human friendly ``name``.  Homonymous
clubs from other states (``"Flamengo - PI"``, ``"Botafogo - PB"``) are kept
distinct from the famous club by qualifying them with their state.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

BRAZIL_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}

# Country tags used for foreign clubs in the Libertadores file.
COUNTRY_TAGS = {
    "URU": "URU", "PAR": "PAR", "EQU": "ECU", "ECU": "ECU", "PER": "PER",
    "VEN": "VEN", "CHI": "CHI", "COL": "COL", "BOL": "BOL", "ARG": "ARG", "MEX": "MEX",
}

# Canonical clubs: display name, home state, and accent-free lower-case aliases.
# An alias may end with a state code ("america rn") to pick a specific club.
_CLUBS: list[tuple[str, str, list[str]]] = [
    ("Flamengo", "RJ", ["cr flamengo", "clube de regatas do flamengo", "mengao"]),
    ("Fluminense", "RJ", ["fluminense fc", "flu"]),
    ("Vasco da Gama", "RJ", ["vasco", "cr vasco da gama"]),
    ("Botafogo", "RJ", ["botafogo fr", "botafogo de futebol e regatas"]),
    ("Palmeiras", "SP", ["se palmeiras", "sociedade esportiva palmeiras", "verdao"]),
    ("Corinthians", "SP", ["sc corinthians", "sport club corinthians paulista", "corinthians paulista",
                           "timao"]),
    ("São Paulo", "SP", ["sao paulo fc", "spfc", "tricolor paulista"]),
    ("Santos", "SP", ["santos fc", "peixe"]),
    ("Red Bull Bragantino", "SP", ["bragantino", "rb bragantino", "bragantino sp"]),
    ("Red Bull Brasil", "SP", []),
    ("Ponte Preta", "SP", []),
    ("Portuguesa", "SP", ["portuguesa desportos"]),
    ("Guarani", "SP", []),
    ("Santo André", "SP", []),
    ("São Caetano", "SP", []),
    ("Grêmio Barueri", "SP", ["barueri"]),
    ("Grêmio Prudente", "SP", []),
    ("Novorizontino", "SP", ["gremio novorizontino"]),
    ("Grêmio", "RS", ["gremio fbpa", "gremio foot ball porto alegrense"]),
    ("Internacional", "RS", ["sc internacional"]),
    ("Juventude", "RS", ["ec juventude"]),
    ("Atlético Mineiro", "MG", ["atletico mg", "clube atletico mineiro", "galo"]),
    ("Cruzeiro", "MG", ["cruzeiro ec"]),
    ("América Mineiro", "MG", ["america mg", "america fc minas gerais"]),
    ("Ipatinga", "MG", []),
    ("Athletico Paranaense", "PR", ["atletico paranaense", "athletico pr", "atletico pr", "athletico",
                                    "club athletico paranaense"]),
    ("Coritiba", "PR", []),
    ("Paraná", "PR", ["parana clube"]),
    ("Londrina", "PR", []),
    ("Operário Ferroviário", "PR", ["operario ferroviario esporte c", "operario pr"]),
    ("Atlético Goianiense", "GO", ["atletico go"]),
    ("Goiás", "GO", []),
    ("Vila Nova", "GO", []),
    ("CRAC", "GO", []),
    ("Bahia", "BA", ["ec bahia"]),
    ("Vitória", "BA", ["ec vitoria"]),
    ("Sport Recife", "PE", ["sport", "sport club do recife", "sport club recife"]),
    ("Náutico", "PE", ["nautico capibaribe", "clube nautico capibaribe"]),
    ("Santa Cruz", "PE", ["santa cruz fc"]),
    ("Ceará", "CE", ["ceara sporting club", "ceara sc"]),
    ("Fortaleza", "CE", ["fortaleza ec"]),
    ("Avaí", "SC", []),
    ("Figueirense", "SC", []),
    ("Chapecoense", "SC", ["associacao chapecoense"]),
    ("Criciúma", "SC", []),
    ("Joinville", "SC", []),
    ("Cuiabá", "MT", []),
    ("CSA", "AL", ["cs alagoano"]),
    ("CRB", "AL", []),
    ("ASA", "AL", []),
    ("ABC", "RN", []),
    ("América-RN", "RN", ["america rn", "america fc natal"]),
    ("Paysandu", "PA", []),
    ("Remo", "PA", ["clube do remo"]),
    ("Bragantino-PA", "PA", ["bragantino pa"]),
    ("Brasiliense", "DF", []),
    ("Sampaio Corrêa", "MA", []),
]

# Words that carry no identity ("Fortaleza EC" == "Fortaleza").
_NOISE = {"ec", "fc", "sc", "ac", "fr", "clube", "club", "futebol", "esporte", "cf"}


@dataclass(frozen=True)
class Team:
    id: str              # stable join key, e.g. "flamengo", "flamengo-pi", "nacional-uru"
    name: str            # display name, e.g. "Flamengo", "Flamengo (PI)"
    state: str | None = None
    country: str | None = "BRA"  # None when unknown (stateless, unlisted club)
    known: bool = False  # True when matched against the curated club list


def fold(text: str) -> str:
    """Lower-case, strip accents and punctuation, collapse whitespace.

    Dotted abbreviations are joined: ``"C. R. B."`` -> ``"crb"``, ``"Vitoria F. C."`` -> ``"vitoria fc"``.
    """
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\b([a-z])\.\s*(?=[a-z]\b\.?)", r"\1", text.lower())
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _strip_noise(key: str) -> str:
    words = key.split()
    while len(words) > 1 and words[0] in _NOISE:
        words = words[1:]
    while len(words) > 1 and (words[-1] in _NOISE or words[-1] == "sport"):
        words = words[:-1]
    return " ".join(words)


def _slug(text: str) -> str:
    return fold(text).replace(" ", "-")


_ALIASES: dict[str, tuple[str, str]] = {}
for _name, _state, _aliases in _CLUBS:
    for _alias in [fold(_name)] + _aliases:
        _ALIASES.setdefault(_alias, (_name, _state))

_PAREN_RE = re.compile(r"^(.*?)\s*\(([A-Za-z]{3})\)\s*$")
_SUFFIX_RE = re.compile(r"^(.+?)(\s*-\s*|\s+)([A-Za-z]{2,3})\s*$")


def split_suffix(raw: str) -> tuple[str, str | None, str | None]:
    """Split a state/country suffix off a team name.

    ``"Palmeiras-SP"`` -> ("Palmeiras", "SP", None);
    ``"Nacional (URU)"`` -> ("Nacional", None, "URU");
    ``"Flamengo"`` -> ("Flamengo", None, None).
    """
    raw = " ".join(raw.replace(" ", " ").split())
    m = _PAREN_RE.match(raw)
    if m and m.group(2).upper() in COUNTRY_TAGS:
        return m.group(1).strip(), None, COUNTRY_TAGS[m.group(2).upper()]
    m = _SUFFIX_RE.match(raw)
    if m:
        base, sep, tag = m.group(1).strip(), m.group(2), m.group(3)
        explicit = tag.isupper() or "-" in sep
        if explicit and tag.upper() in BRAZIL_STATES:
            return base, tag.upper(), None
        if explicit and tag.upper() in COUNTRY_TAGS:
            return base, None, COUNTRY_TAGS[tag.upper()]
    return raw, None, None


def _lookup(key: str, state: str | None) -> tuple[str, str] | None:
    for k in (key, _strip_noise(key)):
        if state and f"{k} {state.lower()}" in _ALIASES:
            return _ALIASES[f"{k} {state.lower()}"]
    for k in (key, _strip_noise(key)):
        if k in _ALIASES:
            return _ALIASES[k]
    return None


@lru_cache(maxsize=None)
def normalize_team(raw: str, state: str | None = None) -> Team:
    """Return the canonical ``Team`` for a raw dataset (or user) spelling."""
    raw = re.sub(r"\s*\(antigo[^)]*\)", "", (raw or "").strip())  # "Boavista Sport Club (antigo ...)"
    base, suffix_state, country = split_suffix(raw)
    st = (state or suffix_state or "").strip().upper() or None
    if st not in BRAZIL_STATES:
        st = None

    if country:
        key = _strip_noise(fold(base))
        return Team(id=f"{key.replace(' ', '-')}-{country.lower()}", name=f"{base} ({country})",
                    state=None, country=country)

    key = fold(base)
    alias = _lookup(key, st)
    if alias:
        name, home_state = alias
        if st and st != home_state:
            # A different club sharing a famous name, e.g. Flamengo-PI or Botafogo-PB.
            return Team(id=f"{_slug(name)}-{st.lower()}", name=f"{name} ({st})", state=st, known=True)
        return Team(id=_slug(name), name=name, state=home_state, known=True)

    key = _strip_noise(key)
    slug = key.replace(" ", "-")
    if st:
        return Team(id=f"{slug}-{st.lower()}", name=_title(base), state=st)
    return Team(id=slug, name=_title(base), state=None, country=None)


def _title(text: str) -> str:
    small = {"de", "da", "do", "das", "dos", "e"}
    out = []
    for i, word in enumerate(text.split()):
        if i and word.lower() in small:
            out.append(word.lower())
        elif word.isupper() and len(word) <= 4:
            out.append(word)
        elif word.islower() or word.isupper():
            out.append(word[:1].upper() + word[1:].lower())
        else:
            out.append(word)
    return " ".join(out)
