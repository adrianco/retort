"""BDD-style tests for the Brazilian Soccer MCP data service."""
from brazilian_soccer_mcp import SoccerData, normalized


def test_given_loaded_data_when_searching_a_derby_then_matches_have_required_fields():
    data = SoccerData().load()
    matches = data.search_matches("Flamengo", "Fluminense")
    assert matches
    assert all(match.date and match.competition and match.home_goal is not None for match in matches)


def test_given_state_suffix_when_searching_team_then_names_match_consistently():
    data = SoccerData().load()
    assert normalized("São Paulo-SP") == normalized("Sao Paulo")
    assert data.search_matches("Palmeiras-SP", season=2023) == data.search_matches("Palmeiras", season=2023)


def test_given_team_season_when_calculating_home_record_then_results_reconcile():
    stats = SoccerData().team_statistics("Corinthians", season=2022, competition="Brasileirão", venue="home")
    assert stats["matches"] == stats["wins"] + stats["draws"] + stats["losses"]
    assert stats["goals_for"] >= 0 and stats["points"] == stats["wins"] * 3 + stats["draws"]


def test_given_two_teams_when_comparing_then_every_result_is_accounted_for():
    record = SoccerData().head_to_head("Palmeiras", "Santos", season=2019)
    assert record["matches"] == record["team_a_wins"] + record["team_b_wins"] + record["draws"]


def test_given_player_filters_when_searching_then_returned_players_match_and_are_sorted():
    players = SoccerData().search_players(nationality="Brazil", limit=10)
    assert players and all(player["Nationality"] == "Brazil" for player in players)
    ratings = [int(player["Overall"]) for player in players]
    assert ratings == sorted(ratings, reverse=True)


def test_given_2019_brasileirao_when_calculating_standings_then_flamengo_is_champion():
    table = SoccerData().standings(2019)
    assert table[0]["team"] == "Flamengo"
    assert table[0]["points"] == 90
    assert table[1]["team"] == "Santos"  # wins break the 74-point tie


def test_given_extended_dataset_when_searching_competition_then_extended_columns_are_retained():
    matches = SoccerData().search_matches(competition="Copa do Brasil", season=2023)
    assert any(match.source == "BR-Football-Dataset.csv" for match in matches)
    assert any(match.extras and "total_corners" in match.extras for match in matches)
