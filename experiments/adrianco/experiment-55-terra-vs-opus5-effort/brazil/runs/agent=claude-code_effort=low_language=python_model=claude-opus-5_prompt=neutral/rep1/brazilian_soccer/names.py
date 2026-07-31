"""
Context
=======
Module: brazilian_soccer.names

Problem this solves: the six datasets spell the same club in many different ways.

    "Palmeiras-SP"                              (Brasileirao_Matches.csv)
    "Palmeiras"                                 (novo_campeonato_brasileiro.csv)
    "Sociedade Esportiva Palmeiras - SP"        (Brazilian_Cup_Matches.csv style)
    "Sao Paulo" vs "São Paulo"                  (accents present or stripped)
    "Nacional (URU)", "Barcelona-EQU"           (foreign clubs in Libertadores)

`normalize_team()` folds all of those onto a single key so that head-to-head,
standings and filtering work across files.  The algorithm is deliberately
conservative -- it only removes tokens that are club-type boilerplate
("esporte clube", "futebol", "sociedade esportiva", ...) or a trailing
state/country code -- and an explicit ALIASES table pins the handful of cases
that boilerplate stripping cannot resolve (e.g. "Vasco" == "Vasco da Gama",
"Atletico-MG" == "Atlético Mineiro").

`display_name()` returns the nicest human spelling seen for a normalised key;
the loader feeds it every raw spelling encountered so that answers show
"São Paulo" rather than "sao paulo".
"""

from __future__ import annotations

import re
import unicodedata

# Two/three letter Brazilian state codes plus the country codes used by the
# Libertadores file for non-Brazilian clubs.
STATE_CODES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}
COUNTRY_CODES = {
    "ARG", "URU", "PAR", "CHI", "BOL", "PER", "EQU", "COL", "VEN", "MEX",
    "BRA", "USA", "CRC", "HON", "JAM", "PAN",
}

# Club-type boilerplate, longest first so multi-word forms match before parts.
_BOILERPLATE = [
    "sociedade esportiva",
    "associacao atletica",
    "associacao desportiva",
    "associacao chapecoense de futebol",
    "clube atletico",
    "clube de regatas do",
    "clube de regatas",
    "esporte clube",
    "esportivo clube",
    "futebol clube",
    "atletico clube",
    "gremio foot ball porto alegrense",
    "gremio football porto alegrense",
    "sport club",
    "sport clube",
    "sporting club",
    "recreativo",
    "regatas",
    "futebol",
    "esporte",
    "esportiva",
    "esportivo",
    "clube",
    "club",
    " ec",
    " fc",
    " sc",
    " ac",
]

# Canonical key -> the set of raw-normalised spellings that mean the same club.
ALIASES = {
    "vasco da gama": {"vasco", "vasco gama", "regatas vasco da gama"},
    "atletico mineiro": {"atletico mg", "atletico mineiro mg"},
    "atletico paranaense": {"atletico pr", "athletico pr", "athletico paranaense", "parana atletico"},
    "atletico goianiense": {"atletico go", "atletico goianiense go"},
    "america mineiro": {"america mg", "america minas gerais", "america de minas gerais"},
    "america carioca": {"america rj"},
    "america de natal": {"america rn"},
    "sao paulo": {"sao paulo sp", "sao paulo futebol"},
    "botafogo": {"botafogo rj", "botafogo de futebol e regatas", "botafogo de regatas"},
    "botafogo sp": {"botafogo ribeirao preto"},
    "gremio": {"gremio rs", "gremio porto alegrense"},
    "internacional": {"internacional rs", "internacional porto alegre"},
    "corinthians": {"corinthians sp", "corinthians paulista", "sport corinthians paulista"},
    "flamengo": {"flamengo rj", "regatas do flamengo", "regatas flamengo"},
    "fluminense": {"fluminense rj", "fluminense de futebol"},
    "palmeiras": {"palmeiras sp"},
    "santos": {"santos sp", "santos futebol"},
    "cruzeiro": {"cruzeiro mg"},
    "sport recife": {"sport pe", "sport recife pe", "sport", "sport do recife", "do recife"},
    "chapecoense": {"chapecoense sc", "chapecoense de futebol"},
    "bahia": {"bahia ba"},
    "vitoria": {"vitoria ba"},
    "ceara": {"ceara ce", "ceara sporting"},
    "fortaleza": {"fortaleza ce"},
    "coritiba": {"coritiba pr"},
    "goias": {"goias go"},
    "figueirense": {"figueirense sc"},
    "avai": {"avai sc"},
    "juventude": {"juventude rs"},
    "ponte preta": {"ponte preta sp", "aa ponte preta"},
    "portuguesa": {"portuguesa sp", "associacao portuguesa de desportos"},
    "nautico": {"nautico pe", "nautico capibaribe"},
    "csa": {"csa al"},
    "crb": {"crb al"},
    "cuiaba": {"cuiaba mt"},
    "bragantino": {"red bull bragantino", "rb bragantino", "bragantino sp"},
    "sao caetano": {"sao caetano sp"},
    "santa cruz": {"santa cruz pe"},
    "parana": {"parana pr", "parana clube"},
    "joinville": {"joinville sc"},
    "criciuma": {"criciuma sc"},
    "guarani": {"guarani sp", "guarani de campinas"},
    "vila nova": {"vila nova go"},
    "remo": {"remo pa", "clube do remo"},
    "paysandu": {"paysandu pa"},
    "abc": {"abc rn"},
    "brasiliense": {"brasiliense df"},
    "ipatinga": {"ipatinga mg"},
    "barueri": {"gremio barueri", "gremio prudente"},
}

# Flattened reverse map, built once at import time.
_ALIAS_TO_CANONICAL: dict[str, str] = {}
for _canon, _variants in ALIASES.items():
    _ALIAS_TO_CANONICAL[_canon] = _canon
    for _v in _variants:
        _ALIAS_TO_CANONICAL[_v] = _canon

# Traditional derbies, keyed by the frozenset of the two canonical names.
DERBIES = {
    frozenset({"flamengo", "fluminense"}): "Fla-Flu",
    frozenset({"flamengo", "vasco da gama"}): "Clássico dos Milhões",
    frozenset({"flamengo", "botafogo"}): "Clássico da Rivalidade",
    frozenset({"botafogo", "vasco da gama"}): "Clássico da Amizade",
    frozenset({"fluminense", "vasco da gama"}): "Clássico dos Gigantes",
    frozenset({"corinthians", "palmeiras"}): "Derby Paulista",
    frozenset({"corinthians", "sao paulo"}): "Majestoso",
    frozenset({"corinthians", "santos"}): "Clássico Alvinegro",
    frozenset({"palmeiras", "sao paulo"}): "Choque-Rei",
    frozenset({"palmeiras", "santos"}): "Clássico da Saudade",
    frozenset({"santos", "sao paulo"}): "San-São",
    frozenset({"gremio", "internacional"}): "Grenal",
    frozenset({"atletico mineiro", "cruzeiro"}): "Clássico Mineiro",
    frozenset({"bahia", "vitoria"}): "Ba-Vi",
    frozenset({"ceara", "fortaleza"}): "Clássico-Rei",
    frozenset({"atletico paranaense", "coritiba"}): "Atletiba",
    frozenset({"nautico", "sport recife"}): "Clássico dos Clássicos",
    frozenset({"santa cruz", "sport recife"}): "Clássico das Multidões",
    frozenset({"goias", "vila nova"}): "Clássico Goianiense",
}

_PUNCT_RE = re.compile(r"[^a-z0-9]+")
_PAREN_RE = re.compile(r"\(([^)]*)\)")


def strip_accents(text: str) -> str:
    """São Paulo -> Sao Paulo (NFD decompose, drop combining marks)."""
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )


def _strip_region_suffix(tokens: list[str]) -> tuple[list[str], str | None]:
    """Remove a trailing state/country code token, returning it separately."""
    if len(tokens) > 1:
        last = tokens[-1].upper()
        if last in STATE_CODES or last in COUNTRY_CODES:
            return tokens[:-1], last
    return tokens, None


def split_region(raw: str) -> tuple[str, str | None]:
    """Return (name without the region marker, region code or None).

    Handles "Palmeiras-SP", "América - MG", "Nacional (URU)" and "Barcelona-EQU".
    """
    if not raw:
        return "", None
    text = raw.strip()
    region = None
    for match in _PAREN_RE.finditer(text):
        candidate = strip_accents(match.group(1)).strip().upper()
        if candidate in STATE_CODES or candidate in COUNTRY_CODES:
            region = candidate
            text = text.replace(match.group(0), " ")
    text = strip_accents(text)
    tokens = [t for t in _PUNCT_RE.split(text.lower()) if t]
    tokens, suffix = _strip_region_suffix(tokens)
    return " ".join(tokens), region or suffix


# Base names shared by several distinct clubs, where the state suffix is the
# only thing telling them apart: Atlético-MG (Mineiro) vs Athletico-PR
# (Paranaense) vs Atlético-GO (Goianiense); América-MG vs América-RJ vs
# América-RN; Botafogo-RJ vs Botafogo-SP.  For these the suffix is kept in the
# key (and then resolved by ALIASES); for every other club it is dropped so
# that "Palmeiras" and "Palmeiras-SP" agree.
AMBIGUOUS_BASES = {
    "atletico", "america", "botafogo", "nacional", "portuguesa", "sao jose",
    "operario", "juventus", "santa cruz", "rio branco", "guarani", "brasil",
    "uniao", "central", "sport", "gremio", "ferroviario", "ferroviaria",
    "independente", "santos", "comercial", "inter", "real",
}

# Spelling variants that are the same word.
_SPELLING_FIXES = (
    ("athletico", "atletico"),
    ("atletico clube", "atletico"),
    ("gremio foot", "gremio"),
)


def normalize_team(raw: str) -> str:
    """Fold any spelling of a club onto its canonical lowercase key.

    Returns "" for empty/blank input so callers can filter unusable rows.
    """
    if not raw:
        return ""
    name, region = split_region(raw)
    if not name:
        return ""
    for wrong, right in _SPELLING_FIXES:
        if name.startswith(wrong):
            name = right + name[len(wrong):]
    padded = f" {name} "
    for phrase in _BOILERPLATE:
        token = phrase if phrase.startswith(" ") else f" {phrase} "
        if token in padded and padded.replace(token, " ").strip():
            padded = padded.replace(token, " ")
    name = " ".join(padded.split())
    if not name:
        name, region = split_region(raw)
    if name in AMBIGUOUS_BASES and region:
        name = f"{name} {region.lower()}"
    return _ALIAS_TO_CANONICAL.get(name, name)


def derby_name(team_a: str, team_b: str) -> str | None:
    """Return the popular name of the derby between two clubs, if any."""
    return DERBIES.get(frozenset({normalize_team(team_a), normalize_team(team_b)}))


class DisplayNames:
    """Remembers the prettiest raw spelling seen for each canonical key.

    "Prettiest" = the shortest spelling, with a bonus for spellings that carry
    accents, so "São Paulo" beats both "Sao Paulo" and
    "Sao Paulo Futebol Clube - SP".
    """

    def __init__(self) -> None:
        self._best: dict[str, str] = {}

    @staticmethod
    def _score(raw: str) -> tuple[int, int]:
        has_accent = 0 if raw != strip_accents(raw) else 1
        return (has_accent, len(raw))

    def observe(self, raw: str) -> str:
        key = normalize_team(raw)
        if not key:
            return ""
        clean = re.sub(r"\s+", " ", raw).strip()
        current = self._best.get(key)
        if current is None or self._score(clean) < self._score(current):
            self._best[key] = clean
        return key

    def display(self, key: str) -> str:
        return self._best.get(key, key.title())

    def keys(self) -> list[str]:
        return list(self._best)
