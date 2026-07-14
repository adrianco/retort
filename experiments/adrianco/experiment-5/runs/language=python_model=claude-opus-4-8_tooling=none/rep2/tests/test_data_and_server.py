"""
BDD scenarios -- Data loading, name normalization and the MCP server layer.

Feature: Robust data loading and tool integration
    As a maintainer
    I want all six datasets to load and the MCP tools to return formatted text
    So that the server satisfies the data-coverage and integration criteria.
"""

import datetime

from data_loader import load_all, parse_date, parse_int
from team_names import display_name, match_key, names_match


class TestDataCoverage:
    """Scenario: All six datasets load and are queryable."""

    def test_all_files_load(self, kg):
        # Then many thousands of (de-duplicated) matches and players load.
        assert len(kg.matches) > 15000
        assert len(kg.players) > 18000

    def test_overlapping_fixtures_are_deduplicated(self, kg):
        # No (competition, season, home, away) fixture is counted twice.
        seen = set()
        for m in kg.matches:
            if m.season is None or m.home_goal is None:
                continue
            key = (m.competition, m.season, m.home_key, m.away_key)
            assert key not in seen, f"duplicate fixture: {key}"
            seen.add(key)

    def test_every_source_file_contributes(self):
        matches, players = load_all()
        sources = {m.source for m in matches}
        for expected in (
            "Brasileirao_Matches.csv",
            "Brazilian_Cup_Matches.csv",
            "Libertadores_Matches.csv",
            "BR-Football-Dataset.csv",
            "novo_campeonato_brasileiro.csv",
        ):
            assert expected in sources
        assert len(players) > 0


class TestNameNormalization:
    """Scenario: Team names normalize to a canonical, region-aware form."""

    def test_suffix_forms_canonicalize_consistently(self):
        # Different suffix conventions produce the same canonical name + key.
        assert display_name("Palmeiras-SP") == "Palmeiras-SP"
        assert display_name("Palmeiras - SP") == "Palmeiras-SP"
        assert match_key("Palmeiras-SP") == match_key("Palmeiras - SP")

    def test_country_suffix_preserved_as_region(self):
        assert display_name("Nacional (URU)") == "Nacional-URU"
        assert match_key("Nacional (URU)") == "nacional-uru"

    def test_region_is_part_of_identity(self):
        # Distinct clubs sharing a base name are NOT merged.
        assert match_key("America-MG") != match_key("America-RN")
        assert not names_match("Atletico-MG", "Atletico-PR")

    def test_accents_and_spelling_folded(self):
        assert match_key("Grêmio-RS") == match_key("Gremio-RS")
        # "Athletico" (Paranaense) folds onto Atletico but keeps its PR region.
        assert match_key("Athletico-PR") == match_key("Atletico-PR")
        assert match_key("Athletico-PR") != match_key("Atletico-MG")

    def test_region_aware_matching(self):
        # A bare query name matches any region; a regioned query is specific.
        assert names_match("Sao Paulo", "Sao Paulo-SP")
        assert names_match("Atletico", "Atletico-MG")        # bare -> any
        assert not names_match("Atletico-GO", "Atletico-MG")  # specific


class TestParsers:
    """Scenario: Mixed date and number formats are parsed."""

    def test_date_formats(self):
        assert parse_date("2012-05-19 18:30:00") == datetime.date(2012, 5, 19)
        assert parse_date("29/03/2003") == datetime.date(2003, 3, 29)
        assert parse_date("2023-09-24") == datetime.date(2023, 9, 24)
        assert parse_date("") is None

    def test_int_formats(self):
        assert parse_int("2") == 2
        assert parse_int("1.0") == 1
        assert parse_int('"3"') == 3
        assert parse_int("") is None


class TestMcpServerTools:
    """Scenario: The MCP server registers tools that return formatted text."""

    def test_tools_registered_and_callable(self):
        import server  # imports load the knowledge graph once

        # Then the expected tools are registered with the MCP app
        names = {t.name for t in server.mcp._tool_manager.list_tools()}
        for expected in (
            "find_matches", "head_to_head", "team_record", "team_competitions",
            "search_players", "top_brazilian_players", "brazilian_players_by_club",
            "league_standings", "list_seasons", "average_goals",
            "biggest_wins", "best_team_records",
        ):
            assert expected in names

    def test_find_matches_tool_returns_text(self):
        import server
        out = server.find_matches(team="Flamengo", opponent="Fluminense", limit=5)
        assert isinstance(out, str) and "Flamengo" in out

    def test_standings_tool_returns_text(self):
        import server
        out = server.league_standings(competition="Brasileirao", season=2019)
        assert "Champion" in out
        assert "Flamengo" in out
