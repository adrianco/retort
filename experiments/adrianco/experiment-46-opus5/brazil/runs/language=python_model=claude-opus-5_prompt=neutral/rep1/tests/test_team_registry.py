"""Feature: One club, many spellings.

  Scenario: Team name variations are handled
    Given the datasets write "Palmeiras-SP", "Palmeiras" and "Palmeiras - SP"
    When any of them is looked up
    Then they all resolve to the same club
"""

from __future__ import annotations

import pytest

from brazilian_soccer.teams import TeamRegistry


@pytest.fixture()
def registry() -> TeamRegistry:
    names = [
        "Palmeiras-SP", "Palmeiras", "Palmeiras - SP", "SE Palmeiras",
        "Flamengo-RJ", "Flamengo", "Flamengo - PI", "Flamengo do Piauí - PI",
        "Atletico-MG", "Atlético Mineiro", "Atlético - MG",
        "Atletico-PR", "Athletico Paranaense", "Athletico",
        "Atletico-GO", "Atletico Goianiense",
        "Santa Cruz - PE", "Santa Cruz - RN", "Santa Cruz - RS",
        "Nacional (URU)", "Nacional-URU", "Nacional - AM",
        "Sport-PE", "Sport Club do Recife", "Sport Recife",
        "Grêmio-RS", "Gremio", "Grêmio",
        "Vasco da Gama-RJ", "Vasco",
    ]
    built = TeamRegistry()
    for name in names:
        built.observe(name)
    built.build()
    return built


class TestCanonicalIds:

    @pytest.mark.parametrize(
        "spellings, expected",
        [
            (["Palmeiras-SP", "Palmeiras", "Palmeiras - SP", "SE Palmeiras"],
             "palmeiras"),
            (["Grêmio-RS", "Gremio", "Grêmio"], "gremio"),
            (["Sport-PE", "Sport Club do Recife", "Sport Recife"], "sport-recife"),
            (["Vasco da Gama-RJ", "Vasco"], "vasco-da-gama"),
            (["Nacional (URU)", "Nacional-URU"], "nacional-uru"),
        ],
    )
    def test_variants_collapse_to_one_club(self, registry, spellings, expected):
        """
        Given several spellings of one club
        When each is mapped to a canonical id
        Then they all produce the same id
        """
        ids = {registry.team_id_for_raw(name) for name in spellings}

        assert ids == {expected}

    def test_same_name_different_state_stays_separate(self, registry):
        """
        Given three clubs called Santa Cruz in different states
        When they are registered
        Then each keeps its own identity
        """
        ids = {registry.team_id_for_raw(name) for name in
               ("Santa Cruz - PE", "Santa Cruz - RN", "Santa Cruz - RS")}

        assert len(ids) == 3

    def test_the_three_atleticos_are_distinct(self, registry):
        """
        Given Atlético-MG, Athletico-PR and Atlético-GO
        When their many spellings are registered
        Then three clubs exist, each with all of its spellings
        """
        mineiro = {registry.team_id_for_raw(n)
                   for n in ("Atletico-MG", "Atlético Mineiro", "Atlético - MG")}
        paranaense = {registry.team_id_for_raw(n)
                      for n in ("Atletico-PR", "Athletico Paranaense", "Athletico")}
        goianiense = {registry.team_id_for_raw(n)
                      for n in ("Atletico-GO", "Atletico Goianiense")}

        assert mineiro == {"atletico-mineiro"}
        assert paranaense == {"athletico-paranaense"}
        assert goianiense == {"atletico-goianiense"}

    def test_famous_and_obscure_namesakes_are_separated(self, registry):
        """
        Given Flamengo of Rio and Flamengo of Piauí
        When both are registered
        Then the bare spelling belongs to the Rio club
        """
        assert registry.team_id_for_raw("Flamengo") == "flamengo"
        assert registry.team_id_for_raw("Flamengo - PI") == "flamengo-pi"

    def test_display_names_keep_their_accents(self, registry):
        assert registry.name_of("gremio") == "Grêmio"
        assert registry.name_of("nacional-uru") == "Nacional (URU)"


class TestResolution:

    @pytest.mark.parametrize(
        "query",
        ["Palmeiras", "palmeiras", "PALMEIRAS", "Palmeiras-SP", "SE Palmeiras",
         "palmeiras "],
    )
    def test_user_queries_resolve(self, registry, query):
        """
        Given a user typing a club name in any case or with a suffix
        When it is resolved
        Then the right club comes back
        """
        assert registry.resolve_one(query).team_id == "palmeiras"

    def test_query_with_a_state_disambiguates(self, registry):
        assert registry.resolve_one("Santa Cruz-RN").state == "RN"

    def test_unknown_names_resolve_to_nothing(self, registry):
        assert registry.resolve_one("Real Madrid") is None

    def test_search_lists_matching_clubs(self, registry):
        """
        Given three clubs that share the name "Santa Cruz"
        When the club list is searched
        Then all three are listed, distinguished by state
        """
        found = registry.search("santa cruz", limit=10)

        assert len(found) == 3
        assert {team.state for team in found} == {"PE", "RN", "RS"}

    def test_namesakes_in_unknown_states_stay_separate(self, graph):
        """
        Given small clubs that share a famous club's name in another state
        When they are registered
        Then they get their own identity instead of being merged into the
        famous club, whose match list would otherwise be polluted

        Náutico-PE and Náutico-RR (Roraima) are different clubs; so are
        Internacional-RS and Internacional-SC, Vitória-BA and Vitória-ES.
        """
        pairs = [
            ("Náutico - PE", "Nautico - RR"),
            ("Internacional", "Internacional - SC"),
            ("Vitória - BA", "Vitoria ES"),
            ("Juventude - RS", "Juventude - MA"),
            ("Guarani - SP", "Guarani - CE"),
            ("Portuguesa - SP", "Portuguesa RJ"),
            ("Fluminense - RJ", "Fluminense PI"),
        ]
        registry = graph.registry
        for famous, namesake in pairs:
            big = registry.team_id_for_raw(famous)
            small = registry.team_id_for_raw(namesake)
            assert big is not None and small is not None, (famous, namesake)
            assert big != small, f"{namesake} was merged into {famous}"

    def test_real_data_resolves_the_big_clubs(self, graph):
        """
        Given the real datasets
        When the twelve biggest clubs are looked up by their common names
        Then each resolves to a club with hundreds of matches
        """
        for name in ("Flamengo", "Palmeiras", "Corinthians", "São Paulo",
                     "Santos", "Grêmio", "Internacional", "Cruzeiro",
                     "Atlético Mineiro", "Fluminense", "Vasco", "Botafogo"):
            team = graph.resolve_team(name)
            assert team is not None, name
            assert len(graph.team_matches(team.team_id)) > 300, name
