"""
================================================================================
tests.test_data_loading
================================================================================

CONTEXT
-------
BDD scenarios covering Success Criteria > Data Coverage: all six CSV files load,
are unified into the matches/players tables, and team-name normalisation behaves
correctly (the trickiest part of the data quality requirements).
================================================================================
"""

from brazilian_soccer_mcp import data_loader
from brazilian_soccer_mcp.normalize import (
    canonical_norm,
    canonical_team_name,
    parse_date,
    team_matches,
)


class TestDataLoads:
    """Feature: All provided datasets are loadable and queryable."""

    def test_all_match_files_contribute_rows(self, kg):
        # Given the match data is loaded
        # When inspecting the unified matches table
        sources = set(kg.matches["source"].unique())
        # Then every match CSV is represented
        expected = {
            "Brasileirao_Matches.csv",
            "Brazilian_Cup_Matches.csv",
            "Libertadores_Matches.csv",
            "novo_campeonato_brasileiro.csv",
            "BR-Football-Dataset.csv",
        }
        assert expected.issubset(sources)

    def test_players_loaded(self, kg):
        # Given the player data is loaded
        # Then there are thousands of players with the expected columns
        assert len(kg.players) > 15_000
        assert {"Name", "Nationality", "Overall", "Club"}.issubset(kg.players.columns)

    def test_competitions_present(self, kg):
        # When listing competitions
        comps = kg.list_competitions()
        # Then the three headline competitions are present
        assert "Brasileirão Série A" in comps
        assert "Copa do Brasil" in comps
        assert "Copa Libertadores" in comps

    def test_seasons_cover_historical_range(self, kg):
        # Then Brasileirão seasons span the historical + modern files
        seasons = kg.list_seasons("Brasileirão Série A")
        assert min(seasons) <= 2003
        assert max(seasons) >= 2019


class TestNormalization:
    """Feature: Team name variations are normalised consistently."""

    def test_state_suffix_removed_for_display(self):
        assert canonical_team_name("Palmeiras-SP") == "Palmeiras"
        assert canonical_team_name("Flamengo-RJ") == "Flamengo"

    def test_cross_source_spellings_unify(self):
        # "Atletico-MG" and "Atletico Mineiro" are the SAME club
        assert canonical_norm("Atletico-MG") == canonical_norm("Atletico Mineiro")
        assert canonical_norm("Sao Paulo-SP") == canonical_norm("Sao Paulo")

    def test_ambiguous_clubs_stay_distinct(self):
        # The three Atléticos must NOT be merged
        assert canonical_norm("Atletico-MG") != canonical_norm("Atletico-PR")
        assert canonical_norm("Atletico-MG") != canonical_norm("Atletico-GO")

    def test_team_matches_is_accent_and_suffix_insensitive(self):
        assert team_matches("Flamengo", "Flamengo-RJ")
        assert team_matches("sao paulo", "São Paulo-SP")
        assert team_matches("Vasco", "Vasco da Gama-RJ")
        assert not team_matches("Santos", "Sao Paulo")

    def test_date_formats_all_parse(self):
        assert parse_date("2023-09-24").isoformat() == "2023-09-24"
        assert parse_date("2012-05-19 18:30:00").isoformat() == "2012-05-19"
        assert parse_date("29/03/2003").isoformat() == "2003-03-29"
        assert parse_date("NA") is None


def test_no_duplicate_inflation_for_a_full_season(kg):
    """A full Série A season has 20 teams x 38 games -> 380 matches, not inflated."""
    table = kg.standings("Brasileirão Série A", 2019)
    assert len(table) == 20
    assert all(t["played"] == 38 for t in table)
