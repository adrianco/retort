"""
================================================================================
BDD Feature: Data Loading
================================================================================

CONTEXT
-------
Verifies that all six bundled datasets load, normalise correctly and are
queryable - covering the specification's "Data Coverage" success criteria
(all CSV files loadable, UTF-8 / name / date handling).
================================================================================
"""

import time

from brazilian_soccer_mcp.normalize import (
    clean_team_name, team_key, names_match, iso_date, to_int,
    competition_matches, COMP_BRASILEIRAO, COMP_COPA_BRASIL, COMP_LIBERTADORES,
)

EXPECTED_SOURCES = {
    "brasileirao_serie_a", "copa_do_brasil", "libertadores",
    "br_football_extended", "brasileirao_historic",
}


class TestNormalisation:
    """Feature: Normalise inconsistent names, dates and competitions."""

    def test_state_suffix_is_stripped(self):
        # Given a team name carrying a state suffix
        # When it is cleaned
        # Then the suffix is removed but accents preserved
        assert clean_team_name("Palmeiras-SP") == "Palmeiras"
        assert clean_team_name("Grêmio-RS") == "Grêmio"
        assert clean_team_name("América - MG") == "América"

    def test_team_key_collapses_variations(self):
        # Given variations of the same team name
        # When the match key is computed
        # Then they collapse to one canonical key
        assert team_key("Flamengo-RJ") == team_key("Flamengo") == "flamengo"
        assert team_key("São Paulo") == "saopaulo"

    def test_names_match_handles_substring(self):
        # Given a short query and a long official name
        # Then they are considered the same team
        assert names_match("Corinthians", "Sport Club Corinthians Paulista")
        assert names_match("Flamengo", "Flamengo-RJ")
        assert not names_match("Flamengo", "Fluminense")

    def test_multiple_date_formats(self):
        # Given dates in several dataset formats
        # Then all parse to ISO YYYY-MM-DD
        assert iso_date("2023-09-24") == "2023-09-24"
        assert iso_date("29/03/2003") == "2003-03-29"
        assert iso_date("2012-05-19 18:30:00") == "2012-05-19"
        assert iso_date("") is None

    def test_int_parsing_is_tolerant(self):
        assert to_int("3") == 3
        assert to_int("2.0") == 2
        assert to_int("") is None
        assert to_int("nan") is None

    def test_competition_aliases(self):
        # Given alias queries
        # Then they map to the right canonical competition
        assert competition_matches("Serie A", COMP_BRASILEIRAO)
        assert competition_matches("brasileirao", COMP_BRASILEIRAO)
        assert competition_matches("Libertadores", COMP_LIBERTADORES)
        assert competition_matches("Copa do Brasil", COMP_COPA_BRASIL)
        assert not competition_matches("Libertadores", COMP_BRASILEIRAO)


class TestRealDataLoading:
    """Feature: Load and query the bundled Kaggle datasets."""

    def test_matches_and_players_loaded(self, kg):
        # Given the bundled data
        # When the knowledge graph is built
        # Then it contains a substantial number of matches and players
        assert len(kg.matches) > 1000
        assert len(kg.players) > 1000

    def test_all_match_sources_present(self, kg):
        # Then every match dataset contributed records
        sources = {m.source for m in kg.matches}
        assert EXPECTED_SOURCES.issubset(sources)

    def test_competitions_include_three_majors(self, kg):
        comps = set(kg.competitions())
        assert COMP_BRASILEIRAO in comps
        assert COMP_COPA_BRASIL in comps
        assert COMP_LIBERTADORES in comps

    def test_matches_have_normalised_fields(self, kg):
        # Then scored matches expose integer goals and a date
        scored = [m for m in kg.matches if m.has_score]
        assert scored
        sample = scored[0]
        assert isinstance(sample.home_goal, int)
        assert isinstance(sample.away_goal, int)
        assert sample.home_key and sample.away_key

    def test_utf8_team_names_preserved(self, kg):
        # Then accented Brazilian names survive loading
        teams = " ".join(kg.teams())
        assert any(ch in teams for ch in "ãâáàéêíóôõúç")

    def test_loading_is_reasonably_fast(self):
        # Then a fresh load completes well within interactive limits
        from brazilian_soccer_mcp import load_knowledge_graph
        start = time.time()
        graph = load_knowledge_graph()
        elapsed = time.time() - start
        assert graph.matches
        assert elapsed < 15.0
