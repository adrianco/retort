"""Canonical club registry and the name resolver built on top of it.

Context
-------
The specification calls out team-name normalisation as the main data-quality
hazard, and it is: the same club shows up as ``Atletico-PR`` (Brasileirão CSV),
``Athletico Paranaense`` *and* ``Atletico Paranaense`` (BR-Football CSV),
``Atlético - PR`` (Copa do Brasil CSV), ``Athletico-PR`` (historical CSV) and
``Atlético Paranaense`` (FIFA CSV).  Meanwhile a bare ``Atlético`` is genuinely
ambiguous between Mineiro (MG), Paranaense (PR) and Goianiense (GO), and only
the state suffix distinguishes ``Botafogo-RJ`` from ``Botafogo-PB``.

:func:`resolve_club` therefore works in layers:

1. normalise the raw string and peel off any trailing state code;
2. look the ``(base, state)`` pair up in the curated alias index;
3. look the bare ``base`` up, but only where it is unambiguous;
4. retry both after stripping filler tokens (``EC``/``FC``/``Esporte``/...);
5. fall back to a generated identity so that the ~250 small cup clubs still
   get a stable key instead of being dropped.

The registry only needs to cover clubs whose spellings actually collide; every
other club is handled correctly by the generic path.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .normalization import (
    drop_filler,
    name_variants,
    normalize_text,
    slugify,
    split_state_suffix,
)

__all__ = [
    "ClubProfile",
    "TeamIdentity",
    "REGISTRY",
    "RIVALRIES",
    "AMBIGUOUS_BASES",
    "resolve_club",
    "profile_for",
    "alternatives_for",
    "rivalry_for",
]


@dataclass(frozen=True)
class ClubProfile:
    """A curated club: canonical display name, home state and known spellings."""

    slug: str
    name: str
    state: str | None
    aliases: tuple[str, ...] = ()
    nicknames: tuple[str, ...] = ()


@dataclass(frozen=True)
class TeamIdentity:
    """The result of resolving a raw team string.

    ``known`` is ``True`` when the name matched the curated registry, which is
    what lets the query layer tell "I understood this club" from "I made up a
    key for a string I have never seen before".
    """

    slug: str
    name: str
    state: str | None
    known: bool = False
    raw: str = ""

    @property
    def display(self) -> str:
        if self.state and not self.known:
            return f"{self.name} ({self.state.upper()})"
        return self.name


def _club(slug, name, state, aliases=(), nicknames=()):
    return ClubProfile(slug, name, state, tuple(aliases), tuple(nicknames))


#: Curated clubs.  Aliases are raw spellings observed in the datasets (or that
#: a user is likely to type); they are normalised when the index is built.
REGISTRY: tuple[ClubProfile, ...] = (
    # --- Rio de Janeiro -----------------------------------------------------
    _club("flamengo", "Flamengo", "rj",
          ["Flamengo", "CR Flamengo", "Clube de Regatas do Flamengo", "Fla"],
          ["Mengão", "Rubro-Negro"]),
    _club("fluminense", "Fluminense", "rj",
          ["Fluminense", "Fluminense FC", "Flu"], ["Tricolor Carioca"]),
    _club("botafogo-rj", "Botafogo", "rj",
          ["Botafogo", "Botafogo RJ", "Botafogo de Futebol e Regatas", "Botafogo FR"],
          ["Fogão", "Glorioso"]),
    _club("vasco-da-gama", "Vasco da Gama", "rj",
          ["Vasco", "Vasco da Gama", "Vasco Da Gama", "CR Vasco da Gama"],
          ["Gigante da Colina", "Cruzmaltino"]),
    _club("boavista-rj", "Boavista", "rj",
          ["Boavista", "Boavista Sport Club",
           "Boavista Sport Club (antigo Esporte Clube Barreira)"]),
    _club("bangu", "Bangu", "rj", ["Bangu", "Bangu AC"]),
    _club("volta-redonda", "Volta Redonda", "rj", ["Volta Redonda"]),
    _club("madureira", "Madureira", "rj", ["Madureira"]),
    _club("cabofriense", "Cabofriense", "rj", ["Cabofriense"]),
    _club("resende", "Resende", "rj", ["Resende"]),
    _club("macae", "Macaé", "rj", ["Macae", "Macaé"]),
    _club("americano-rj", "Americano", "rj", ["Americano"]),

    # --- São Paulo ----------------------------------------------------------
    _club("sao-paulo", "São Paulo", "sp",
          ["Sao Paulo", "São Paulo", "Sao Paulo FC", "São Paulo FC", "SPFC"],
          ["Tricolor Paulista", "Soberano"]),
    _club("corinthians", "Corinthians", "sp",
          ["Corinthians", "SC Corinthians Paulista",
           "Sport Club Corinthians Paulista", "Corinthians Paulista"],
          ["Timão"]),
    _club("palmeiras", "Palmeiras", "sp",
          ["Palmeiras", "SE Palmeiras", "Sociedade Esportiva Palmeiras"],
          ["Verdão", "Porco"]),
    _club("santos", "Santos", "sp",
          ["Santos", "Santos FC"], ["Peixe", "Alvinegro Praiano"]),
    _club("red-bull-bragantino", "Red Bull Bragantino", "sp",
          ["Bragantino", "Red Bull Bragantino", "RB Bragantino",
           "Red Bull Brasil"], ["Massa Bruta"]),
    _club("ponte-preta", "Ponte Preta", "sp",
          ["Ponte Preta", "AA Ponte Preta"], ["Macaca"]),
    _club("portuguesa-sp", "Portuguesa", "sp",
          ["Portuguesa", "Associacao Portuguesa de Desportos", "Lusa"]),
    _club("guarani", "Guarani", "sp", ["Guarani", "Guarani FC"], ["Bugre"]),
    _club("sao-caetano", "São Caetano", "sp", ["Sao Caetano", "São Caetano"]),
    _club("santo-andre", "Santo André", "sp", ["Santo Andre", "Santo André"]),
    _club("barueri", "Grêmio Barueri", "sp",
          ["Barueri", "Gremio Barueri", "Grêmio Barueri", "Gremio Prudente",
           "Grêmio Prudente"]),
    _club("audax-sp", "Audax", "sp", ["Audax", "Audax Sao Paulo"]),
    _club("ituano", "Ituano", "sp", ["Ituano"]),
    _club("mirassol", "Mirassol", "sp", ["Mirassol"]),
    _club("novorizontino", "Novorizontino", "sp", ["Novorizontino"]),
    _club("botafogo-sp", "Botafogo-SP", "sp", ["Botafogo SP", "Botafogo Ribeirao Preto"]),
    _club("sao-bento", "São Bento", "sp", ["Sao Bento", "São Bento"]),
    _club("oeste", "Oeste", "sp", ["Oeste"]),
    _club("capivariano", "Capivariano", "sp", ["Capivariano"]),
    _club("juventus-sp", "Juventus-SP", "sp", ["Juventus SP"]),

    # --- Minas Gerais -------------------------------------------------------
    _club("atletico-mg", "Atlético Mineiro", "mg",
          ["Atletico Mineiro", "Atlético Mineiro", "Atletico MG", "Clube Atletico Mineiro"],
          ["Galo"]),
    _club("cruzeiro", "Cruzeiro", "mg", ["Cruzeiro", "Cruzeiro EC"], ["Raposa"]),
    _club("america-mg", "América Mineiro", "mg",
          ["America MG", "América MG", "America Mineiro", "América Mineiro",
           "America FC (Minas Gerais)", "America FC Minas Gerais"], ["Coelho"]),
    _club("tombense", "Tombense", "mg", ["Tombense"]),
    _club("caldense", "Caldense", "mg", ["Caldense"]),
    _club("ipatinga", "Ipatinga", "mg", ["Ipatinga"]),
    _club("villa-nova-mg", "Villa Nova", "mg", ["Villa Nova"]),
    _club("uberlandia", "Uberlândia", "mg", ["Uberlandia", "Uberlândia"]),
    _club("boa-esporte", "Boa Esporte", "mg", ["Boa", "Boa Esporte"]),
    _club("betim", "Betim", "mg", ["Betim"]),
    _club("democrata-gv", "Democrata", "mg", ["Democrata"]),

    # --- Rio Grande do Sul --------------------------------------------------
    _club("gremio", "Grêmio", "rs",
          ["Gremio", "Grêmio", "Gremio FBPA", "Gremio Foot-Ball Porto Alegrense"],
          ["Imortal Tricolor"]),
    _club("internacional", "Internacional", "rs",
          ["Internacional", "SC Internacional", "Inter"], ["Colorado"]),
    _club("juventude", "Juventude", "rs",
          ["Juventude", "EC Juventude", "Esporte Clube Juventude"]),
    _club("caxias", "Caxias", "rs", ["Caxias", "SER Caxias"]),
    _club("brasil-de-pelotas", "Brasil de Pelotas", "rs",
          ["Brasil", "Brasil de Pelotas", "GE Brasil"]),
    _club("ypiranga-rs", "Ypiranga", "rs", ["Ypiranga"]),
    _club("sao-jose-rs", "São José", "rs", ["Sao Jose", "São José"]),
    _club("aimore", "Aimoré", "rs", ["Aimore", "Aimoré"]),
    _club("avenida", "Avenida", "rs", ["Avenida"]),
    _club("veranopolis", "Veranópolis", "rs", ["Veranopolis", "Veranópolis"]),

    # --- Paraná / Santa Catarina -------------------------------------------
    _club("athletico-pr", "Athletico Paranaense", "pr",
          ["Athletico PR", "Atletico PR", "Athletico Paranaense",
           "Atletico Paranaense", "Atlético Paranaense", "Club Athletico Paranaense"],
          ["Furacão"]),
    _club("coritiba", "Coritiba", "pr", ["Coritiba", "Coritiba FC"], ["Coxa"]),
    _club("parana", "Paraná", "pr", ["Parana", "Paraná", "Parana Clube"]),
    _club("londrina", "Londrina", "pr", ["Londrina"]),
    _club("operario-pr", "Operário-PR", "pr", ["Operario PR", "Operario Ferroviario"]),
    _club("cianorte", "Cianorte", "pr", ["Cianorte"]),
    _club("maringa", "Maringá", "pr", ["Maringa", "Maringá"]),
    _club("toledo", "Toledo", "pr", ["Toledo"]),
    _club("arapongas", "Arapongas", "pr", ["Arapongas", "Arapongas Esporte Clube"]),
    _club("chapecoense", "Chapecoense", "sc",
          ["Chapecoense", "Associacao Chapecoense de Futebol"], ["Chape"]),
    _club("avai", "Avaí", "sc", ["Avai", "Avaí", "Avai FC"]),
    _club("figueirense", "Figueirense", "sc", ["Figueirense", "Figueirense FC"]),
    _club("criciuma", "Criciúma", "sc", ["Criciuma", "Criciúma", "Criciuma EC"]),
    _club("joinville", "Joinville", "sc", ["Joinville", "Joinville EC"]),
    _club("brusque", "Brusque", "sc", ["Brusque"]),
    _club("hercilio-luz", "Hercílio Luz", "sc", ["Hercilio Luz"]),
    _club("marcilio-dias", "Marcílio Dias", "sc", ["Marcilio Dias"]),
    _club("metropolitano", "Metropolitano", "sc", ["Metropolitano"]),

    # --- Nordeste -----------------------------------------------------------
    _club("bahia", "Bahia", "ba",
          ["Bahia", "EC Bahia", "Esporte Clube Bahia"], ["Esquadrão de Aço"]),
    _club("vitoria", "Vitória", "ba",
          ["Vitoria", "Vitória", "EC Vitoria"], ["Leão da Barra"]),
    _club("bahia-de-feira", "Bahia de Feira", "ba", ["Bahia de Feira"]),
    _club("juazeirense", "Juazeirense", "ba", ["Juazeirense"]),
    _club("jacuipense", "Jacuipense", "ba", ["Jacuipense"]),
    _club("atletico-ba", "Atlético-BA", "ba", ["Atletico BA"]),
    _club("sport", "Sport Recife", "pe",
          ["Sport", "Sport Recife", "Sport Club do Recife", "Sport Club Recife"],
          ["Leão da Ilha"]),
    _club("nautico", "Náutico", "pe",
          ["Nautico", "Náutico", "Clube Nautico Capibaribe"], ["Timbu"]),
    _club("santa-cruz", "Santa Cruz", "pe",
          ["Santa Cruz", "Santa Cruz FC", "Santa Cruz Futebol Clube"], ["Cobra Coral"]),
    _club("salgueiro", "Salgueiro", "pe", ["Salgueiro"]),
    _club("central-pe", "Central", "pe", ["Central"]),
    _club("afogados", "Afogados", "pe", ["Afogados"]),
    _club("ceara", "Ceará", "ce",
          ["Ceara", "Ceará", "Ceara Sporting Club", "Ceara SC"], ["Vozão"]),
    _club("fortaleza", "Fortaleza", "ce",
          ["Fortaleza", "Fortaleza FC", "Fortaleza Esporte Clube"], ["Leão do Pici"]),
    _club("ferroviario-ce", "Ferroviário", "ce", ["Ferroviario"]),
    _club("atletico-ce", "Atlético Cearense", "ce",
          ["Atletico Cearense", "Uniclinic"]),
    _club("guarany-sobral", "Guarany de Sobral", "ce", ["Guarany de Sobral", "Guarany"]),
    _club("caucaia", "Caucaia", "ce", ["Caucaia"]),
    _club("barbalha", "Barbalha", "ce", ["Barbalha"]),
    _club("abc", "ABC", "rn", ["ABC", "Abc", "A.b.c."]),
    _club("america-rn", "América de Natal", "rn",
          ["America RN", "América RN", "America de Natal", "América de Natal"]),
    _club("alecrim", "Alecrim", "rn", ["Alecrim"]),
    _club("globo-fc", "Globo FC", "rn", ["Globo"]),
    _club("potiguar", "Potiguar", "rn", ["Potiguar"]),
    _club("csa", "CSA", "al", ["CSA", "Csa", "C.s.a.", "Centro Sportivo Alagoano"]),
    _club("crb", "CRB", "al", ["CRB", "Crb", "C.r.b.", "Clube de Regatas Brasil"]),
    _club("asa", "ASA", "al", ["ASA", "Asa", "A.s.a.", "Agremiacao Sportiva Arapiraquense"]),
    _club("murici", "Murici", "al", ["Murici"]),
    _club("confianca", "Confiança", "se", ["Confianca", "Confiança"]),
    _club("sergipe", "Sergipe", "se", ["Sergipe"]),
    _club("itabaiana", "Itabaiana", "se", ["Itabaiana"]),
    _club("botafogo-pb", "Botafogo-PB", "pb", ["Botafogo PB"]),
    _club("campinense", "Campinense", "pb", ["Campinense"]),
    _club("treze", "Treze", "pb", ["Treze"]),
    _club("sousa", "Sousa", "pb", ["Sousa"]),
    _club("sampaio-correa", "Sampaio Corrêa", "ma", ["Sampaio Correa", "Sampaio Corrêa"]),
    _club("moto-club", "Moto Club", "ma", ["Moto Club"]),
    _club("imperatriz", "Imperatriz", "ma", ["Imperatriz"]),
    _club("river-pi", "River-PI", "pi", ["River PI", "River"]),
    _club("altos", "Altos", "pi", ["Altos"]),
    _club("quatro-de-julho", "4 de Julho", "pi", ["4 de Julho"]),

    # --- Norte / Centro-Oeste ----------------------------------------------
    _club("remo", "Remo", "pa", ["Remo", "Clube do Remo"]),
    _club("paysandu", "Paysandu", "pa", ["Paysandu", "Paysandu SC"]),
    _club("aguia-de-maraba", "Águia de Marabá", "pa", ["Aguia", "Águia", "Aguia de Maraba"]),
    _club("castanhal", "Castanhal", "pa", ["Castanhal"]),
    _club("cameta", "Cametá", "pa", ["Cameta", "Cametá"]),
    _club("bragantino-pa", "Bragantino-PA", "pa", ["Bragantino PA"]),
    _club("sao-raimundo-am", "São Raimundo", "am", ["Sao Raimundo", "São Raimundo"]),
    _club("manaus", "Manaus", "am", ["Manaus"]),
    _club("princesa-do-solimoes", "Princesa do Solimões", "am", ["Princesa do Solimoes"]),
    _club("santos-ap", "Santos-AP", "ap", ["Santos AP"]),
    _club("trem", "Trem", "ap", ["Trem"]),
    _club("ypiranga-ap", "Ypiranga-AP", "ap", ["Ypiranga AP"]),
    _club("genus", "Genus", "ro", ["Genus"]),
    _club("vilhena", "Vilhena", "ro", ["Vilhena"]),
    _club("real-ariquemes", "Real Ariquemes", "ro", ["Real Ariquemes"]),
    _club("atletico-ac", "Atlético Acreano", "ac", ["Atletico AC", "Atletico Acreano"]),
    _club("rio-branco-ac", "Rio Branco", "ac", ["Rio Branco"]),
    _club("nacional-rr", "Nacional-RR", "rr", ["Nacional RR"]),
    _club("bare-rr", "Baré", "rr", ["Bare", "Baré"]),
    _club("goias", "Goiás", "go", ["Goias", "Goiás", "Goias EC"], ["Esmeraldino"]),
    _club("atletico-go", "Atlético Goianiense", "go",
          ["Atletico GO", "Atletico Goianiense", "Atlético Goianiense"], ["Dragão"]),
    _club("vila-nova-go", "Vila Nova", "go", ["Vila Nova", "Vila Nova GO"]),
    _club("aparecidense", "Aparecidense", "go", ["Aparecidense"]),
    _club("anapolina", "Anapolina", "go", ["Anapolina"]),
    _club("anapolis", "Anápolis", "go", ["Anapolis", "Anápolis"]),
    _club("crac", "CRAC", "go", ["CRAC", "C.r.a.c."]),
    _club("cuiaba", "Cuiabá", "mt", ["Cuiaba", "Cuiabá", "Cuiaba EC"], ["Dourado"]),
    _club("luverdense", "Luverdense", "mt", ["Luverdense"]),
    _club("mixto", "Mixto", "mt", ["Mixto"]),
    _club("operario-ms", "Operário-MS", "ms", ["Operario MS"]),
    _club("comercial-ms", "Comercial-MS", "ms", ["Comercial MS"]),
    _club("aguia-negra", "Águia Negra", "ms", ["Aguia Negra", "Águia Negra"]),
    _club("brasiliense", "Brasiliense", "df", ["Brasiliense"]),
    _club("gama", "Gama", "df", ["Gama"]),
    _club("ceilandia", "Ceilândia", "df", ["Ceilandia", "Ceilândia"]),
    _club("brasilia-fc", "Brasília FC", "df", ["Brasilia FC", "Brasilia"]),

    # --- Espírito Santo -----------------------------------------------------
    _club("vitoria-es", "Vitória-ES", "es", ["Vitoria ES"]),
    _club("atletico-es", "Atlético-ES", "es", ["Atletico ES"]),
    _club("desportiva-ferroviaria", "Desportiva Ferroviária", "es",
          ["Desportiva", "Desportiva Ferroviaria"]),
    _club("aracruz", "Aracruz", "es", ["Aracruz"]),
    _club("real-noroeste", "Real Noroeste", "es", ["Real Noroeste"]),

    # --- Non-Brazilian clubs that appear in the Libertadores file -----------
    _club("boca-juniors", "Boca Juniors", None, ["Boca Juniors", "Boca"]),
    _club("river-plate", "River Plate", None, ["River Plate"]),
    _club("racing-club", "Racing Club", None, ["Racing Club", "Racing"]),
    _club("independiente", "Independiente", None, ["Independiente"]),
    _club("san-lorenzo", "San Lorenzo", None, ["San Lorenzo"]),
    _club("velez-sarsfield", "Vélez Sarsfield", None, ["Velez Sarsfield", "Velez"]),
    _club("estudiantes", "Estudiantes", None, ["Estudiantes"]),
    _club("lanus", "Lanús", None, ["Lanus", "Lanús"]),
    # Names here deliberately avoid parentheses: a parenthesised alias such as
    # "Nacional (COL)" would also register the bare form "nacional", which
    # three different clubs in this file legitimately claim.
    _club("nacional-uru", "Nacional-URU", None, ["Nacional (URU)", "Nacional URU"]),
    _club("nacional-par", "Nacional-PAR", None, ["Nacional (PAR)", "Nacional PAR"]),
    _club("penarol", "Peñarol", None, ["Penarol", "Peñarol"]),
    _club("colo-colo", "Colo-Colo", None, ["Colo Colo", "Colo-Colo"]),
    _club("universidad-de-chile", "Universidad de Chile", None, ["Universidad de Chile"]),
    _club("u-catolica", "Universidad Católica", None,
          ["Universidad Catolica", "U. Catolica"]),
    _club("atletico-nacional", "Atlético Nacional", None, ["Atletico Nacional"]),
    _club("millonarios", "Millonarios", None, ["Millonarios"]),
    _club("junior-barranquilla", "Junior de Barranquilla", None,
          ["Junior Barranquilla", "Junior de Barranquilla", "Atletico Junior"]),
    _club("libertad", "Libertad", None, ["Libertad", "Libertad-PAR", "Libertad PAR"]),
    _club("cerro-porteno", "Cerro Porteño", None, ["Cerro Porteno", "Cerro Porteño"]),
    _club("olimpia", "Olimpia", None, ["Olimpia", "Olimpia-PAR", "Olimpia PAR"]),
    _club("guarani-par", "Guaraní-PAR", None,
          ["Guarani (PAR)", "Guarani PAR", "Guarani-PAR"]),
    _club("universitario-per", "Universitario-PER", None,
          ["Universitario (PER)", "Universitario PER"]),
    _club("trujillanos", "Trujillanos", None,
          ["Trujillanos (VEN)", "Trujillanos VEN"]),
    _club("the-strongest", "The Strongest", None, ["The Strongest"]),
    _club("bolivar", "Bolívar", None, ["Bolivar", "Bolívar"]),
    # "Barcelona" on its own must NOT claim this club -- FC Barcelona appears
    # in the FIFA player file and would otherwise be joined to it.
    _club("barcelona-equ", "Barcelona-EQU", None, ["Barcelona EQU", "Barcelona-EQU"]),
    _club("delfin", "Delfín", None, ["Delfin", "Delfín", "Delfin-EQU", "Delfin EQU"]),
    _club("emelec", "Emelec", None, ["Emelec"]),
    _club("ldu-quito", "LDU Quito", None, ["LDU Quito", "LDU"]),
    _club("sporting-cristal", "Sporting Cristal", None, ["Sporting Cristal"]),
    _club("alianza-lima", "Alianza Lima", None, ["Alianza Lima"]),
    _club("tigres-uanl", "Tigres UANL", None, ["Tigres UANL", "Tigres"]),
    _club("toluca", "Toluca", None, ["Toluca"]),
    _club("deportes-tolima", "Deportes Tolima", None, ["Deportes Tolima", "Tolima"]),
    _club("deportivo-tachira", "Deportivo Táchira", None,
          ["Deportivo Tachira", "Deportivo Táchira"]),
    _club("caracas", "Caracas", None, ["Caracas"]),
    _club("river-plate-uru", "River Plate-URU", None,
          ["River Plate URU", "River Plate-URU"]),
)


#: Classic Brazilian derbies, keyed by the frozenset of the two club slugs.
RIVALRIES: dict[frozenset, str] = {
    frozenset({"flamengo", "fluminense"}): "Fla-Flu",
    frozenset({"flamengo", "vasco-da-gama"}): "Clássico dos Milhões",
    frozenset({"flamengo", "botafogo-rj"}): "Clássico da Rivalidade",
    frozenset({"fluminense", "botafogo-rj"}): "Clássico Vovô",
    frozenset({"fluminense", "vasco-da-gama"}): "Clássico dos Gigantes",
    frozenset({"botafogo-rj", "vasco-da-gama"}): "Clássico da Amizade",
    frozenset({"corinthians", "palmeiras"}): "Derby Paulista",
    frozenset({"corinthians", "sao-paulo"}): "Majestoso",
    frozenset({"corinthians", "santos"}): "Clássico Alvinegro",
    frozenset({"palmeiras", "sao-paulo"}): "Choque-Rei",
    frozenset({"palmeiras", "santos"}): "Clássico da Saudade",
    frozenset({"santos", "sao-paulo"}): "San-São",
    frozenset({"gremio", "internacional"}): "Gre-Nal",
    frozenset({"atletico-mg", "cruzeiro"}): "Clássico Mineiro",
    frozenset({"athletico-pr", "coritiba"}): "Atletiba",
    frozenset({"bahia", "vitoria"}): "Ba-Vi",
    frozenset({"ceara", "fortaleza"}): "Clássico-Rei",
    frozenset({"sport", "nautico"}): "Clássico dos Clássicos",
    frozenset({"sport", "santa-cruz"}): "Clássico das Multidões",
    frozenset({"nautico", "santa-cruz"}): "Clássico dos Maiorais",
    frozenset({"goias", "atletico-go"}): "Clássico Goianiense",
    frozenset({"abc", "america-rn"}): "Clássico Rei do Rio Grande do Norte",
    frozenset({"csa", "crb"}): "Clássico das Multidões Alagoano",
}


def rivalry_for(slug_a: str, slug_b: str) -> str | None:
    """Return the derby name for a pair of clubs, if it is a classic fixture."""
    return RIVALRIES.get(frozenset({slug_a, slug_b}))


# ---------------------------------------------------------------------------
# Alias index construction
# ---------------------------------------------------------------------------

#: When a bare name such as ``botafogo`` or ``america`` is claimed by several
#: clubs, the first one listed here wins.  This only affects *user* input --
#: every dataset spells these clubs with their state suffix.
PROMINENCE: tuple[str, ...] = (
    "flamengo", "palmeiras", "corinthians", "sao-paulo", "santos",
    "gremio", "internacional", "cruzeiro", "atletico-mg", "vasco-da-gama",
    "fluminense", "botafogo-rj", "athletico-pr", "bahia", "vitoria",
    "sport", "nautico", "santa-cruz", "ceara", "fortaleza", "goias",
    "atletico-go", "coritiba", "america-mg", "chapecoense", "cuiaba",
    "avai", "figueirense", "juventude", "ponte-preta", "portuguesa-sp",
    "red-bull-bragantino", "csa", "crb", "abc", "america-rn", "paysandu",
    "remo", "guarani", "criciuma", "parana", "brasiliense",
)

_REGISTRY_ORDER = {club.slug: i for i, club in enumerate(REGISTRY)}
_PROMINENCE_ORDER = {slug: i for i, slug in enumerate(PROMINENCE)}


def _rank(slug: str) -> int:
    """Sort key expressing how likely a bare name refers to this club."""
    if slug in _PROMINENCE_ORDER:
        return _PROMINENCE_ORDER[slug]
    return 1000 + _REGISTRY_ORDER.get(slug, 9999)


def _build_index() -> tuple[dict, dict, dict, dict]:
    """Build the ``(base, state) -> slug`` and ``base -> [slug]`` lookup tables."""
    by_pair: dict[tuple[str, str | None], str] = {}
    bare_owners: dict[str, set[str]] = {}
    by_slug: dict[str, ClubProfile] = {}

    for club in REGISTRY:
        by_slug[club.slug] = club
        forms: set[str] = set()
        for alias in (club.name, *club.aliases, *club.nicknames):
            for variant in name_variants(alias):
                base, state = split_state_suffix(variant)
                if not base:
                    continue
                reduced = drop_filler(base)
                forms.add(base)
                if reduced:
                    forms.add(reduced)
                # ``America MG`` also teaches us the (america, mg) pair.
                if state:
                    by_pair.setdefault((base, state), club.slug)
                    if reduced:
                        by_pair.setdefault((reduced, state), club.slug)
        for form in forms:
            by_pair.setdefault((form, club.state), club.slug)
            bare_owners.setdefault(form, set()).add(club.slug)

    owners = {form: tuple(sorted(slugs, key=_rank))
              for form, slugs in bare_owners.items()}
    by_bare = {form: slugs[0] for form, slugs in owners.items()}
    ambiguous = {form: slugs for form, slugs in owners.items() if len(slugs) > 1}
    return by_pair, by_bare, by_slug, ambiguous


_BY_PAIR, _BY_BARE, _BY_SLUG, AMBIGUOUS_BASES = _build_index()


def alternatives_for(raw: str) -> tuple[str, ...]:
    """Return the other clubs a bare, ambiguous name could have meant."""
    for variant in name_variants(raw):
        base, state = split_state_suffix(variant)
        if state:
            return ()
        for candidate in (base, drop_filler(base)):
            if candidate in AMBIGUOUS_BASES:
                return AMBIGUOUS_BASES[candidate]
    return ()


def profile_for(slug: str) -> ClubProfile | None:
    """Return the curated :class:`ClubProfile` for *slug*, if there is one."""
    return _BY_SLUG.get(slug)


@lru_cache(maxsize=8192)
def resolve_club(raw: str) -> TeamIdentity:
    """Resolve any raw team spelling to a stable :class:`TeamIdentity`.

    Unknown clubs still get a deterministic slug (``"<base>-<state>"``) so that
    the ~250 minor Copa do Brasil sides remain queryable; they are simply
    flagged ``known=False``.
    """
    if raw is None:
        return TeamIdentity(slug="", name="", state=None, known=False, raw="")
    text = str(raw).strip()
    if not text:
        return TeamIdentity(slug="", name="", state=None, known=False, raw="")

    fallback: tuple[str, str | None] | None = None
    for variant in name_variants(text):
        base, state = split_state_suffix(variant)
        if not base:
            continue
        if fallback is None:
            fallback = (base, state)
        candidates = [base, drop_filler(base)]
        for candidate in candidates:
            if not candidate:
                continue
            if state is None:
                # No state to disambiguate with: fall straight to the
                # prominence-ranked bare index, so "Guarani" means the
                # Campinas club rather than Guaraní of Paraguay.
                slug = _BY_BARE.get(candidate)
            else:
                slug = _BY_PAIR.get((candidate, state))
                if slug is None:
                    # The state suffix may be missing from the registry entry
                    # (e.g. a foreign club written as "Nacional URU").
                    bare = _BY_BARE.get(candidate)
                    if bare is not None and _BY_SLUG[bare].state in (None, state):
                        slug = bare
            if slug is not None:
                club = _BY_SLUG[slug]
                return TeamIdentity(slug=club.slug, name=club.name,
                                    state=club.state, known=True, raw=text)

    # Unknown club: build a deterministic key from the filler-free base so
    # that "Aquidauanense Futebol Clube - MS" and "Aquidauanense - MS" agree.
    base, state = fallback if fallback else (normalize_text(text), None)
    base = drop_filler(base) or base
    slug = slugify(base, state or "")
    display = " ".join(word.capitalize() for word in base.split()) or text
    return TeamIdentity(slug=slug or slugify(text), name=display,
                        state=state, known=False, raw=text)
