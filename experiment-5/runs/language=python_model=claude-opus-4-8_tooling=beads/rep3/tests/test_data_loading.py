"""
==============================================================================
File: tests/test_data_loading.py
==============================================================================
CONTEXT
-------
BDD tests for the data layer / knowledge graph construction. Confirms all six
CSV files load, parse and index correctly, and that the de-duplication strategy
(primary-flag) yields exactly one Brasileirão source per overlapping season.
==============================================================================
"""

from datetime import date

from brazilian_soccer.data_loader import parse_date


class TestDateParsing:
    def test_iso_format(self):
        # Given an ISO date string / When parsed / Then a date is returned
        assert parse_date("2023-09-24") == date(2023, 9, 24)

    def test_brazilian_format(self):
        # Given a DD/MM/YYYY Brazilian date
        assert parse_date("29/03/2003") == date(2003, 3, 29)

    def test_datetime_with_time(self):
        # Given a datetime with a time component
        assert parse_date("2012-05-19 18:30:00") == date(2012, 5, 19)

    def test_missing_or_invalid(self):
        # Given empty / NA values / Then None is returned (no crash)
        assert parse_date("") is None
        assert parse_date("NA") is None
        assert parse_date(None) is None


class TestGraphLoading:
    def test_all_six_files_contribute(self, graph):
        # Given the loaded graph
        # When inspecting the source files
        # Then all six datasets are represented
        sources = {m.source for m in graph.matches}
        expected = {
            "Brasileirao_Matches.csv",
            "Brazilian_Cup_Matches.csv",
            "Libertadores_Matches.csv",
            "BR-Football-Dataset.csv",
            "novo_campeonato_brasileiro.csv",
        }
        assert expected.issubset(sources)
        assert len(graph.players) > 18000  # fifa_data.csv loaded

    def test_matches_and_players_counts_are_substantial(self, graph):
        # Given the graph / Then it holds tens of thousands of matches/players
        assert len(graph.matches) > 20000
        assert len(graph.players) > 18000

    def test_competitions_present(self, graph):
        # Given the graph / Then the three core competitions exist
        comps = set(graph.matches_by_competition.keys())
        assert {"Brasileirão", "Copa do Brasil", "Libertadores"} <= comps

    def test_primary_dedup_one_brasileirao_source_per_season(self, graph):
        # Given overlapping Brasileirão sources (2012-2019 appear twice)
        # When filtering primary matches for an overlap season
        # Then exactly one source supplies them (no double counting)
        primary_2019 = [
            m
            for m in graph.matches_by_season[2019]
            if m.competition == "Brasileirão" and m.primary
        ]
        sources = {m.source for m in primary_2019}
        assert sources == {"Brasileirao_Matches.csv"}
        # A full 20-team double round-robin = 380 matches.
        assert len(primary_2019) == 380

    def test_team_index_lookup(self, graph):
        # Given the team index / When looking up Flamengo / Then matches exist
        assert len(graph.matches_for_team("Flamengo")) > 0
