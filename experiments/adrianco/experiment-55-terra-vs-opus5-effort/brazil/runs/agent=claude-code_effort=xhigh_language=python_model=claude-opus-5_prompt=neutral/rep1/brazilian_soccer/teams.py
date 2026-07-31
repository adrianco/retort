"""
Canonical club registry -- the heart of cross-dataset name reconciliation.

Context
-------
TASK.md ("Team Name Variations") requires that ``Palmeiras-SP``, ``Palmeiras``
and ``Sport Club Corinthians Paulista`` style spellings all resolve to one
club.  Across the five match files the same club shows up as, for example::

    Atletico-MG | Atlético-MG | Atlético - MG | Atletico Mineiro | Atlético Mineiro
    Bahia-BA    | Bahia - BA  | EC Bahia      | Bahia
    Nacional (URU)                            | Nacional-URU

and some *bases* are genuinely ambiguous -- Botafogo exists in RJ, SP and PB;
América in MG and RN; River Plate in Argentina and Uruguay.

Resolution strategy (three tiers, cheapest first)
-------------------------------------------------
1. **Curated registry** (:data:`CLUB_SPECS`) -- ~90 well known clubs with
   explicit ids, states/countries, aliases and nicknames.  A spec only "claims"
   its bare, unqualified name when that name is unambiguous
   (``claims_bare_name``), which is why ``Botafogo`` -> Botafogo-RJ but
   ``América`` alone stays unresolved.
2. **Observed clustering** -- every raw name seen while loading is bucketed by
   ``(match_key, qualifier)``.  ``match_key`` is the accent-free token form with
   club-type noise removed (``EC``, ``FC``, ``Clube``, ``do``, ...), so
   ``"EC Bahia"`` and ``"Bahia - BA"`` share the key ``bahia``.  An unqualified
   name joins a qualified cluster only when exactly one qualifier exists for
   that key -- otherwise it stays its own club.
3. **Fuzzy search** (:meth:`TeamRegistry.search`) -- user facing lookup used by
   the MCP tools, matching nicknames, prefixes and substrings so an LLM can
   pass "Flamengo", "Mengão" or "flamengo rj".

Nationality is inferred, not guessed: a club observed in Serie A/B/C or the
Copa do Brasil is Brazilian; a Libertadores-only club is foreign.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .models import Team
from .text import (
    BRAZILIAN_STATES,
    COUNTRY_CODES,
    normalize_name,
    slugify,
    split_qualifier,
    titleize,
    unique,
)

__all__ = ["ClubSpec", "CLUB_SPECS", "DERBIES", "TeamRegistry", "Derby"]


@dataclass(frozen=True, slots=True)
class ClubSpec:
    """A hand-curated club identity."""

    id: str
    name: str
    state: str | None = None
    country: str = "BRA"
    aliases: tuple[str, ...] = ()
    nicknames: tuple[str, ...] = ()
    #: When False the bare name (no state/country) does *not* resolve here --
    #: used for ambiguous bases such as América, Atlético, Nacional.
    claims_bare_name: bool = True


def _br(
    club_id: str,
    name: str,
    state: str,
    *,
    aliases: tuple[str, ...] = (),
    nicknames: tuple[str, ...] = (),
    bare: bool = True,
) -> ClubSpec:
    return ClubSpec(club_id, name, state, "BRA", aliases, nicknames, bare)


def _foreign(
    club_id: str,
    name: str,
    country: str,
    *,
    aliases: tuple[str, ...] = (),
    bare: bool = True,
) -> ClubSpec:
    return ClubSpec(club_id, name, None, country, aliases, (), bare)


CLUB_SPECS: tuple[ClubSpec, ...] = (
    # ---- Rio de Janeiro -------------------------------------------------
    _br("flamengo-rj", "Flamengo", "RJ",
        aliases=("cr flamengo", "clube de regatas do flamengo"),
        nicknames=("mengao", "fla", "rubro-negro")),
    _br("fluminense-rj", "Fluminense", "RJ",
        aliases=("fluminense fc",), nicknames=("flu", "tricolor carioca")),
    _br("botafogo-rj", "Botafogo", "RJ",
        aliases=("botafogo de futebol e regatas", "botafogo fr"),
        nicknames=("fogao", "glorioso")),
    _br("vasco-da-gama-rj", "Vasco da Gama", "RJ",
        aliases=("vasco", "cr vasco da gama", "club de regatas vasco da gama"),
        nicknames=("gigante da colina", "cruzmaltino")),
    _br("boavista-rj", "Boavista", "RJ",
        aliases=("boavista sport", "boavista saquarema", "boavista sc saquarema")),
    _br("bangu-rj", "Bangu", "RJ"),
    _br("americano-rj", "Americano", "RJ", bare=False),
    _br("cabofriense-rj", "Cabofriense", "RJ"),
    _br("madureira-rj", "Madureira", "RJ"),
    _br("volta-redonda-rj", "Volta Redonda", "RJ"),
    _br("resende-rj", "Resende", "RJ"),
    # ---- São Paulo ------------------------------------------------------
    _br("palmeiras-sp", "Palmeiras", "SP",
        aliases=("se palmeiras", "palestra italia"), nicknames=("verdao", "porco")),
    _br("corinthians-sp", "Corinthians", "SP",
        aliases=("sc corinthians paulista", "sport club corinthians paulista",
                 "corinthians paulista"),
        nicknames=("timao",)),
    _br("sao-paulo-sp", "São Paulo", "SP",
        aliases=("sao paulo fc",), nicknames=("tricolor paulista", "soberano")),
    _br("santos-sp", "Santos", "SP", aliases=("santos fc",), nicknames=("peixe",)),
    _br("ponte-preta-sp", "Ponte Preta", "SP",
        aliases=("aa ponte preta",), nicknames=("macaca",)),
    _br("portuguesa-sp", "Portuguesa", "SP",
        aliases=("associacao portuguesa de desportos", "lusa")),
    _br("bragantino-sp", "Red Bull Bragantino", "SP",
        aliases=("bragantino", "rb bragantino", "red bull brasil"),
        nicknames=("massa bruta",)),
    _br("guarani-sp", "Guarani", "SP", aliases=("guarani fc",), nicknames=("bugre",)),
    _br("santo-andre-sp", "Santo André", "SP", aliases=("ec santo andre",)),
    _br("sao-caetano-sp", "São Caetano", "SP", aliases=("ad sao caetano",)),
    _br("barueri-sp", "Grêmio Barueri", "SP", aliases=("barueri", "gremio barueri")),
    _br("gremio-prudente-sp", "Grêmio Prudente", "SP"),
    _br("oeste-sp", "Oeste", "SP"),
    _br("botafogo-sp", "Botafogo", "SP", aliases=("Botafogo-SP",), bare=False,
        nicknames=("pantera",)),
    _br("audax-sp", "Audax", "SP"),
    _br("mirassol-sp", "Mirassol", "SP"),
    _br("novorizontino-sp", "Novorizontino", "SP"),
    _br("ituano-sp", "Ituano", "SP"),
    _br("sao-bento-sp", "São Bento", "SP"),
    # ---- Minas Gerais ---------------------------------------------------
    _br("cruzeiro-mg", "Cruzeiro", "MG", aliases=("cruzeiro ec",), nicknames=("raposa",)),
    _br("atletico-mg", "Atlético Mineiro", "MG", bare=False,
        aliases=("Atlético-MG", "Atletico-MG", "atletico mineiro",
                 "clube atletico mineiro"),
        nicknames=("galo",)),
    _br("america-mg", "América Mineiro", "MG", bare=False,
        aliases=("América-MG", "America-MG", "america mineiro", "america fc"),
        nicknames=("coelho",)),
    _br("ipatinga-mg", "Ipatinga", "MG"),
    _br("villa-nova-mg", "Villa Nova", "MG", bare=False),
    _br("tombense-mg", "Tombense", "MG"),
    _br("caldense-mg", "Caldense", "MG"),
    _br("uberlandia-mg", "Uberlândia", "MG"),
    # ---- Paraná / Santa Catarina / Rio Grande do Sul --------------------
    _br("athletico-pr", "Athletico Paranaense", "PR", bare=False,
        aliases=("Athletico-PR", "Atlético-PR", "Atletico-PR", "athletico",
                 "atletico paranaense", "athletico paranaense",
                 "clube athletico paranaense"),
        nicknames=("furacao",)),
    _br("coritiba-pr", "Coritiba", "PR", aliases=("coritiba fbc",), nicknames=("coxa",)),
    _br("parana-pr", "Paraná", "PR", aliases=("parana clube",)),
    _br("londrina-pr", "Londrina", "PR"),
    _br("operario-pr", "Operário", "PR", bare=False),
    _br("gremio-rs", "Grêmio", "RS",
        aliases=("gremio fbpa", "gremio foot-ball porto alegrense"),
        nicknames=("imortal", "tricolor gaucho")),
    # "inter" is a nickname, not an alias: FIFA calls Inter Milan "Inter", and
    # nicknames are deliberately excluded from dataset-name resolution.
    _br("internacional-rs", "Internacional", "RS",
        aliases=("sc internacional",), nicknames=("colorado", "inter")),
    _br("juventude-rs", "Juventude", "RS", aliases=("ec juventude",)),
    _br("brasil-de-pelotas-rs", "Brasil de Pelotas", "RS", aliases=("brasil pelotas",)),
    _br("caxias-rs", "Caxias", "RS"),
    _br("avai-sc", "Avaí", "SC", aliases=("avai fc",)),
    _br("figueirense-sc", "Figueirense", "SC"),
    _br("chapecoense-sc", "Chapecoense", "SC",
        aliases=("associacao chapecoense de futebol",)),
    _br("criciuma-sc", "Criciúma", "SC"),
    _br("joinville-sc", "Joinville", "SC", aliases=("joinville ec",)),
    _br("brusque-sc", "Brusque", "SC"),
    # ---- Nordeste -------------------------------------------------------
    _br("bahia-ba", "Bahia", "BA",
        aliases=("ec bahia", "esporte clube bahia"), nicknames=("esquadrao",)),
    _br("vitoria-ba", "Vitória", "BA", aliases=("ec vitoria",), nicknames=("leao da barra",)),
    _br("sport-pe", "Sport", "PE",
        aliases=("sport recife", "sport club do recife"), nicknames=("leao da ilha",)),
    _br("nautico-pe", "Náutico", "PE",
        aliases=("clube nautico capibaribe",), nicknames=("timbu",)),
    _br("santa-cruz-pe", "Santa Cruz", "PE", nicknames=("cobra coral",)),
    _br("ceara-ce", "Ceará", "CE",
        aliases=("ceara sporting", "ceara sporting club"), nicknames=("vozao",)),
    _br("fortaleza-ce", "Fortaleza", "CE",
        aliases=("fortaleza ec", "fortaleza fc"), nicknames=("leao do pici",)),
    _br("csa-al", "CSA", "AL", aliases=("centro sportivo alagoano", "cs alagoano")),
    _br("crb-al", "CRB", "AL", aliases=("clube de regatas brasil",)),
    _br("asa-al", "ASA", "AL"),
    _br("abc-rn", "ABC", "RN"),
    _br("america-rn", "América de Natal", "RN", bare=False,
        aliases=("América-RN", "America-RN", "america natal", "america fc natal")),
    _br("botafogo-pb", "Botafogo", "PB", aliases=("Botafogo-PB",), bare=False),
    _br("campinense-pb", "Campinense", "PB", aliases=("campinense clube",)),
    _br("treze-pb", "Treze", "PB"),
    _br("sampaio-correa-ma", "Sampaio Corrêa", "MA"),
    _br("confianca-se", "Confiança", "SE", aliases=("ad confianca",)),
    _br("sergipe-se", "Sergipe", "SE", aliases=("cs sergipe",)),
    _br("altos-pi", "Altos", "PI", aliases=("ae altos",)),
    # ---- Centro-Oeste / Norte -------------------------------------------
    _br("goias-go", "Goiás", "GO", aliases=("goias ec",), nicknames=("esmeraldino",)),
    _br("atletico-go", "Atlético Goianiense", "GO", bare=False,
        aliases=("Atlético-GO", "Atletico-GO", "atletico goianiense"),
        nicknames=("dragao",)),
    _br("vila-nova-go", "Vila Nova", "GO", aliases=("Vila Nova-GO",), bare=False),
    _br("aparecidense-go", "Aparecidense", "GO"),
    _br("crac-go", "CRAC", "GO"),
    _br("brasiliense-df", "Brasiliense", "DF"),
    _br("gama-df", "Gama", "DF"),
    _br("cuiaba-mt", "Cuiabá", "MT"),
    _br("paysandu-pa", "Paysandu", "PA"),
    _br("remo-pa", "Remo", "PA", aliases=("clube do remo",)),
    _br("bragantino-pa", "Bragantino", "PA", bare=False),
    _br("manaus-am", "Manaus", "AM"),
    # ---- Argentina ------------------------------------------------------
    _foreign("boca-juniors", "Boca Juniors", "ARG"),
    _foreign("river-plate", "River Plate", "ARG", aliases=("ca river plate",)),
    _foreign("racing-club", "Racing Club", "ARG"),
    _foreign("independiente", "Independiente", "ARG"),
    _foreign("san-lorenzo", "San Lorenzo", "ARG"),
    _foreign("estudiantes", "Estudiantes", "ARG"),
    _foreign("velez-sarsfield", "Vélez Sarsfield", "ARG"),
    _foreign("lanus", "Lanús", "ARG"),
    _foreign("newells-old-boys", "Newell's Old Boys", "ARG", aliases=("newells old boys",)),
    _foreign("rosario-central", "Rosario Central", "ARG"),
    _foreign("talleres", "Talleres", "ARG"),
    _foreign("godoy-cruz", "Godoy Cruz", "ARG"),
    _foreign("colon", "Colón", "ARG"),
    _foreign("huracan", "Huracán", "ARG"),
    _foreign("argentinos-juniors", "Argentinos Juniors", "ARG"),
    _foreign("arsenal-sarandi", "Arsenal Sarandí", "ARG"),
    _foreign("defensa-y-justicia", "Defensa y Justicia", "ARG"),
    _foreign("atletico-tucuman", "Atlético Tucumán", "ARG"),
    _foreign("tigre", "Tigre", "ARG"),
    # ---- Uruguay --------------------------------------------------------
    _foreign("nacional-uru", "Nacional", "URU", bare=False),
    _foreign("penarol", "Peñarol", "URU"),
    _foreign("defensor-sporting", "Defensor Sporting", "URU"),
    _foreign("danubio", "Danubio", "URU"),
    _foreign("montevideo-wanderers", "Montevideo Wanderers", "URU"),
    _foreign("river-plate-uru", "River Plate", "URU", bare=False),
    _foreign("rentistas", "Rentistas", "URU"),
    # ---- Chile ----------------------------------------------------------
    _foreign("colo-colo", "Colo-Colo", "CHI"),
    _foreign("universidad-de-chile", "Universidad de Chile", "CHI"),
    _foreign("universidad-catolica", "Universidad Católica", "CHI"),
    _foreign("palestino", "Palestino", "CHI"),
    _foreign("huachipato", "Huachipato", "CHI"),
    _foreign("cobresal", "Cobresal", "CHI"),
    _foreign("ohiggins", "O'Higgins", "CHI"),
    _foreign("union-espanola", "Unión Española", "CHI"),
    _foreign("union-la-calera", "Unión La Calera", "CHI"),
    _foreign("deportes-iquique", "Deportes Iquique", "CHI"),
    _foreign("universidad-de-concepcion", "Universidad de Concepción", "CHI"),
    # ---- Colombia -------------------------------------------------------
    _foreign("atletico-nacional", "Atlético Nacional", "COL"),
    _foreign("deportivo-cali", "Deportivo Cali", "COL"),
    _foreign("millonarios", "Millonarios", "COL"),
    _foreign("independiente-medellin", "Independiente Medellín", "COL"),
    _foreign("santa-fe", "Independiente Santa Fe", "COL", aliases=("ind santa fe",)),
    _foreign("junior-barranquilla", "Junior de Barranquilla", "COL"),
    _foreign("deportes-tolima", "Deportes Tolima", "COL", aliases=("tolima",)),
    _foreign("america-de-cali", "América de Cali", "COL"),
    # ---- Ecuador --------------------------------------------------------
    _foreign("emelec", "Emelec", "ECU"),
    _foreign("barcelona-sc", "Barcelona SC", "ECU", bare=False),
    _foreign("ldu-quito", "LDU Quito", "ECU", aliases=("ldu",)),
    _foreign("independiente-del-valle", "Independiente del Valle", "ECU"),
    _foreign("delfin", "Delfín", "ECU"),
    # ---- Peru / Bolivia / Paraguay / Venezuela --------------------------
    _foreign("alianza-lima", "Alianza Lima", "PER"),
    _foreign("sporting-cristal", "Sporting Cristal", "PER"),
    _foreign("universitario", "Universitario", "PER", bare=False),
    _foreign("melgar", "Melgar", "PER"),
    _foreign("bolivar", "Bolívar", "BOL"),
    _foreign("the-strongest", "The Strongest", "BOL"),
    _foreign("jorge-wilstermann", "Jorge Wilstermann", "BOL"),
    _foreign("always-ready", "Always Ready", "BOL"),
    _foreign("olimpia", "Olimpia", "PAR"),
    _foreign("libertad", "Libertad", "PAR"),
    _foreign("cerro-porteno", "Cerro Porteño", "PAR"),
    _foreign("guarani-par", "Guaraní", "PAR", bare=False),
    _foreign("nacional-par", "Nacional", "PAR", bare=False),
    _foreign("caracas", "Caracas", "VEN"),
    _foreign("deportivo-tachira", "Deportivo Táchira", "VEN"),
    _foreign("zamora", "Zamora", "VEN"),
    # ---- Mexico (Libertadores invitees up to 2016) ----------------------
    _foreign("pumas", "Pumas UNAM", "MEX", aliases=("pumas",)),
    _foreign("toluca", "Toluca", "MEX"),
    _foreign("tijuana", "Tijuana", "MEX"),
    _foreign("santos-laguna", "Santos Laguna", "MEX"),
    _foreign("atlas", "Atlas", "MEX"),
    _foreign("leon", "León", "MEX"),
    _foreign("tigres-uanl", "Tigres UANL", "MEX", aliases=("tigres",)),
)


@dataclass(frozen=True, slots=True)
class Derby:
    """A traditional rivalry, used by the ``find_derbies`` tool."""

    name: str
    team_a: str
    team_b: str
    description: str = ""


DERBIES: tuple[Derby, ...] = (
    Derby("Fla-Flu", "flamengo-rj", "fluminense-rj", "Rio de Janeiro classic"),
    Derby("Clássico dos Milhões", "flamengo-rj", "vasco-da-gama-rj", "Rio de Janeiro classic"),
    Derby("Clássico da Rivalidade", "flamengo-rj", "botafogo-rj", "Rio de Janeiro classic"),
    Derby("Clássico Vovô", "botafogo-rj", "fluminense-rj", "Oldest Rio derby"),
    Derby("Clássico dos Gigantes", "botafogo-rj", "vasco-da-gama-rj", "Rio de Janeiro classic"),
    Derby("Derby Paulista", "corinthians-sp", "palmeiras-sp", "São Paulo classic"),
    Derby("Majestoso", "corinthians-sp", "sao-paulo-sp", "São Paulo classic"),
    Derby("Clássico Alvinegro", "corinthians-sp", "santos-sp", "São Paulo classic"),
    Derby("Choque-Rei", "palmeiras-sp", "sao-paulo-sp", "São Paulo classic"),
    Derby("Clássico da Saudade", "palmeiras-sp", "santos-sp", "São Paulo classic"),
    Derby("San-São", "santos-sp", "sao-paulo-sp", "São Paulo classic"),
    Derby("Grenal", "gremio-rs", "internacional-rs", "Porto Alegre derby"),
    Derby("Clássico Mineiro", "atletico-mg", "cruzeiro-mg", "Belo Horizonte derby"),
    Derby("Atletiba", "athletico-pr", "coritiba-pr", "Curitiba derby"),
    Derby("Clássico-Rei", "ceara-ce", "fortaleza-ce", "Fortaleza derby"),
    Derby("Ba-Vi", "bahia-ba", "vitoria-ba", "Salvador derby"),
    Derby("Clássico dos Clássicos", "sport-pe", "santa-cruz-pe", "Recife derby"),
)


#: Tokens that carry no club identity ("Esporte Clube Bahia" == "Bahia").
_NOISE_TOKENS: frozenset[str] = frozenset(
    """
    ec fc sc ac cr ca cs ce ad se aa ea gd cd cf fbc afc cfc sec esc
    clube club esporte esportivo esportiva desportivo desportiva desportos
    associacao sociedade recreativo recreativa futebol futebolistico atletica
    de da do das dos del e
    """.split()
)

#: Brazilian competitions -- observing a club here proves it is Brazilian.
_BRAZILIAN_COMPETITIONS = frozenset({"serie-a", "serie-b", "serie-c", "copa-do-brasil"})


def match_key(name: str) -> str:
    """Identity key for a club name with qualifier and noise words removed.

    ``"Esporte Clube Bahia" -> "bahia"``, ``"CA Paraná" -> "parana"``,
    ``"Independiente Del Valle" -> "independiente valle"``.  If *every* token is
    noise (``"Sport"``) the original tokens are kept.
    """

    base, _ = split_qualifier(name)
    tokens = normalize_name(base).split()
    kept = [tok for tok in tokens if tok not in _NOISE_TOKENS]
    return " ".join(kept or tokens)


def _spec_qualifier(spec: ClubSpec) -> str | None:
    if spec.state:
        return spec.state
    if spec.country and spec.country != "BRA":
        return spec.country
    return None


@dataclass
class _Cluster:
    """A group of raw spellings believed to be the same club."""

    key: str
    qualifier: str | None
    raw_names: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    competitions: set[str] = field(default_factory=set)


class TeamRegistry:
    """Resolves raw dataset spellings to canonical :class:`Team` objects."""

    def __init__(self, specs: tuple[ClubSpec, ...] = CLUB_SPECS) -> None:
        self._teams: dict[str, Team] = {}
        self._by_exact: dict[str, str] = {}  # normalized full string -> team id
        self._by_key: dict[tuple[str, str | None], str] = {}
        self._cache: dict[tuple[str, str | None], str] = {}
        self._observations: dict[str, dict[str | None, _Cluster]] = defaultdict(dict)
        self._curated_keys: set[str] = set()
        self._built = False
        for spec in specs:
            self._register_spec(spec)

    # -- construction ------------------------------------------------------
    def _register_spec(self, spec: ClubSpec) -> None:
        team = Team(
            id=spec.id,
            name=spec.name,
            state=spec.state,
            country=spec.country,
            nicknames=spec.nicknames,
            aliases=tuple(unique((spec.name, *spec.aliases, *spec.nicknames))),
        )
        self._teams[team.id] = team

        qualifier = _spec_qualifier(spec)
        key = match_key(spec.name)
        self._curated_keys.add(key)
        self._by_key[(key, qualifier)] = team.id
        if spec.claims_bare_name:
            self._by_key.setdefault((key, None), team.id)

        # Nicknames are intentionally *not* indexed here.  They are for fuzzy,
        # user-facing search only (:meth:`search`); letting them resolve dataset
        # names would link FIFA's "Inter" (Milan) to Internacional of Porto Alegre.
        for alias in (spec.name, *spec.aliases):
            self._by_exact.setdefault(normalize_name(alias), team.id)
            alias_key = match_key(alias)
            self._curated_keys.add(alias_key)
            _, alias_qualifier = split_qualifier(alias)
            self._by_key.setdefault((alias_key, alias_qualifier or qualifier), team.id)
            if spec.claims_bare_name:
                self._by_key.setdefault((alias_key, None), team.id)

    def observe(self, raw_name: str, *, state: str | None = None,
                competition_id: str | None = None) -> None:
        """Record a raw spelling seen while loading (phase 1 of two)."""

        if self._built:  # pragma: no cover - defensive
            raise RuntimeError("TeamRegistry.observe() called after build()")
        raw_name = (raw_name or "").strip()
        if not raw_name:
            return
        key, qualifier = self._key_and_qualifier(raw_name, state)
        cluster = self._observations[key].get(qualifier)
        if cluster is None:
            cluster = _Cluster(key=key, qualifier=qualifier)
            self._observations[key][qualifier] = cluster
        cluster.raw_names[raw_name] += 1
        if competition_id:
            cluster.competitions.add(competition_id)

    def _key_and_qualifier(self, raw_name: str,
                           state: str | None) -> tuple[str, str | None]:
        base, qualifier = split_qualifier(raw_name)
        if qualifier is None and state:
            candidate = str(state).strip().upper()
            if candidate in BRAZILIAN_STATES or candidate in COUNTRY_CODES:
                qualifier = candidate
        return match_key(base), qualifier

    def build(self) -> None:
        """Turn observations into canonical teams (phase 2 of two)."""

        if self._built:
            return
        for key in sorted(self._observations):
            groups = self._observations[key]
            if key in self._curated_keys:
                # Curated specs own this key; only mint teams for qualifiers the
                # registry does not already cover (e.g. "Botafogo - PB").
                for qualifier, cluster in sorted(groups.items(), key=_qualifier_sort):
                    if (key, qualifier) not in self._by_key:
                        self._mint(cluster)
                continue

            qualified = sorted(q for q in groups if q)
            for qualifier in qualified:
                self._mint(groups[qualifier])
            if None in groups:
                if len(qualified) == 1:
                    # Unqualified spelling of an otherwise unambiguous club:
                    # fold it into the single qualified cluster.
                    target = self._by_key[(key, qualified[0])]
                    self._by_key[(key, None)] = target
                    self._absorb(target, groups[None])
                else:
                    self._mint(groups[None])
        self._built = True

    def _mint(self, cluster: _Cluster) -> Team:
        name = self._pick_display_name(cluster)
        qualifier = cluster.qualifier
        state = qualifier if qualifier in BRAZILIAN_STATES else None
        if state:
            country = "BRA"
        elif qualifier in COUNTRY_CODES:
            country = qualifier
        elif cluster.competitions & _BRAZILIAN_COMPETITIONS:
            country = "BRA"
        else:
            country = ""
        team_id = slugify(f"{name} {qualifier}" if qualifier else name) or slugify(cluster.key)
        team_id = self._unique_id(team_id)
        team = Team(
            id=team_id,
            name=name,
            state=state,
            country=country,
            aliases=tuple(sorted(cluster.raw_names)),
        )
        self._teams[team_id] = team
        self._by_key[(cluster.key, qualifier)] = team_id
        for raw in cluster.raw_names:
            self._by_exact.setdefault(normalize_name(raw), team_id)
        return team

    def _absorb(self, team_id: str, cluster: _Cluster) -> None:
        team = self._teams[team_id]
        merged = tuple(unique((*team.aliases, *sorted(cluster.raw_names))))
        self._teams[team_id] = Team(
            id=team.id, name=team.name, state=team.state, country=team.country,
            nicknames=team.nicknames, aliases=merged,
        )
        for raw in cluster.raw_names:
            self._by_exact.setdefault(normalize_name(raw), team_id)

    @staticmethod
    def _pick_display_name(cluster: _Cluster) -> str:
        """Prefer the most common, accented, properly-capitalised spelling."""

        def score(item: tuple[str, int]) -> tuple:
            raw, count = item
            base, _ = split_qualifier(raw)
            base = base.strip()
            has_accent = any(ord(ch) > 127 for ch in base)
            mixed_case = base != base.lower() and base != base.upper()
            return (count, has_accent, mixed_case, -len(base), base)

        best_raw = max(cluster.raw_names.items(), key=score)[0]
        base, _ = split_qualifier(best_raw)
        base = base.strip()
        if base == base.lower() or base == base.upper():
            base = titleize(base)
        return base

    def _unique_id(self, candidate: str) -> str:
        if candidate not in self._teams:
            return candidate
        index = 2
        while f"{candidate}-{index}" in self._teams:
            index += 1
        return f"{candidate}-{index}"

    # -- lookup ------------------------------------------------------------
    @property
    def teams(self) -> dict[str, Team]:
        return self._teams

    def get(self, team_id: str) -> Team | None:
        return self._teams.get(team_id)

    def resolve_id(self, raw_name: str, *, state: str | None = None) -> str:
        """Resolve a raw dataset spelling, minting a team if necessary."""

        raw_name = (raw_name or "").strip()
        cache_key = (raw_name, state)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        exact = self._by_exact.get(normalize_name(raw_name))
        if exact is not None:
            self._cache[cache_key] = exact
            return exact

        key, qualifier = self._key_and_qualifier(raw_name, state)
        found = self._by_key.get((key, qualifier))
        if found is None and qualifier is not None:
            # A qualified name may only borrow an unqualified entry when the
            # qualifier agrees -- this keeps "River Plate-URU" away from the
            # Argentinian River Plate.
            candidate = self._by_key.get((key, None))
            if candidate is not None:
                team = self._teams[candidate]
                if qualifier in (team.state, team.country):
                    found = candidate
        if found is None:
            cluster = _Cluster(key=key, qualifier=qualifier)
            cluster.raw_names[raw_name] = 1
            found = self._mint(cluster).id
        self._cache[cache_key] = found
        return found

    def resolve(self, raw_name: str, *, state: str | None = None) -> Team:
        return self._teams[self.resolve_id(raw_name, state=state)]

    def lookup(self, raw_name: str, *, brazilian_only: bool = False) -> Team | None:
        """Strict lookup that never mints a team.

        Used to link FIFA club names to the match graph.  ``brazilian_only``
        guards against e.g. "FC Barcelona" colliding with Barcelona SC (ECU).
        """

        raw_name = (raw_name or "").strip()
        if not raw_name:
            return None
        team_id = self._by_exact.get(normalize_name(raw_name))
        if team_id is None:
            key, qualifier = self._key_and_qualifier(raw_name, None)
            team_id = self._by_key.get((key, qualifier))
        if team_id is None:
            return None
        team = self._teams[team_id]
        if brazilian_only and team.country != "BRA":
            return None
        return team

    def search(self, query: str, *, limit: int = 10) -> list[Team]:
        """Fuzzy, user-facing search over names, aliases and nicknames."""

        query = (query or "").strip()
        if not query:
            return []
        normalized = normalize_name(query)
        key, qualifier = self._key_and_qualifier(query, None)

        exact_id = self._by_exact.get(normalized) or self._by_key.get((key, qualifier))
        if exact_id is None and qualifier is None:
            exact_id = self._by_key.get((key, None))
        results: list[Team] = []
        seen: set[str] = set()
        if exact_id:
            results.append(self._teams[exact_id])
            seen.add(exact_id)

        scored: list[tuple[tuple, Team]] = []
        for team in self._teams.values():
            if team.id in seen:
                continue
            haystacks = [normalize_name(team.name), *(normalize_name(a) for a in team.aliases),
                         *(normalize_name(n) for n in team.nicknames), team.id.replace("-", " ")]
            best: tuple | None = None
            for hay in haystacks:
                if hay == normalized:
                    rank = 0
                elif hay.startswith(normalized):
                    rank = 1
                elif normalized in hay:
                    rank = 2
                elif normalized and hay and normalized.split()[0] == hay.split()[0]:
                    rank = 3
                else:
                    continue
                candidate = (rank, len(hay))
                if best is None or candidate < best:
                    best = candidate
            if best is not None:
                scored.append(((best[0], best[1], team.name), team))
        scored.sort(key=lambda item: item[0])
        results.extend(team for _, team in scored)
        return results[:limit]


def _qualifier_sort(item: tuple[str | None, _Cluster]) -> tuple[int, str]:
    qualifier = item[0]
    return (1, "") if qualifier is None else (0, qualifier)
