"""Entity resolution for Brazilian club names.

Context
-------
The five match CSVs in ``data/kaggle`` spell the same club in many different
ways -- ``"Palmeiras-SP"``, ``"Palmeiras - SP"``, ``"Palmeiras"``,
``"Sport Club do Recife"`` vs ``"Sport-PE"``, ``"Atlético-MG"`` vs
``"Atletico Mineiro"``.  The FIFA player file adds a sixth convention
(``"América FC (Minas Gerais)"``).  Every downstream feature -- head to head
records, standings, cross-file joins between players and matches -- depends on
mapping all of those spellings onto a single club node.

Resolution happens in two stages:

1. *Mechanical normalisation* (:func:`parse_team_name`) strips accents, pulls a
   trailing state/country code off the name (``-SP``, ``" - RJ"``, ``"(URU)"``,
   ``" MG"``), joins dotted acronyms (``"A.b.c."`` -> ``"abc"``), removes club
   type words (``FC``, ``Esporte Clube``, ``Sport Club``...) and connector words
   (``de``, ``do``, ``da``).  Most variant spellings collapse at this point.
2. *A curated registry* (:data:`CLUBS`, 358 clubs) settles what normalisation
   cannot: names that differ substantively between files (``"Sport"`` vs
   ``"Sport Club do Recife"``), and clubs that share a name but are not the same
   club.  It also carries display names, home states and nicknames, so ``"Timão"``
   and ``"Fla"`` resolve too.  Clubs outside it still get a stable derived id --
   eight of the 363 clubs in the data are resolved that way.

Ambiguity is handled explicitly: a base name registered for more than one state
(``América``-MG/RN, ``Botafogo``-RJ/PB/SP, ``Vitória``-BA/ES ...) never collapses
into one node -- an unregistered state produces its own ``base-uf`` id instead.

Public API: :func:`resolve_team`, :func:`resolve_competition`,
:func:`search_clubs`, :func:`normalize_query`.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable

__all__ = [
    "UF_STATES",
    "COUNTRY_CODES",
    "Club",
    "TeamRef",
    "CLUBS",
    "DERBIES",
    "strip_accents",
    "slugify",
    "parse_team_name",
    "resolve_team",
    "resolve_competition",
    "search_clubs",
    "normalize_query",
    "known_club",
]


# --------------------------------------------------------------------------
# Region codes
# --------------------------------------------------------------------------

UF_STATES: dict[str, str] = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
}

COUNTRY_CODES: dict[str, str] = {
    "ARG": "Argentina",
    "BOL": "Bolivia",
    "BRA": "Brazil",
    "CHI": "Chile",
    "COL": "Colombia",
    "EQU": "Ecuador",
    "MEX": "Mexico",
    "PAR": "Paraguay",
    "PER": "Peru",
    "URU": "Uruguay",
    "VEN": "Venezuela",
}

_REGION_CODES = set(UF_STATES) | set(COUNTRY_CODES)


# --------------------------------------------------------------------------
# String helpers
# --------------------------------------------------------------------------

_CLUB_PHRASES = (
    "clube de regatas",
    "sport club",
    "sport clube",
    "esporte clube",
    "futebol clube",
    "atletico clube",
    "associacao atletica",
    "gremio esportivo",
    "esporte c",
    "futebol regatas",
)

_CLUB_TOKENS = {
    "fc",
    "ec",
    "sc",
    "cf",
    "ca",
    "aa",
    "ad",
    "ge",
    "cr",
    "fr",
    "se",
    "clube",
    "club",
    "futebol",
    "esporte",
    "esportes",
    "desportos",
    "ltda",
    "sociedade",
}

_CONNECTORS = {"de", "do", "da", "dos", "das", "del", "e"}


def strip_accents(text: str) -> str:
    """Return *text* with diacritics removed (``"Grêmio"`` -> ``"Gremio"``)."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def slugify(text: str) -> str:
    """Lower case, accent free, hyphen separated identifier."""
    cleaned = re.sub(r"[^a-z0-9]+", "-", strip_accents(text).lower())
    return cleaned.strip("-")


def _split_region(raw: str) -> tuple[str, str | None]:
    """Split a trailing state/country code off *raw*.

    Handles ``"Palmeiras-SP"``, ``"América - MG"``, ``"Nacional (URU)"`` and
    ``"Vasco Da Gama RJ"``.  Only recognised codes are stripped, so
    ``"Colo-Colo"`` and ``"Ji-paraná"`` survive intact.
    """
    text = raw.strip()
    patterns = (
        r"\s*[-–—]\s*([A-Za-z]{2,3})\s*$",  # "Palmeiras-SP", "América - MG"
        r"\s*\(\s*([A-Za-z]{2,3})\s*\)\s*$",  # "Nacional (URU)", "River (PI)"
        r"\s+([A-Za-z]{2,3})\s*$",  # "America MG", "Vasco Da Gama RJ"
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        code = match.group(1).upper()
        if code not in _REGION_CODES:
            continue
        remainder = text[: match.start()].strip(" -–—")
        if remainder:
            return remainder, code
    return text, None


def _join_initial_runs(tokens: list[str]) -> list[str]:
    """Collapse runs of single letters: ``["a","b","c"]`` -> ``["abc"]``."""
    out: list[str] = []
    run: list[str] = []
    for token in tokens:
        if len(token) == 1 and token.isalpha():
            run.append(token)
            continue
        if len(run) > 1:
            out.append("".join(run))
        elif run:
            out.extend(run)
        run = []
        out.append(token)
    if len(run) > 1:
        out.append("".join(run))
    elif run:
        out.extend(run)
    return out


def normalize_query(text: str) -> str:
    """Accent free, lower case, single spaced text (used for free-text search)."""
    return re.sub(r"\s+", " ", strip_accents(text).lower()).strip()


def _normalize_base(name: str) -> str:
    """Reduce a club name (region already removed) to its comparison key."""
    text = strip_accents(name).lower()
    text = text.replace("&", " ").replace("'", "")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    for phrase in _CLUB_PHRASES:
        if text == phrase:
            continue
        text = re.sub(rf"(?:^|\s){re.escape(phrase)}(?:\s|$)", " ", text).strip()

    tokens = _join_initial_runs(text.split())
    if len(tokens) == 2 and tokens[0] in {"club", "clube"}:
        # "Club América" is the club's whole identity, unlike "Clube do Remo"
        # (three tokens) or "EC Bahia", where the prefix is just a club type.
        return " ".join(tokens)
    kept = [t for t in tokens if t not in _CLUB_TOKENS and t not in _CONNECTORS]
    if not kept:  # the whole name was made of club-type words, keep it as is
        kept = tokens
    return " ".join(kept).strip()


@dataclass(frozen=True, slots=True)
class ParsedName:
    """Mechanically normalised club name.

    ``region`` is the code embedded in the name itself; ``hint`` is a code that
    came from a separate column of the source file.  They are kept apart on
    purpose -- ``novo_campeonato_brasileiro.csv`` files Vitória (Bahia) under
    ``Mandante_UF = "ES"``, so the name is the stronger signal.
    """

    base: str
    region: str | None
    raw: str
    hint: str | None = None


def parse_team_name(raw: str, state_hint: str | None = None) -> ParsedName:
    """Normalise *raw* into a ``(base, region)`` pair."""
    name, region = _split_region(raw or "")
    name = name.replace("(", " ").replace(")", " ")
    base = _normalize_base(name)
    hint = None
    if state_hint:
        candidate = strip_accents(state_hint).strip().upper()
        if candidate in _REGION_CODES:
            hint = candidate
    return ParsedName(base=base, region=region, raw=(raw or "").strip(), hint=hint)


# --------------------------------------------------------------------------
# Curated club registry
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Club:
    """A canonical club node.

    ``claims_base`` decides whether the club may own its *bare* name, i.e. the
    spelling without a state code.  ``Santos`` (SP) claims ``"santos"`` while
    ``Santos-AP`` does not, so an unqualified "Santos" in the Libertadores file
    resolves to the Vila Belmiro club and never to the Amapá side.
    """

    id: str
    name: str
    state: str | None = None
    country: str = "Brazil"
    aliases: tuple[str, ...] = ()
    nicknames: tuple[str, ...] = ()
    claims_base: bool = True

    @property
    def state_name(self) -> str | None:
        return UF_STATES.get(self.state or "")


def _c(
    club_id: str,
    name: str,
    state: str | None = None,
    *,
    country: str = "Brazil",
    aliases: Iterable[str] = (),
    nicknames: Iterable[str] = (),
    claims_base: bool = True,
) -> Club:
    return Club(
        id=club_id,
        name=name,
        state=state,
        country=country,
        aliases=tuple(aliases),
        nicknames=tuple(nicknames),
        claims_base=claims_base,
    )


#: Bases that must never be resolved without a region -- several distinct clubs
#: share them and picking a default would silently merge two clubs.
REQUIRES_REGION = {"atletico", "america", "sao raimundo", "rio branco"}


CLUBS: tuple[Club, ...] = (
    # -- Rio de Janeiro ----------------------------------------------------
    _c("flamengo", "Flamengo", "RJ",
       aliases=("Flamengo-RJ", "Flamengo - RJ", "CR Flamengo", "Clube de Regatas do Flamengo"),
       nicknames=("Fla", "Mengão", "Mengao", "Rubro-Negro")),
    _c("fluminense", "Fluminense", "RJ",
       aliases=("Fluminense-RJ", "Fluminense RJ", "Fluminense FC"),
       nicknames=("Flu", "Tricolor Carioca")),
    _c("botafogo-rj", "Botafogo", "RJ",
       aliases=("Botafogo-RJ", "Botafogo - RJ", "Botafogo RJ", "Botafogo de Futebol e Regatas"),
       nicknames=("Fogão", "Fogao", "Glorioso", "Botafogo do Rio")),
    _c("vasco-da-gama", "Vasco da Gama", "RJ",
       aliases=("Vasco", "Vasco da Gama-RJ", "Vasco Da Gama RJ", "Vasco da Gama - RJ", "CR Vasco da Gama"),
       nicknames=("Cruzmaltino", "Gigante da Colina")),
    _c("volta-redonda", "Volta Redonda", "RJ"),
    _c("madureira", "Madureira", "RJ", aliases=("Madureira EC", "Madureira RJ")),
    _c("boavista-rj", "Boavista", "RJ",
       aliases=("Boavista RJ", "Boavista SC Saquarema",
                "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")),
    _c("macae", "Macaé", "RJ", aliases=("Macae Esporte FC", "Macae Esporte RJ")),
    _c("resende", "Resende", "RJ", aliases=("Resende RJ",)),
    _c("bangu", "Bangu", "RJ"),
    _c("nova-iguacu", "Nova Iguaçu", "RJ"),
    _c("cabofriense", "Cabofriense", "RJ"),
    _c("americano-rj", "Americano", "RJ", aliases=("Americano RJ",)),
    _c("friburguense", "Friburguense", "RJ"),
    _c("duque-de-caxias", "Duque de Caxias", "RJ",
       aliases=("Duque de Caxias FC", "Duque De Caxias RJ")),
    _c("portuguesa-rj", "Portuguesa-RJ", "RJ", aliases=("Portuguesa RJ",), claims_base=False),
    # -- São Paulo ---------------------------------------------------------
    _c("palmeiras", "Palmeiras", "SP",
       aliases=("Palmeiras-SP", "Palmeiras - SP", "SE Palmeiras"),
       nicknames=("Verdão", "Verdao", "Porco", "Alviverde")),
    _c("corinthians", "Corinthians", "SP",
       aliases=("Corinthians-SP", "Corinthians - SP", "Sport Club Corinthians Paulista"),
       nicknames=("Timão", "Timao", "Coringão")),
    _c("sao-paulo", "São Paulo", "SP",
       aliases=("Sao Paulo", "São Paulo-SP", "São Paulo - SP", "Sao Paulo FC", "SPFC"),
       nicknames=("Tricolor Paulista", "Soberano")),
    _c("santos", "Santos", "SP",
       aliases=("Santos-SP", "Santos - SP", "Santos FC"),
       nicknames=("Peixe", "Alvinegro Praiano")),
    _c("ponte-preta", "Ponte Preta", "SP",
       aliases=("Ponte Preta-SP", "Ponte Preta - SP", "AA Ponte Preta"), nicknames=("Macaca",)),
    _c("guarani-sp", "Guarani", "SP", aliases=("Guarani SP", "Guarani-SP", "Guarani - SP")),
    _c("portuguesa-sp", "Portuguesa", "SP",
       aliases=("Portuguesa-SP", "Portuguesa - SP", "Portuguesa Desportos", "Lusa")),
    _c("bragantino-sp", "Red Bull Bragantino", "SP",
       aliases=("Bragantino", "Bragantino - SP", "Bragantino-SP",
                "Red Bull Bragantino-SP", "Red Bull Bragantino - SP", "RB Bragantino")),
    _c("red-bull-brasil", "Red Bull Brasil", "SP", aliases=("Red Bull Brasil - SP",)),
    _c("sao-caetano", "São Caetano", "SP", aliases=("Sao Caetano", "São Caetano - SP")),
    _c("santo-andre", "Santo André", "SP", aliases=("Santo Andre", "Santo Andre SP")),
    _c("oeste", "Oeste", "SP", aliases=("Oeste - SP",)),
    _c("ituano", "Ituano", "SP"),
    _c("mirassol", "Mirassol", "SP"),
    _c("botafogo-sp", "Botafogo-SP", "SP", aliases=("Botafogo SP", "Botafogo Ribeirão Preto"), claims_base=False),
    _c("sao-bento", "São Bento", "SP", aliases=("Sao Bento",)),
    _c("sao-bernardo", "São Bernardo", "SP", aliases=("Sao Bernardo",)),
    _c("ferroviaria", "Ferroviária", "SP", aliases=("Ferroviaria SP", "Ferroviária - SP")),
    _c("novorizontino", "Novorizontino", "SP", aliases=("Gremio Novorizontino", "Grêmio Novorizontino")),
    _c("gremio-barueri", "Grêmio Barueri", "SP", aliases=("Barueri", "Grêmio Barueri - SP")),
    _c("gremio-prudente", "Grêmio Prudente", "SP"),
    _c("xv-piracicaba", "XV de Piracicaba", "SP", aliases=("XV Piracicaba", "Xv de Piracicaba - SP")),
    _c("audax-sp", "Audax", "SP", aliases=("Audax SP", "Audax - SP")),
    _c("linense", "Linense", "SP"),
    _c("capivariano", "Capivariano", "SP", aliases=("Capivariano SP",)),
    _c("inter-de-limeira", "Inter de Limeira", "SP"),
    _c("mogi-mirim", "Mogi Mirim", "SP"),
    _c("guaratingueta", "Guaratinguetá", "SP", aliases=("Guaratingueta",)),
    _c("marilia", "Marília", "SP", aliases=("Marilia",)),
    _c("paulista", "Paulista", "SP", aliases=("Paulista Futebol Clube - SP",)),
    _c("noroeste", "Noroeste", "SP"),
    _c("votuporanguense", "Votuporanguense", "SP", aliases=("CA Votuporanguense",)),
    # -- Minas Gerais ------------------------------------------------------
    _c("cruzeiro", "Cruzeiro", "MG",
       aliases=("Cruzeiro-MG", "Cruzeiro - MG"), nicknames=("Raposa", "Cabuloso")),
    _c("atletico-mg", "Atlético Mineiro", "MG",
       aliases=("Atletico-MG", "Atlético-MG", "Atlético - MG", "Atletico Mineiro",
                "Atlético Mineiro - MG", "Clube Atlético Mineiro"),
       nicknames=("Galo",)),
    _c("america-mg", "América-MG", "MG",
       aliases=("America MG", "América - MG", "America - MG", "América FC (Minas Gerais)",
                "America FC MG", "América Mineiro"),
       nicknames=("Coelho",)),
    _c("tombense", "Tombense", "MG", aliases=("Tombense MG",)),
    _c("tupi", "Tupi", "MG", aliases=("Tupi MG",)),
    _c("boa-esporte", "Boa Esporte", "MG", aliases=("Boa", "Boa - MG")),
    # The extended stats file spells Vila Nova (GO) "Villa Nova"; the Minas
    # Gerais club only ever appears with its state, so it does not claim the
    # bare spelling.
    _c("villa-nova-mg", "Villa Nova-MG", "MG", aliases=("Villa Nova - MG", "Villa Nova MG"),
       claims_base=False),
    _c("uberlandia", "Uberlândia", "MG", aliases=("Uberlandia",)),
    _c("caldense", "Caldense", "MG", aliases=("Caldense MG",)),
    _c("urt", "URT", "MG", aliases=("URT MG", "Urt - MG")),
    _c("betim", "Betim", "MG"),
    _c("ipatinga", "Ipatinga", "MG"),
    _c("democrata-gv", "Democrata GV", "MG"),
    _c("athletic-club-mg", "Athletic Club", "MG", aliases=("Athletic Club MG",)),
    _c("pouso-alegre", "Pouso Alegre", "MG"),
    # -- Rio Grande do Sul -------------------------------------------------
    _c("gremio", "Grêmio", "RS",
       aliases=("Gremio", "Grêmio - RS", "Gremio RS", "Gremio-RS", "Grêmio FBPA"),
       nicknames=("Imortal", "Tricolor Gaúcho")),
    _c("internacional", "Internacional", "RS",
       aliases=("Internacional-RS", "Internacional - RS", "Internacional RS", "SC Internacional"),
       nicknames=("Inter", "Colorado")),
    _c("juventude", "Juventude", "RS",
       aliases=("Juventude-RS", "Juventude - RS", "EC Juventude")),
    _c("caxias", "Caxias", "RS", aliases=("Caxias RS", "Ser Caxias", "SER Caxias", "Caxias - RS")),
    _c("brasil-de-pelotas", "Brasil de Pelotas", "RS", aliases=("Brasil - RS", "Brasil RS")),
    _c("ypiranga-rs", "Ypiranga", "RS", aliases=("Ypiranga RS", "Ypiranga - RS")),
    _c("novo-hamburgo", "Novo Hamburgo", "RS"),
    _c("sao-jose-rs", "São José-RS", "RS", aliases=("Sao Jose RS", "São José - RS", "Sao Jose - POA")),
    _c("sao-luiz", "São Luiz", "RS", aliases=("Sao Luiz", "São Luiz - RS")),
    _c("lajeadense", "Lajeadense", "RS"),
    _c("veranopolis", "Veranópolis", "RS", aliases=("Veranopolis",)),
    _c("avenida", "Avenida", "RS"),
    _c("esportivo", "Esportivo", "RS", aliases=("Esportivo Bento Goncalves",)),
    _c("aimore", "Aimoré", "RS", aliases=("CE Aimore",)),
    _c("santa-cruz-rs", "Santa Cruz-RS", "RS", aliases=("Santa Cruz - RS", "Santa Cruz RS"), claims_base=False),
    _c("gremio-sapucaiense", "Grêmio Sapucaiense", "RS", aliases=("Gremio Esportivo Sapucaiense - RS",)),
    # -- Paraná ------------------------------------------------------------
    _c("athletico-pr", "Athletico Paranaense", "PR",
       aliases=("Athletico-PR", "Atletico-PR", "Atlético-PR", "Atlético - PR", "Atletico - PR",
                "Athletico", "Athletico Paranaense", "Atletico Paranaense", "Atlético Paranaense"),
       nicknames=("Furacão", "Furacao", "CAP")),
    _c("coritiba", "Coritiba", "PR",
       aliases=("Coritiba-PR", "Coritiba - PR", "Coritiba PR"), nicknames=("Coxa",)),
    _c("parana", "Paraná", "PR", aliases=("Parana", "Paraná - PR", "Paraná-PR", "CA Parana")),
    _c("londrina", "Londrina", "PR"),
    _c("operario-pr", "Operário-PR", "PR",
       aliases=("Operario PR", "Operário - PR", "Operario - PR",
                "Operario Ferroviario Esporte C - PR")),
    _c("cianorte", "Cianorte", "PR"),
    _c("maringa", "Maringá", "PR", aliases=("Maringa", "Metropolitano Maringa PR")),
    _c("cascavel", "FC Cascavel", "PR", aliases=("Fc Cascavel - PR",)),
    _c("pstc", "PSTC", "PR", aliases=("Pstc - PR",)),
    _c("toledo", "Toledo", "PR", aliases=("Toledo EC",)),
    _c("j-malucelli", "J. Malucelli", "PR"),
    _c("arapongas", "Arapongas", "PR", aliases=("Arapongas Esporte Clube - PR",)),
    _c("foz-do-iguacu", "Foz do Iguaçu", "PR", aliases=("Foz Do Iguacu",)),
    _c("azuriz", "Azuriz", "PR", aliases=("Azuriz FC",)),
    # -- Santa Catarina ----------------------------------------------------
    _c("avai", "Avaí", "SC", aliases=("Avai-SC", "Avaí - SC", "Avai SC")),
    _c("figueirense", "Figueirense", "SC", aliases=("Figueirense-SC", "Figueirense - SC")),
    _c("chapecoense", "Chapecoense", "SC",
       aliases=("Chapecoense-SC", "Chapecoense - SC"), nicknames=("Chape",)),
    _c("criciuma", "Criciúma", "SC", aliases=("Criciuma-SC", "Criciúma - SC", "Criciuma - SC")),
    _c("joinville", "Joinville", "SC", aliases=("Joinville-SC", "Joinville - SC")),
    _c("brusque", "Brusque", "SC"),
    _c("tubarao", "Tubarão", "SC", aliases=("Tubarao",)),
    _c("marcilio-dias", "Marcílio Dias", "SC", aliases=("Marcilio Dias",)),
    _c("camboriu", "Camboriú", "SC", aliases=("Camboriu",)),
    _c("internacional-sc", "Internacional-SC", "SC",
       aliases=("Internacional - SC", "EC Internacional SC"), claims_base=False),
    # -- Bahia / Sergipe ---------------------------------------------------
    _c("bahia", "Bahia", "BA",
       aliases=("Bahia-BA", "Bahia - BA", "EC Bahia"), nicknames=("Esquadrão de Aço", "Tricolor de Aço")),
    _c("vitoria-ba", "Vitória", "BA",
       aliases=("Vitoria", "Vitória - BA", "Vitoria-BA", "EC Vitoria", "Vitoria EC"),
       nicknames=("Leão da Barra",)),
    _c("juazeirense", "Juazeirense", "BA"),
    _c("jacuipense", "Jacuipense", "BA"),
    _c("vitoria-da-conquista", "Vitória da Conquista", "BA"),
    _c("bahia-de-feira", "Bahia de Feira", "BA"),
    _c("fluminense-de-feira", "Fluminense de Feira", "BA", aliases=("Fluminense De Feira",)),
    _c("atletico-ba", "Atlético de Alagoinhas", "BA", aliases=("Atletico Alagoinhas", "Atlético - BA")),
    _c("confianca", "Confiança", "SE", aliases=("AD Confianca", "Confianca SE", "Confiança - SE")),
    _c("sergipe", "Sergipe", "SE", aliases=("CS Sergipe",)),
    _c("itabaiana", "Itabaiana", "SE"),
    _c("lagarto", "Lagarto", "SE"),
    _c("frei-paulistano", "Frei Paulistano", "SE", aliases=("AD Frei Paulistano",)),
    _c("estanciano", "Estanciano", "SE"),
    _c("river-plate-se", "River Plate-SE", "SE", aliases=("River Plate - SE",), claims_base=False),
    _c("amadense", "Amadense", "SE", aliases=("Amadense EC",)),
    _c("sao-domingos", "São Domingos", "SE", aliases=("Sao Domingos Futebol Clube - SE",)),
    _c("falcon", "Falcon", "SE"),
    # -- Pernambuco / Alagoas / Paraíba -----------------------------------
    _c("sport-recife", "Sport Recife", "PE",
       aliases=("Sport", "Sport-PE", "Sport - PE", "Sport Recife", "Sport Club do Recife", "Recife"),
       nicknames=("Leão da Ilha",)),
    _c("nautico", "Náutico", "PE",
       aliases=("Nautico-PE", "Náutico - PE", "Nautico Capibaribe", "Náutico Capibaribe"),
       nicknames=("Timbu",)),
    _c("santa-cruz-pe", "Santa Cruz", "PE",
       aliases=("Santa Cruz", "Santa Cruz - PE", "Santa Cruz-PE", "Santa Cruz FC"),
       nicknames=("Cobra Coral",)),
    _c("salgueiro", "Salgueiro", "PE"),
    _c("central-pe", "Central", "PE", aliases=("Central SC", "Central - PE")),
    _c("afogados", "Afogados da Ingazeira", "PE", aliases=("Afogados", "Afogados da Ingazeira FC")),
    _c("retro", "Retrô", "PE", aliases=("Retro", "Retro FC Brasil", "Retrô - PE")),
    _c("csa", "CSA", "AL", aliases=("Csa-AL", "C.s.a. - AL", "CS Alagoano", "Csa - AL")),
    _c("crb", "CRB", "AL", aliases=("C.r.b. - AL", "C. R. B. - AL", "Crb - AL")),
    _c("asa", "ASA", "AL", aliases=("A.s.a. - AL", "ASA AL", "Asa - AL")),
    _c("murici", "Murici", "AL"),
    _c("santa-rita", "Santa Rita", "AL"),
    _c("coruripe", "Coruripe", "AL"),
    _c("botafogo-pb", "Botafogo-PB", "PB", aliases=("Botafogo PB", "Botafogo - PB"), claims_base=False),
    _c("campinense", "Campinense", "PB", aliases=("Campinense Clube",)),
    _c("treze", "Treze", "PB"),
    _c("sousa", "Sousa", "PB", aliases=("Sousa EC", "Souza - PB")),
    _c("auto-esporte", "Auto Esporte", "PB"),
    # -- Ceará / Rio Grande do Norte / Piauí / Maranhão --------------------
    _c("ceara", "Ceará", "CE",
       aliases=("Ceara-CE", "Ceará - CE", "Ceara", "Ceará Sporting Club"), nicknames=("Vozão",)),
    _c("fortaleza", "Fortaleza", "CE",
       aliases=("Fortaleza-CE", "Fortaleza - CE", "Fortaleza EC", "Fortaleza FC",
                "Fortaleza Esporte Clube"),
       nicknames=("Leão do Pici", "Tricolor de Aço do Pici")),
    _c("ferroviario-ce", "Ferroviário", "CE", aliases=("Ferroviario", "Ferroviário - CE")),
    _c("floresta", "Floresta", "CE", aliases=("Floresta EC",)),
    _c("icasa", "Icasa", "CE"),
    _c("atletico-ce", "Atlético Cearense", "CE",
       aliases=("FC Atlético Cearense", "Atlético Cearense - CE", "Uniclinic", "Uniclinic CE")),
    _c("guarany-de-sobral", "Guarany de Sobral", "CE", aliases=("Guarany - CE",)),
    _c("guarani-ce", "Guarani-CE", "CE", aliases=("Guarani - CE", "Guarani de Juazeiro"), claims_base=False),
    _c("horizonte", "Horizonte", "CE"),
    _c("caucaia", "Caucaia", "CE"),
    _c("barbalha", "Barbalha", "CE"),
    _c("iguatu", "Iguatu", "CE"),
    _c("abc", "ABC", "RN", aliases=("A.b.c. - RN", "Abc - RN", "ABC - RN")),
    _c("america-rn", "América-RN", "RN",
       aliases=("America RN", "América - RN", "América de Natal - RN", "America FC Natal")),
    _c("potiguar", "Potiguar", "RN"),
    _c("globo-fc", "Globo FC", "RN", aliases=("Globo - RN",)),
    _c("santa-cruz-rn", "Santa Cruz-RN", "RN", aliases=("Santa Cruz - RN", "Santa Cruz RN"), claims_base=False),
    _c("alecrim", "Alecrim", "RN"),
    _c("river-pi", "River-PI", "PI", aliases=("River - PI", "Ríver - PI", "River AC", "River (PI)")),
    _c("altos", "Altos", "PI", aliases=("AE Altos", "Altos - PI")),
    _c("parnahyba", "Parnahyba", "PI", aliases=("Parnahyba S.c - PI",)),
    _c("flamengo-pi", "Flamengo-PI", "PI", aliases=("Flamengo - PI", "Flamengo do Piauí - PI"), claims_base=False),
    _c("fluminense-pi", "Fluminense-PI", "PI", aliases=("Fluminense PI",), claims_base=False),
    _c("quatro-de-julho", "4 de Julho", "PI", aliases=("4 de Julho EC", "4 de Julho - PI", "Iv de Julho - PI")),
    _c("picos", "Picos", "PI"),
    _c("comercial-pi", "Comercial-PI", "PI", aliases=("Comercial - PI",), claims_base=False),
    _c("piaui", "Piauí", "PI"),
    _c("sampaio-correa", "Sampaio Corrêa", "MA", aliases=("Sampaio Correa", "Sampaio Corrêa - MA")),
    _c("moto-club", "Moto Club", "MA", aliases=("Moto Clube", "Moto Club de São Luís", "Moto Club - MA")),
    _c("imperatriz", "Imperatriz", "MA"),
    _c("maranhao", "Maranhão", "MA", aliases=("Maranhao",)),
    _c("cordino", "Cordino", "MA", aliases=("Cordino EC",)),
    _c("juventude-ma", "Juventude-MA", "MA", aliases=("Juventude - MA",), claims_base=False),
    _c("tuntum", "Tuntum", "MA", aliases=("tuntum EC",)),
    _c("santa-quiteria", "Santa Quitéria", "MA", aliases=("Santa Quiteria Futebol Clube - MA",)),
    # -- Goiás / DF / Mato Grosso -----------------------------------------
    _c("goias", "Goiás", "GO", aliases=("Goias-GO", "Goiás - GO", "Goias"), nicknames=("Esmeraldino",)),
    _c("atletico-go", "Atlético Goianiense", "GO",
       aliases=("Atletico-GO", "Atlético - GO", "Atletico Goianiense", "Atlético Goianiense")),
    _c("vila-nova", "Vila Nova", "GO",
       aliases=("Vila Nova - GO", "Vila Nova FC", "Villa Nova", "Villa Nova - GO")),
    _c("aparecidense", "Aparecidense", "GO", aliases=("Aparecidense GO",)),
    _c("crac", "CRAC", "GO", aliases=("C.r.a.c. - GO",)),
    _c("anapolis", "Anápolis", "GO", aliases=("Anapolis FC", "Anápolis - GO")),
    _c("anapolina", "Anapolina", "GO"),
    _c("goianesia", "Goianésia", "GO", aliases=("Goianesia",)),
    _c("jaragua", "Jaraguá", "GO", aliases=("Jaragua EC",)),
    _c("gremio-anapolis", "Grêmio Anápolis", "GO", aliases=("Gremio Anapolis",)),
    _c("brasiliense", "Brasiliense", "DF"),
    _c("gama", "Gama", "DF", aliases=("SE Gama", "Gama - DF")),
    _c("ceilandia", "Ceilândia", "DF", aliases=("Ceilandia",)),
    _c("sobradinho", "Sobradinho", "DF"),
    _c("brasilia", "Brasília", "DF", aliases=("Brasilia FC", "Brasília - DF")),
    _c("luziania", "Luziânia", "DF", aliases=("Luziania",)),
    _c("real-brasilia", "Real Brasília", "DF"),
    _c("taguatinga", "Taguatinga", "DF", aliases=("CA Taguatinga",)),
    _c("cuiaba", "Cuiabá", "MT", aliases=("Cuiaba-MT", "Cuiabá - MT", "Cuiaba MT")),
    _c("luverdense", "Luverdense", "MT"),
    _c("mixto", "Mixto", "MT"),
    _c("sinop", "Sinop", "MT", aliases=("Sinop FC",)),
    _c("operario-mt", "Operário-MT", "MT", aliases=("Operario MT", "Operário - MT"), claims_base=False),
    _c("dom-bosco", "Dom Bosco", "MT", aliases=("CE Dom Bosco",)),
    _c("uniao-rondonopolis", "União de Rondonópolis", "MT",
       aliases=("Uniao Rondonopolis", "União de Rondonópolis - MT", "União - MT", "Rondonopolis - MT")),
    _c("nova-mutum", "Nova Mutum", "MT", aliases=("Nova Mutum EC",)),
    _c("varzeagrandense", "Várzea Grande", "MT", aliases=("CEO Varzeagrandense",)),
    _c("operario-ms", "Operário-MS", "MS", aliases=("Operario MS", "Operário - MS", "Operario FC MS"), claims_base=False),
    _c("aguia-negra", "Águia Negra", "MS", aliases=("Aguia Negra-MS", "Águia Negra - MS", "Aguia Negra - MS")),
    _c("cene", "CENE", "MS", aliases=("CENE MS", "Cene - MS")),
    _c("comercial-ms", "Comercial-MS", "MS", aliases=("Comercial MS", "Comercial - MS"), claims_base=False),
    _c("naviraiense", "Naviraiense", "MS"),
    _c("corumbaense", "Corumbaense", "MS"),
    _c("aquidauanense", "Aquidauanense", "MS", aliases=("Aquidauanense Futebol Clube - MS",)),
    _c("ivinhema", "Ivinhema", "MS"),
    _c("novoperario", "Novoperário", "MS", aliases=("Novoperario",)),
    _c("costa-rica-ms", "Costa Rica", "MS", aliases=("Costa Rica EC",)),
    _c("sete-de-setembro", "Sete de Setembro", "MS", aliases=("7 de Setembro - MS",)),
    # -- Norte -------------------------------------------------------------
    _c("paysandu", "Paysandu", "PA"),
    _c("remo", "Remo", "PA", aliases=("Clube Do Remo", "Remo - PA", "Remo PA")),
    _c("aguia-de-maraba", "Águia de Marabá", "PA", aliases=("Aguia de Maraba", "Aguia - PA", "Águia - PA")),
    _c("castanhal", "Castanhal", "PA"),
    _c("bragantino-pa", "Bragantino-PA", "PA", aliases=("Bragantino PA", "Bragantino - PA"), claims_base=False),
    _c("independente-pa", "Independente-PA", "PA",
       aliases=("Independente PA", "Independente - PA", "Independente de Tucuruí - PA")),
    _c("sao-raimundo-pa", "São Raimundo-PA", "PA", aliases=("Sao Raimundo PA", "São Raimundo - PA")),
    _c("sao-francisco-pa", "São Francisco-PA", "PA",
       aliases=("Sao Francisco PA", "S.francisco - PA", "São Francisco - PA")),
    _c("tuna-luso", "Tuna Luso", "PA"),
    _c("cameta", "Cametá", "PA", aliases=("Cametá - PA",)),
    _c("paragominas", "Paragominas", "PA"),
    _c("parauapebas", "Parauapebas", "PA"),
    _c("sao-jose-pa", "São José-PA", "PA", aliases=("Sao Jose PA",), claims_base=False),
    _c("nacional-am", "Nacional-AM", "AM", aliases=("Nacional AM", "Nacional - AM"), claims_base=False),
    _c("manaus", "Manaus", "AM"),
    _c("fast-clube", "Fast Clube", "AM", aliases=("Fast Clube - AM",)),
    _c("princesa-do-solimoes", "Princesa do Solimões", "AM", aliases=("Princesa do Solimoes",)),
    _c("penarol-am", "Penarol-AM", "AM", aliases=("Penarol AM", "Penarol - AM"), claims_base=False),
    _c("amazonas", "Amazonas", "AM"),
    _c("sao-raimundo-am", "São Raimundo-AM", "AM", aliases=("Sao Raimundo AM",)),
    _c("trem", "Trem", "AP", aliases=("Trem AP",)),
    _c("santos-ap", "Santos-AP", "AP", aliases=("Santos AP", "Santos - AP"), claims_base=False),
    _c("ypiranga-ap", "Ypiranga-AP", "AP", aliases=("Ypiranga AP", "Ypiranga - AP"), claims_base=False),
    _c("oratorio", "Oratório", "AP", aliases=("Oratorio",)),
    _c("peixe-da-amazonia", "Peixe da Amazônia", "AP", aliases=("Peixe da Amazonia",)),
    _c("sao-raimundo-rr", "São Raimundo-RR", "RR", aliases=("Sao Raimundo RR", "São Raimundo - RR")),
    _c("real-rr", "Real-RR", "RR", aliases=("Real - RR", "Real FC")),
    _c("nautico-rr", "Náutico-RR", "RR", aliases=("Nautico RR", "Nautico - RR"), claims_base=False),
    _c("rio-branco-ac", "Rio Branco-AC", "AC", aliases=("Rio Branco AC", "Rio Branco - AC")),
    _c("atletico-ac", "Atlético Acreano", "AC", aliases=("Atletico Acreano", "Atlético - AC")),
    _c("galvez", "Galvez", "AC", aliases=("Galvez AC", "Galvez - AC")),
    _c("humaita", "Humaitá", "AC", aliases=("Humaita",)),
    _c("placido-de-castro", "Plácido de Castro", "AC"),
    _c("genus", "Genus", "RO", aliases=("SC Genus", "Genus - RO")),
    _c("vilhena", "Vilhena", "RO", aliases=("Vilhena RO", "Vilhenense", "Vilhenense EC")),
    _c("porto-velho", "Porto Velho", "RO", aliases=("Porto Velho EC",)),
    _c("real-ariquemes", "Real Ariquemes", "RO", aliases=("Real Desportivo - RO",)),
    _c("ji-parana", "Ji-Paraná", "RO", aliases=("Ji-paraná - RO",)),
    _c("rondoniense", "Rondoniense", "RO"),
    _c("espigao", "Espigão", "RO", aliases=("Espigão - RO",)),
    _c("palmas", "Palmas", "TO", aliases=("Palmas FR", "Palmas Ltda - TO")),
    _c("gurupi", "Gurupi", "TO"),
    _c("interporto", "Interporto", "TO"),
    _c("tocantinopolis", "Tocantinópolis", "TO", aliases=("Tocantinopolis", "Tocantinopolis EC")),
    # -- Espírito Santo ----------------------------------------------------
    _c("rio-branco-es", "Rio Branco-ES", "ES", aliases=("Rio Branco ES", "Rio Branco - ES", "Rio Branco - Vn - ES")),
    _c("real-noroeste", "Real Noroeste", "ES", aliases=("Real Noroeste ES", "Real Noroeste Capixaba - ES")),
    _c("desportiva-es", "Desportiva Ferroviária", "ES",
       aliases=("Desportiva - ES", "Desportiva Ferroviaria - ES")),
    _c("serra-es", "Serra", "ES", aliases=("Serra F. C. - ES", "Serra - ES")),
    _c("vitoria-es", "Vitória-ES", "ES", aliases=("Vitoria ES", "Vitoria F. C. - ES", "Vitória - ES"), claims_base=False),
    _c("estrela-do-norte", "Estrela do Norte", "ES"),
    _c("aracruz", "Aracruz", "ES"),
    _c("nova-venecia", "Nova Venécia", "ES", aliases=("Nova Venecia FC",)),
    _c("sao-mateus", "São Mateus", "ES", aliases=("Sao Mateus Es - ES",)),
    _c("atletico-es", "Atlético-ES", "ES", aliases=("Atletico - ES",)),
    # -- South American clubs (Libertadores) -------------------------------
    _c("boca-juniors", "Boca Juniors", country="Argentina"),
    _c("river-plate", "River Plate", country="Argentina"),
    _c("racing-club", "Racing Club", country="Argentina"),
    _c("independiente", "Independiente", country="Argentina"),
    _c("san-lorenzo", "San Lorenzo", country="Argentina"),
    _c("velez-sarsfield", "Vélez Sarsfield", country="Argentina", aliases=("Velez Sarsfield",)),
    _c("estudiantes", "Estudiantes", country="Argentina"),
    _c("lanus", "Lanús", country="Argentina", aliases=("Lanus",)),
    _c("huracan", "Huracán", country="Argentina", aliases=("Huracan", "Club Atlético Huracán")),
    _c("newells-old-boys", "Newell's Old Boys", country="Argentina", aliases=("Newells Old Boys",)),
    _c("rosario-central", "Rosario Central", country="Argentina"),
    _c("godoy-cruz", "Godoy Cruz", country="Argentina"),
    _c("arsenal-sarandi", "Arsenal Sarandí", country="Argentina", aliases=("Arsenal Sarandi",)),
    _c("atletico-tucuman", "Atlético Tucumán", country="Argentina", aliases=("Atletico Tucuman",)),
    _c("argentinos-juniors", "Argentinos Juniors", country="Argentina"),
    _c("defensa-y-justicia", "Defensa y Justicia", country="Argentina"),
    _c("talleres", "Talleres", country="Argentina"),
    _c("colon", "Colón", country="Argentina", aliases=("Colon",)),
    _c("tigre", "Tigre", country="Argentina"),
    _c("banfield", "Banfield", country="Argentina", aliases=("Club Atlético Banfield",)),
    _c("aldosivi", "Aldosivi", country="Argentina", aliases=("Club Atlético Aldosivi",)),
    _c("penarol", "Peñarol", country="Uruguay", aliases=("Penarol",)),
    _c("nacional-uru", "Nacional", country="Uruguay",
       aliases=("Nacional (URU)", "Nacional-URU", "Nacional - URU")),
    _c("defensor-sporting", "Defensor Sporting", country="Uruguay"),
    _c("danubio", "Danubio", country="Uruguay"),
    _c("montevideo-wanderers", "Montevideo Wanderers", country="Uruguay"),
    _c("rentistas", "Rentistas", country="Uruguay"),
    _c("river-plate-uru", "River Plate (URU)", country="Uruguay", aliases=("River Plate-URU",), claims_base=False),
    _c("colo-colo", "Colo-Colo", country="Chile"),
    _c("universidad-catolica", "Universidad Católica", country="Chile", aliases=("Universidad Catolica",)),
    _c("universidad-de-chile", "Universidad de Chile", country="Chile"),
    _c("union-espanola", "Unión Española", country="Chile", aliases=("Union Espanola",)),
    _c("palestino", "Palestino", country="Chile"),
    _c("huachipato", "Huachipato", country="Chile"),
    _c("cobresal", "Cobresal", country="Chile"),
    _c("deportes-iquique", "Deportes Iquique", country="Chile"),
    _c("ohiggins", "O'Higgins", country="Chile"),
    _c("union-la-calera", "Unión La Calera", country="Chile", aliases=("Union La Calera",)),
    _c("universidad-de-concepcion", "Universidad de Concepción", country="Chile",
       aliases=("Universidad de Concepcion",)),
    _c("atletico-nacional", "Atlético Nacional", country="Colombia", aliases=("Atletico Nacional",)),
    _c("santa-fe", "Independiente Santa Fe", country="Colombia", aliases=("Ind. Santa Fe",)),
    _c("deportivo-cali", "Deportivo Cali", country="Colombia"),
    _c("millonarios", "Millonarios", country="Colombia"),
    _c("junior", "Junior de Barranquilla", country="Colombia"),
    _c("independiente-medellin", "Independiente Medellín", country="Colombia",
       aliases=("Independiente Medellin",)),
    _c("deportes-tolima", "Deportes Tolima", country="Colombia", aliases=("Tolima",)),
    _c("america-de-cali", "América de Cali", country="Colombia"),
    _c("emelec", "Emelec", country="Ecuador"),
    _c("barcelona-sc", "Barcelona SC", country="Ecuador", aliases=("Barcelona-EQU", "Barcelona - EQU")),
    _c("ldu", "LDU Quito", country="Ecuador", aliases=("LDU",)),
    _c("independiente-del-valle", "Independiente del Valle", country="Ecuador",
       aliases=("Independiente Del Valle",)),
    _c("delfin", "Delfín", country="Ecuador", aliases=("Delfin", "Delfín-EQU")),
    _c("sporting-cristal", "Sporting Cristal", country="Peru"),
    _c("melgar", "Melgar", country="Peru"),
    _c("alianza-lima", "Alianza Lima", country="Peru"),
    _c("universitario", "Universitario", country="Peru",
       aliases=("Universitario (PER)", "Universitario-PER")),
    _c("real-garcilaso", "Real Garcilaso", country="Peru"),
    _c("juan-aurich", "Juan Aurich", country="Peru"),
    _c("binacional", "Binacional", country="Peru"),
    _c("sport-boys", "Sport Boys", country="Peru"),
    _c("olimpia", "Olimpia", country="Paraguay", aliases=("Olimpia-PAR", "Olimpia - PAR")),
    _c("cerro-porteno", "Cerro Porteño", country="Paraguay", aliases=("Cerro Porteno",)),
    _c("libertad", "Libertad", country="Paraguay", aliases=("Libertad-PAR", "Libertad - PAR")),
    _c("guarani-par", "Guaraní (PAR)", country="Paraguay", aliases=("Guaraní-PAR", "Guarani-PAR"), claims_base=False),
    _c("nacional-par", "Nacional (PAR)", country="Paraguay", aliases=("Nacional-PAR",), claims_base=False),
    _c("the-strongest", "The Strongest", country="Bolivia"),
    _c("bolivar", "Bolívar", country="Bolivia", aliases=("Bolivar",)),
    _c("jorge-wilstermann", "Jorge Wilstermann", country="Bolivia"),
    _c("san-jose", "San José", country="Bolivia", aliases=("San Jose",)),
    _c("always-ready", "Always Ready", country="Bolivia"),
    _c("universitario-de-sucre", "Universitario de Sucre", country="Bolivia"),
    _c("independiente-petrolero", "Independiente Petrolero", country="Bolivia"),
    _c("real-atletico", "Real Atlético", country="Bolivia", aliases=("Real Atlético", "Real Atletico")),
    _c("deportivo-tachira", "Deportivo Táchira", country="Venezuela", aliases=("Deportivo Tachira",)),
    _c("caracas", "Caracas", country="Venezuela"),
    _c("zamora", "Zamora", country="Venezuela"),
    _c("deportivo-lara", "Deportivo Lara", country="Venezuela"),
    _c("zulia", "Zulia", country="Venezuela"),
    _c("monagas", "Monagas", country="Venezuela"),
    _c("la-guaira", "La Guaira", country="Venezuela"),
    _c("mineros", "Mineros de Guayana", country="Venezuela", aliases=("Mineros de Guaiana",)),
    _c("estudiantes-de-merida", "Estudiantes de Mérida", country="Venezuela",
       aliases=("Estudiantes de Merida",)),
    _c("trujillanos", "Trujillanos", country="Venezuela", aliases=("Trujillanos (VEN)",)),
    _c("deportivo-anzoategui", "Deportivo Anzoátegui", country="Venezuela",
       aliases=("Deportivo Anzoategui",)),
    _c("tigres-mex", "Tigres UANL", country="Mexico", aliases=("Tigres",)),
    _c("toluca", "Toluca", country="Mexico"),
    _c("santos-laguna", "Santos Laguna", country="Mexico"),
    _c("pumas", "Pumas UNAM", country="Mexico", aliases=("Pumas",)),
    _c("club-america", "Club América", country="Mexico", aliases=("Club America",)),
    _c("leon", "León", country="Mexico", aliases=("Leon",)),
    _c("tijuana", "Tijuana", country="Mexico"),
    _c("atlas", "Atlas", country="Mexico"),
)


# --------------------------------------------------------------------------
# Lookup tables
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TeamRef:
    """The result of resolving a raw club spelling."""

    id: str
    name: str
    state: str | None = None
    country: str = "Brazil"
    known: bool = False

    @property
    def state_name(self) -> str | None:
        return UF_STATES.get(self.state or "")


_BY_ID: dict[str, Club] = {club.id: club for club in CLUBS}
_EXACT: dict[tuple[str, str | None], str] = {}
_REGIONS_FOR_BASE: dict[str, set[str]] = {}
_ALIAS_TEXT: dict[str, str] = {}  # normalised free text -> club id
_CONFLICTS: list[str] = []


def _register(base: str, region: str | None, club_id: str) -> None:
    if not base:
        return
    key = (base, region)
    existing = _EXACT.get(key)
    if existing and existing != club_id:
        if region is not None:
            _CONFLICTS.append(f"{key} claimed by {existing} and {club_id}")
        return  # first registration wins for the bare-base key
    _EXACT[key] = club_id
    if region:
        _REGIONS_FOR_BASE.setdefault(base, set()).add(region)


def _spellings(club: Club) -> tuple[str, ...]:
    return (club.name, club.id.replace("-", " "), *club.aliases, *club.nicknames)


def _build_indexes() -> None:
    # A base is "contested" when more than one club spells itself that way
    # ("botafogo" for the Rio, Paraíba and Ribeirão Preto clubs).  Only a club
    # with claims_base may own the unqualified form of a contested base;
    # uncontested bases are always registered, so an alias unique to one club
    # ("Botafogo Ribeirão Preto") still resolves without a state code.
    claimants: dict[str, set[str]] = {}
    for club in CLUBS:
        for spelling in _spellings(club):
            base = parse_team_name(spelling).base
            if base:
                claimants.setdefault(base, set()).add(club.id)
    contested = {base for base, ids in claimants.items() if len(ids) > 1}

    for club in CLUBS:
        for spelling in _spellings(club):
            parsed = parse_team_name(spelling)
            base = parsed.base
            region = parsed.region or club.state
            if base:
                _register(base, region, club.id)
                claims = club.claims_base or base not in contested
                if claims and base not in REQUIRES_REGION:
                    if base in contested and _EXACT.get((base, None), club.id) != club.id:
                        _CONFLICTS.append(
                            f"base {base!r} claimed by {_EXACT[(base, None)]} and {club.id}"
                        )
                    _register(base, None, club.id)
            _ALIAS_TEXT.setdefault(normalize_query(spelling), club.id)
        _ALIAS_TEXT.setdefault(normalize_query(club.name), club.id)


_build_indexes()

if _CONFLICTS:  # pragma: no cover - guarded by tests/test_names.py
    raise RuntimeError("Conflicting club registrations: " + "; ".join(_CONFLICTS))


def known_club(club_id: str) -> Club | None:
    """Return the registry entry for *club_id* (or ``None`` if synthetic)."""
    return _BY_ID.get(club_id)


def _known_ref(club_id: str) -> TeamRef:
    club = _BY_ID[club_id]
    return TeamRef(id=club.id, name=club.name, state=club.state, country=club.country, known=True)


def _synthetic_ref(parsed: ParsedName, region: str | None) -> TeamRef:
    slug = slugify(parsed.base) or slugify(parsed.raw) or "unknown"
    if region:
        slug = f"{slug}-{region.lower()}"
    return TeamRef(
        id=slug,
        name=parsed.raw or parsed.base.title(),
        state=region if region in UF_STATES else None,
        country=COUNTRY_CODES.get(region or "", "Brazil"),
        known=False,
    )


def resolve_team(raw: str, state_hint: str | None = None) -> TeamRef:
    """Resolve a raw club spelling to a canonical :class:`TeamRef`.

    Signals are tried strongest first: a state code embedded in the name, then
    the registry's default club for that name, then the ``state_hint`` column of
    the source file (unreliable in the historical CSV).  Unknown clubs still get
    a stable id derived from the normalised name, so the long tail of Copa do
    Brasil minnows is queryable too, and a base name the registry knows in
    several states never collapses -- an unregistered state gets its own
    ``base-uf`` id.
    """
    parsed = parse_team_name(raw, state_hint)
    base = parsed.base

    if parsed.region:
        club_id = _EXACT.get((base, parsed.region))
        if club_id is not None:
            return _known_ref(club_id)
        if base in _REGIONS_FOR_BASE or base in REQUIRES_REGION:
            # Known base, different state -> a different club of the same name.
            return _synthetic_ref(parsed, parsed.region)

    if base not in REQUIRES_REGION:
        club_id = _EXACT.get((base, None))
        if club_id is not None:
            return _known_ref(club_id)

    if parsed.hint:
        club_id = _EXACT.get((base, parsed.hint))
        if club_id is not None:
            return _known_ref(club_id)
        if base in _REGIONS_FOR_BASE or base in REQUIRES_REGION:
            return _synthetic_ref(parsed, parsed.hint)

    return _synthetic_ref(parsed, None)


def search_clubs(query: str, limit: int = 10) -> list[Club]:
    """Fuzzy-ish lookup over the registry, used to suggest alternatives."""
    needle = normalize_query(query)
    if not needle:
        return []
    scored: list[tuple[int, Club]] = []
    for club in CLUBS:
        haystacks = [normalize_query(club.name), *(normalize_query(a) for a in club.aliases),
                     *(normalize_query(n) for n in club.nicknames)]
        best: int | None = None
        for hay in haystacks:
            if hay == needle:
                score = 0
            elif hay.startswith(needle):
                score = 1
            elif needle in hay:
                score = 2
            else:
                continue
            best = score if best is None else min(best, score)
        if best is not None:
            scored.append((best, club))
    scored.sort(key=lambda item: (item[0], item[1].name))
    return [club for _, club in scored[:limit]]


# --------------------------------------------------------------------------
# Competitions
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Competition:
    """A canonical competition node."""

    id: str
    name: str
    kind: str  # "league" or "cup"
    aliases: tuple[str, ...] = field(default=())


COMPETITIONS: tuple[Competition, ...] = (
    Competition(
        "serie-a",
        "Brasileirão Série A",
        "league",
        (
            "serie a", "série a", "brasileirao", "brasileirão", "brasileirao serie a",
            "campeonato brasileiro", "campeonato brasileiro serie a", "brazilian serie a",
            "brasileirao a", "liga", "brazilian league", "brasileiro",
        ),
    ),
    Competition(
        "serie-b",
        "Brasileirão Série B",
        "league",
        ("serie b", "série b", "brasileirao serie b", "campeonato brasileiro serie b",
         "brazilian serie b", "segunda divisao"),
    ),
    Competition(
        "serie-c",
        "Brasileirão Série C",
        "league",
        ("serie c", "série c", "brasileirao serie c", "brazilian serie c", "terceira divisao"),
    ),
    Competition(
        "copa-do-brasil",
        "Copa do Brasil",
        "cup",
        ("copa do brasil", "brazilian cup", "cup", "copa brasil", "brazil cup"),
    ),
    Competition(
        "libertadores",
        "Copa Libertadores",
        "cup",
        ("libertadores", "copa libertadores", "conmebol libertadores", "copa libertadores da america"),
    ),
)

_COMPETITION_BY_ID = {competition.id: competition for competition in COMPETITIONS}
_COMPETITION_LOOKUP: dict[str, Competition] = {}
for _competition in COMPETITIONS:
    _COMPETITION_LOOKUP[normalize_query(_competition.id)] = _competition
    _COMPETITION_LOOKUP[normalize_query(_competition.name)] = _competition
    for _alias in _competition.aliases:
        _COMPETITION_LOOKUP[normalize_query(_alias)] = _competition


def resolve_competition(text: str | None) -> Competition | None:
    """Map free text such as ``"brasileirao"`` onto a competition node."""
    if not text:
        return None
    needle = normalize_query(text)
    if needle in _COMPETITION_LOOKUP:
        return _COMPETITION_LOOKUP[needle]
    matches = [comp for key, comp in _COMPETITION_LOOKUP.items() if needle and needle in key]
    unique = {comp.id: comp for comp in matches}
    if len(unique) == 1:
        return next(iter(unique.values()))
    return None


def competition_by_id(competition_id: str) -> Competition | None:
    return _COMPETITION_BY_ID.get(competition_id)


# --------------------------------------------------------------------------
# Classic rivalries -- used by the "show me all derbies" style questions
# --------------------------------------------------------------------------

DERBIES: tuple[tuple[str, str, str], ...] = (
    ("flamengo", "fluminense", "Fla-Flu"),
    ("flamengo", "vasco-da-gama", "Clássico dos Milhões"),
    ("flamengo", "botafogo-rj", "Clássico da Rivalidade"),
    ("fluminense", "botafogo-rj", "Clássico Vovô"),
    ("fluminense", "vasco-da-gama", "Clássico dos Gigantes"),
    ("botafogo-rj", "vasco-da-gama", "Clássico da Amizade"),
    ("corinthians", "palmeiras", "Derby Paulista"),
    ("corinthians", "sao-paulo", "Majestoso"),
    ("corinthians", "santos", "Clássico Alvinegro"),
    ("palmeiras", "sao-paulo", "Choque-Rei"),
    ("palmeiras", "santos", "Clássico da Saudade"),
    ("santos", "sao-paulo", "San-São"),
    ("gremio", "internacional", "Gre-Nal"),
    ("atletico-mg", "cruzeiro", "Clássico Mineiro"),
    ("athletico-pr", "coritiba", "Atletiba"),
    ("bahia", "vitoria-ba", "Ba-Vi"),
    ("sport-recife", "santa-cruz-pe", "Clássico dos Clássicos"),
    ("sport-recife", "nautico", "Clássico dos Clássicos do Recife"),
    ("nautico", "santa-cruz-pe", "Clássico das Emoções"),
    ("ceara", "fortaleza", "Clássico-Rei"),
    ("goias", "vila-nova", "Clássico Goianiense"),
    ("america-mg", "atletico-mg", "Clássico das Multidões"),
    ("america-mg", "cruzeiro", "Clássico das Multidões"),
    ("gremio", "juventude", "Ca-Ju"),
    ("abc", "america-rn", "Clássico Rei"),
    ("remo", "paysandu", "Re-Pa"),
    ("csa", "crb", "Clássico das Multidões Alagoano"),
)
