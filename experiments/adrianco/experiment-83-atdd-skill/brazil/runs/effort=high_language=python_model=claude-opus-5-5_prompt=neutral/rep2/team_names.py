"""Team-name normalization for the Brazilian soccer datasets.

The CSV files spell the same club in many different ways, for example:

    "Palmeiras-SP", "Palmeiras - SP", "Palmeiras", "SE Palmeiras"
    "Atlético-MG", "Atletico Mineiro", "Atlético Mineiro - MG"
    "Athletico-PR", "Atletico Paranaense", "Athletico", "Atlético - PR"
    "Sport Club Corinthians Paulista", "Corinthians-SP"

`canonical_team_id()` maps any raw spelling (optionally with a separate state
column) to a stable id such as ``"palmeiras"`` or ``"atletico-mg"``.  Clubs that
share a name but come from a different state (Botafogo-PB vs Botafogo-RJ,
Flamengo-PI vs Flamengo-RJ) or country (Guaraní of Paraguay vs Guarani-SP) get
a state/country-qualified id so they are never merged with the big club.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

BRAZILIAN_STATES = frozenset(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)

# Non-standard region codes seen in the data, mapped to a state.
_STATE_FIXUPS = {"POA": "RS"}


@dataclass(frozen=True)
class Club:
    id: str
    name: str
    state: str
    aliases: tuple[str, ...]


def _club(cid: str, name: str, state: str, *aliases: str) -> Club:
    return Club(cid, name, state, tuple(aliases))


# Well-known clubs. Aliases are written in normalized form (lowercase, no
# accents, punctuation replaced by spaces).
KNOWN_CLUBS: tuple[Club, ...] = (
    _club("flamengo", "Flamengo", "RJ", "flamengo", "cr flamengo", "clube de regatas do flamengo", "mengao"),
    _club("flamengo-pi", "Flamengo-PI", "PI", "flamengo pi", "flamengo do piaui"),
    _club("fluminense", "Fluminense", "RJ", "fluminense", "fluminense football club"),
    _club("botafogo", "Botafogo", "RJ", "botafogo", "botafogo de futebol e regatas"),
    _club("vasco", "Vasco da Gama", "RJ", "vasco", "vasco da gama", "club de regatas vasco da gama",
          "cr vasco da gama"),
    _club("palmeiras", "Palmeiras", "SP", "palmeiras", "sociedade esportiva palmeiras", "verdao"),
    _club("corinthians", "Corinthians", "SP", "corinthians", "sport club corinthians paulista",
          "corinthians paulista", "timao"),
    _club("sao paulo", "São Paulo", "SP", "sao paulo", "sao paulo futebol clube", "spfc", "tricolor paulista"),
    _club("santos", "Santos", "SP", "santos", "santos futebol clube", "peixe"),
    _club("gremio", "Grêmio", "RS", "gremio", "gremio fbpa", "gremio foot ball porto alegrense"),
    _club("internacional", "Internacional", "RS", "internacional", "inter", "sport club internacional"),
    _club("cruzeiro", "Cruzeiro", "MG", "cruzeiro", "cruzeiro esporte clube"),
    _club("atletico-mg", "Atlético Mineiro", "MG", "atletico mg", "atletico mineiro", "clube atletico mineiro",
          "galo"),
    _club("athletico-pr", "Athletico Paranaense", "PR", "athletico pr", "atletico pr", "athletico",
          "athletico paranaense", "atletico paranaense", "club athletico paranaense", "furacao"),
    _club("atletico-go", "Atlético Goianiense", "GO", "atletico go", "atletico goianiense", "dragao"),
    _club("america-mg", "América Mineiro", "MG", "america mg", "america mineiro", "america fc minas gerais"),
    _club("america-rn", "América de Natal", "RN", "america rn", "america fc natal", "america de natal"),
    _club("bahia", "Bahia", "BA", "bahia", "esporte clube bahia"),
    _club("vitoria", "Vitória", "BA", "vitoria", "esporte clube vitoria"),
    _club("sport", "Sport Recife", "PE", "sport", "sport recife", "sport club do recife", "sport club recife"),
    _club("nautico", "Náutico", "PE", "nautico", "nautico capibaribe", "clube nautico capibaribe"),
    _club("santa cruz", "Santa Cruz", "PE", "santa cruz", "santa cruz futebol clube"),
    _club("ceara", "Ceará", "CE", "ceara", "ceara sporting club", "ceara sporting"),
    _club("fortaleza", "Fortaleza", "CE", "fortaleza", "fortaleza esporte clube"),
    _club("goias", "Goiás", "GO", "goias", "goias esporte clube"),
    _club("coritiba", "Coritiba", "PR", "coritiba", "coritiba foot ball club"),
    _club("parana", "Paraná Clube", "PR", "parana", "parana clube"),
    _club("chapecoense", "Chapecoense", "SC", "chapecoense", "associacao chapecoense de futebol"),
    _club("avai", "Avaí", "SC", "avai"),
    _club("figueirense", "Figueirense", "SC", "figueirense"),
    _club("criciuma", "Criciúma", "SC", "criciuma"),
    _club("joinville", "Joinville", "SC", "joinville"),
    _club("juventude", "Juventude", "RS", "juventude"),
    _club("ponte preta", "Ponte Preta", "SP", "ponte preta", "aa ponte preta"),
    _club("guarani", "Guarani", "SP", "guarani"),
    _club("portuguesa", "Portuguesa", "SP", "portuguesa", "portuguesa desportos",
          "associacao portuguesa de desportos"),
    _club("bragantino", "Red Bull Bragantino", "SP", "bragantino", "red bull bragantino", "rb bragantino"),
    _club("cuiaba", "Cuiabá", "MT", "cuiaba"),
    _club("csa", "CSA", "AL", "csa", "cs alagoano", "centro sportivo alagoano"),
    _club("crb", "CRB", "AL", "crb", "clube de regatas brasil"),
    _club("sao caetano", "São Caetano", "SP", "sao caetano"),
    _club("santo andre", "Santo André", "SP", "santo andre"),
    _club("barueri", "Grêmio Barueri", "SP", "barueri", "gremio barueri"),
    _club("gremio prudente", "Grêmio Prudente", "SP", "gremio prudente"),
    _club("paysandu", "Paysandu", "PA", "paysandu"),
    _club("remo", "Remo", "PA", "remo", "clube do remo"),
    _club("brasiliense", "Brasiliense", "DF", "brasiliense"),
    _club("ipatinga", "Ipatinga", "MG", "ipatinga"),
    _club("vila nova", "Vila Nova", "GO", "vila nova"),
    _club("abc", "ABC", "RN", "abc"),
)

CLUBS_BY_ID: dict[str, Club] = {c.id: c for c in KNOWN_CLUBS}

ALIASES: dict[str, str] = {}
for _c in KNOWN_CLUBS:
    for _a in _c.aliases:
        ALIASES[_a] = _c.id

# Foreign clubs whose spelling varies within the Libertadores file.
FOREIGN_ALIASES: dict[str, str] = {
    "libertad par": "libertad",
    "delfin equ": "delfin",
    "olimpia par": "olimpia",
}

# Bare names that are too generic to identify a club without a state.
_AMBIGUOUS_BASES = frozenset({"atletico", "america", "nacional", "universitario"})

# Generic words that may be stripped from either end of a club name.
_FILLER = frozenset({"fc", "ec", "sc", "clube", "club", "futebol", "esporte", "de", "do", "da", "se", "cr", "fr",
                     "football", "esportivo"})


def strip_accents(text: str) -> str:
    """Remove diacritics: 'São Paulo' -> 'Sao Paulo'."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_text(text: str) -> str:
    """Lowercase, accent-free, punctuation-free, single-spaced text.

    Runs of single letters are joined so 'C. R. B.' and 'A.b.c.' become 'crb'
    and 'abc'.
    """
    text = strip_accents(text).lower().replace(".", " ").replace("'", "")
    tokens = re.sub(r"[^a-z0-9]+", " ", text).split()
    out: list[str] = []
    run = ""
    for tok in tokens:
        if len(tok) == 1 and tok.isalpha():
            run += tok
            continue
        if run:
            out.append(run)
            run = ""
        out.append(tok)
    if run:
        out.append(run)
    return " ".join(out)


def _strip_filler(base: str) -> str:
    tokens = base.split()
    while len(tokens) > 1 and tokens[0] in _FILLER:
        tokens.pop(0)
    while len(tokens) > 1 and tokens[-1] in _FILLER:
        tokens.pop()
    return " ".join(tokens)


_PAREN_CODE = re.compile(r"^(.*?)\s*\(([A-Z]{2,3})\)$")
_DASH_CODE = re.compile(r"^(.*\S)\s*-\s*([A-Z]{2,3})$")
_SPACE_UF = re.compile(r"^(.*\S)\s+([A-Z]{2})$")


def split_state(raw: str) -> tuple[str, str | None]:
    """Split a trailing state/country code from a raw team name.

    >>> split_state("Palmeiras-SP")
    ('Palmeiras', 'SP')
    >>> split_state("Nacional (URU)")
    ('Nacional', 'URU')
    >>> split_state("Botafogo RJ")
    ('Botafogo', 'RJ')
    """
    raw = raw.strip()
    for pattern in (_PAREN_CODE, _DASH_CODE):
        m = pattern.match(raw)
        if m:
            return m.group(1).strip(), _STATE_FIXUPS.get(m.group(2), m.group(2))
    m = _SPACE_UF.match(raw)
    if m and m.group(2) in BRAZILIAN_STATES:
        return m.group(1).strip(), m.group(2)
    return raw, None


def _lookup_alias(base: str, state: str | None) -> str | None:
    candidates = []
    if state:
        candidates.append(f"{base} {state.lower()}")
    candidates.append(base)
    stripped = _strip_filler(base)
    if stripped != base:
        if state:
            candidates.append(f"{stripped} {state.lower()}")
        candidates.append(stripped)
    for cand in candidates:
        if cand in ALIASES:
            return ALIASES[cand]
        if cand in FOREIGN_ALIASES:
            return FOREIGN_ALIASES[cand]
    return None


def canonical_team_id(raw: str, state: str | None = None) -> str:
    """Return a stable id for a raw team name.

    ``state`` is an optional state column value used when the name itself
    carries no suffix (e.g. the 2003-2019 file stores 'Grêmio' + 'RS').
    """
    name, suffix = split_state(raw)
    # Drop explanatory parentheticals such as "(antigo Esporte Clube Barreira)".
    name = re.sub(r"\([^)]*\)", " ", name)
    st = suffix or (state.strip().upper() if state and state.strip() else None)
    base = normalize_text(name)
    if not base:
        return normalize_text(raw)

    cid = _lookup_alias(base, st)
    if cid is not None:
        club = CLUBS_BY_ID.get(cid)
        # Only a suffix in the name itself disambiguates; separate state
        # columns contain errors (e.g. 'Bahia' + 'BH', 'Vitória' + 'ES').
        if club is not None and suffix and st != club.state:
            # Same name, different club (e.g. Botafogo-PB, Flamengo-PI, Guaraní-PAR).
            return f"{_strip_filler(base)}-{st.lower()}"
        return cid

    stripped = _strip_filler(base)
    if st and (st not in BRAZILIAN_STATES or stripped in _AMBIGUOUS_BASES):
        return f"{stripped}-{st.lower()}"
    return stripped


def display_name(team_id: str) -> str | None:
    """Preferred display name for a known club id, else None."""
    club = CLUBS_BY_ID.get(team_id)
    return club.name if club else None


# FIFA 19 club names for Brazilian clubs present in fifa_data.csv.  FIFA 19 did
# not license Flamengo, Palmeiras, Corinthians, São Paulo, Vasco and others.
FIFA_CLUB_TO_TEAM: dict[str, str] = {
    "Grêmio": "gremio",
    "Atlético Mineiro": "atletico-mg",
    "Cruzeiro": "cruzeiro",
    "Fluminense": "fluminense",
    "Santos": "santos",
    "Internacional": "internacional",
    "América FC (Minas Gerais)": "america-mg",
    "Botafogo": "botafogo",
    "Bahia": "bahia",
    "Paraná": "parana",
    "Atlético Paranaense": "athletico-pr",
    "Vitória": "vitoria",
    "Sport Club do Recife": "sport",
    "Chapecoense": "chapecoense",
    "Ceará Sporting Club": "ceara",
}
TEAM_TO_FIFA_CLUB: dict[str, str] = {v: k for k, v in FIFA_CLUB_TO_TEAM.items()}


# Traditional Brazilian derbies (unordered pairs of team ids).
DERBIES: dict[frozenset[str], str] = {
    frozenset({"flamengo", "fluminense"}): "Fla-Flu",
    frozenset({"flamengo", "vasco"}): "Clássico dos Milhões",
    frozenset({"flamengo", "botafogo"}): "Clássico da Rivalidade",
    frozenset({"fluminense", "vasco"}): "Clássico dos Gigantes",
    frozenset({"botafogo", "fluminense"}): "Clássico Vovô",
    frozenset({"botafogo", "vasco"}): "Clássico da Amizade",
    frozenset({"corinthians", "palmeiras"}): "Derby Paulista",
    frozenset({"palmeiras", "sao paulo"}): "Choque-Rei",
    frozenset({"corinthians", "sao paulo"}): "Majestoso",
    frozenset({"santos", "sao paulo"}): "San-São",
    frozenset({"corinthians", "santos"}): "Clássico Alvinegro",
    frozenset({"palmeiras", "santos"}): "Clássico da Saudade",
    frozenset({"gremio", "internacional"}): "Grenal",
    frozenset({"atletico-mg", "cruzeiro"}): "Clássico Mineiro",
    frozenset({"athletico-pr", "coritiba"}): "Atletiba",
    frozenset({"bahia", "vitoria"}): "Ba-Vi",
    frozenset({"ceara", "fortaleza"}): "Clássico-Rei",
    frozenset({"nautico", "sport"}): "Clássico dos Clássicos",
    frozenset({"santa cruz", "sport"}): "Clássico das Multidões",
    frozenset({"atletico-go", "goias"}): "Clássico Goiano",
    frozenset({"avai", "figueirense"}): "Clássico da Capital",
    frozenset({"guarani", "ponte preta"}): "Dérbi Campineiro",
    frozenset({"paysandu", "remo"}): "Re-Pa",
    frozenset({"crb", "csa"}): "Clássico Alagoano",
}


def derby_name(team_a: str, team_b: str) -> str | None:
    return DERBIES.get(frozenset({team_a, team_b}))
